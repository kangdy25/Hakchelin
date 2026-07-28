type AiLog = {
  id: string;
  created_at: string;
  stage: string;
  model: string | null;
  latency_ms: number;
  status_code: number;
  error_message: string | null;
  users?: { name: string; student_id: string } | null;
};

export const useAdminAiLogs = () => {
  const api = useApi();
  const logs = ref<AiLog[]>([]);
  const loading = ref(false);
  const error = ref("");

  const load = async () => {
    loading.value = true;
    error.value = "";
    try {
      logs.value = await api.ai.getLogs();
    } catch (loadError) {
      error.value = api.getErrorMessage(loadError);
    } finally {
      loading.value = false;
    }
  };

  return { logs, loading, error, load };
};
