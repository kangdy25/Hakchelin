<script setup lang="ts">
const { t, locale, setLocale } = useI18n({ useScope: 'global' })

const toggleLanguage = async () => {
  await setLocale(locale.value === 'ko' ? 'en' : 'ko')
}

const { profile: userData, userId } = useUserProfile()
const { showAlert } = useModal()

const showChargeModal = ref(false)

const handleCharge = async () => {
  if (!userId.value) {
    await showAlert('사용자 정보를 불러올 수 없습니다. 새로고침 후 다시 시도해주세요.', { title: '오류', type: 'error' })
    return
  }
  showChargeModal.value = true
}
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
      <button 
        @click="handleCharge"
        class="bg-[#4CAF50] text-white border-none py-[6px] px-[12px] rounded-[6px] font-bold cursor-pointer text-[12px] active:scale-[0.98] transition-transform"
      >
        {{ t('charge') }}
      </button>
    </div>

    <ChargeModal :show="showChargeModal" @close="showChargeModal = false" />
  </header>
</template>
