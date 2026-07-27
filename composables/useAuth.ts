type AuthMetadata = {
  name?: string
  student_id?: string
}

export type AuthUser = {
  id: string
  metadata: AuthMetadata
}

const toAuthUser = (user: { id: string; user_metadata?: AuthMetadata } | null): AuthUser | null => {
  if (!user) return null
  return { id: user.id, metadata: user.user_metadata || {} }
}

/**
 * 인증 공급자 경계다. 현재는 Supabase Auth를 사용하지만, Django 쿠키 인증으로
 * 전환할 때 화면·미들웨어를 바꾸지 않고 이 composable만 교체한다.
 */
export const useAuth = () => {
  const supabase = useSupabaseClient()
  const user = useState<AuthUser | null>('auth-user', () => null)
  const loading = useState('auth-loading', () => false)
  const initialized = useState('auth-initialized', () => false)

  const refresh = async () => {
    loading.value = true
    try {
      const { data, error } = await supabase.auth.getUser()
      if (error) {
        user.value = null
        return null
      }
      user.value = toAuthUser(data.user)
      return user.value
    } finally {
      initialized.value = true
      loading.value = false
    }
  }

  const ensureInitialized = async () => initialized.value ? user.value : refresh()

  const signIn = async ({ email, password }: { email: string; password: string }) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) throw new Error(error.message)
    return refresh()
  }

  const signUp = async ({ email, password, name, studentId }: { email: string; password: string; name: string; studentId: string }) => {
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: { data: { name, student_id: studentId, role: 'student' } }
    })
    if (error) throw new Error(error.message)
  }

  const signOut = async () => {
    const { error } = await supabase.auth.signOut()
    if (error) throw new Error(error.message)
    user.value = null
    initialized.value = true
  }

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
  }
}
