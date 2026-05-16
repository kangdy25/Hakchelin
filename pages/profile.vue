<script setup lang="ts">
const { t } = useI18n({ useScope: 'global' })
</script>

<template>
  <div>
    <h1 class="text-2xl md:text-3xl font-black text-gray-800 mb-6">{{ t('my_profile') }}</h1>
    
    <div class="bg-white rounded-[2rem] p-8 text-center shadow-[0_2px_8px_rgba(0,0,0,0.05)] border border-[#eee] flex flex-col items-center justify-center min-h-[40vh]">
      <div class="text-6xl mb-6">👤</div>
      <h2 class="text-xl font-bold text-gray-700 mb-2">{{ t('coming_soon') }}</h2>
      <p class="text-[#777] font-medium">{{ t('empty_profile') }}</p>
    </div>
  </div>
</template>
