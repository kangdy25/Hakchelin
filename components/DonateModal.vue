<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import type { Database } from '~/types/database.types'

const props = defineProps<{
  show: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const { t, locale } = useI18n()
const supabase = useSupabaseClient<Database>()
const { profile: userData, userId, refreshProfile, adjustPoint } = useUserProfile()
const { showAlert } = useModal()

const amount = ref<number>(1000)
const customAmountStr = ref<string>('1,000')
const isDonating = ref(false)

const presets = [1000, 3000, 5000, 10000]

// 1,000P 미만 잔돈 계산
const restAmount = computed(() => {
  const current = userData.value?.current_point || 0
  return current % 1000
})

// 직접 입력 폼 변경 시 감지
watch(customAmountStr, (newVal) => {
  const parsed = parseInt(newVal.replace(/[^0-9]/g, ''), 10)
  if (!isNaN(parsed)) {
    amount.value = parsed
  } else if (newVal === '') {
    amount.value = 0
  }
})

// 프리셋 선택 시 작동
const selectPreset = (val: number) => {
  amount.value = val
  customAmountStr.value = val.toLocaleString()
}

// 초기화
watch(() => props.show, (newVal) => {
  if (newVal) {
    amount.value = 1000
    customAmountStr.value = '1,000'
  }
})

// 기부 가능 여부 검증
const isValidAmount = computed(() => {
  if (amount.value <= 0) return false
  const current = userData.value?.current_point || 0
  return amount.value <= current
})

const handleDonate = async () => {
  if (!userId.value) {
    showAlert('사용자 정보를 불러올 수 없습니다. 다시 로그인해 주세요.', {
      title: '오류',
      type: 'error'
    })
    return
  }

  if (amount.value <= 0) {
    showAlert('기부 금액은 0P보다 커야 합니다.', {
      title: '금액 오류',
      type: 'warning'
    })
    return
  }

  const current = userData.value?.current_point || 0
  if (amount.value > current) {
    showAlert('보유 포인트보다 더 많은 금액은 기부할 수 없습니다.', {
      title: '포인트 부족',
      type: 'warning'
    })
    return
  }

  const confirmMsg = locale.value === 'ko' 
    ? `${amount.value.toLocaleString()}P를 기부하시겠습니까?` 
    : `Would you like to donate ${amount.value.toLocaleString()}P?`

  if (!confirm(confirmMsg)) {
    return
  }

  isDonating.value = true
  try {
    const { error } = await supabase.rpc('donate_points', {
      p_user_id: userId.value,
      p_amount: amount.value
    })

    if (error) throw error

    // 로컬 포인트 실시간 차감 반영
    adjustPoint(-amount.value)
    await refreshProfile()

    await showAlert(t('heartTable.donateSuccess'), {
      title: t('heartTable.title'),
      type: 'success'
    })
    emit('close')
  } catch (err: unknown) {
    showAlert('기부 진행 중 오류가 발생했습니다: ' + (err as Error).message, {
      title: '기부 실패',
      type: 'error'
    })
  } finally {
    isDonating.value = false
  }
}
</script>

<template>
  <Transition name="modal-fade">
    <div 
      v-if="show" 
      class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-[4px]"
      @click.self="emit('close')"
    >
      <div class="bg-white rounded-[24px] p-6 max-w-md w-full shadow-[0_20px_50px_rgba(0,0,0,0.15)] border border-gray-100 flex flex-col transform transition-all duration-300 scale-100">
        
        <!-- Header -->
        <div class="flex justify-between items-center mb-6">
          <h3 class="text-xl font-bold text-gray-800 flex items-center gap-2">
            <span>🤝</span>
            <span>{{ t('heartTable.donateBtn') }}</span>
          </h3>
          <button 
            @click="emit('close')"
            class="text-gray-400 hover:text-gray-600 bg-gray-50 hover:bg-gray-100 w-8 h-8 rounded-full flex items-center justify-center transition-colors cursor-pointer"
          >
            ✕
          </button>
        </div>

        <!-- Body -->
        <div class="space-y-5">
          <!-- Guide Text -->
          <p class="text-sm text-gray-500 font-medium leading-relaxed">
            {{ locale === 'ko' ? '기부할 포인트 금액을 선택하거나 직접 입력해주세요.' : 'Please select or enter the amount of points to donate.' }}
          </p>

          <!-- Presets -->
          <div class="grid grid-cols-2 gap-2">
            <button 
              v-for="preset in presets" 
              :key="preset"
              @click="selectPreset(preset)"
              class="py-2.5 px-2 bg-gray-50 hover:bg-orange-50 hover:text-[#E65100] hover:border-orange-300 border border-gray-200/80 rounded-xl text-xs font-bold text-gray-700 transition-all duration-150 cursor-pointer"
              :class="{ 'bg-orange-50 text-[#E65100] border-[#E65100] ring-2 ring-orange-100': amount === preset }"
            >
              +{{ preset.toLocaleString() }}P
            </button>
            
            <!-- 잔돈 기부하기 버튼 -->
            <button 
              v-if="restAmount > 0"
              @click="selectPreset(restAmount)"
              class="col-span-2 py-2.5 px-2 bg-orange-50 hover:bg-orange-100 text-[#E65100] border border-orange-200 rounded-xl text-xs font-bold transition-all duration-150 cursor-pointer text-center flex items-center justify-center gap-1"
              :class="{ 'ring-2 ring-orange-200 border-[#E65100]': amount === restAmount }"
            >
              <span>🪙</span> {{ locale === 'ko' ? `잔돈 전액 기부 (${restAmount.toLocaleString()}P)` : `Donate remaining change (${restAmount.toLocaleString()}P)` }}
            </button>
          </div>

          <!-- Input field -->
          <div class="relative">
            <input 
              type="text" 
              v-model="customAmountStr"
              class="w-full pl-4 pr-12 py-3.5 bg-gray-50 border border-gray-200 focus:bg-white focus:border-[#E65100] focus:ring-4 focus:ring-orange-100 outline-none rounded-xl text-base font-bold text-gray-800 transition-all duration-200"
              :placeholder="locale === 'ko' ? '직접 입력' : 'Enter amount'"
            />
            <span class="absolute right-4 top-1/2 -translate-y-1/2 font-black text-gray-400 text-sm">
              Point
            </span>
          </div>

          <!-- Summary info -->
          <div class="bg-gray-50 border border-gray-100 rounded-2xl p-4 flex justify-between items-center">
            <span class="text-xs text-gray-500 font-bold">
              {{ locale === 'ko' ? '기부 후 잔여 포인트' : 'Est. Points After Donation' }}
            </span>
            <div class="text-right">
              <span class="text-xs text-gray-400 line-through mr-1.5">
                {{ (userData?.current_point || 0).toLocaleString() }}P
              </span>
              <strong class="text-base text-[#E65100] font-black">
                {{ Math.max(0, (userData?.current_point || 0) - amount).toLocaleString() }} P
              </strong>
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex gap-3 w-full mt-6">
          <button 
            @click="emit('close')"
            :disabled="isDonating"
            class="flex-1 py-3.5 bg-gray-100 hover:bg-gray-200 active:scale-[0.98] text-gray-600 font-bold rounded-xl transition-all duration-150 cursor-pointer disabled:opacity-50"
          >
            {{ t('admin.menus.cancel') || '취소' }}
          </button>
          <button 
            @click="handleDonate"
            :disabled="isDonating || !isValidAmount"
            class="flex-1 py-3.5 bg-[#E65100] hover:bg-[#F57C00] active:scale-[0.98] text-white font-bold rounded-xl shadow-lg shadow-orange-100 transition-all duration-150 cursor-pointer flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <div v-if="isDonating" class="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
            <span>{{ isDonating ? '기부 진행중...' : locale === 'ko' ? '기부하기' : 'Donate' }}</span>
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.25s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-active .transform,
.modal-fade-leave-active .transform {
  transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.modal-fade-enter-from .transform {
  transform: scale(0.9) translateY(10px);
}

.modal-fade-leave-to .transform {
  transform: scale(0.95) translateY(0);
}
</style>
