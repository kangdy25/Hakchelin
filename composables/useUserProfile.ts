import type { Database } from '~/types/database.types'

type UserProfile = {
  name: string
  student_id: string
  current_point: number
  role: 'student' | 'admin'
}

const emptyProfile = (): UserProfile => ({
  name: '학생',
  student_id: '',
  current_point: 0,
  role: 'student'
})

export const useUserProfile = () => {
  const supabase = useSupabaseClient<Database>()
  const authUser = useSupabaseUser()

  const profile = useState<UserProfile>('user-profile', emptyProfile)
  const loading = useState('user-profile-loading', () => false)
  const loadedUserId = useState<string | null>('user-profile-loaded-user-id', () => null)
  const userId = computed(() => {
    const user = authUser.value as { sub?: string; id?: string } | null
    return user?.sub || user?.id || null
  })

  const userMetadata = computed(() => {
    const user = authUser.value as { user_metadata?: { name?: string; student_id?: string } } | null
    return user?.user_metadata || {}
  })

  const fallbackProfile = (): UserProfile => ({
    name: userMetadata.value.name || '학생',
    student_id: userMetadata.value.student_id || '',
    current_point: profile.value.current_point || 0,
    role: profile.value.role || 'student'
  })

  const isAdmin = computed(() => profile.value.role === 'admin')

  const resetProfile = () => {
    profile.value = emptyProfile()
    loadedUserId.value = null
  }

  const refreshProfile = async () => {
    if (!userId.value) {
      resetProfile()
      return null
    }

    const currentUserId = userId.value
    loading.value = true

    try {
      const { data, error } = await supabase
        .from('users')
        .select('name, student_id, current_point, role')
        .eq('id', currentUserId)
        .single()

      if (error || !data) {
        profile.value = fallbackProfile()
      } else {
        profile.value = {
          name: data.name || fallbackProfile().name,
          student_id: data.student_id || fallbackProfile().student_id,
          current_point: Number(data.current_point || 0),
          role: (data.role || 'student') as 'student' | 'admin'
        }
      }

      loadedUserId.value = currentUserId
      return profile.value
    } finally {
      loading.value = false
    }
  }

  const adjustPoint = (amount: number) => {
    profile.value = {
      ...profile.value,
      current_point: profile.value.current_point + amount
    }
  }

  watch(
    () => userId.value,
    (currentUserId) => {
      if (!currentUserId) {
        resetProfile()
        return
      }

      if (loadedUserId.value !== currentUserId) {
        refreshProfile()
      }
    },
    { immediate: true }
  )

  return {
    profile,
    loading,
    userId,
    isAdmin,
    refreshProfile,
    adjustPoint
  }
}
