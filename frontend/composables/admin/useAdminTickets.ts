import type { Reservation } from "~/types/api";

export const useAdminTickets = () => {
  const api = useApi();
  const reservations = ref<Reservation[]>([]);
  const loading = ref(false);
  const processing = ref(false);

  const load = async () => {
    loading.value = true;
    try {
      reservations.value = await api.reservations.getAll();
    } finally {
      loading.value = false;
    }
  };

  const useTicket = async (id: string) => {
    processing.value = true;
    try {
      await api.reservations.useTicket(id);
      await load();
    } finally {
      processing.value = false;
    }
  };

  const cancelTicket = async (id: string) => {
    processing.value = true;
    try {
      await api.reservations.cancelTicket(id);
      await load();
    } finally {
      processing.value = false;
    }
  };

  return { reservations, loading, processing, load, useTicket, cancelTicket };
};
