<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { Database, Reservation } from '~/types/database.types'

const { t, locale } = useI18n({ useScope: 'global' })
const supabase = useSupabaseClient<Database>()
const { profile, isAdmin, userId } = useUserProfile()
const { showAlert } = useModal()

const reservations = ref<Pick<Reservation, 'options' | 'status'>[]>([])
const loadingStats = ref(true)

const fetchStats = async () => {
  if (!userId.value) return
  const { data } = await supabase
    .from('reservations')
    .select('options, status')
    .eq('user_id', userId.value)
  if (data) {
    reservations.value = data.map(r => ({
      status: r.status,
      options: (r.options || {}) as { rice?: number; main?: number; [key: string]: any }
    }))
  }
  loadingStats.value = false
}

const totalSaved = computed(() => {
  const activeCount = reservations.value.filter(r => r.status !== 'cancelled').length
  return activeCount * 1000
})

const ecoCount = computed(() => {
  return reservations.value.filter(r => r.status !== 'cancelled' && r.options?.rice === 1).length
})

const handleLogout = async () => {
  const { error } = await supabase.auth.signOut()
  if (!error) {
    navigateTo('/login')
  } else {
    await showAlert(t('logout_error'), { title: '오류', type: 'error' })
  }
}

watch(
  () => userId.value,
  (newId) => {
    if (newId) {
      fetchStats()
    }
  },
  { immediate: true }
)
</script>

<template>
  <div>
    <h1 class="text-2xl md:text-3xl font-black text-gray-800 mb-6">{{ t('my_profile') }}</h1>
    
    <div class="bg-white rounded-[2rem] p-8 text-center shadow-[0_2px_8px_rgba(0,0,0,0.05)] border border-[#eee] flex flex-col items-center justify-center min-h-[50vh]">
      <div class="w-24 h-24 bg-gradient-to-tr from-[#4ade80] to-[#22c55e] rounded-full flex items-center justify-center text-4xl text-white mb-6 shadow-lg shadow-green-200">
        {{ profile.name?.[0] || '👤' }}
      </div>
      
      <div class="flex items-center gap-2 mb-2 justify-center">
        <h2 class="text-2xl font-bold text-gray-800">{{ profile.name }}</h2>
        <span 
          class="text-xs font-black px-2.5 py-0.5 rounded-full border shadow-sm flex items-center gap-1"
          :class="isAdmin ? 'bg-purple-50 text-purple-700 border-purple-200 shadow-purple-100' : 'bg-green-50 text-[#2E7D32] border-green-200 shadow-green-100'"
        >
          <span>{{ isAdmin ? '👑' : '🎓' }}</span>
          <span>{{ isAdmin ? t('admin.users.roles.admin') : t('admin.users.roles.student') }}</span>
        </span>
      </div>
      
      <p class="text-gray-500 font-medium mb-1">{{ t('student_id') }} {{ profile.student_id || '-' }}</p>
      
      <!-- Stats Report -->
      <div v-if="!loadingStats" class="grid grid-cols-2 gap-4 w-full max-w-sm mt-6 mb-8">
        <div class="bg-[#E8F5E9] border border-green-100 rounded-2xl p-4 text-center">
          <div class="text-[11px] text-[#2E7D32] font-black uppercase tracking-wider mb-1">💰 {{ locale === 'ko' ? '사전예약 절약' : 'Pre-order Saved' }}</div>
          <div class="text-[18px] font-black text-[#2E7D32]">{{ totalSaved.toLocaleString() }}P</div>
        </div>
        <div class="bg-blue-50 border border-blue-100 rounded-2xl p-4 text-center">
          <div class="text-[11px] text-blue-700 font-black uppercase tracking-wider mb-1">🌱 No-Waste {{ locale === 'ko' ? '실천' : 'Eco Count' }}</div>
          <div class="text-[18px] font-black text-blue-700">{{ ecoCount }}{{ locale === 'ko' ? '회' : ' times' }}</div>
        </div>
      </div>
      
      <div v-else class="h-20 flex items-center justify-center mb-8">
        <div class="animate-spin rounded-full h-6 w-6 border-2 border-[#4ade80] border-t-transparent"></div>
      </div>
      
      <button 
        @click="handleLogout"
        class="px-8 py-3 bg-red-50 text-red-600 hover:bg-red-100 font-bold rounded-xl transition-colors w-full max-w-xs"
      >
        {{ t('logout') }}
      </button>
    </div>
  </div>
</template>
