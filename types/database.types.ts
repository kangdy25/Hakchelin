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
  day_of_week: 'mon' | 'tue' | 'wed' | 'thu' | 'fri'
  type: 'kr' | 'premium' | 'takeout'
  title_ko: string;
  title_en: string;
  price: number;
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
  status: 'reserved' | 'used' | 'cancelled' | string | null
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
