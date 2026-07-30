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
  if (typeof error === "string") return error;
  if (typeof error === "object" && error) {
    const body = error as Record<string, unknown>;
    if (typeof body.detail === "string") return body.detail;
    const first = Object.values(body)[0];
    if (typeof first === "string") return first;
    if (Array.isArray(first) && typeof first[0] === "string") return first[0];
  }
  return fallback;
};

export const useApi = () => {
  const djangoApi = useDjangoApi();

  const unwrap = <T>(result: { data?: T; error?: unknown }): T => {
    if (result.error) throw new Error(getErrorMessage(result.error));
    if (result.data === undefined) throw new Error("API 응답 데이터가 없습니다.");
    return result.data;
  };

  const getMenus = async (
    { activeOnly = false, fromDate }: { activeOnly?: boolean; fromDate?: string } = {}
  ) =>
    unwrap(
      await djangoApi.getClient().GET("/api/v1/menus/", {
        params: { query: { active_only: activeOnly, from_date: fromDate } }
      })
    ) as Menu[];

  const createMenu = async (input: CreateMenuInput) => {
    await djangoApi.ensureCsrf();
    const { id: _legacyId, ...body } = input;
    unwrap(await djangoApi.getClient().POST("/api/v1/menus/", { body }));
  };

  const updateMenu = async (id: string, input: UpdateMenuInput) => {
    await djangoApi.ensureCsrf();
    unwrap(
      await djangoApi.getClient().PATCH("/api/v1/menus/{menu_id}/", {
        params: { path: { menu_id: id } },
        body: input
      })
    );
  };

  const deactivateMenu = async (id: string) => {
    await djangoApi.ensureCsrf();
    const { error } = await djangoApi.getClient().DELETE("/api/v1/menus/{menu_id}/", {
      params: { path: { menu_id: id } }
    });
    if (error) throw new Error(getErrorMessage(error));
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
    await djangoApi.ensureCsrf();
    unwrap(
      await djangoApi.getClient().POST("/api/v1/reservations/", {
        body: { menu_id: menuId, options, total_price: totalPrice }
      })
    );
  };

  const getMyReservations = async () =>
    unwrap(await djangoApi.getClient().GET("/api/v1/reservations/me/")) as unknown as Reservation[];

  const getReservations = async () =>
    unwrap(await djangoApi.getClient().GET("/api/v1/admin/reservations/")) as unknown as Reservation[];

  const getMenusByIds = async (ids: string[]) => {
    if (!ids.length) {
      return [] as Pick<Menu, "id" | "type" | "title_ko" | "title_en" | "day_of_week" | "price">[];
    }
    const menus = await getMenus();
    const idSet = new Set(ids);
    return menus
      .filter((menu) => idSet.has(menu.id))
      .map(({ id, type, title_ko, title_en, day_of_week, price }) => ({
        id,
        type,
        title_ko,
        title_en,
        day_of_week,
        price
      }));
  };

  const cancelReservation = async (reservationId: string) => {
    await djangoApi.ensureCsrf();
    unwrap(
      await djangoApi.getClient().POST("/api/v1/reservations/{reservation_id}/cancel/", {
        params: { path: { reservation_id: reservationId } }
      })
    );
  };

  const reservationAdminAction = async (reservationId: string, action: "use" | "cancel") => {
    await djangoApi.ensureCsrf();
    unwrap(
      await djangoApi.getClient().POST("/api/v1/admin/reservations/{reservation_id}/{action}/", {
        params: { path: { reservation_id: reservationId, action } }
      })
    );
  };

  const getMyTransactions = async () =>
    unwrap(await djangoApi.getClient().GET("/api/v1/wallet/transactions/me/")) as Transaction[];

  const getTransactions = async () =>
    unwrap(await djangoApi.getClient().GET("/api/v1/admin/transactions/")) as Transaction[];

  const getUsers = async () =>
    unwrap(await djangoApi.getClient().GET("/api/v1/admin/users/")) as User[];

  const getMyProfile = async () =>
    unwrap(await djangoApi.getClient().GET("/api/v1/me/")) as Pick<
      User,
      "name" | "student_id" | "current_point" | "role"
    >;

  const adjustUserPoints = async ({
    userId,
    amount,
    description
  }: {
    userId: string;
    amount: number;
    description: string;
  }) => {
    await djangoApi.ensureCsrf();
    unwrap(
      await djangoApi.getClient().POST("/api/v1/admin/users/{user_id}/points/", {
        params: { path: { user_id: userId } },
        body: { amount, description }
      })
    );
  };

  const updateUserRole = async ({ userId, role }: { userId: string; role: "student" | "admin" }) => {
    await djangoApi.ensureCsrf();
    unwrap(
      await djangoApi.getClient().POST("/api/v1/admin/users/{user_id}/role/", {
        params: { path: { user_id: userId } },
        body: { role }
      })
    );
  };

  const donatePoints = async (amount: number) => {
    await djangoApi.ensureCsrf();
    unwrap(
      await djangoApi.getClient().POST("/api/v1/wallet/donations/", {
        body: { amount }
      })
    );
  };

  const createPointOrder = async (amount: number) => {
    await djangoApi.ensureCsrf();
    return unwrap(
      await djangoApi.getClient().POST("/api/v1/payments/point-orders/", {
        body: { amount }
      })
    );
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
    await djangoApi.ensureCsrf();
    const order = unwrap(
      await djangoApi.getClient().POST("/api/v1/payments/point-orders/confirm/", {
        body: { payment_key: paymentKey, order_id: orderId, amount }
      })
    );
    return { order };
  };

  const getChatMessages = async (conversationId: string) =>
    unwrap(
      await djangoApi.getClient().GET("/api/v1/chat/{conversation_id}/", {
        params: { path: { conversation_id: conversationId } }
      })
    ).filter((item): item is ChatMessage => item.role === "user" || item.role === "assistant");

  const streamChat = ({ message, conversationId }: { message: string; conversationId: string }) =>
    djangoApi.streamChat({ message, conversation_id: conversationId });

  const getAiLogs = async () =>
    unwrap(await djangoApi.getClient().GET("/api/v1/admin/ai-logs/")) as AiLog[];

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
      useTicket: (id: string) => reservationAdminAction(id, "use"),
      cancelTicket: (id: string) => reservationAdminAction(id, "cancel")
    },
    transactions: { getMine: getMyTransactions, getAll: getTransactions },
    users: {
      getAll: getUsers,
      getMine: getMyProfile,
      adjustPoints: adjustUserPoints,
      updateRole: updateUserRole
    },
    points: {
      donate: donatePoints,
      createOrder: createPointOrder,
      confirmPayment: confirmTossPayment
    },
    chat: { getMessages: getChatMessages, stream: streamChat },
    ai: { getLogs: getAiLogs }
  };
};
