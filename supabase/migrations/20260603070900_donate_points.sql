-- 8. 기부 기능 RPC
CREATE OR REPLACE FUNCTION public.donate_points(
  p_user_id UUID,
  p_amount INTEGER
) RETURNS void AS $$
DECLARE
  v_current_point INTEGER;
BEGIN
  -- 본인 확인
  IF auth.uid() IS NOT NULL AND auth.uid() <> p_user_id THEN
    RAISE EXCEPTION '본인 포인트만 기부할 수 있습니다.';
  END IF;

  -- 기부 금액 검증
  IF p_amount <= 0 THEN
    RAISE EXCEPTION '기부 금액은 0보다 커야 합니다.';
  END IF;

  -- 사용자 포인트 확인
  SELECT current_point INTO v_current_point
  FROM public.users
  WHERE id = p_user_id;

  IF v_current_point IS NULL THEN
    RAISE EXCEPTION '사용자를 찾을 수 없습니다.';
  END IF;

  IF v_current_point < p_amount THEN
    RAISE EXCEPTION '포인트가 부족합니다.';
  END IF;

  -- 포인트 차감
  UPDATE public.users
  SET current_point = current_point - p_amount
  WHERE id = p_user_id;

  -- 트랜잭션 기록 생성
  INSERT INTO public.transactions (user_id, amount, type, description)
  VALUES (p_user_id, -p_amount, 'deduct', '마음을 잇는 식탁 기부');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;
