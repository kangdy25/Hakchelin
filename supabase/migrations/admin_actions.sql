-- 1. 메뉴 삭제 RLS 정책 추가 (관리자만 삭제 가능)
DROP POLICY IF EXISTS "Admins can delete menus" ON public.menus;
CREATE POLICY "Admins can delete menus" ON public.menus FOR DELETE USING (public.is_admin(auth.uid()));

-- 2. 식사 완료 처리 RPC (관리자가 특정 식권을 사용 완료 처리)
CREATE OR REPLACE FUNCTION public.admin_use_ticket(
  p_reservation_id UUID
) RETURNS void AS $$
DECLARE
  v_reservation public.reservations%ROWTYPE;
BEGIN
  -- 관리자 권한 확인
  IF NOT public.is_admin(auth.uid()) THEN
    RAISE EXCEPTION '관리자 권한이 필요합니다.';
  END IF;

  -- 예약 정보 조회 및 잠금
  SELECT * INTO v_reservation
  FROM public.reservations
  WHERE id = p_reservation_id
  FOR UPDATE;

  IF v_reservation.id IS NULL THEN
    RAISE EXCEPTION '예약 내역을 찾을 수 없습니다.';
  END IF;

  IF v_reservation.status <> 'reserved' THEN
    RAISE EXCEPTION '예약 완료 상태인 식권만 사용 처리할 수 있습니다. 현재 상태: %', v_reservation.status;
  END IF;

  -- 사용 완료로 업데이트
  UPDATE public.reservations
  SET status = 'used'
  WHERE id = p_reservation_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- 3. 예약 강제 취소 및 환불 RPC (관리자 권한)
CREATE OR REPLACE FUNCTION public.admin_cancel_ticket(
  p_reservation_id UUID
) RETURNS void AS $$
DECLARE
  v_reservation public.reservations%ROWTYPE;
BEGIN
  -- 관리자 권한 확인
  IF NOT public.is_admin(auth.uid()) THEN
    RAISE EXCEPTION '관리자 권한이 필요합니다.';
  END IF;

  -- 예약 정보 조회 및 잠금
  SELECT * INTO v_reservation
  FROM public.reservations
  WHERE id = p_reservation_id
  FOR UPDATE;

  IF v_reservation.id IS NULL THEN
    RAISE EXCEPTION '예약 내역을 찾을 수 없습니다.';
  END IF;

  IF v_reservation.status <> 'reserved' THEN
    RAISE EXCEPTION '예약 완료 상태인 식권만 취소할 수 있습니다. 현재 상태: %', v_reservation.status;
  END IF;

  -- 1. 취소 상태로 변경
  UPDATE public.reservations
  SET status = 'cancelled'
  WHERE id = p_reservation_id;

  -- 2. 포인트 환불
  UPDATE public.users
  SET current_point = current_point + v_reservation.total_price
  WHERE id = v_reservation.user_id;

  -- 3. 트랜잭션 로그 기록
  INSERT INTO public.transactions (user_id, amount, type, description)
  VALUES (v_reservation.user_id, v_reservation.total_price, 'refund', '예약 취소 환불 (관리자)');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- 4. 사용자 포인트 강제 조정 RPC (관리자 권한)
CREATE OR REPLACE FUNCTION public.admin_adjust_points(
  p_user_id UUID,
  p_amount INTEGER,
  p_description TEXT
) RETURNS void AS $$
DECLARE
  v_user_exists BOOLEAN;
  v_type TEXT;
BEGIN
  -- 관리자 권한 확인
  IF NOT public.is_admin(auth.uid()) THEN
    RAISE EXCEPTION '관리자 권한이 필요합니다.';
  END IF;

  -- 사용자 존재 확인
  SELECT EXISTS(SELECT 1 FROM public.users WHERE id = p_user_id) INTO v_user_exists;
  IF NOT v_user_exists THEN
    RAISE EXCEPTION '사용자를 찾을 수 없습니다.';
  END IF;

  -- 포인트 타입 결정
  IF p_amount > 0 THEN
    v_type := 'charge';
  ELSE
    v_type := 'deduct';
  END IF;

  -- 포인트 업데이트
  UPDATE public.users
  SET current_point = current_point + p_amount
  WHERE id = p_user_id;

  -- 트랜잭션 기록 생성
  INSERT INTO public.transactions (user_id, amount, type, description)
  VALUES (p_user_id, p_amount, v_type, COALESCE(p_description, '관리자 포인트 조정'));
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- 5. 사용자 권한 변경 RPC (관리자 권한)
CREATE OR REPLACE FUNCTION public.admin_update_user_role(
  p_user_id UUID,
  p_role TEXT
) RETURNS void AS $$
DECLARE
  v_user_exists BOOLEAN;
BEGIN
  -- 관리자 권한 확인
  IF NOT public.is_admin(auth.uid()) THEN
    RAISE EXCEPTION '관리자 권한이 필요합니다.';
  END IF;

  -- 권한 값 확인
  IF p_role NOT IN ('student', 'admin') THEN
    RAISE EXCEPTION '올바르지 않은 권한입니다. (student 또는 admin 필요)';
  END IF;

  -- 사용자 존재 확인
  SELECT EXISTS(SELECT 1 FROM public.users WHERE id = p_user_id) INTO v_user_exists;
  IF NOT v_user_exists THEN
    RAISE EXCEPTION '사용자를 찾을 수 없습니다.';
  END IF;

  -- 권한 업데이트
  UPDATE public.users
  SET role = p_role
  WHERE id = p_user_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;
