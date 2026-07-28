/**
 * 프런트엔드가 의존하는 API 계약이다.
 * Django OpenAPI 생성 타입을 도입하면 이 파일은 packages/api-client의 생성 결과로 대체한다.
 */

export type UserRole = "student" | "admin";
export type MenuType = "kr" | "premium" | "takeout";
export type ReservationStatus = "reserved" | "used" | "cancelled" | "no_show";
export type TransactionType = "charge" | "deduct" | "refund";

export type MealOptions = {
  rice?: number;
  main?: number;
  [key: string]: number | undefined;
};

export interface User {
  id: string;
  role: UserRole | null;
  student_id: string;
  name: string;
  current_point: number | null;
  created_at?: string | null;
}

export interface Menu {
  id: string;
  day_of_week: string;
  meal_date: string;
  meal_time: string;
  type: MenuType;
  title_ko: string;
  title_en: string;
  price: number;
  capacity: number;
  reservation_deadline: string;
  deposit_amount: number;
  is_active: boolean;
  created_at?: string | null;
}

export interface Reservation {
  id: string;
  user_id: string | null;
  menu_id: string | null;
  options: MealOptions;
  total_price: number;
  status: ReservationStatus | null;
  meal_date?: string | null;
  meal_time?: string | null;
  deposit_amount?: number | null;
  refunded_amount?: number | null;
  menu_snapshot?: {
    title_ko?: string;
    title_en?: string;
    type?: string;
    price?: number;
  } | null;
  created_at: string | null;
  users?: Pick<User, "name" | "student_id"> | null;
  menus?: Pick<Menu, "type" | "title_ko" | "title_en" | "day_of_week" | "price"> | null;
}

export interface Transaction {
  id: string;
  user_id: string | null;
  amount: number;
  type: TransactionType | null;
  description: string | null;
  created_at: string | null;
  users?: Pick<User, "name" | "student_id"> | null;
}

export type CreateMenuInput = Omit<Menu, "created_at">;
export type UpdateMenuInput = Omit<CreateMenuInput, "id">;
