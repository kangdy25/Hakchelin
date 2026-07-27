<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { Database, Menu } from '~/types/database.types'

interface ReservePayload {
  menu_id: string
  price: number
  options: {
    rice?: number
    main?: number
    [key: string]: any
  }
}

const { t, tm, rt, locale } = useI18n({ useScope: 'global' })
const api = useApi()
const { profile, userId, refreshProfile, adjustPoint } = useUserProfile()
const { showAlert } = useModal()

const today = new Date().toISOString().slice(0, 10)
const selectedDate = ref('')
const loading = ref(false)

const dbMenus = ref<Menu[]>([])
const availableDates = computed(() => [...new Set(dbMenus.value.map(menu => menu.meal_date))])
const selectedMenus = computed(() => dbMenus.value.filter(menu => menu.meal_date === selectedDate.value))

const formatMealDate = (date: string) => new Intl.DateTimeFormat(locale.value === 'ko' ? 'ko-KR' : 'en-US', {
  month: 'short', day: 'numeric', weekday: 'short'
}).format(new Date(`${date}T00:00:00`))

// 한글 타입(DB 저장값)을 영문 코드(UI 뱃지용)로 변환
const mapMenuType = (koType: string): 'kr' | 'premium' | 'takeout' => {
  if (['kr', 'premium', 'takeout'].includes(koType)) return koType as 'kr' | 'premium' | 'takeout'
  if (koType === '한식') return 'kr'
  if (koType === '일품') return 'premium'
  if (koType === '포장') return 'takeout'
  return 'kr'
}

// Supabase 메뉴 불러오기
const fetchMenus = async () => {
  try {
    const data = await api.menus.get({ activeOnly: true, fromDate: today })
    dbMenus.value = data.map((menu) => ({
        id: menu.id,
        day_of_week: (menu.day_of_week || 'mon') as 'mon' | 'tue' | 'wed' | 'thu' | 'fri',
        meal_date: menu.meal_date,
        meal_time: menu.meal_time,
        type: mapMenuType(menu.type || 'kr'),
        title_ko: menu.title_ko,
        title_en: menu.title_en,
        price: Number(menu.price || 4500),
        capacity: menu.capacity,
        reservation_deadline: menu.reservation_deadline,
        deposit_amount: menu.deposit_amount,
        is_active: menu.is_active,
        created_at: menu.created_at
    }))
    if (!selectedDate.value || !availableDates.value.includes(selectedDate.value)) {
      selectedDate.value = availableDates.value[0] || ''
    }
  } catch (error) {
    console.error('메뉴 불러오기 실패:', error)
  }
}

onMounted(() => {
  fetchMenus()
})

// 예약 처리 로직
const onReserve = async (payload: ReservePayload) => {
  if (!userId.value) {
    await showAlert('로그인이 필요합니다.', { title: '로그인 필요', type: 'warning' })
    return navigateTo('/login')
  }

  if (!payload.menu_id || !payload.price) {
    await showAlert('예약할 메뉴 정보를 확인할 수 없습니다.', { title: '정보 부족', type: 'error' })
    return
  }

  const latestProfile = await refreshProfile()
  const currentPoint = latestProfile?.current_point ?? profile.value.current_point
  if (currentPoint < payload.price) {
    await showAlert('포인트가 부족합니다. 상단 메뉴에서 포인트를 먼저 충전해주세요.', { title: '포인트 부족', type: 'warning' })
    return
  }

  loading.value = true
  try {
    await api.reservations.reserve({ menuId: payload.menu_id, options: payload.options, totalPrice: payload.price })

    await showAlert('예약이 성공적으로 완료되었습니다! 내 식권 메뉴에서 확인하세요.', { title: '예약 완료', type: 'success' })
    adjustPoint(-payload.price)
    await refreshProfile()
  } catch (err: unknown) {
    const message = api.getErrorMessage(err)
    if (message.includes('Insufficient points')) {
      await showAlert('포인트가 부족합니다. 상단 메뉴에서 포인트를 먼저 충전해주세요.', { title: '포인트 부족', type: 'warning' })
    } else {
      await showAlert('오류: ' + message, { title: '오류 발생', type: 'error' })
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <!-- 이용 규정 안내 배너 -->
    <div class="bg-gradient-to-r from-[#FFF3E0]/50 to-[#FFE0B2]/40 rounded-[18px] p-5 mb-[20px] border border-[#FFE0B2] shadow-[0_4px_16px_rgba(230,81,0,0.02)]">
      <!-- 제목 -->
      <div class="text-[15.5px] font-black text-[#D84315] flex items-center gap-2 mb-3">
        {{ t('policy_title') }}
      </div>
      <!-- 리스트 내용 -->
      <div class="flex flex-col gap-2.5">
        <div 
          v-for="item in tm('policy')" 
          :key="item"
          class="text-[13.5px] font-medium text-gray-700 leading-relaxed flex items-start gap-1.5"
        >
          {{ rt(item) }}
        </div>
      </div>
    </div>

    <div class="flex justify-between bg-[#f8f9fa] p-[5px] rounded-[10px] mb-[15px]">
      <button 
        v-for="date in availableDates" :key="date"
        @click="selectedDate = date"
        class="flex-1 border-none bg-transparent py-[10px] text-[16px] rounded-[8px] text-[#777] font-bold cursor-pointer transition-colors"
        :class="{ 'bg-[#b2fab4] text-black': selectedDate === date }"
      >
        <span>{{ formatMealDate(date) }}</span>
      </button>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-[15px] pb-6">
      <MenuCard 
        v-for="menu in selectedMenus"
        :key="menu.id" 
        :menu="menu" 
        :disabled="loading"
        @reserve="onReserve"
      />
    </div>

    <!-- 마음을 잇는 식탁 카드는 메뉴 카드 하단에 독립적으로 w-full 상태를 유지하여 노출 -->
    <div v-if="selectedDate === today" class="mt-4 pb-6 w-full">
      <HeartTableCard />
    </div>
    
    <div v-if="!selectedMenus.length" class="text-center py-[40px] bg-white rounded-[15px] border border-[#eee] mb-6">
      <div class="text-[#777] font-bold text-[13px]">{{ t('empty_menu') }}</div>
    </div>
    
    <!-- 예약 처리 중 로딩 화면 -->
    <div v-if="loading" class="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center z-50">
      <div class="bg-white p-6 rounded-2xl shadow-xl flex flex-col items-center">
        <div class="animate-spin rounded-full h-12 w-12 border-4 border-[#4ade80] border-t-transparent mb-4"></div>
        <div class="text-gray-700 font-bold">예약 처리 중입니다...</div>
      </div>
    </div>
  </div>
</template>
