<script setup lang="ts">
import type { User } from "~/types/api";
import { useAdminUsers } from "~/composables/admin/useAdminUsers";
import { formatPoints } from "~/utils/format";

const { t, locale } = useI18n({ useScope: "global" });
const { showAlert, showConfirm } = useModal();
const api = useApi();
const { userId, refreshProfile } = useUserProfile();
const { users, loading, processing, load, adjustPoints, updateRole } = useAdminUsers();
const search = ref("");
const pointModalOpen = ref(false);
const selectedUser = ref<User | null>(null);
const amountText = ref("10,000");
const amount = ref(10_000);
const description = ref("");

const filteredUsers = computed(() => {
  const query = search.value.trim().toLowerCase();
  if (!query) return users.value;
  return users.value.filter(
    (user) => user.name.toLowerCase().includes(query) || user.student_id.toLowerCase().includes(query)
  );
});

watch(amountText, (value) => {
  if (value === "" || value === "-") {
    amount.value = 0;
    return;
  }
  const negative = value.startsWith("-");
  const digits = value.replace(/\D/g, "");
  if (!digits) return;
  const limit = negative ? selectedUser.value?.current_point || 0 : 99_999_999;
  const parsed = Math.min(Number(digits), limit);
  amount.value = negative ? -parsed : parsed;
  const formatted = `${negative ? "-" : ""}${formatPoints(parsed, "ko")}`;
  if (formatted !== value) amountText.value = formatted;
});

const openPointModal = (user: User) => {
  selectedUser.value = user;
  amount.value = 10_000;
  amountText.value = "10,000";
  description.value = t("admin.users.actions.adjust_desc_default");
  pointModalOpen.value = true;
};

const submitPointAdjustment = async () => {
  if (!selectedUser.value || amount.value === 0) {
    await showAlert(t("admin.users.actions.adjust_alert_amount"), { type: "warning" });
    return;
  }
  try {
    await adjustPoints({ userId: selectedUser.value.id, amount: amount.value, description: description.value });
    await showAlert(
      t("admin.users.actions.adjust_success", {
        amount: `${amount.value > 0 ? "+" : ""}${formatPoints(amount.value, locale)}`
      }),
      { type: "success" }
    );
    pointModalOpen.value = false;
  } catch (error) {
    await showAlert(api.getErrorMessage(error), { type: "error" });
  }
};

const toggleRole = async (user: User) => {
  if (user.id === userId.value) {
    await showAlert(t("admin.users.actions.self_demotion_error"), { type: "warning" });
    return;
  }
  const role = user.role === "admin" ? "student" : "admin";
  const roleName = t(`admin.users.roles.${role}`);
  if (!(await showConfirm(t("admin.users.actions.confirm_role", { name: user.name, role: roleName })))) return;
  try {
    await updateRole({ userId: user.id, role });
    await refreshProfile();
    await showAlert(t("admin.users.actions.success_role"), { type: "success" });
  } catch (error) {
    await showAlert(api.getErrorMessage(error), { type: "error" });
  }
};

onMounted(load);
</script>

<template>
  <section class="space-y-4">
    <div class="rounded-3xl border border-gray-100 bg-white p-4 shadow-sm">
      <div class="relative w-full md:w-72">
        <span class="absolute left-3.5 top-1/2 -translate-y-1/2 text-sm text-gray-400">🔍</span
        ><input
          v-model="search"
          type="search"
          :placeholder="t('admin.users.search_placeholder')"
          class="w-full rounded-xl border border-gray-200 py-2.5 pl-9 pr-4 text-sm"
        />
      </div>
    </div>
    <div
      v-if="loading"
      class="rounded-3xl border border-gray-100 bg-white p-12 text-center text-sm font-semibold text-gray-500"
    >
      {{ t("admin.loading") }}
    </div>
    <div v-else-if="filteredUsers.length" class="overflow-hidden rounded-3xl border border-gray-100 bg-white shadow-sm">
      <div class="overflow-x-auto">
        <table class="w-full min-w-[720px] border-collapse text-left">
          <thead>
            <tr class="border-b border-gray-100 bg-gray-50 text-xs font-bold tracking-wider text-gray-500">
              <th class="px-6 py-4">{{ t("admin.users.table.name") }}</th>
              <th class="px-6 py-4">{{ t("admin.users.table.student_id") }}</th>
              <th class="px-6 py-4">{{ t("admin.users.table.role") }}</th>
              <th class="px-6 py-4">{{ t("admin.users.table.points") }}</th>
              <th class="px-6 py-4 text-right">{{ t("admin.users.table.actions") }}</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100 text-sm font-semibold text-gray-700">
            <tr v-for="user in filteredUsers" :key="user.id">
              <td class="px-6 py-4 font-extrabold text-gray-950">{{ user.name }}</td>
              <td class="px-6 py-4 text-gray-500">{{ user.student_id }}</td>
              <td class="px-6 py-4">
                <span
                  class="inline-flex rounded border px-2 py-0.5 text-[10px] font-black"
                  :class="
                    user.role === 'admin'
                      ? 'border-purple-200 bg-purple-100 text-purple-800'
                      : 'border-gray-200 bg-gray-100 text-gray-800'
                  "
                  >{{ t(`admin.users.roles.${user.role || "student"}`) }}</span
                >
              </td>
              <td class="px-6 py-4 font-black text-[#2E7D32]">{{ formatPoints(user.current_point, locale) }}P</td>
              <td class="px-6 py-4 text-right">
                <div class="flex justify-end gap-2">
                  <button
                    :disabled="processing"
                    class="rounded-lg border border-green-200 bg-[#E8F5E9] px-3 py-1.5 text-xs text-[#2E7D32]"
                    @click="openPointModal(user)"
                  >
                    {{ t("admin.users.actions.adjust_points") }}</button
                  ><button
                    :disabled="processing"
                    class="rounded-lg border border-purple-200 bg-purple-50 px-3 py-1.5 text-xs text-purple-600"
                    @click="toggleRole(user)"
                  >
                    {{
                      user.role === "admin"
                        ? t("admin.users.actions.demote_student")
                        : t("admin.users.actions.promote_admin")
                    }}
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <div v-else class="rounded-3xl border border-gray-100 bg-white py-20 text-center">
      <div class="mb-4 text-4xl">👤</div>
      <p class="text-sm font-bold text-gray-500">{{ t("admin.users.empty") }}</p>
    </div>

    <div
      v-if="pointModalOpen"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm"
      @click.self="pointModalOpen = false"
    >
      <div class="w-full max-w-sm rounded-3xl border border-gray-100 bg-white p-6 shadow-2xl">
        <h3 class="mb-1 text-xl font-black text-gray-900">{{ t("admin.users.actions.adjust_modal_title") }}</h3>
        <p class="mb-5 text-xs font-bold text-gray-400">
          {{
            t("admin.users.actions.adjust_modal_target", {
              name: selectedUser?.name,
              student_id: selectedUser?.student_id
            })
          }}
        </p>
        <form class="space-y-4 text-sm font-semibold" @submit.prevent="submitPointAdjustment">
          <label class="block"
            ><span class="mb-1 block text-xs text-gray-500">{{ t("admin.users.actions.adjust_amount") }}</span
            ><input
              v-model="amountText"
              inputmode="numeric"
              required
              class="w-full rounded-xl border border-gray-200 px-3 py-2.5" /></label
          ><label class="block"
            ><span class="mb-1 block text-xs text-gray-500">{{ t("admin.users.actions.adjust_desc") }}</span
            ><input v-model="description" required class="w-full rounded-xl border border-gray-200 px-3 py-2.5"
          /></label>
          <div class="flex justify-end gap-3 pt-2">
            <button
              type="button"
              class="rounded-xl bg-gray-100 px-4 py-2 font-bold text-gray-600"
              @click="pointModalOpen = false"
            >
              {{ t("admin.menus.cancel") }}</button
            ><button
              type="submit"
              :disabled="processing"
              class="rounded-xl bg-[#2E7D32] px-4 py-2 font-bold text-white disabled:opacity-50"
            >
              {{ t("admin.menus.save") }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </section>
</template>
