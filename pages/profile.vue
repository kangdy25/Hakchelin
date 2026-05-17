<script setup lang="ts">
const { t } = useI18n({ useScope: 'global' })
const supabase = useSupabaseClient()
const user = useSupabaseUser()

const handleLogout = async () => {
  const { error } = await supabase.auth.signOut()
  if (!error) {
    navigateTo('/login')
  } else {
    alert(t('logout_error'))
  }
}
</script>

<template>
  <div>
    <h1 class="text-2xl md:text-3xl font-black text-gray-800 mb-6">{{ t('my_profile') }}</h1>
    
    <div class="bg-white rounded-[2rem] p-8 text-center shadow-[0_2px_8px_rgba(0,0,0,0.05)] border border-[#eee] flex flex-col items-center justify-center min-h-[50vh]">
      <div class="w-24 h-24 bg-gradient-to-tr from-[#4ade80] to-[#22c55e] rounded-full flex items-center justify-center text-4xl text-white mb-6 shadow-lg shadow-green-200">
        {{ user?.user_metadata?.name?.[0] || '👤' }}
      </div>
      <h2 class="text-2xl font-bold text-gray-800 mb-1">{{ user?.user_metadata?.name || t('student') }}</h2>
      <p class="text-gray-500 font-medium mb-2">{{ t('student_id') }} {{ user?.user_metadata?.student_id || '-' }}</p>
      <p class="text-gray-400 text-sm mb-8">{{ user?.email }}</p>
      
      <button 
        @click="handleLogout"
        class="px-8 py-3 bg-red-50 text-red-600 hover:bg-red-100 font-bold rounded-xl transition-colors w-full max-w-xs"
      >
        {{ t('logout') }}
      </button>
    </div>
  </div>
</template>
