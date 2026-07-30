import type { Database } from "~/types/supabase";
import type {
  CreateMenuInput,
  Menu,
  MealOptions,
  Reservation,
  Transaction,
  UpdateMenuInput,
  User
} from "~/types/api";

type ChatRole = "user" | "assistant";
type ChatMessage = { role: ChatRole; content: string };
type AiLog = {
  id: string;
  created_at: string;
  stage: string;
  model: string | null;
  latency_ms: number;
  status_code: number;
  error_message: string | null;
  users?: { name: string; student_id: string } | null;
};

const getErrorMessage = (error: unknown, fallback = "요청 처리 중 오류가 발생했습니다.") => {
  if (error instanceof Error) return error.message;
  if (typeof error === "object" && error && "message" in error && typeof error.message === "string")
    return error.message;
  return fallback;
};

/**
 * UI가 데이터 공급자(Supabase, Django REST API 등)를 직접 알지 않도록 만드는
 * 임시 호환 어댑터다. Django 이전 시 이 파일의 구현만 OpenAPI 클라이언트로 교체한다.
 */
export const useApi = () => {
  const supabase = useSupabaseClient<Database>();
  const runtimeConfig = useRuntimeConfig();
  const djangoApi = useDjangoApi();

  const getDjangoData = async <T>(request: () => Promise<{ data?: unknown; error?: unknown }>) => {
    const { data, error } = await request();
    if (error) throw new Error(getErrorMessage(error));
    return data as T;
  };

  const currentUserId = async () => {
    const { data } = await supabase.auth.getClaims();
    const claims = data?.claims as { sub?: string; id?: string } | undefined;
    const userId = claims?.sub || claims?.id;
    if (!userId) throw new Error("로그인이 필요합니다.");
    return userId;
  };

  const getMenus = async ({ activeOnly = false, fromDate }: { activeOnly?: boolean; fromDate?: string } = {}) => {
    if (djangoApi.enabled.value) {
      const client = await djangoApi.getClient();
      return getDjangoData<Menu[]>(() => client.GET("/api/v1/menus/", { params: { query: { active_only: activeOnly, from_date: fromDate } } }));
    }
    let query = supabase.from("menus").select("*").order("meal_date").order("meal_time");
    if (activeOnly) query = query.eq("is_active", true);
    if (fromDate) query = query.gte("meal_date", fromDate);
    const { data, error } = await query;
    if (error) throw new Error(error.message);
    return (data || []) as Menu[];
  };

  const createMenu = async (input: CreateMenuInput) => {
    const { error } = await supabase.from("menus").insert(input);
    if (error) throw new Error(error.message);
  };

  const updateMenu = async (id: string, input: UpdateMenuInput) => {
    const { error } = await supabase.from("menus").update(input).eq("id", id);
    if (error) throw new Error(error.message);
  };

  const deactivateMenu = async (id: string) => {
    const { error } = await supabase.from("menus").update({ is_active: false }).eq("id", id);
    if (error) throw new Error(error.message);
  };

  const reserveMenu = async ({
    menuId,
    options,
    totalPrice
  }: {
    menuId: string;
    options: MealOptions;
    totalPrice: number;
  }) => {
    const userId = await currentUserId();
    const { error } = await supabase.rpc("reserve_menu", {
      p_user_id: userId,
      p_menu_id: menuId,
      p_options: options,
      p_total_price: totalPrice
    });
    if (error) throw new Error(error.message);
  };

  const getMyReservations = async () => {
    if (djangoApi.enabled.value) {
      const client = await djangoApi.getClient();
      return getDjangoData<Reservation[]>(() => client.GET("/api/v1/reservations/me/"));
    }
    const userId = await currentUserId();
    const { data, error } = await supabase
      .from("reservations")
      .select(
        "id, user_id, menu_id, options, total_price, status, created_at, meal_date, meal_time, deposit_amount, refunded_amount, menu_snapshot"
      )
      .eq("user_id", userId)
      .order("created_at", { ascending: false });
    if (error) throw new Error(error.message);
    return (data || []) as Reservation[];
  };

  const getReservations = async () => {
    const { data, error } = await supabase
      .from("reservations")
      .select(
        "id, user_id, menu_id, options, total_price, status, created_at, meal_date, meal_time, deposit_amount, refunded_amount, menu_snapshot, users(name, student_id), menus(title_ko, title_en, price)"
      )
      .order("created_at", { ascending: false });
    if (error) throw new Error(error.message);
    return (data || []) as Reservation[];
  };

  const getMenusByIds = async (ids: string[]) => {
    if (!ids.length) return [] as Pick<Menu, "id" | "type" | "title_ko" | "title_en" | "day_of_week" | "price">[];
    const { data, error } = await supabase
      .from("menus")
      .select("id, type, title_ko, title_en, day_of_week, price")
      .in("id", ids);
    if (error) throw new Error(error.message);
    return (data || []) as Pick<Menu, "id" | "type" | "title_ko" | "title_en" | "day_of_week" | "price">[];
  };

  const cancelReservation = async (reservationId: string) => {
    const userId = await currentUserId();
    const { error } = await supabase.rpc("cancel_reservation", { p_reservation_id: reservationId, p_user_id: userId });
    if (error) throw new Error(error.message);
  };

  const useTicket = async (reservationId: string) => {
    const { error } = await supabase.rpc("admin_use_ticket", { p_reservation_id: reservationId });
    if (error) throw new Error(error.message);
  };

  const cancelTicket = async (reservationId: string) => {
    const { error } = await supabase.rpc("admin_cancel_ticket", { p_reservation_id: reservationId });
    if (error) throw new Error(error.message);
  };

  const getMyTransactions = async () => {
    if (djangoApi.enabled.value) {
      const client = await djangoApi.getClient();
      return getDjangoData<Transaction[]>(() => client.GET("/api/v1/wallet/transactions/me/"));
    }
    const userId = await currentUserId();
    const { data, error } = await supabase
      .from("transactions")
      .select("id, user_id, amount, type, description, created_at")
      .eq("user_id", userId)
      .order("created_at", { ascending: false });
    if (error) throw new Error(error.message);
    return (data || []) as Transaction[];
  };

  const getTransactions = async () => {
    const { data, error } = await supabase
      .from("transactions")
      .select("id, user_id, amount, type, description, created_at, users(name, student_id)")
      .order("created_at", { ascending: false })
      .limit(50);
    if (error) throw new Error(error.message);
    return (data || []) as Transaction[];
  };

  const getUsers = async () => {
    const { data, error } = await supabase.from("users").select("*").order("student_id", { ascending: true });
    if (error) throw new Error(error.message);
    return (data || []) as User[];
  };

  const getMyProfile = async () => {
    if (djangoApi.enabled.value) {
      const client = await djangoApi.getClient();
      return getDjangoData<Pick<User, "name" | "student_id" | "current_point" | "role">>(() => client.GET("/api/v1/me/"));
    }
    const userId = await currentUserId();
    const { data, error } = await supabase
      .from("users")
      .select("name, student_id, current_point, role")
      .eq("id", userId)
      .single();
    if (error) throw new Error(error.message);
    return data as Pick<User, "name" | "student_id" | "current_point" | "role">;
  };

  const adjustUserPoints = async ({
    userId,
    amount,
    description
  }: {
    userId: string;
    amount: number;
    description: string;
  }) => {
    const { error } = await supabase.rpc("admin_adjust_points", {
      p_user_id: userId,
      p_amount: amount,
      p_description: description
    });
    if (error) throw new Error(error.message);
  };

  const updateUserRole = async ({ userId, role }: { userId: string; role: "student" | "admin" }) => {
    const { error } = await supabase.rpc("admin_update_user_role", { p_user_id: userId, p_role: role });
    if (error) throw new Error(error.message);
  };

  const donatePoints = async (amount: number) => {
    const userId = await currentUserId();
    const { error } = await supabase.rpc("donate_points", { p_user_id: userId, p_amount: amount });
    if (error) throw new Error(error.message);
  };

  const createPointOrder = async (amount: number) => {
    const userId = await currentUserId();
    const { data, error } = await supabase.rpc("create_point_order", { p_user_id: userId, p_amount: amount });
    if (error) throw new Error(error.message);
    return Array.isArray(data) ? data[0] : data;
  };

  const confirmTossPayment = async ({
    paymentKey,
    orderId,
    amount
  }: {
    paymentKey: string;
    orderId: string;
    amount: number;
  }) => {
    const { data, error } = await supabase.functions.invoke("confirm-toss-payment", {
      body: { paymentKey, orderId, amount }
    });
    if (error) throw new Error(error.message);
    if (data?.error) throw new Error(String(data.error));
    return data;
  };

  const getChatMessages = async (conversationId: string) => {
    const userId = await currentUserId();
    const { data, error } = await supabase
      .from("chat_messages")
      .select("role, content")
      .eq("user_id", userId)
      .eq("conversation_id", conversationId)
      .order("created_at", { ascending: true })
      .limit(30);
    if (error) throw new Error(error.message);
    return (data || []).filter((item): item is ChatMessage => item.role === "user" || item.role === "assistant");
  };

  const streamChat = async ({ message, conversationId }: { message: string; conversationId: string }) => {
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    if (!token || !runtimeConfig.public.supabaseUrl) throw new Error("로그인이 필요합니다.");
    return fetch(`${runtimeConfig.public.supabaseUrl}/functions/v1/chat`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify({ message, conversationId })
    });
  };

  const getAiLogs = async () => {
    const { data, error } = await supabase
      .from("ai_logs")
      .select("id, created_at, stage, model, latency_ms, status_code, error_message, users(name, student_id)")
      .order("created_at", { ascending: false })
      .limit(50);
    if (error) throw new Error(error.message);
    return (data || []) as unknown as AiLog[];
  };

  return {
    getErrorMessage,
    menus: {
      get: getMenus,
      create: createMenu,
      update: updateMenu,
      deactivate: deactivateMenu,
      getByIds: getMenusByIds
    },
    reservations: {
      reserve: reserveMenu,
      getMine: getMyReservations,
      getAll: getReservations,
      cancel: cancelReservation,
      useTicket,
      cancelTicket
    },
    transactions: { getMine: getMyTransactions, getAll: getTransactions },
    users: { getAll: getUsers, getMine: getMyProfile, adjustPoints: adjustUserPoints, updateRole: updateUserRole },
    points: { donate: donatePoints, createOrder: createPointOrder, confirmPayment: confirmTossPayment },
    chat: { getMessages: getChatMessages, stream: streamChat },
    ai: { getLogs: getAiLogs }
  };
};
