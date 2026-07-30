export type Json = string | number | boolean | null | { [key: string]: Json | undefined } | Json[];

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.5";
  };
  public: {
    Tables: {
      menus: {
        Row: {
          capacity: number;
          created_at: string | null;
          day_of_week: string | null;
          deposit_amount: number;
          id: string;
          is_active: boolean;
          meal_date: string;
          meal_time: string;
          price: number | null;
          reservation_deadline: string;
          title_en: string;
          title_ko: string;
          type: string | null;
        };
        Insert: {
          capacity?: number;
          created_at?: string | null;
          day_of_week?: string | null;
          deposit_amount?: number;
          id?: string;
          is_active?: boolean;
          meal_date: string;
          meal_time?: string;
          price?: number | null;
          reservation_deadline?: string;
          title_en: string;
          title_ko: string;
          type?: string | null;
        };
        Update: {
          capacity?: number;
          created_at?: string | null;
          day_of_week?: string | null;
          deposit_amount?: number;
          id?: string;
          is_active?: boolean;
          meal_date?: string;
          meal_time?: string;
          price?: number | null;
          reservation_deadline?: string;
          title_en?: string;
          title_ko?: string;
          type?: string | null;
        };
        Relationships: [];
      };
      point_orders: {
        Row: {
          amount: number;
          created_at: string | null;
          id: string;
          order_id: string;
          paid_at: string | null;
          payment_key: string | null;
          payment_provider: string | null;
          point_amount: number;
          status: string | null;
          toss_response: Json | null;
          updated_at: string | null;
          user_id: string;
        };
        Insert: {
          amount: number;
          created_at?: string | null;
          id?: string;
          order_id: string;
          paid_at?: string | null;
          payment_key?: string | null;
          payment_provider?: string | null;
          point_amount: number;
          status?: string | null;
          toss_response?: Json | null;
          updated_at?: string | null;
          user_id: string;
        };
        Update: {
          amount?: number;
          created_at?: string | null;
          id?: string;
          order_id?: string;
          paid_at?: string | null;
          payment_key?: string | null;
          payment_provider?: string | null;
          point_amount?: number;
          status?: string | null;
          toss_response?: Json | null;
          updated_at?: string | null;
          user_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: "point_orders_user_id_fkey";
            columns: ["user_id"];
            isOneToOne: false;
            referencedRelation: "users";
            referencedColumns: ["id"];
          }
        ];
      };
      ai_logs: {
        Row: {
          created_at: string;
          error_message: string | null;
          estimated_cost_usd: number | null;
          id: string;
          input_tokens: number | null;
          latency_ms: number;
          model: string | null;
          output_tokens: number | null;
          prompt_version: number | null;
          request_id: string;
          stage: string;
          status_code: number;
          user_id: string | null;
        };
        Insert: {
          created_at?: string;
          error_message?: string | null;
          estimated_cost_usd?: number | null;
          id?: string;
          input_tokens?: number | null;
          latency_ms?: number;
          model?: string | null;
          output_tokens?: number | null;
          prompt_version?: number | null;
          request_id: string;
          stage: string;
          status_code: number;
          user_id?: string | null;
        };
        Update: {
          created_at?: string;
          error_message?: string | null;
          estimated_cost_usd?: number | null;
          id?: string;
          input_tokens?: number | null;
          latency_ms?: number;
          model?: string | null;
          output_tokens?: number | null;
          prompt_version?: number | null;
          request_id?: string;
          stage?: string;
          status_code?: number;
          user_id?: string | null;
        };
        Relationships: [];
      };
      chat_messages: {
        Row: {
          content: string;
          conversation_id: string;
          created_at: string;
          id: string;
          role: string;
          user_id: string;
        };
        Insert: {
          content: string;
          conversation_id: string;
          created_at?: string;
          id?: string;
          role: string;
          user_id: string;
        };
        Update: {
          content?: string;
          conversation_id?: string;
          created_at?: string;
          id?: string;
          role?: string;
          user_id?: string;
        };
        Relationships: [
          {
            foreignKeyName: "chat_messages_user_id_fkey";
            columns: ["user_id"];
            isOneToOne: false;
            referencedRelation: "users";
            referencedColumns: ["id"];
          }
        ];
      };
      prompt_templates: {
        Row: {
          created_at: string;
          id: string;
          is_active: boolean;
          prompt_content: string;
          service_name: string;
          temperature: number;
          updated_at: string;
          version: number;
        };
        Insert: {
          created_at?: string;
          id?: string;
          is_active?: boolean;
          prompt_content: string;
          service_name: string;
          temperature?: number;
          updated_at?: string;
          version: number;
        };
        Update: {
          created_at?: string;
          id?: string;
          is_active?: boolean;
          prompt_content?: string;
          service_name?: string;
          temperature?: number;
          updated_at?: string;
          version?: number;
        };
        Relationships: [];
      };
      reservations: {
        Row: {
          cancelled_at: string | null;
          created_at: string | null;
          deposit_amount: number;
          enforces_meal_limit: boolean;
          id: string;
          meal_date: string | null;
          meal_time: string | null;
          menu_id: string | null;
          menu_snapshot: Json;
          options: Json;
          refunded_amount: number;
          status: string | null;
          total_price: number;
          used_at: string | null;
          user_id: string | null;
        };
        Insert: {
          cancelled_at?: string | null;
          created_at?: string | null;
          deposit_amount?: number;
          enforces_meal_limit?: boolean;
          id?: string;
          meal_date?: string | null;
          meal_time?: string | null;
          menu_id?: string | null;
          menu_snapshot?: Json;
          options?: Json;
          refunded_amount?: number;
          status?: string | null;
          total_price: number;
          used_at?: string | null;
          user_id?: string | null;
        };
        Update: {
          cancelled_at?: string | null;
          created_at?: string | null;
          deposit_amount?: number;
          enforces_meal_limit?: boolean;
          id?: string;
          meal_date?: string | null;
          meal_time?: string | null;
          menu_id?: string | null;
          menu_snapshot?: Json;
          options?: Json;
          refunded_amount?: number;
          status?: string | null;
          total_price?: number;
          used_at?: string | null;
          user_id?: string | null;
        };
        Relationships: [
          {
            foreignKeyName: "reservations_menu_id_fkey";
            columns: ["menu_id"];
            isOneToOne: false;
            referencedRelation: "menus";
            referencedColumns: ["id"];
          },
          {
            foreignKeyName: "reservations_user_id_fkey";
            columns: ["user_id"];
            isOneToOne: false;
            referencedRelation: "users";
            referencedColumns: ["id"];
          }
        ];
      };
      transactions: {
        Row: {
          amount: number;
          created_at: string | null;
          description: string | null;
          id: string;
          type: string | null;
          user_id: string | null;
        };
        Insert: {
          amount: number;
          created_at?: string | null;
          description?: string | null;
          id?: string;
          type?: string | null;
          user_id?: string | null;
        };
        Update: {
          amount?: number;
          created_at?: string | null;
          description?: string | null;
          id?: string;
          type?: string | null;
          user_id?: string | null;
        };
        Relationships: [
          {
            foreignKeyName: "transactions_user_id_fkey";
            columns: ["user_id"];
            isOneToOne: false;
            referencedRelation: "users";
            referencedColumns: ["id"];
          }
        ];
      };
      users: {
        Row: {
          created_at: string | null;
          current_point: number | null;
          id: string;
          name: string;
          role: string | null;
          student_id: string;
        };
        Insert: {
          created_at?: string | null;
          current_point?: number | null;
          id: string;
          name: string;
          role?: string | null;
          student_id: string;
        };
        Update: {
          created_at?: string | null;
          current_point?: number | null;
          id?: string;
          name?: string;
          role?: string | null;
          student_id?: string;
        };
        Relationships: [];
      };
    };
    Views: {
      [_ in never]: never;
    };
    Functions: {
      admin_adjust_points: {
        Args: { p_amount: number; p_description: string; p_user_id: string };
        Returns: undefined;
      };
      admin_cancel_ticket: {
        Args: { p_reservation_id: string };
        Returns: undefined;
      };
      admin_update_user_role: {
        Args: { p_role: string; p_user_id: string };
        Returns: undefined;
      };
      admin_use_ticket: {
        Args: { p_reservation_id: string };
        Returns: undefined;
      };
      cancel_reservation: {
        Args: { p_reservation_id: string; p_user_id: string };
        Returns: undefined;
      };
      charge_point: {
        Args: { p_amount: number; p_user_id: string };
        Returns: undefined;
      };
      confirm_point_payment: {
        Args: {
          p_order_id: string;
          p_payment_key: string;
          p_toss_response?: Json;
        };
        Returns: {
          amount: number;
          order_id: string;
          point_amount: number;
          status: string;
          user_id: string;
        }[];
      };
      create_point_order: {
        Args: { p_amount: number; p_user_id: string };
        Returns: {
          amount: number;
          order_id: string;
          point_amount: number;
        }[];
      };
      donate_points: {
        Args: { p_amount: number; p_user_id: string };
        Returns: undefined;
      };
      is_admin: { Args: { p_user_id: string }; Returns: boolean };
      process_no_shows: { Args: Record<PropertyKey, never>; Returns: number };
      reserve_menu: {
        Args: {
          p_menu_id: string;
          p_options: Json;
          p_total_price: number;
          p_user_id: string;
        };
        Returns: undefined;
      };
    };
    Enums: {
      [_ in never]: never;
    };
    CompositeTypes: {
      [_ in never]: never;
    };
  };
};

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">;

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">];

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R;
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] & DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R;
      }
      ? R
      : never
    : never;

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"] | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I;
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I;
      }
      ? I
      : never
    : never;

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"] | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U;
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U;
      }
      ? U
      : never
    : never;

export type Enums<
  DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"] | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never;

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals;
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals;
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never;

export const Constants = {
  public: {
    Enums: {}
  }
} as const;
