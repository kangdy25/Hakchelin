-- Point payment schema and functions.
-- Run this in Supabase SQL Editor before testing Toss Payments.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS public.point_orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  order_id TEXT UNIQUE NOT NULL,
  user_id UUID REFERENCES public.users(id) ON DELETE CASCADE NOT NULL,
  amount INTEGER NOT NULL CHECK (amount > 0),
  point_amount INTEGER NOT NULL CHECK (point_amount > 0),
  status TEXT CHECK (status IN ('pending', 'paid', 'failed', 'cancelled')) DEFAULT 'pending',
  payment_key TEXT UNIQUE,
  payment_provider TEXT DEFAULT 'toss',
  paid_at TIMESTAMPTZ,
  toss_response JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.point_orders ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.point_orders
ALTER COLUMN id SET DEFAULT gen_random_uuid();

DROP POLICY IF EXISTS "Users can view own point orders" ON public.point_orders;
DROP POLICY IF EXISTS "Users can create own point orders" ON public.point_orders;
DROP POLICY IF EXISTS "Admins can view all point orders" ON public.point_orders;

CREATE POLICY "Users can view own point orders" ON public.point_orders FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users can create own point orders" ON public.point_orders FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Admins can view all point orders" ON public.point_orders FOR SELECT USING (public.is_admin(auth.uid()));

CREATE OR REPLACE FUNCTION public.create_point_order(
  p_user_id UUID,
  p_amount INTEGER
) RETURNS TABLE (
  order_id TEXT,
  amount INTEGER,
  point_amount INTEGER
) AS $$
DECLARE
  v_order_id TEXT;
BEGIN
  IF auth.uid() IS NOT NULL AND auth.uid() <> p_user_id THEN
    RAISE EXCEPTION '본인 계정만 충전할 수 있습니다.';
  END IF;

  IF p_amount <= 0 THEN
    RAISE EXCEPTION '충전 금액은 0보다 커야 합니다.';
  END IF;

  SELECT 'POINT_' || REPLACE(gen_random_uuid()::TEXT, '-', '') INTO v_order_id;

  INSERT INTO public.point_orders (order_id, user_id, amount, point_amount)
  VALUES (v_order_id, p_user_id, p_amount, p_amount);

  RETURN QUERY
  SELECT po.order_id, po.amount, po.point_amount
  FROM public.point_orders po
  WHERE po.order_id = v_order_id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

CREATE OR REPLACE FUNCTION public.confirm_point_payment(
  p_order_id TEXT,
  p_payment_key TEXT,
  p_toss_response JSONB DEFAULT '{}'::JSONB
) RETURNS TABLE (
  order_id TEXT,
  user_id UUID,
  amount INTEGER,
  point_amount INTEGER,
  status TEXT
) AS $$
DECLARE
  v_order public.point_orders%ROWTYPE;
BEGIN
  IF auth.role() <> 'service_role' THEN
    RAISE EXCEPTION '서버에서만 결제 승인을 완료할 수 있습니다.';
  END IF;

  SELECT *
  INTO v_order
  FROM public.point_orders
  WHERE point_orders.order_id = p_order_id
  FOR UPDATE;

  IF v_order.id IS NULL THEN
    RAISE EXCEPTION '충전 주문을 찾을 수 없습니다.';
  END IF;

  IF v_order.status = 'paid' THEN
    RETURN QUERY
    SELECT po.order_id, po.user_id, po.amount, po.point_amount, po.status
    FROM public.point_orders po
    WHERE po.id = v_order.id;
    RETURN;
  END IF;

  IF v_order.status <> 'pending' THEN
    RAISE EXCEPTION '처리할 수 없는 충전 주문 상태입니다: %', v_order.status;
  END IF;

  UPDATE public.point_orders
  SET
    status = 'paid',
    payment_key = p_payment_key,
    toss_response = p_toss_response,
    paid_at = NOW(),
    updated_at = NOW()
  WHERE id = v_order.id;

  UPDATE public.users
  SET current_point = current_point + v_order.point_amount
  WHERE id = v_order.user_id;

  INSERT INTO public.transactions (user_id, amount, type, description)
  VALUES (v_order.user_id, v_order.point_amount, 'charge', '포인트 충전');

  RETURN QUERY
  SELECT po.order_id, po.user_id, po.amount, po.point_amount, po.status
  FROM public.point_orders po
  WHERE po.id = v_order.id;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;
