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
CREATE POLICY "Admins can view all users" ON public.users FOR SELECT USING (
  EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'admin')
);
CREATE POLICY "Admins can update users" ON public.users FOR UPDATE USING (
  EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'admin')
);

-- 2. Menus Table
CREATE TABLE public.menus (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
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
CREATE POLICY "Admins can insert menus" ON public.menus FOR INSERT WITH CHECK (
  EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'admin')
);
CREATE POLICY "Admins can update menus" ON public.menus FOR UPDATE USING (
  EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'admin')
);

-- 3. Reservations Table
CREATE TABLE public.reservations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
  menu_id UUID REFERENCES public.menus(id) ON DELETE CASCADE,
  options JSONB NOT NULL DEFAULT '{}'::jsonb,
  total_price INTEGER NOT NULL,
  status TEXT CHECK (status IN ('reserved', 'used', 'cancelled')) DEFAULT 'reserved',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS for Reservations
ALTER TABLE public.reservations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own reservations" ON public.reservations FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Admins can view all reservations" ON public.reservations FOR SELECT USING (
  EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'admin')
);

-- 4. Transactions Table
CREATE TABLE public.transactions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
  amount INTEGER NOT NULL,
  type TEXT CHECK (type IN ('charge', 'deduct', 'refund')),
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS for Transactions
ALTER TABLE public.transactions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users can view own transactions" ON public.transactions FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Admins can view all transactions" ON public.transactions FOR SELECT USING (
  EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'admin')
);

-- 5. DB Function for Reservation and Point Deduction (Atomic Transaction)
CREATE OR REPLACE FUNCTION reserve_menu(
  p_user_id UUID,
  p_menu_id UUID,
  p_options JSONB,
  p_total_price INTEGER
) RETURNS void AS $$
DECLARE
  v_current_point INTEGER;
BEGIN
  -- 사용자 포인트 잠금 (Row-level lock)
  SELECT current_point INTO v_current_point
  FROM public.users
  WHERE id = p_user_id
  FOR UPDATE;

  -- 포인트 확인
  IF v_current_point < p_total_price THEN
    RAISE EXCEPTION 'Insufficient points';
  END IF;

  -- 포인트 차감
  UPDATE public.users
  SET current_point = current_point - p_total_price
  WHERE id = p_user_id;

  -- 예약 내역 생성
  INSERT INTO public.reservations (user_id, menu_id, options, total_price)
  VALUES (p_user_id, p_menu_id, p_options, p_total_price);

  -- 트랜잭션 기록 생성
  INSERT INTO public.transactions (user_id, amount, type, description)
  VALUES (p_user_id, -p_total_price, 'deduct', '메뉴 예약');

END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 6. Trigger to Create User Record on Supabase Auth Signup
CREATE OR REPLACE FUNCTION public.handle_new_user() 
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.users (id, student_id, name, role)
  VALUES (
    new.id,
    new.raw_user_meta_data->>'student_id',
    new.raw_user_meta_data->>'name',
    COALESCE(new.raw_user_meta_data->>'role', 'student')
  );
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

-- 초기 데이터 세팅 예시
INSERT INTO public.menus (day_of_week, type, title_ko, title_en, price) VALUES 
('mon', '한식', '매콤 제육 쌈밥 정식', 'Spicy Pork Wrap Set', 4500),
('tue', '일품', '춘천식 닭갈비 정식', 'Chuncheon Chicken Stir-fry', 4500),
('wed', '포장', '수제 등심 돈까스', 'Handmade Pork Cutlet', 4500),
('thu', '한식', '소불고기 버섯 전골', 'Bulgogi Mushroom Hot Pot', 4500),
('fri', '일품', '매콤 오징어 볶음', 'Spicy Stir-fried Squid', 4500);
