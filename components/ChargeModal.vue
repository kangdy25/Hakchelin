<script setup lang="ts">
import { ref, watch } from 'vue'
import type { Database } from '~/types/database.types'

const props = defineProps<{
  show: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const { t, locale } = useI18n()
const supabase = useSupabaseClient<Database>()
const config = useRuntimeConfig()
const { profile: userData, userId } = useUserProfile()
const { showAlert } = useModal()

const amount = ref<number>(10000)
const customAmountStr = ref<string>('')
const isCharging = ref(false)

const presets = [5000, 10000, 20000, 30000, 50000]

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
    amount.value = 10000
    customAmountStr.value = '10,000'
  }
})

const loadTossPayments = () => {
  return new Promise<any>((resolve, reject) => {
    if (typeof window === 'undefined') {
      reject(new Error('브라우저에서만 결제를 시작할 수 있습니다.'))
      return
    }

    const existingTossPayments = (window as any).TossPayments
    if (existingTossPayments) {
      resolve(existingTossPayments)
      return
    }

    const script = document.createElement('script')
    script.src = 'https://js.tosspayments.com/v2/standard'
    script.async = true
    script.onload = () => resolve((window as any).TossPayments)
    script.onerror = () => reject(new Error('토스페이먼츠 SDK를 불러오지 못했습니다.'))
    document.head.appendChild(script)
  })
}

const handlePayment = async () => {
  if (!userId.value) {
    showAlert('사용자 정보를 불러올 수 없습니다. 다시 로그인해 주세요.', {
      title: '오류',
      type: 'error'
    })
    return
  }

  if (amount.value < 1000) {
    showAlert('최소 충전 금액은 1,000원입니다.', {
      title: '금액 오류',
      type: 'warning'
    })
    return
  }

  const clientKey = config.public.tossPaymentsClientKey
  if (!clientKey) {
    showAlert('토스페이먼츠 클라이언트 키가 설정되지 않았습니다.', {
      title: '설정 오류',
      type: 'error'
    })
    return
  }

  isCharging.value = true
  try {
    const { data, error } = await supabase.rpc('create_point_order', {
      p_user_id: userId.value,
      p_amount: amount.value
    })

    if (error) throw error

    const order = Array.isArray(data) ? data[0] : data
    if (!order?.order_id) {
      throw new Error('충전 주문을 생성하지 못했습니다.')
    }

    const TossPayments = await loadTossPayments()
    const tossPayments = TossPayments(clientKey)
    const payment = tossPayments.payment({ customerKey: userId.value })

    await payment.requestPayment({
      method: 'CARD',
      card: {
        flowMode: 'DEFAULT'
      },
      amount: {
        currency: 'KRW',
        value: order.amount
      },
      orderId: order.order_id,
      orderName: `${order.point_amount.toLocaleString()}P 포인트 충전`,
      customerName: userData.value.name,
      successUrl: `${window.location.origin}/payment/success`,
      failUrl: `${window.location.origin}/payment/fail`
    })
  } catch (err: unknown) {
    showAlert('결제 시작 중 오류가 발생했습니다: ' + (err as Error).message, {
      title: '결제 실패',
      type: 'error'
    })
  } finally {
    isCharging.value = false
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
            <span>🪙</span>
            <span>{{ t('payment.charge') }}</span>
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
            {{ locale === 'ko' ? '충전할 포인트 금액을 선택하거나 직접 입력해주세요. (1원 = 1포인트)' : 'Please select or enter the amount of points to charge. (1 KRW = 1 Point)' }}
          </p>

          <!-- Presets -->
          <div class="grid grid-cols-3 gap-2">
            <button 
              v-for="preset in presets" 
              :key="preset"
              @click="selectPreset(preset)"
              class="py-2.5 px-2 bg-gray-50 hover:bg-green-50 hover:text-[#2E7D32] hover:border-green-300 border border-gray-200/80 rounded-xl text-xs font-bold text-gray-700 transition-all duration-150 cursor-pointer"
              :class="{ 'bg-green-50 text-[#2E7D32] border-[#2E7D32] ring-2 ring-green-100': amount === preset }"
            >
              +{{ preset.toLocaleString() }}P
            </button>
          </div>

          <!-- Input field -->
          <div class="relative">
            <input 
              type="text" 
              v-model="customAmountStr"
              class="w-full pl-4 pr-12 py-3.5 bg-gray-50 border border-gray-200 focus:bg-white focus:border-[#2E7D32] focus:ring-4 focus:ring-green-100 outline-none rounded-xl text-base font-bold text-gray-800 transition-all duration-200"
              :placeholder="locale === 'ko' ? '직접 입력 (최소 1,000P)' : 'Enter amount (min 1,000P)'"
            />
            <span class="absolute right-4 top-1/2 -translate-y-1/2 font-black text-gray-400 text-sm">
              KRW
            </span>
          </div>

          <!-- Summary info -->
          <div class="bg-gray-50 border border-gray-100 rounded-2xl p-4 flex justify-between items-center">
            <span class="text-xs text-gray-500 font-bold">
              {{ locale === 'ko' ? '충전 후 예상 포인트' : 'Est. Points After Charge' }}
            </span>
            <div class="text-right">
              <span class="text-xs text-gray-400 line-through mr-1.5">
                {{ (userData?.current_point || 0).toLocaleString() }}P
              </span>
              <strong class="text-base text-[#2E7D32] font-black">
                {{ ((userData?.current_point || 0) + amount).toLocaleString() }} P
              </strong>
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex gap-3 w-full mt-6">
          <button 
            @click="emit('close')"
            :disabled="isCharging"
            class="flex-1 py-3.5 bg-gray-100 hover:bg-gray-200 active:scale-[0.98] text-gray-600 font-bold rounded-xl transition-all duration-150 cursor-pointer disabled:opacity-50"
          >
            {{ t('admin.menus.cancel') || '취소' }}
          </button>
          <button 
            @click="handlePayment"
            :disabled="isCharging"
            class="flex-1 py-3.5 bg-[#2E7D32] hover:bg-primary-dark active:scale-[0.98] text-white font-bold rounded-xl shadow-lg shadow-green-100 transition-all duration-150 cursor-pointer flex items-center justify-center gap-2 disabled:opacity-50"
          >
            <div v-if="isCharging" class="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
            <span>{{ isCharging ? '결제 진행중...' : t('charge') || '충전하기' }}</span>
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
