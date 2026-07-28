<script setup lang="ts">
import type { ReservationStatus } from "~/types/api";
import { useAdminTickets } from "~/composables/admin/useAdminTickets";
import { formatPoints } from "~/utils/format";
import { reservationStatusClass } from "~/utils/menu";

const { t, locale } = useI18n({ useScope: "global" });
const { showAlert, showConfirm } = useModal();
const api = useApi();
const { reservations, loading, processing, load, useTicket, cancelTicket } = useAdminTickets();
const search = ref("");
const status = ref<"all" | ReservationStatus>("all");
const statuses: Array<"all" | ReservationStatus> = ["all", "reserved", "used", "cancelled", "no_show"];

const filteredReservations = computed(() => {
  const query = search.value.trim().toLowerCase();
  return reservations.value.filter((reservation) => {
    if (status.value !== "all" && reservation.status !== status.value) return false;
    if (!query) return true;
    return [
      reservation.users?.name,
      reservation.users?.student_id,
      reservation.menus?.title_ko,
      reservation.menus?.title_en,
      reservation.id
    ].some((value) => value?.toLowerCase().includes(query));
  });
});

const handleUseTicket = async (id: string) => {
  if (!(await showConfirm(t("admin.tickets.actions.confirm_meal")))) return;
  try {
    await useTicket(id);
    await showAlert(t("admin.tickets.actions.success_meal"), { type: "success" });
  } catch (error) {
    await showAlert(api.getErrorMessage(error), { type: "error" });
  }
};

const handleCancelTicket = async (id: string) => {
  if (!(await showConfirm(t("admin.tickets.actions.confirm_cancel")))) return;
  try {
    await cancelTicket(id);
    await showAlert(t("admin.tickets.actions.success_cancel"), { type: "success" });
  } catch (error) {
    await showAlert(api.getErrorMessage(error), { type: "error" });
  }
};

onMounted(load);
</script>

<template>
  <section class="space-y-4">
    <div
      class="flex flex-col items-center justify-between gap-4 rounded-3xl border border-gray-100 bg-white p-4 shadow-sm md:flex-row"
    >
      <div class="relative w-full md:w-72">
        <span class="absolute left-3.5 top-1/2 -translate-y-1/2 text-sm text-gray-400">🔍</span
        ><input
          v-model="search"
          type="search"
          :placeholder="t('admin.tickets.search_placeholder')"
          class="w-full rounded-xl border border-gray-200 py-2.5 pl-9 pr-4 text-sm"
        />
      </div>
      <div class="flex w-full gap-1.5 overflow-x-auto rounded-xl border border-gray-200/50 bg-gray-50 p-1 md:w-auto">
        <button
          v-for="item in statuses"
          :key="item"
          class="rounded-lg px-3.5 py-1.5 text-xs font-bold"
          :class="status === item ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500'"
          @click="status = item"
        >
          {{ t(`admin.tickets.filter_${item}`) }}
        </button>
      </div>
    </div>
    <div
      v-if="loading"
      class="rounded-3xl border border-gray-100 bg-white p-12 text-center text-sm font-semibold text-gray-500"
    >
      {{ t("admin.loading") }}
    </div>
    <div
      v-else-if="filteredReservations.length"
      class="overflow-hidden rounded-3xl border border-gray-100 bg-white shadow-sm"
    >
      <div class="overflow-x-auto">
        <table class="w-full min-w-[780px] border-collapse text-left">
          <thead>
            <tr class="border-b border-gray-100 bg-gray-50 text-xs font-bold tracking-wider text-gray-500">
              <th class="px-6 py-4">{{ t("admin.tickets.table.student") }}</th>
              <th class="px-6 py-4">{{ t("admin.tickets.table.menu") }}</th>
              <th class="px-6 py-4">{{ t("admin.tickets.table.price_opts") }}</th>
              <th class="px-6 py-4">{{ t("admin.tickets.table.status") }}</th>
              <th class="px-6 py-4 text-right">{{ t("admin.tickets.table.action") }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 text-sm font-semibold text-gray-700">
            <tr v-for="reservation in filteredReservations" :key="reservation.id">
              <td class="px-6 py-4">
                <div class="font-extrabold text-gray-950">
                  {{ reservation.users?.name || t("admin.tickets.table.no_info") }}
                </div>
                <div class="mt-0.5 text-xs text-gray-400">
                  {{ t("student_id") }} {{ reservation.users?.student_id || "-" }}
                </div>
              </td>
              <td class="px-6 py-4">
                <div class="max-w-[200px] truncate font-bold text-gray-900">
                  {{
                    locale === "ko"
                      ? reservation.menus?.title_ko || t("admin.tickets.table.deleted_menu")
                      : reservation.menus?.title_en || t("admin.tickets.table.deleted_menu")
                  }}
                </div>
                <div class="mt-0.5 text-xs text-gray-400">
                  {{ reservation.meal_date || "-" }} {{ reservation.meal_time?.slice(0, 5) || "" }}
                </div>
              </td>
              <td class="px-6 py-4">
                <div class="font-black text-[#2E7D32]">{{ formatPoints(reservation.total_price, locale) }}P</div>
                <div class="mt-0.5 text-[10px] text-gray-400">
                  {{ t("admin.tickets.table.rice") }}:
                  {{ t(`admin.tickets.table.rice_opt.${reservation.options.rice || 0}`) }} |
                  {{ t("admin.tickets.table.main") }}:
                  {{ t(`admin.tickets.table.main_opt.${reservation.options.main || 0}`) }}
                </div>
              </td>
              <td class="px-6 py-4">
                <span
                  class="inline-flex rounded-full border px-2.5 py-1 text-[11px] font-extrabold"
                  :class="reservationStatusClass[reservation.status || 'reserved']"
                  >{{ t(`admin.tickets.filter_${reservation.status || "reserved"}`) }}</span
                >
              </td>
              <td class="px-6 py-4 text-right">
                <div v-if="reservation.status === 'reserved'" class="flex justify-end gap-2">
                  <button
                    :disabled="processing"
                    class="rounded-lg border border-green-200 bg-green-50 px-3 py-1.5 text-xs text-[#2E7D32]"
                    @click="handleUseTicket(reservation.id)"
                  >
                    {{ t("admin.tickets.actions.complete_meal") }}</button
                  ><button
                    :disabled="processing"
                    class="rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-xs text-red-600"
                    @click="handleCancelTicket(reservation.id)"
                  >
                    {{ t("admin.tickets.actions.cancel_refund") }}
                  </button>
                </div>
                <span v-else class="text-xs text-gray-400">-</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div v-else class="rounded-3xl border border-gray-100 bg-white py-20 text-center">
      <div class="mb-4 text-4xl">🎫</div>
      <p class="text-sm font-bold text-gray-500">{{ t("admin.tickets.empty") }}</p>
    </div>
  </section>
</template>
