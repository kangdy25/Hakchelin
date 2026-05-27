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

const { t, tm, rt } = useI18n({ useScope: 'global' })
const supabase = useSupabaseClient<Database>()
const { profile, userId, refreshProfile, adjustPoint } = useUserProfile()
const { showAlert } = useModal()

const days = ['mon', 'tue', 'wed', 'thu', 'fri']
const selectedDay = ref('mon')
const loading = ref(false)

// 요일별 빈 배열로 초기화
const dbMenus = ref<Record<string, Menu[]>>({
  mon: [], tue: [], wed: [], thu: [], fri: []
})

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
  const { data, error } = await supabase.from('menus').select('*')
  if (data) {
    const grouped: Record<string, Menu[]> = { mon: [], tue: [], wed: [], thu: [], fri: [] }
    data.forEach((menu) => {
      const menuItem: Menu = {
        id: menu.id,
        day_of_week: (menu.day_of_week || 'mon') as 'mon' | 'tue' | 'wed' | 'thu' | 'fri',
        type: mapMenuType(menu.type || 'kr'),
        title_ko: menu.title_ko,
        title_en: menu.title_en,
        price: Number(menu.price || 4500),
        created_at: menu.created_at
      }

      if (grouped[menuItem.day_of_week]) {
        grouped[menuItem.day_of_week]?.push(menuItem)
      }
    })
    dbMenus.value = grouped
  } else if (error) {
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
    const { error } = await supabase.rpc('reserve_menu', {
      p_user_id: userId.value,
      p_menu_id: payload.menu_id,
      p_options: payload.options,
      p_total_price: payload.price
    })

    if (error) {
      if (error.message.includes('Insufficient points')) {
        await showAlert('포인트가 부족합니다. 상단 메뉴에서 포인트를 먼저 충전해주세요.', { title: '포인트 부족', type: 'warning' })
      } else {
        await showAlert('예약 중 오류가 발생했습니다: ' + error.message, { title: '예약 실패', type: 'error' })
      }
      return
    }

    await showAlert('예약이 성공적으로 완료되었습니다! 내 식권 메뉴에서 확인하세요.', { title: '예약 완료', type: 'success' })
    adjustPoint(-payload.price)
    await refreshProfile()
  } catch (err: unknown) {
    await showAlert('오류: ' + (err as Error).message, { title: '오류 발생', type: 'error' })
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <div class="bg-[#FFF3E0] rounded-[10px] p-[12px] mb-[15px] text-[12px] text-[#E65100] border border-[#FFE0B2] leading-[1.6]">
      <div v-for="item in tm('policy')" :key="item">
        {{ rt(item) }}
      </div>
    </div>

    <div class="flex justify-between bg-[#f8f9fa] p-[5px] rounded-[10px] mb-[15px]">
      <button 
        v-for="day in days" :key="day"
        @click="selectedDay = day"
        class="flex-1 border-none bg-transparent py-[10px] text-[16px] rounded-[8px] text-[#777] font-bold cursor-pointer transition-colors"
        :class="{ 'bg-[#b2fab4] text-black': selectedDay === day }"
      >
        <span>{{ t(`days.${day}`) }}</span>
      </button>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-[15px] pb-6">
      <MenuCard 
        v-for="menu in dbMenus[selectedDay]" 
        :key="menu.id" 
        :menu="menu" 
        :disabled="loading"
        @reserve="onReserve"
      />
    </div>
    
    <div v-if="!dbMenus[selectedDay]?.length" class="text-center py-[40px] bg-white rounded-[15px] border border-[#eee] mb-6">
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
