<script setup lang="ts">
import { useAdminStats } from "~/composables/admin/useAdminStats";
import { formatDateTime } from "~/utils/date";
import { formatPoints } from "~/utils/format";

const { t, locale } = useI18n({ useScope: "global" });
const { transactions, loading, summary, load } = useAdminStats();

const transactionDescription = (description: string | null) => {
  if (description === "포인트 충전") return t("payment.charge");
  if (description === "메뉴 예약") return t("payment.use");
  if (description === "예약 취소 환불") return t("payment.refund");
  if (description === "예약 취소 환불 (관리자)") return t("payment.refund_admin");
  if (description === "관리자 포인트 조정") return t("payment.admin_adjust");
  if (description === "마음을 잇는 식탁 기부") return t("heartTable.donateBtn");
  return description || "-";
};

onMounted(load);
</script>

<template>
  <section class="space-y-6">
    <div
      v-if="loading"
      class="rounded-3xl border border-gray-100 bg-white p-12 text-center text-sm font-semibold text-gray-500"
    >
      {{ t("admin.loading") }}
    </div>
    <template v-else>
      <div class="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <article class="rounded-3xl border border-gray-100 bg-white p-5 shadow-sm">
          <span class="text-xs font-bold uppercase tracking-wider text-gray-400">{{
            t("admin.stats.users_count")
          }}</span>
          <div class="mt-3 flex items-baseline gap-1">
            <span class="text-3xl font-black text-gray-900">{{ summary.totalUsersCount }}</span
            ><span class="text-sm font-bold text-gray-500">{{ locale === "ko" ? "명" : "" }}</span>
          </div>
          <p class="mt-2 text-[11px] font-bold text-purple-600">
            {{
              locale === "ko"
                ? `운영 관리자: ${summary.totalAdminsCount}명 포함`
                : `Includes ${summary.totalAdminsCount} admins`
            }}
          </p>
        </article>
        <article class="rounded-3xl border border-gray-100 bg-white p-5 shadow-sm">
          <span class="text-xs font-bold uppercase tracking-wider text-gray-400">{{
            t("admin.stats.active_tickets")
          }}</span>
          <div class="mt-3 flex items-baseline gap-1">
            <span class="text-3xl font-black text-amber-500">{{ summary.activeTicketsCount }}</span
            ><span class="text-sm font-bold text-gray-500">{{ locale === "ko" ? "개" : "" }}</span>
          </div>
          <p class="mt-2 text-[11px] font-bold text-gray-400">{{ t("admin.stats.active_tickets_desc") }}</p>
        </article>
        <article class="rounded-3xl border border-gray-100 bg-white p-5 shadow-sm">
          <span class="text-xs font-bold uppercase tracking-wider text-gray-400">{{
            t("admin.stats.total_sales")
          }}</span>
          <div class="mt-3">
            <span class="text-2xl font-black text-[#2E7D32]">{{ formatPoints(summary.totalSales, locale) }}</span
            ><span class="ml-1 text-sm font-bold text-gray-500">P</span>
          </div>
          <p class="mt-2 text-[11px] font-bold text-gray-400">{{ t("admin.stats.total_sales_desc") }}</p>
        </article>
        <article class="rounded-3xl border border-gray-100 bg-white p-5 shadow-sm">
          <span class="text-xs font-bold uppercase tracking-wider text-gray-400">{{
            t("admin.stats.total_charges")
          }}</span>
          <div class="mt-3">
            <span class="text-2xl font-black text-blue-600">{{ formatPoints(summary.totalCharges, locale) }}</span
            ><span class="ml-1 text-sm font-bold text-gray-500">P</span>
          </div>
          <p class="mt-2 text-[11px] font-bold text-red-500">
            {{ t("admin.stats.total_charges_desc", { refunds: formatPoints(summary.totalRefunds, locale) }) }}
          </p>
        </article>
      </div>
      <div>
        <h2 class="mb-3 text-lg font-black text-gray-900">{{ t("admin.stats.log_title") }}</h2>
        <div v-if="transactions.length" class="overflow-hidden rounded-3xl border border-gray-100 bg-white shadow-sm">
          <div class="overflow-x-auto">
            <table class="w-full min-w-[760px] border-collapse text-left">
              <thead>
                <tr class="border-b border-gray-100 bg-gray-50 text-xs font-bold tracking-wider text-gray-500">
                  <th class="px-6 py-4">{{ t("admin.stats.log_table.date") }}</th>
                  <th class="px-6 py-4">{{ t("admin.stats.log_table.student") }}</th>
                  <th class="px-6 py-4">{{ t("admin.stats.log_table.amount") }}</th>
                  <th class="px-6 py-4">{{ t("admin.stats.log_table.type") }}</th>
                  <th class="px-6 py-4">{{ t("admin.stats.log_table.desc") }}</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100 text-xs font-bold text-gray-700">
                <tr v-for="transaction in transactions" :key="transaction.id">
                  <td class="px-6 py-3 text-gray-400">{{ formatDateTime(transaction.created_at, locale) }}</td>
                  <td class="px-6 py-3 text-gray-800">
                    {{ transaction.users?.name || t("admin.stats.log_table.no_info") }} ({{
                      transaction.users?.student_id || "-"
                    }})
                  </td>
                  <td class="px-6 py-3" :class="transaction.amount > 0 ? 'text-[#2E7D32]' : 'text-gray-950'">
                    {{ transaction.amount > 0 ? "+" : "" }}{{ formatPoints(transaction.amount, locale) }}P
                  </td>
                  <td class="px-6 py-3">
                    <span
                      class="inline-block rounded px-1.5 py-0.5 text-[10px]"
                      :class="
                        transaction.type === 'charge'
                          ? 'bg-blue-50 text-blue-700'
                          : transaction.type === 'refund'
                            ? 'bg-green-50 text-[#2E7D32]'
                            : 'bg-gray-50 text-gray-700'
                      "
                      >{{ t(`admin.stats.log_table.${transaction.type || "deduct"}`) }}</span
                    >
                  </td>
                  <td class="px-6 py-3 font-semibold text-gray-500">
                    {{ transactionDescription(transaction.description) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div
          v-else
          class="rounded-3xl border border-gray-100 bg-white py-20 text-center text-sm font-bold text-gray-400"
        >
          {{ t("admin.stats.empty_logs") }}
        </div>
      </div>
    </template>
  </section>
</template>
