import type { CreateMenuInput, Menu, UpdateMenuInput } from "~/types/api";

export const useAdminMenus = () => {
  const api = useApi();
  const menus = ref<Menu[]>([]);
  const loading = ref(false);
  const processing = ref(false);

  const load = async () => {
    loading.value = true;
    try {
      menus.value = await api.menus.get();
    } finally {
      loading.value = false;
    }
  };

  const create = async (input: CreateMenuInput) => {
    processing.value = true;
    try {
      await api.menus.create(input);
      await load();
    } finally {
      processing.value = false;
    }
  };

  const update = async (id: string, input: UpdateMenuInput) => {
    processing.value = true;
    try {
      await api.menus.update(id, input);
      await load();
    } finally {
      processing.value = false;
    }
  };

  const deactivate = async (id: string) => {
    processing.value = true;
    try {
      await api.menus.deactivate(id);
      await load();
    } finally {
      processing.value = false;
    }
  };

  return { menus, loading, processing, load, create, update, deactivate };
};
