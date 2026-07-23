-- Date-based meal operations, capacity controls, and immutable reservation history.
-- Existing weekday menus are moved to their next matching weekday so legacy demo data
-- remains available after this migration.

ALTER TABLE public.menus
  ADD COLUMN IF NOT EXISTS meal_date DATE,
  ADD COLUMN IF NOT EXISTS meal_time TIME NOT NULL DEFAULT '12:00:00',
  ADD COLUMN IF NOT EXISTS capacity INTEGER NOT NULL DEFAULT 100 CHECK (capacity > 0),
  ADD COLUMN IF NOT EXISTS reservation_deadline TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS deposit_amount INTEGER NOT NULL DEFAULT 1000 CHECK (deposit_amount >= 0),
  ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT true;

-- `meal_date` is now the source of truth; the legacy weekday value is retained only
-- for backwards compatibility and must not block weekend/holiday meal publication.
ALTER TABLE public.menus DROP CONSTRAINT IF EXISTS menus_day_of_week_check;

-- Normalize the original Korean labels to the UI/API codes used by Nuxt.
ALTER TABLE public.menus DROP CONSTRAINT IF EXISTS menus_type_check;
UPDATE public.menus
SET type = CASE type
  WHEN '한식' THEN 'kr'
  WHEN '일품' THEN 'premium'
  WHEN '포장' THEN 'takeout'
  ELSE type
END;
ALTER TABLE public.menus
  ADD CONSTRAINT menus_type_check CHECK (type IN ('kr', 'premium', 'takeout'));

UPDATE public.menus
SET meal_date = CURRENT_DATE + ((
  CASE day_of_week
    WHEN 'mon' THEN 1 WHEN 'tue' THEN 2 WHEN 'wed' THEN 3
    WHEN 'thu' THEN 4 WHEN 'fri' THEN 5 ELSE 1
  END - EXTRACT(ISODOW FROM CURRENT_DATE)::INTEGER + 7
) % 7)
WHERE meal_date IS NULL;

ALTER TABLE public.menus
  ALTER COLUMN meal_date SET NOT NULL;

UPDATE public.menus
SET reservation_deadline = (meal_date + meal_time) - INTERVAL '1 hour'
WHERE reservation_deadline IS NULL;

ALTER TABLE public.menus
  ALTER COLUMN reservation_deadline SET NOT NULL;
ALTER TABLE public.menus
  DROP CONSTRAINT IF EXISTS menus_deadline_before_meal_check;
ALTER TABLE public.menus
  ADD CONSTRAINT menus_deadline_before_meal_check
  CHECK (reservation_deadline < (meal_date + meal_time));

CREATE INDEX IF NOT EXISTS menus_active_date_idx
  ON public.menus (meal_date, meal_time) WHERE is_active = true;

ALTER TABLE public.reservations
  ADD COLUMN IF NOT EXISTS meal_date DATE,
  ADD COLUMN IF NOT EXISTS meal_time TIME,
  ADD COLUMN IF NOT EXISTS menu_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN IF NOT EXISTS deposit_amount INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS refunded_amount INTEGER NOT NULL DEFAULT 0,
  -- Existing records may predate the one-meal rule. New reservations opt in.
  ADD COLUMN IF NOT EXISTS enforces_meal_limit BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS used_at TIMESTAMPTZ;

UPDATE public.reservations r
SET
  meal_date = m.meal_date,
  meal_time = m.meal_time,
  deposit_amount = m.deposit_amount,
  menu_snapshot = jsonb_build_object(
    'title_ko', m.title_ko,
    'title_en', m.title_en,
    'type', m.type,
    'price', m.price,
    'meal_date', m.meal_date,
    'meal_time', m.meal_time
  )
FROM public.menus m
WHERE r.menu_id = m.id AND r.meal_date IS NULL;

-- A menu must never erase paid reservation history. Retire it instead of deleting it.
ALTER TABLE public.reservations
  DROP CONSTRAINT IF EXISTS reservations_menu_id_fkey;
ALTER TABLE public.reservations
  ADD CONSTRAINT reservations_menu_id_fkey
  FOREIGN KEY (menu_id) REFERENCES public.menus(id) ON DELETE RESTRICT;

ALTER TABLE public.reservations
  DROP CONSTRAINT IF EXISTS reservations_status_check;
ALTER TABLE public.reservations
  ADD CONSTRAINT reservations_status_check
  CHECK (status IN ('reserved', 'used', 'cancelled', 'no_show'));

CREATE UNIQUE INDEX IF NOT EXISTS reservations_one_meal_per_user_idx
  ON public.reservations (user_id, meal_date, meal_time)
  WHERE status IN ('reserved', 'used') AND enforces_meal_limit = true;
CREATE INDEX IF NOT EXISTS reservations_menu_status_idx
  ON public.reservations (menu_id, status);

-- The former delete policy is intentionally removed. The UI now performs a soft delete.
DROP POLICY IF EXISTS "Admins can delete menus" ON public.menus;

CREATE OR REPLACE FUNCTION public.reserve_menu(
  p_user_id UUID,
  p_menu_id TEXT,
  p_options JSONB,
  p_total_price INTEGER
) RETURNS void AS $$
DECLARE
  v_menu public.menus%ROWTYPE;
  v_current_point INTEGER;
  v_total_price INTEGER;
  v_reserved_count INTEGER;
  v_main_count INTEGER := COALESCE((p_options->>'main')::INTEGER, 0);
  v_rice_amount INTEGER := COALESCE((p_options->>'rice')::INTEGER, 0);
BEGIN
  IF auth.uid() IS NULL OR auth.uid() <> p_user_id THEN
    RAISE EXCEPTION '본인 계정으로만 예약할 수 있습니다.';
  END IF;

  IF v_main_count NOT IN (0, 1) OR v_rice_amount NOT IN (0, 1, 2) THEN
    RAISE EXCEPTION '올바르지 않은 메뉴 옵션입니다.';
  END IF;

  -- Locking the menu row serializes capacity checks for this meal.
  SELECT * INTO v_menu FROM public.menus WHERE id = p_menu_id FOR UPDATE;
  IF v_menu.id IS NULL OR NOT v_menu.is_active THEN
    RAISE EXCEPTION '예약할 수 없는 메뉴입니다.';
  END IF;
  IF CURRENT_DATE > v_menu.meal_date OR NOW() >= v_menu.reservation_deadline THEN
    RAISE EXCEPTION '예약 마감 시간이 지났습니다.';
  END IF;

  SELECT COUNT(*) INTO v_reserved_count
  FROM public.reservations
  WHERE menu_id = p_menu_id AND status = 'reserved';
  IF v_reserved_count >= v_menu.capacity THEN
    RAISE EXCEPTION '예약 가능 수량이 모두 소진되었습니다.';
  END IF;

  IF EXISTS (
    SELECT 1 FROM public.reservations
    WHERE user_id = p_user_id
      AND meal_date = v_menu.meal_date
      AND meal_time = v_menu.meal_time
      AND status IN ('reserved', 'used')
  ) THEN
    RAISE EXCEPTION '해당 식사 시간에는 이미 예약한 식권이 있습니다.';
  END IF;

  v_total_price := v_menu.price + (v_main_count * 1000) + v_menu.deposit_amount;
  IF p_total_price <> v_total_price THEN
    RAISE EXCEPTION '결제 금액이 메뉴 가격과 일치하지 않습니다.';
  END IF;

  SELECT current_point INTO v_current_point FROM public.users WHERE id = p_user_id FOR UPDATE;
  IF v_current_point IS NULL THEN
    RAISE EXCEPTION '사용자 프로필이 없습니다.';
  END IF;
  IF v_current_point < v_total_price THEN
    RAISE EXCEPTION 'Insufficient points';
  END IF;

  UPDATE public.users SET current_point = current_point - v_total_price WHERE id = p_user_id;
  INSERT INTO public.reservations (
    user_id, menu_id, options, total_price, meal_date, meal_time, deposit_amount, menu_snapshot, enforces_meal_limit
  ) VALUES (
    p_user_id, p_menu_id, p_options, v_total_price, v_menu.meal_date, v_menu.meal_time,
    v_menu.deposit_amount,
    jsonb_build_object(
      'title_ko', v_menu.title_ko, 'title_en', v_menu.title_en, 'type', v_menu.type,
      'price', v_menu.price, 'meal_date', v_menu.meal_date, 'meal_time', v_menu.meal_time
    ), true
  );
  INSERT INTO public.transactions (user_id, amount, type, description)
  VALUES (p_user_id, -v_total_price, 'deduct', '메뉴 예약');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

CREATE OR REPLACE FUNCTION public.cancel_reservation(
  p_reservation_id UUID,
  p_user_id UUID
) RETURNS void AS $$
DECLARE
  v_reservation public.reservations%ROWTYPE;
  v_deadline TIMESTAMPTZ;
  v_refund_amount INTEGER;
BEGIN
  IF auth.uid() IS NULL OR auth.uid() <> p_user_id THEN
    RAISE EXCEPTION '본인 예약만 취소할 수 있습니다.';
  END IF;

  SELECT * INTO v_reservation FROM public.reservations
  WHERE id = p_reservation_id AND user_id = p_user_id FOR UPDATE;
  IF v_reservation.id IS NULL OR v_reservation.status <> 'reserved' THEN
    RAISE EXCEPTION '취소할 수 있는 예약이 아닙니다.';
  END IF;

  SELECT reservation_deadline INTO v_deadline FROM public.menus WHERE id = v_reservation.menu_id;
  v_refund_amount := CASE
    WHEN v_deadline IS NOT NULL AND NOW() >= v_deadline
      THEN GREATEST(v_reservation.total_price - v_reservation.deposit_amount, 0)
    ELSE v_reservation.total_price
  END;

  UPDATE public.reservations
  SET status = 'cancelled', cancelled_at = NOW(), refunded_amount = v_refund_amount
  WHERE id = p_reservation_id;
  UPDATE public.users SET current_point = current_point + v_refund_amount WHERE id = p_user_id;
  INSERT INTO public.transactions (user_id, amount, type, description)
  VALUES (p_user_id, v_refund_amount, 'refund',
    CASE WHEN v_refund_amount = v_reservation.total_price THEN '예약 취소 전액 환불' ELSE '예약 마감 후 취소 (예약금 제외 환불)' END);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

CREATE OR REPLACE FUNCTION public.admin_use_ticket(p_reservation_id UUID) RETURNS void AS $$
DECLARE v_reservation public.reservations%ROWTYPE;
BEGIN
  IF NOT public.is_admin(auth.uid()) THEN RAISE EXCEPTION '관리자 권한이 필요합니다.'; END IF;
  SELECT * INTO v_reservation FROM public.reservations WHERE id = p_reservation_id FOR UPDATE;
  IF v_reservation.id IS NULL OR v_reservation.status <> 'reserved' THEN RAISE EXCEPTION '사용 처리할 수 있는 식권이 아닙니다.'; END IF;
  UPDATE public.reservations SET status = 'used', used_at = NOW() WHERE id = p_reservation_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

CREATE OR REPLACE FUNCTION public.admin_cancel_ticket(p_reservation_id UUID) RETURNS void AS $$
DECLARE v_reservation public.reservations%ROWTYPE;
BEGIN
  IF NOT public.is_admin(auth.uid()) THEN RAISE EXCEPTION '관리자 권한이 필요합니다.'; END IF;
  SELECT * INTO v_reservation FROM public.reservations WHERE id = p_reservation_id FOR UPDATE;
  IF v_reservation.id IS NULL OR v_reservation.status <> 'reserved' THEN RAISE EXCEPTION '취소할 수 있는 식권이 아닙니다.'; END IF;
  UPDATE public.reservations SET status = 'cancelled', cancelled_at = NOW(), refunded_amount = v_reservation.total_price WHERE id = p_reservation_id;
  UPDATE public.users SET current_point = current_point + v_reservation.total_price WHERE id = v_reservation.user_id;
  INSERT INTO public.transactions (user_id, amount, type, description)
  VALUES (v_reservation.user_id, v_reservation.total_price, 'refund', '예약 취소 전액 환불 (관리자)');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- Runs after meal_time + 1 hour. It is only callable by the scheduler/service
-- role; ordinary browser clients cannot change reservations to no-show.
CREATE OR REPLACE FUNCTION public.process_no_shows() RETURNS INTEGER AS $$
DECLARE v_reservation public.reservations%ROWTYPE; v_count INTEGER := 0; v_refund INTEGER;
BEGIN
  IF auth.role() NOT IN ('service_role', 'postgres') THEN
    RAISE EXCEPTION '서비스 작업에서만 노쇼를 처리할 수 있습니다.';
  END IF;
  FOR v_reservation IN
    SELECT * FROM public.reservations
    WHERE status = 'reserved' AND (meal_date + meal_time + INTERVAL '1 hour') <= NOW()
    FOR UPDATE
  LOOP
    v_refund := GREATEST(v_reservation.total_price - v_reservation.deposit_amount, 0);
    UPDATE public.reservations SET status = 'no_show', refunded_amount = v_refund, cancelled_at = NOW() WHERE id = v_reservation.id;
    UPDATE public.users SET current_point = current_point + v_refund WHERE id = v_reservation.user_id;
    INSERT INTO public.transactions (user_id, amount, type, description)
    VALUES (v_reservation.user_id, v_refund, 'refund', '노쇼 처리 (예약금 제외 환불)');
    v_count := v_count + 1;
  END LOOP;
  RETURN v_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

REVOKE EXECUTE ON FUNCTION public.process_no_shows() FROM anon, authenticated;

-- Supabase pg_cron invokes this every 15 minutes. The extension is available on
-- Supabase projects; the DO block keeps local environments without it usable.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'pg_cron') THEN
    CREATE EXTENSION IF NOT EXISTS pg_cron;
    PERFORM cron.schedule('hakchelin-process-no-shows', '*/15 * * * *', 'SELECT public.process_no_shows()');
  END IF;
END;
$$;
