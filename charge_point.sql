-- DB Function for Point Charging
CREATE OR REPLACE FUNCTION charge_point(
  p_user_id UUID,
  p_amount INTEGER
) RETURNS void AS $$
DECLARE
  v_updated_user_id UUID;
BEGIN
  IF auth.role() <> 'service_role' THEN
    RAISE EXCEPTION '서버에서만 포인트를 충전할 수 있습니다.';
  END IF;

  IF auth.uid() IS NOT NULL AND auth.uid() <> p_user_id THEN
    RAISE EXCEPTION '본인 계정만 충전할 수 있습니다.';
  END IF;

  IF p_amount <= 0 THEN
    RAISE EXCEPTION '충전 금액은 0보다 커야 합니다.';
  END IF;

  -- 포인트 추가
  UPDATE public.users
  SET current_point = current_point + p_amount
  WHERE id = p_user_id
  RETURNING id INTO v_updated_user_id;

  IF v_updated_user_id IS NULL THEN
    RAISE EXCEPTION '사용자 프로필이 없습니다. public.users row를 먼저 생성해야 합니다.';
  END IF;

  -- 트랜잭션 기록 생성
  INSERT INTO public.transactions (user_id, amount, type, description)
  VALUES (p_user_id, p_amount, 'charge', '포인트 충전');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;
