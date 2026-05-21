<script setup lang="ts">
const { t, locale } = useI18n({ useScope: 'global' })
const supabase = useSupabaseClient<any>()
const { userId } = useUserProfile()

type Transaction = {
  id: string
  amount: number
  type: 'charge' | 'deduct' | 'refund'
  description: string | null
  created_at: string
}

const loading = ref(true)
const errorMessage = ref('')
const transactions = ref<Transaction[]>([])

const formatDate = (value: string) => {
  return new Intl.DateTimeFormat(locale.value === 'ko' ? 'ko-KR' : 'en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(new Date(value))
}

const fetchTransactions = async () => {
  if (!userId.value) {
    loading.value = false
    return
  }

  loading.value = true
  errorMessage.value = ''

  const { data, error } = await supabase
    .from('transactions')
    .select('id, amount, type, description, created_at')
    .eq('user_id', userId.value)
    .order('created_at', { ascending: false })

  if (error) {
    errorMessage.value = error.message
  } else {
    transactions.value = data || []
  }

  loading.value = false
}

watch(
  () => userId.value,
  () => fetchTransactions(),
  { immediate: true }
)
</script>

<template>
  <div>
    <h1 class="text-2xl md:text-3xl font-black text-gray-800 mb-6">{{ t('point_history') }}</h1>

    <div v-if="loading" class="bg-white rounded-[15px] p-8 text-center border border-[#eee]">
      <div class="animate-spin rounded-full h-10 w-10 border-4 border-[#4ade80] border-t-transparent mx-auto mb-4"></div>
      <p class="text-sm text-gray-500">{{ t('payment.loading_history') }}</p>
    </div>

    <div v-else-if="errorMessage" class="bg-red-50 text-red-600 rounded-[15px] p-5 border border-red-100 text-sm font-bold">
      {{ errorMessage }}
    </div>

    <div v-else-if="!transactions.length" class="bg-white rounded-[15px] p-8 text-center shadow-[0_2px_8px_rgba(0,0,0,0.05)] border border-[#eee] flex flex-col items-center justify-center min-h-[40vh]">
      <div class="text-5xl mb-6">💳</div>
      <p class="text-[#777] font-medium">{{ t('empty_history') }}</p>
    </div>

    <div v-else class="bg-white border border-[#eee] rounded-[15px] overflow-hidden shadow-[0_2px_8px_rgba(0,0,0,0.05)]">
      <div
        v-for="transaction in transactions"
        :key="transaction.id"
        class="flex items-center justify-between gap-4 p-5 border-b border-[#eee] last:border-b-0"
      >
        <div>
          <div class="text-[14px] font-black text-gray-800">
            {{ transaction.description === '포인트 충전' ? t('payment.charge') : (transaction.description === '메뉴 예약' ? t('payment.use') : (transaction.description || (transaction.type === 'charge' ? t('payment.charge') : t('payment.use')))) }}
          </div>
          <div class="text-[12px] text-[#777] mt-1">{{ formatDate(transaction.created_at) }}</div>
        </div>

        <div class="text-right">
          <div 
            :class="[
              'font-black text-[18px]',
              transaction.amount > 0 ? 'text-[#2E7D32]' : 'text-gray-800'
            ]"
          >
            {{ transaction.amount > 0 ? '+' : '' }}{{ transaction.amount.toLocaleString() }}{{ t('payment.unit') }}
          </div>
          <div class="text-[11px] text-[#777] mt-1">
            {{ transaction.type === 'charge' ? t('payment.complete') : t('payment.used') }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
