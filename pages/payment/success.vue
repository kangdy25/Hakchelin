<script setup lang="ts">
import type { Database } from '~/types/database.types'

definePageMeta({
  layout: 'default'
})

const route = useRoute()
const supabase = useSupabaseClient<Database>()
const { refreshProfile } = useUserProfile()

const loading = ref(true)
const errorMessage = ref('')
const confirmedAmount = ref(0)

const confirmPayment = async () => {
  const paymentKey = String(route.query.paymentKey || '')
  const orderId = String(route.query.orderId || '')
  const amount = Number(route.query.amount || 0)

  if (!paymentKey || !orderId || !amount) {
    errorMessage.value = '결제 승인에 필요한 정보가 없습니다.'
    loading.value = false
    return
  }

  try {
    const { data, error } = await supabase.functions.invoke('confirm-toss-payment', {
      body: { paymentKey, orderId, amount }
    })

    if (error) throw error
    if (data?.error) throw new Error(data.error)

    confirmedAmount.value = Number(data?.order?.point_amount || amount)
    await refreshProfile()
  } catch (err: unknown) {
    errorMessage.value = (err as Error).message || '결제 승인 중 오류가 발생했습니다.'
  } finally {
    loading.value = false
  }
}

onMounted(confirmPayment)
</script>

<template>
  <div class="max-w-xl mx-auto bg-white border border-[#eee] rounded-[15px] p-8 text-center shadow-[0_2px_8px_rgba(0,0,0,0.05)]">
    <div v-if="loading">
      <div class="animate-spin rounded-full h-12 w-12 border-4 border-[#4ade80] border-t-transparent mx-auto mb-4"></div>
      <h1 class="text-xl font-black text-gray-800 mb-2">결제를 승인하고 있습니다</h1>
      <p class="text-sm text-gray-500">잠시만 기다려주세요.</p>
    </div>

    <div v-else-if="errorMessage">
      <h1 class="text-xl font-black text-red-600 mb-3">결제 승인 실패</h1>
      <p class="text-sm text-gray-600 mb-6">{{ errorMessage }}</p>
      <NuxtLink to="/" class="inline-flex px-5 py-3 bg-[#2E7D32] text-white rounded-lg font-bold text-sm">
        홈으로 돌아가기
      </NuxtLink>
    </div>

    <div v-else>
      <h1 class="text-xl font-black text-gray-800 mb-3">포인트 충전 완료</h1>
      <p class="text-sm text-gray-600 mb-6">{{ confirmedAmount.toLocaleString() }}P가 충전되었습니다.</p>
      <NuxtLink to="/" class="inline-flex px-5 py-3 bg-[#2E7D32] text-white rounded-lg font-bold text-sm">
        메뉴 예약하러 가기
      </NuxtLink>
    </div>
  </div>
</template>
