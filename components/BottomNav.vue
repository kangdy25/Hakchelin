<script setup lang="ts">
const { t } = useI18n({ useScope: 'global' })
const user = useSupabaseUser()
const { isAdmin } = useUserProfile()
</script>

<template>
  <div>
    <!-- Mobile Bottom Nav -->
    <nav class="md:hidden fixed bottom-0 w-full bg-white flex justify-around py-[12px] border-t border-[#eee] z-50 pb-safe">
      <NuxtLink to="/" class="flex flex-col items-center text-[#999] text-[11px]" active-class="!text-[#2E7D32] font-bold">
        <span class="text-xl mb-1">🏠</span>
        <span>{{ t('nav0') }}</span>
      </NuxtLink>
      <NuxtLink to="/tickets" class="flex flex-col items-center text-[#999] text-[11px]" active-class="!text-[#2E7D32] font-bold">
        <span class="text-xl mb-1">🎫</span>
        <span>{{ t('nav1') }}</span>
      </NuxtLink>
      <NuxtLink to="/history" class="flex flex-col items-center text-[#999] text-[11px]" active-class="!text-[#2E7D32] font-bold">
        <span class="text-xl mb-1">💳</span>
        <span>{{ t('nav2') }}</span>
      </NuxtLink>
      <NuxtLink v-if="isAdmin" to="/admin" class="flex flex-col items-center text-[#999] text-[11px]" active-class="!text-[#2E7D32] font-bold">
        <span class="text-xl mb-1">🛠️</span>
        <span>{{ t('nav_admin') }}</span>
      </NuxtLink>
      <NuxtLink to="/profile" class="flex flex-col items-center text-[#999] text-[11px]" active-class="!text-[#2E7D32] font-bold">
        <span class="text-xl mb-1">👤</span>
        <span>{{ t('nav3') }}</span>
      </NuxtLink>
    </nav>

    <!-- Desktop Sidebar -->
    <aside class="hidden md:flex flex-col fixed top-0 left-0 h-screen w-64 lg:w-72 bg-white border-r border-[#eee] z-50 py-[25px] px-[20px]">
      <div class="text-[24px] font-bold text-[#2E7D32] mb-[30px] flex items-center gap-3">
        <span>🍽️</span> {{ t('app_name') }}
      </div>
      
      <div class="flex flex-col gap-[10px] flex-1">
        <NuxtLink to="/" class="flex items-center gap-4 px-[15px] py-[12px] text-[#999] rounded-[8px] font-bold hover:bg-[#f8f9fa]" active-class="bg-[#E8F5E9] !text-[#2E7D32]">
          <span class="text-[18px]">🏠</span>
          <span class="text-[15px]">{{ t('nav0') }}</span>
        </NuxtLink>
        <NuxtLink to="/tickets" class="flex items-center gap-4 px-[15px] py-[12px] text-[#999] rounded-[8px] font-bold hover:bg-[#f8f9fa]" active-class="bg-[#E8F5E9] !text-[#2E7D32]">
          <span class="text-[18px]">🎫</span>
          <span class="text-[15px]">{{ t('nav1') }}</span>
        </NuxtLink>
        <NuxtLink to="/history" class="flex items-center gap-4 px-[15px] py-[12px] text-[#999] rounded-[8px] font-bold hover:bg-[#f8f9fa]" active-class="bg-[#E8F5E9] !text-[#2E7D32]">
          <span class="text-[18px]">💳</span>
          <span class="text-[15px]">{{ t('nav2') }}</span>
        </NuxtLink>
        <NuxtLink v-if="isAdmin" to="/admin" class="flex items-center gap-4 px-[15px] py-[12px] text-[#999] rounded-[8px] font-bold hover:bg-[#f8f9fa]" active-class="bg-[#E8F5E9] !text-[#2E7D32]">
          <span class="text-[18px]">🛠️</span>
          <span class="text-[15px]">{{ t('nav_admin') }}</span>
        </NuxtLink>
        <NuxtLink to="/profile" class="flex items-center gap-4 px-[15px] py-[12px] text-[#999] rounded-[8px] font-bold hover:bg-[#f8f9fa]" active-class="bg-[#E8F5E9] !text-[#2E7D32]">
          <span class="text-[18px]">👤</span>
          <span class="text-[15px]">{{ t('nav3') }}</span>
        </NuxtLink>
      </div>
      
      <div class="mt-auto bg-[#f8f9fa] p-[15px] rounded-[10px] border border-[#eee] flex items-center gap-3">
         <div class="w-[40px] h-[40px] bg-white rounded-[20px] flex items-center justify-center text-[#2E7D32] font-bold border border-[#ddd] overflow-hidden">
            {{ user?.user_metadata?.name?.[0] || '👤' }}
         </div>
         <div>
           <div class="font-bold text-[14px]">{{ user?.user_metadata?.name || '학생' }}</div>
           <div class="text-[12px] text-[#777]">{{ user?.user_metadata?.student_id || 'N/A' }}</div>
         </div>
      </div>
    </aside>
  </div>
</template>

<style>
.pb-safe { padding-bottom: env(safe-area-inset-bottom); }
</style>
