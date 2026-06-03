-- DB Function for Reservation Cancellation and Refund
CREATE OR REPLACE FUNCTION cancel_reservation(
  p_reservation_id UUID,
  p_user_id UUID
) RETURNS void AS $$
DECLARE
  v_reservation public.reservations%ROWTYPE;
BEGIN
  -- Verify ownership
  IF auth.uid() IS NOT NULL AND auth.uid() <> p_user_id THEN
    RAISE EXCEPTION '본인 예약만 취소할 수 있습니다.';
  END IF;

  -- Select and lock reservation row
  SELECT * INTO v_reservation
  FROM public.reservations
  WHERE id = p_reservation_id AND user_id = p_user_id
  FOR UPDATE;

  -- Validation
  IF v_reservation.id IS NULL THEN
    RAISE EXCEPTION '예약을 찾을 수 없습니다.';
  END IF;

  IF v_reservation.status <> 'reserved' THEN
    RAISE EXCEPTION '이미 사용되었거나 취소된 예약입니다.';
  END IF;

  -- 1. Update status
  UPDATE public.reservations
  SET status = 'cancelled'
  WHERE id = p_reservation_id;

  -- 2. Refund points to user
  UPDATE public.users
  SET current_point = current_point + v_reservation.total_price
  WHERE id = p_user_id;

  -- 3. Record transaction log
  INSERT INTO public.transactions (user_id, amount, type, description)
  VALUES (p_user_id, v_reservation.total_price, 'refund', '예약 취소 환불');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;
