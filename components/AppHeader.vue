<script setup lang="ts">
const { t, locale, setLocale } = useI18n({ useScope: 'global' })

const toggleLanguage = async () => {
  await setLocale(locale.value === 'ko' ? 'en' : 'ko')
}

const supabase = useSupabaseClient()
const authUser = useSupabaseUser()
const userData = ref({ name: '학생', student_id: '', current_point: 0 })

onMounted(async () => {
  if (authUser.value) {
    // DB에서 최신 포인트 및 정보 가져오기
    const { data } = await supabase
      .from('users')
      .select('name, student_id, current_point')
      .eq('id', authUser.value.id)
      .single()
      
    if (data) {
      userData.value = data
    } else {
      // DB fetch 실패 시 Auth 메타데이터 사용
      userData.value.name = authUser.value.user_metadata?.name || '학생'
      userData.value.student_id = authUser.value.user_metadata?.student_id || ''
    }
  }
})
</script>

<template>
  <header class="bg-[#2E7D32] text-white p-[25px_20px] rounded-b-[20px]">
    <div class="flex justify-between items-center mb-[15px] md:hidden">
      <!-- Only show user info in header on mobile, desktop sidebar has it -->
      <div>
        <p class="text-[18px] font-bold m-0">{{ t('welcome', { name: userData.name }) }}</p>
        <p class="text-[12px] opacity-80 m-0 mt-1">ID: {{ userData.student_id }}</p>
      </div>
      <button 
        @click="toggleLanguage" 
        class="bg-[#FF9800] text-white border-none py-[5px] px-[12px] rounded-[15px] font-bold cursor-pointer text-[12px] shadow-[0_2px_5px_rgba(0,0,0,0.2)]"
      >
        {{ t('btnLang') }}
      </button>
    </div>
    
    <div class="hidden md:flex justify-between items-center mb-[15px]">
      <p class="text-[24px] font-bold m-0">{{ t('welcome', { name: userData.name }) }} 👋</p>
      <button 
        @click="toggleLanguage" 
        class="bg-[#FF9800] text-white border-none py-[6px] px-[16px] rounded-[15px] font-bold cursor-pointer text-[13px] shadow-[0_2px_5px_rgba(0,0,0,0.2)]"
      >
        {{ t('btnLang') }}
      </button>
    </div>

    <div class="bg-white text-[#2E7D32] p-[15px] rounded-[12px] flex justify-between items-center">
      <div class="flex items-center">
        <span class="text-[14px]">{{ t('point') }}</span>: 
        <b class="text-[18px] ml-1">{{ userData.current_point.toLocaleString() }} P</b>
      </div>
      <button class="bg-[#4CAF50] text-white border-none py-[6px] px-[12px] rounded-[6px] font-bold cursor-pointer text-[12px]">
        {{ t('charge') }}
      </button>
    </div>
  </header>
</template>
