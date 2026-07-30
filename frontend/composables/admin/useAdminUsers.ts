import type { User } from "~/types/api";

export const useAdminUsers = () => {
  const api = useApi();
  const users = ref<User[]>([]);
  const loading = ref(false);
  const processing = ref(false);

  const load = async () => {
    loading.value = true;
    try {
      users.value = await api.users.getAll();
    } finally {
      loading.value = false;
    }
  };

  const adjustPoints = async (input: { userId: string; amount: number; description: string }) => {
    processing.value = true;
    try {
      await api.users.adjustPoints(input);
      await load();
    } finally {
      processing.value = false;
    }
  };

  const updateRole = async (input: { userId: string; role: "student" | "admin" }) => {
    processing.value = true;
    try {
      await api.users.updateRole(input);
      await load();
    } finally {
      processing.value = false;
    }
  };

  return { users, loading, processing, load, adjustPoints, updateRole };
};
