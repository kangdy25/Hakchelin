<script setup lang="ts">
import { onMounted, ref } from 'vue'
import type { Database } from '~/types/database.types'

type AiLog = {
  id: string
  created_at: string
  stage: string
  model: string | null
  latency_ms: number
  status_code: number
  error_message: string | null
  users?: { name: string, student_id: string } | null
}

const supabase = useSupabaseClient<Database>()
const { locale } = useI18n({ useScope: 'global' })
const loading = ref(true)
const logs = ref<AiLog[]>([])
const error = ref('')

const isKo = computed(() => locale.value === 'ko')
const formatDate = (value: string) => new Intl.DateTimeFormat(isKo.value ? 'ko-KR' : 'en-US', {
  month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
}).format(new Date(value))

const load = async () => {
  loading.value = true
  error.value = ''
  const { data: logRows, error: logError } = await supabase
    .from('ai_logs').select('id, created_at, stage, model, latency_ms, status_code, error_message, users(name, student_id)')
    .order('created_at', { ascending: false }).limit(50)
  if (!logError && logRows) logs.value = logRows as unknown as AiLog[]
  if (logError) error.value = logError.message
  loading.value = false
}

onMounted(load)
</script>

<template>
  <section class="space-y-5">
    <div class="rounded-3xl border border-gray-100 bg-white p-5 shadow-sm">
      <div>
        <div>
          <h2 class="text-lg font-black text-gray-900">🤖 {{ isKo ? 'AI 관리' : 'AI Control' }}</h2>
          <p class="mt-1 text-xs font-medium text-gray-500">{{ isKo ? '프롬프트와 가드레일은 개발자가 코드 배포로만 관리합니다. 이 화면에서는 운영 로그를 확인할 수 있습니다.' : 'Prompts and guardrails are managed only through developer deployments. This page provides operational logs.' }}</p>
        </div>
      </div>
    </div>

    <div class="overflow-hidden rounded-3xl border border-gray-100 bg-white shadow-sm">
      <div class="border-b border-gray-100 px-5 py-4"><h2 class="font-black text-gray-900">{{ isKo ? '최근 AI 요청 로그' : 'Recent AI request logs' }}</h2></div>
      <div class="overflow-x-auto">
        <table class="w-full min-w-[700px] text-left text-xs">
          <thead class="bg-gray-50 text-gray-500"><tr><th class="px-5 py-3">{{ isKo ? '시각' : 'Time' }}</th><th class="px-5 py-3">{{ isKo ? '사용자' : 'User' }}</th><th class="px-5 py-3">Stage</th><th class="px-5 py-3">Model</th><th class="px-5 py-3">Latency</th><th class="px-5 py-3">Status</th><th class="px-5 py-3">Error</th></tr></thead>
          <tbody class="divide-y divide-gray-100 text-gray-700">
            <tr v-for="log in logs" :key="log.id"><td class="px-5 py-3">{{ formatDate(log.created_at) }}</td><td class="px-5 py-3">{{ log.users?.name || '-' }}</td><td class="px-5 py-3 font-bold">{{ log.stage }}</td><td class="px-5 py-3">{{ log.model || '-' }}</td><td class="px-5 py-3">{{ log.latency_ms }}ms</td><td class="px-5 py-3"><span :class="log.status_code < 400 ? 'text-green-700' : 'text-red-600'" class="font-black">{{ log.status_code }}</span></td><td class="max-w-xs truncate px-5 py-3 text-red-500">{{ log.error_message || '-' }}</td></tr>
            <tr v-if="loading"><td colspan="7" class="px-5 py-10 text-center text-gray-400">Loading...</td></tr>
            <tr v-else-if="!logs.length"><td colspan="7" class="px-5 py-10 text-center text-gray-400">{{ isKo ? '아직 AI 요청 기록이 없습니다.' : 'No AI requests yet.' }}</td></tr>
          </tbody>
        </table>
      </div>
      <p v-if="error" class="m-4 rounded-xl bg-red-50 p-3 text-xs font-bold text-red-600">{{ error }}</p>
    </div>
  </section>
</template>
