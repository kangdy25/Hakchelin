import type { Database as SupabaseDatabase, Tables, Json } from './supabase'

export type Database = SupabaseDatabase

export interface User {
  id: string
  role: 'student' | 'admin' | string | null
  student_id: string
  name: string
  current_point: number | null
  created_at?: string | null
}

export interface Menu {
  id: string
  day_of_week: string
  meal_date: string
  meal_time: string
  type: 'kr' | 'premium' | 'takeout'
  title_ko: string;
  title_en: string;
  price: number;
  capacity: number
  reservation_deadline: string
  deposit_amount: number
  is_active: boolean
  created_at?: string | null
}

export interface Reservation {
  id: string
  user_id: string | null
  menu_id: string | null
  options: {
    rice?: number
    main?: number
    [key: string]: any
  }
  total_price: number
  status: 'reserved' | 'used' | 'cancelled' | 'no_show' | string | null
  meal_date?: string | null
  meal_time?: string | null
  deposit_amount?: number | null
  refunded_amount?: number | null
  menu_snapshot?: {
    title_ko?: string
    title_en?: string
    type?: string
    price?: number
  } | null
  created_at: string | null
  // Joins
  users?: {
    name: string
    student_id: string
  } | null
  menus?: {
    type?: string | null
    title_ko: string
    title_en: string
    day_of_week?: string | null
    price?: number | null
  } | null
}

export interface Transaction {
  id: string
  user_id: string | null
  amount: number
  type: 'charge' | 'deduct' | 'refund' | string | null
  description: string | null
  created_at: string | null
  // Joins
  users?: {
    name: string
    student_id: string
  } | null
}

export type PointOrder = Tables<'point_orders'>
