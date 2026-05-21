<script setup lang="ts">
definePageMeta({
  layout: 'default'
})

const route = useRoute()

const message = computed(() => String(route.query.message || '결제가 완료되지 않았습니다.'))
const code = computed(() => String(route.query.code || 'PAYMENT_FAILED'))
</script>

<template>
  <div class="max-w-xl mx-auto bg-white border border-[#eee] rounded-[15px] p-8 text-center shadow-[0_2px_8px_rgba(0,0,0,0.05)]">
    <h1 class="text-xl font-black text-red-600 mb-3">결제 실패</h1>
    <p class="text-sm text-gray-500 mb-2">{{ code }}</p>
    <p class="text-sm text-gray-700 mb-6">{{ message }}</p>
    <NuxtLink to="/" class="inline-flex px-5 py-3 bg-[#2E7D32] text-white rounded-lg font-bold text-sm">
      다시 시도하기
    </NuxtLink>
  </div>
</template>
