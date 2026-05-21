<script setup lang="ts">
const { t, locale, setLocale } = useI18n({ useScope: 'global' })

const toggleLanguage = async () => {
  await setLocale(locale.value === 'ko' ? 'en' : 'ko')
}

const supabase = useSupabaseClient<any>()
const config = useRuntimeConfig()
const { profile: userData, userId } = useUserProfile()

const isCharging = ref(false)

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

const handleCharge = async () => {
  if (!userId.value) {
    alert('사용자 정보를 불러올 수 없습니다. 새로고침 후 다시 시도해주세요.')
    return
  }

  const amountStr = prompt('충전할 포인트 금액을 입력하세요 (예: 10000):', '10000')
  if (!amountStr) return

  const amount = parseInt(amountStr, 10)
  if (isNaN(amount) || amount <= 0) {
    alert('올바른 금액을 입력해주세요.')
    return
  }

  const clientKey = config.public.tossPaymentsClientKey
  if (!clientKey) {
    alert('토스페이먼츠 클라이언트 키가 설정되지 않았습니다.')
    return
  }

  isCharging.value = true
  try {
    const { data, error } = await supabase.rpc('create_point_order', {
      p_user_id: userId.value,
      p_amount: amount
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
  } catch (err: any) {
    alert('결제 시작 중 오류가 발생했습니다: ' + err.message)
  } finally {
    isCharging.value = false
  }
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
        :disabled="isCharging"
        class="bg-[#4CAF50] text-white border-none py-[6px] px-[12px] rounded-[6px] font-bold cursor-pointer text-[12px] disabled:opacity-50"
      >
        {{ isCharging ? '처리중...' : t('charge') }}
      </button>
    </div>
  </header>
</template>
