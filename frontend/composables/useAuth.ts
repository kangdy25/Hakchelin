type AuthMetadata = {
  name?: string;
  student_id?: string;
};

export type AuthUser = {
  id: string;
  metadata: AuthMetadata;
};

type DjangoUser = {
  id: string;
  name: string;
  student_id: string;
};

const toAuthUser = (user: DjangoUser): AuthUser => ({
  id: user.id,
  metadata: { name: user.name, student_id: user.student_id }
});

const apiError = (error: unknown, fallback: string) => {
  if (error instanceof Error) return error;
  if (typeof error === "object" && error) {
    const body = error as { detail?: string; non_field_errors?: string[] };
    return new Error(body.detail || body.non_field_errors?.[0] || fallback);
  }
  return new Error(fallback);
};

export const useAuth = () => {
  const djangoApi = useDjangoApi();
  const user = useState<AuthUser | null>("auth-user", () => null);
  const loading = useState("auth-loading", () => false);
  const initialized = useState("auth-initialized", () => false);

  const refresh = async () => {
    loading.value = true;
    try {
      const { data, error, response } = await djangoApi.getClient().GET("/api/me/");
      if (response.status === 401 || response.status === 403) {
        user.value = null;
        return null;
      }
      if (error || !data) throw apiError(error, "사용자 정보를 불러오지 못했습니다.");
      user.value = toAuthUser(data);
      return user.value;
    } finally {
      initialized.value = true;
      loading.value = false;
    }
  };

  const ensureInitialized = async () => (initialized.value ? user.value : refresh());

  const signIn = async ({ email, password }: { email: string; password: string }) => {
    await djangoApi.ensureCsrf();
    const { data, error } = await djangoApi
      .getClient()
      .POST("/api/auth/login/", { body: { email, password } });
    if (error || !data) throw apiError(error, "로그인에 실패했습니다.");
    user.value = toAuthUser(data);
    initialized.value = true;
    return user.value;
  };

  const signUp = async ({
    email,
    password,
    name,
    studentId
  }: {
    email: string;
    password: string;
    name: string;
    studentId: string;
  }) => {
    await djangoApi.ensureCsrf();
    const { error } = await djangoApi.getClient().POST("/api/auth/signup/", {
      body: { email, password, name, student_id: studentId }
    });
    if (error) throw apiError(error, "회원가입에 실패했습니다.");
  };

  const signOut = async () => {
    await djangoApi.ensureCsrf();
    const { error } = await djangoApi.getClient().POST("/api/auth/logout/");
    if (error) throw apiError(error, "로그아웃에 실패했습니다.");
    user.value = null;
    initialized.value = true;
  };

  return {
    user,
    loading,
    userId: computed(() => user.value?.id || null),
    isAuthenticated: computed(() => Boolean(user.value?.id)),
    refresh,
    ensureInitialized,
    signIn,
    signUp,
    signOut
  };
};
