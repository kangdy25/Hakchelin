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
const saving = ref(false)
const promptContent = ref('')
const temperature = ref(0.2)
const activeVersion = ref<number | null>(null)
const logs = ref<AiLog[]>([])
const error = ref('')

const isKo = computed(() => locale.value === 'ko')
const formatDate = (value: string) => new Intl.DateTimeFormat(isKo.value ? 'ko-KR' : 'en-US', {
  month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
}).format(new Date(value))

const load = async () => {
  loading.value = true
  error.value = ''
  const [{ data: prompt, error: promptError }, { data: logRows, error: logError }] = await Promise.all([
    supabase.from('prompt_templates').select('*').eq('service_name', 'meal_helper_chatbot').eq('is_active', true).single(),
    supabase.from('ai_logs').select('id, created_at, stage, model, latency_ms, status_code, error_message, users(name, student_id)').order('created_at', { ascending: false }).limit(50)
  ])
  if (promptError || !prompt) error.value = promptError?.message || '활성 프롬프트를 찾을 수 없습니다.'
  else {
    promptContent.value = prompt.prompt_content
    temperature.value = Number(prompt.temperature)
    activeVersion.value = prompt.version
  }
  if (!logError && logRows) logs.value = logRows as unknown as AiLog[]
  loading.value = false
}

const publish = async () => {
  if (!promptContent.value.trim() || saving.value) return
  saving.value = true
  error.value = ''
  try {
    const { data: versions, error: versionError } = await supabase
      .from('prompt_templates').select('version').eq('service_name', 'meal_helper_chatbot').order('version', { ascending: false }).limit(1)
    if (versionError) throw versionError
    const nextVersion = Number(versions?.[0]?.version || 0) + 1
    const { error: insertError } = await supabase.from('prompt_templates').insert({
      service_name: 'meal_helper_chatbot', version: nextVersion, prompt_content: promptContent.value.trim(), temperature: temperature.value, is_active: false
    })
    if (insertError) throw insertError
    const { error: deactivateError } = await supabase.from('prompt_templates').update({ is_active: false })
      .eq('service_name', 'meal_helper_chatbot').eq('is_active', true)
    if (deactivateError) throw deactivateError
    const { error: activateError } = await supabase.from('prompt_templates').update({ is_active: true })
      .eq('service_name', 'meal_helper_chatbot').eq('version', nextVersion)
    if (activateError) throw activateError
    await load()
  } catch (err) {
    error.value = err instanceof Error ? err.message : '프롬프트 배포에 실패했습니다.'
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="space-y-5">
    <div class="rounded-3xl border border-gray-100 bg-white p-5 shadow-sm">
      <div class="mb-4 flex items-start justify-between gap-4">
        <div>
          <h2 class="text-lg font-black text-gray-900">🤖 {{ isKo ? 'AI 관리' : 'AI Control' }}</h2>
          <p class="mt-1 text-xs font-medium text-gray-500">{{ isKo ? '응답 프롬프트를 새 버전으로 배포합니다. 가드레일은 코드로 고정됩니다.' : 'Publish response-prompt versions. Guardrails remain fixed in code.' }}</p>
        </div>
        <span class="rounded-full bg-green-50 px-3 py-1 text-xs font-black text-[#2E7D32]">v{{ activeVersion || '-' }}</span>
      </div>
      <div v-if="loading" class="py-10 text-center text-sm text-gray-400">Loading...</div>
      <form v-else @submit.prevent="publish" class="space-y-4">
        <textarea v-model="promptContent" rows="8" required class="w-full rounded-2xl border border-gray-200 p-3 text-sm leading-relaxed outline-none focus:border-[#2E7D32]" />
        <div class="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
          <label class="text-sm font-bold text-gray-600">Temperature <input v-model.number="temperature" type="number" min="0" max="1" step="0.1" class="ml-2 w-20 rounded-lg border border-gray-200 px-2 py-1" /></label>
          <button :disabled="saving" class="rounded-xl bg-[#2E7D32] px-4 py-2.5 text-sm font-bold text-white disabled:opacity-50">{{ saving ? 'Publishing...' : (isKo ? '새 버전 배포' : 'Publish new version') }}</button>
        </div>
      </form>
      <p v-if="error" class="mt-3 rounded-xl bg-red-50 p-3 text-xs font-bold text-red-600">{{ error }}</p>
    </div>

    <div class="overflow-hidden rounded-3xl border border-gray-100 bg-white shadow-sm">
      <div class="border-b border-gray-100 px-5 py-4"><h2 class="font-black text-gray-900">{{ isKo ? '최근 AI 요청 로그' : 'Recent AI request logs' }}</h2></div>
      <div class="overflow-x-auto">
        <table class="w-full min-w-[700px] text-left text-xs">
          <thead class="bg-gray-50 text-gray-500"><tr><th class="px-5 py-3">{{ isKo ? '시각' : 'Time' }}</th><th class="px-5 py-3">{{ isKo ? '사용자' : 'User' }}</th><th class="px-5 py-3">Stage</th><th class="px-5 py-3">Model</th><th class="px-5 py-3">Latency</th><th class="px-5 py-3">Status</th><th class="px-5 py-3">Error</th></tr></thead>
          <tbody class="divide-y divide-gray-100 text-gray-700">
            <tr v-for="log in logs" :key="log.id"><td class="px-5 py-3">{{ formatDate(log.created_at) }}</td><td class="px-5 py-3">{{ log.users?.name || '-' }}</td><td class="px-5 py-3 font-bold">{{ log.stage }}</td><td class="px-5 py-3">{{ log.model || '-' }}</td><td class="px-5 py-3">{{ log.latency_ms }}ms</td><td class="px-5 py-3"><span :class="log.status_code < 400 ? 'text-green-700' : 'text-red-600'" class="font-black">{{ log.status_code }}</span></td><td class="max-w-xs truncate px-5 py-3 text-red-500">{{ log.error_message || '-' }}</td></tr>
            <tr v-if="!logs.length"><td colspan="7" class="px-5 py-10 text-center text-gray-400">{{ isKo ? '아직 AI 요청 기록이 없습니다.' : 'No AI requests yet.' }}</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>
