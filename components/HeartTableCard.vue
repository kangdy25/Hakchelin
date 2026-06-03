<script setup lang="ts">
import { ref } from 'vue'
const { t } = useI18n({ useScope: 'global' })
const { showAlert } = useModal()

const selectedSurvey = ref<'great' | 'normal' | null>(null)
const showDonateModal = ref(false)

const handleDonate = () => {
  showDonateModal.value = true
}

const handleConsult = async () => {
  await showAlert(t('heartTable.consultSuccess'), { 
    title: t('heartTable.title'), 
    type: 'success' 
  })
}

const handleSurvey = async (type: 'great' | 'normal') => {
  selectedSurvey.value = type
  await showAlert(t('heartTable.surveySuccess'), { 
    title: t('heartTable.surveyTitle'), 
    type: 'success' 
  })
}
</script>

<template>
  <div class="w-full mt-6 mb-6 bg-gradient-to-br from-[#FFF9F5] via-[#FFF3E0]/20 to-[#FFF9F5] border border-orange-100/60 rounded-[24px] p-6 shadow-[0_12px_36px_rgba(230,81,0,0.02)] transition-all duration-300">
    <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
      
      <!-- 좌측 영역: 타이틀 및 식사 투표 -->
      <div class="flex flex-col gap-4 flex-1 min-w-0">
        <!-- 타이틀과 설명 -->
        <div class="flex items-center gap-3">
          <span class="text-3xl select-none animate-pulse">💝</span>
          <div class="min-w-0">
            <h4 class="text-[19px] font-black text-gray-800 leading-tight">{{ t('heartTable.title') }}</h4>
            <p class="text-[13px] text-gray-400 mt-1 font-semibold">{{ t('heartTable.subtitle') }}</p>
          </div>
        </div>
        
        <!-- 오늘 식사 평가 (불투명 글래스 패널 형태) -->
        <div class="flex flex-wrap items-center gap-3 bg-white/70 backdrop-blur-[2px] p-2.5 px-4 rounded-2xl border border-orange-100/30 w-fit">
          <span class="text-sm font-black text-gray-500 uppercase tracking-wider">{{ t('heartTable.surveyTitle') }}</span>
          <div class="flex gap-2">
            <button 
              @click="handleSurvey('great')"
              :class="[
                'px-[18px] py-[9px] rounded-full text-[13.5px] font-black cursor-pointer transition-all duration-150 flex items-center gap-1.5 border outline-none',
                selectedSurvey === 'great' 
                  ? 'bg-gradient-to-r from-emerald-500 to-teal-600 text-white border-transparent shadow-md shadow-emerald-100' 
                  : 'bg-white hover:bg-gray-50 text-gray-600 border-gray-200/60'
              ]"
            >
              <span>😍</span> {{ t('heartTable.surveyGreat') }}
            </button>
            
            <button 
              @click="handleSurvey('normal')"
              :class="[
                'px-[18px] py-[9px] rounded-full text-[13.5px] font-black cursor-pointer transition-all duration-150 flex items-center gap-1.5 border outline-none',
                selectedSurvey === 'normal' 
                  ? 'bg-gradient-to-r from-emerald-500 to-teal-600 text-white border-transparent shadow-md shadow-emerald-100' 
                  : 'bg-white hover:bg-gray-50 text-gray-600 border-gray-200/60'
              ]"
            >
              <span>🙂</span> {{ t('heartTable.surveyNormal') }}
            </button>
          </div>
        </div>
      </div>

      <!-- 우측 영역: 기부 및 상담 버튼들 (상하 계층 배치) -->
      <div class="flex flex-col gap-2.5 shrink-0 w-full sm:w-[260px] lg:w-[280px]">
        <!-- 기부하기 버튼 -->
        <button 
          @click="handleDonate" 
          class="w-full bg-gradient-to-r from-[#FF6F00] to-[#FF8F00] text-white border-none py-3.5 px-5 lg:py-2.5 rounded-xl font-black cursor-pointer text-[14px] lg:text-[13px] hover:shadow-lg hover:shadow-orange-100/50 hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 flex items-center justify-center gap-2 shadow-md shadow-orange-100/30"
        >
          <span class="text-[16px]">🤝</span> {{ t('heartTable.donateBtn') }}
        </button>
        
        <!-- 상담하기 버튼 -->
        <button 
          @click="handleConsult" 
          class="w-full bg-gradient-to-r from-[#1E88E5] to-[#1565C0] text-white border-none py-3.5 px-5 lg:py-2.5 rounded-xl font-black cursor-pointer text-[14px] lg:text-[13px] hover:shadow-lg hover:shadow-blue-100/50 hover:scale-[1.02] active:scale-[0.98] transition-all duration-200 flex items-center justify-center gap-2 shadow-md shadow-blue-100/30"
        >
          <span class="text-[16px]">👩‍🍳</span> {{ t('heartTable.consultBtn') }}
        </button>
      </div>
      
    </div>

    <!-- 기부 결제 팝업 모달 -->
    <DonateModal :show="showDonateModal" @close="showDonateModal = false" />
  </div>
</template>
