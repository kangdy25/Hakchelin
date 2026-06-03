CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. Users Table (auth.users와 1:1 매핑)
CREATE TABLE public.users (
  id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
  role TEXT CHECK (role IN ('student', 'admin')) DEFAULT 'student',
  student_id TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  current_point INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS for Users
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own data" ON public.users FOR SELECT USING (auth.uid() = id);
CREATE OR REPLACE FUNCTION public.is_admin(p_user_id UUID)
RETURNS BOOLEAN AS $$
BEGIN
  RETURN EXISTS (
    SELECT 1
    FROM public.users
    WHERE id = p_user_id
      AND role = 'admin'
  );

END;
$$ LANGUAGE plpgsql SECURITY DEFINER STABLE SET search_path = public;

CREATE POLICY "Admins can view all users" ON public.users FOR SELECT USING (public.is_admin(auth.uid()));
CREATE POLICY "Admins can update users" ON public.users FOR UPDATE USING (public.is_admin(auth.uid()));

-- 2. Menus Table
CREATE TABLE public.menus (
  id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::TEXT,
  day_of_week TEXT CHECK (day_of_week IN ('mon', 'tue', 'wed', 'thu', 'fri')),
  type TEXT CHECK (type IN ('한식', '일품', '포장')),
  title_ko TEXT NOT NULL,
  title_en TEXT NOT NULL,
  price INTEGER DEFAULT 4500,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS for Menus
ALTER TABLE public.menus ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Anyone can view menus" ON public.menus FOR SELECT USING (true);
CREATE POLICY "Admins can insert menus" ON public.menus FOR INSERT WITH CHECK (public.is_admin(auth.uid()));
CREATE POLICY "Admins can update menus" ON public.menus FOR UPDATE USING (public.is_admin(auth.uid()));

-- 3. Reservations Table
CREATE TABLE public.reservations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
  menu_id TEXT REFERENCES public.menus(id) ON DELETE CASCADE,
  options JSONB NOT NULL DEFAULT '{}'::jsonb,
  total_price INTEGER NOT NULL,
  status TEXT CHECK (status IN ('reserved', 'used', 'cancelled')) DEFAULT 'reserved',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS for Reservations
ALTER TABLE public.reservations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own reservations" ON public.reservations FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Admins can view all reservations" ON public.reservations FOR SELECT USING (public.is_admin(auth.uid()));

-- 4. Transactions Table
CREATE TABLE public.transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
  amount INTEGER NOT NULL,
  type TEXT CHECK (type IN ('charge', 'deduct', 'refund')),
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS for Transactions
ALTER TABLE public.transactions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own transactions" ON public.transactions FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Admins can view all transactions" ON public.transactions FOR SELECT USING (public.is_admin(auth.uid()));

-- 5. Point Payment Orders
CREATE TABLE public.point_orders (
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

-- 6. DB Function for Reservation and Point Deduction (Atomic Transaction)
DROP FUNCTION IF EXISTS public.reserve_menu(UUID, TEXT, JSONB, INTEGER);
DROP FUNCTION IF EXISTS public.reserve_menu(UUID, UUID, JSONB, INTEGER);

CREATE OR REPLACE FUNCTION reserve_menu(
  p_user_id UUID,
  p_menu_id TEXT,
  p_options JSONB,
  p_total_price INTEGER
) RETURNS void AS $$
DECLARE
  v_current_point INTEGER;
  v_base_price INTEGER;
  v_total_price INTEGER;
BEGIN
  IF auth.uid() IS NOT NULL AND auth.uid() <> p_user_id THEN
    RAISE EXCEPTION '본인 계정으로만 예약할 수 있습니다.';
  END IF;

  SELECT price INTO v_base_price
  FROM public.menus
  WHERE id = p_menu_id;

  IF v_base_price IS NULL THEN
    RAISE EXCEPTION '메뉴를 찾을 수 없습니다.';
  END IF;

  v_total_price := v_base_price + CASE
    WHEN COALESCE((p_options->>'main')::INTEGER, 0) = 1 THEN 1000
    ELSE 0
  END;

  IF p_total_price <> v_total_price THEN
    RAISE EXCEPTION '결제 금액이 메뉴 가격과 일치하지 않습니다.';
  END IF;

  -- 사용자 포인트 잠금 (Row-level lock)
  SELECT current_point INTO v_current_point
  FROM public.users
  WHERE id = p_user_id
  FOR UPDATE;

  IF v_current_point IS NULL THEN
    RAISE EXCEPTION '사용자 프로필이 없습니다. public.users row를 먼저 생성해야 합니다.';
  END IF;

  -- 포인트 확인
  IF v_current_point < v_total_price THEN
    RAISE EXCEPTION 'Insufficient points';
  END IF;

  -- 포인트 차감
  UPDATE public.users
  SET current_point = current_point - v_total_price
  WHERE id = p_user_id;

  -- 예약 내역 생성
  INSERT INTO public.reservations (user_id, menu_id, options, total_price)
  VALUES (p_user_id, p_menu_id, p_options, v_total_price);

  -- 트랜잭션 기록 생성
  INSERT INTO public.transactions (user_id, amount, type, description)
  VALUES (p_user_id, -v_total_price, 'deduct', '메뉴 예약');
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- 7. Trigger to Create User Record on Supabase Auth Signup
CREATE OR REPLACE FUNCTION public.handle_new_user() 
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.users (id, student_id, name, role)
  VALUES (
    new.id,
    COALESCE(NULLIF(new.raw_user_meta_data->>'student_id', ''), 'student-' || LEFT(new.id::TEXT, 8)),
    COALESCE(NULLIF(new.raw_user_meta_data->>'name', ''), '학생'),
    COALESCE(NULLIF(new.raw_user_meta_data->>'role', ''), 'student')
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

-- 초기 데이터 세팅 예시
INSERT INTO public.menus (id, day_of_week, type, title_ko, title_en, price) VALUES
('1', 'mon', '한식', 'A. 매콤 제육 쌈밥 정식', 'A. Spicy Pork Wrap Set', 4500),
('2', 'mon', '일품', 'B. 단짠 간장 돼지 덮밥', 'B. Soy Sauce Pork Bowl', 4500),
('3', 'mon', '포장', 'C. 바베큐 샌드위치 팩', 'C. BBQ Sandwich Pack', 4500),
('4', 'tue', '일품', 'A. 춘천식 닭갈비 정식', 'A. Chuncheon Chicken Stir-fry', 4500),
('5', 'tue', '한식', 'B. 치킨 마요 덮밥', 'B. Chicken Mayo Bowl', 4500),
('10', 'tue', '포장', 'C. 리코타 치즈 샐러드', 'C. Ricotta Cheese Salad', 4500),
('6', 'wed', '포장', 'A. 수제 등심 돈까스', 'A. Handmade Pork Cutlet', 4500),
('11', 'wed', '한식', 'B. 꼬치어묵 우동', 'B. Fish Cake Udon', 4500),
('12', 'wed', '일품', 'C. 삼각김밥&라면 세트', 'C. Triangle Kimbap & Ramen Set', 4500),
('7', 'thu', '한식', 'A. 소불고기 버섯 전골', 'A. Bulgogi Mushroom Hot Pot', 4500),
('13', 'thu', '일품', 'B. 나물 비빔밥', 'B. Vegetable Bibimbap', 4500),
('14', 'thu', '포장', 'C. 불고기 베이크 빵', 'C. Bulgogi Baked Bread', 4500),
('8', 'fri', '일품', 'A. 매콤 오징어 볶음', 'A. Spicy Stir-fried Squid', 4500),
('9', 'fri', '일품', 'B. 얼큰 해물 짬뽕', 'B. Spicy Seafood Noodle', 5500),
('15', 'fri', '포장', 'C. 크래미 샌드위치 팩', 'C. Crab Meat Sandwich Pack', 4500);
