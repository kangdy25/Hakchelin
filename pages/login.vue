<script setup lang="ts">
import { ref } from 'vue'

definePageMeta({
  layout: 'auth'
})

const supabase = useSupabaseClient()
const authUser = useSupabaseUser()
const isLoginMode = ref(true)
const email = ref('')
const password = ref('')
const name = ref('')
const studentId = ref('')
const loading = ref(false)
const errorMessage = ref('')

const toggleMode = () => {
  isLoginMode.value = !isLoginMode.value
  errorMessage.value = ''
}

const handleSubmit = async () => {
  loading.value = true
  errorMessage.value = ''
  
  try {
    if (isLoginMode.value) {
      // Login
      const { error } = await supabase.auth.signInWithPassword({
        email: email.value,
        password: password.value,
      })
      if (error) throw error

      const { data: claimsData } = await supabase.auth.getClaims()
      authUser.value = claimsData?.claims ?? null
      await navigateTo('/', { replace: true })
    } else {
      // Signup
      const { error } = await supabase.auth.signUp({
        email: email.value,
        password: password.value,
        options: {
          data: {
            name: name.value,
            student_id: studentId.value,
            role: 'student'
          }
        }
      })
      if (error) throw error
      
      alert('회원가입이 완료되었습니다! 화면이 로그인으로 전환됩니다.')
      isLoginMode.value = true
      password.value = ''
    }
  } catch (error: any) {
    errorMessage.value = error.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="w-full max-w-md bg-white/80 backdrop-blur-md rounded-2xl shadow-xl overflow-hidden p-8 border border-white">
    <div class="text-center mb-8">
      <h1 class="text-3xl font-bold text-gray-900 tracking-tight">Smart Campus Meal</h1>
      <p class="text-gray-500 mt-2 text-sm">
        {{ isLoginMode ? '학식 예약을 위해 로그인해주세요' : '학식 예약을 위한 계정을 생성합니다' }}
      </p>
    </div>

    <form @submit.prevent="handleSubmit" class="space-y-5">
      <div v-if="!isLoginMode" class="space-y-5">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">학번 (Student ID)</label>
          <input 
            v-model="studentId" 
            type="text" 
            required
            class="w-full px-4 py-3 rounded-xl border border-gray-200 bg-white/50 focus:outline-none focus:ring-2 focus:ring-[#4ade80] focus:border-transparent transition-all"
            placeholder="예: 20240001"
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">이름 (Name)</label>
          <input 
            v-model="name" 
            type="text" 
            required
            class="w-full px-4 py-3 rounded-xl border border-gray-200 bg-white/50 focus:outline-none focus:ring-2 focus:ring-[#4ade80] focus:border-transparent transition-all"
            placeholder="홍길동"
          />
        </div>
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">이메일 (Email)</label>
        <input 
          v-model="email" 
          type="email" 
          required
          class="w-full px-4 py-3 rounded-xl border border-gray-200 bg-white/50 focus:outline-none focus:ring-2 focus:ring-[#4ade80] focus:border-transparent transition-all"
          placeholder="your@email.com"
        />
      </div>

      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">비밀번호 (Password)</label>
        <input 
          v-model="password" 
          type="password" 
          required
          class="w-full px-4 py-3 rounded-xl border border-gray-200 bg-white/50 focus:outline-none focus:ring-2 focus:ring-[#4ade80] focus:border-transparent transition-all"
          placeholder="••••••••"
        />
      </div>

      <div v-if="errorMessage" class="p-3 bg-red-50 text-red-600 rounded-lg text-sm border border-red-100">
        {{ errorMessage }}
      </div>

      <button 
        type="submit" 
        :disabled="loading"
        class="w-full py-3.5 px-4 bg-gradient-to-r from-[#4ade80] to-[#22c55e] hover:from-[#22c55e] hover:to-[#16a34a] text-white rounded-xl font-bold shadow-lg shadow-green-200/50 transition-all transform hover:-translate-y-0.5 disabled:opacity-70 disabled:cursor-not-allowed disabled:transform-none"
      >
        <span v-if="loading" class="animate-pulse">처리 중...</span>
        <span v-else>{{ isLoginMode ? '로그인' : '회원가입' }}</span>
      </button>
    </form>

    <div class="mt-8 text-center">
      <p class="text-sm text-gray-600">
        {{ isLoginMode ? '아직 계정이 없으신가요?' : '이미 계정이 있으신가요?' }}
        <button 
          @click="toggleMode" 
          class="ml-1 text-[#16a34a] font-semibold hover:underline"
          type="button"
        >
          {{ isLoginMode ? '회원가입' : '로그인' }}
        </button>
      </p>
    </div>
  </div>
</template>
