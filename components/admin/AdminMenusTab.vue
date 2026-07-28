<script setup lang="ts">
import type { Menu } from "~/types/api";
import { useAdminMenus } from "~/composables/admin/useAdminMenus";
import { formatDateTime, formatMealDate, getKstDateString, toKstDateTimeLocal } from "~/utils/date";
import { formatPoints } from "~/utils/format";
import { mapMenuType, menuBadgeClass } from "~/utils/menu";

const { t, locale } = useI18n({ useScope: "global" });
const { showAlert, showConfirm } = useModal();
const api = useApi();
const { menus, loading, processing, load, create, update, deactivate } = useAdminMenus();

const today = getKstDateString();
const selectedDate = ref(today);
const menuModalOpen = ref(false);
const isEditMode = ref(false);
const dayCodes = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"] as const;
const dayOfWeek = (date: string) => dayCodes[new Date(`${date}T00:00:00+09:00`).getDay()];
const defaultDeadline = (date: string) => `${date}T11:00`;
const emptyForm = (date: string): Omit<Menu, "created_at"> => ({
  id: "",
  day_of_week: dayOfWeek(date),
  meal_date: date,
  meal_time: "12:00:00",
  type: "kr",
  title_ko: "",
  title_en: "",
  price: 4500,
  capacity: 100,
  reservation_deadline: defaultDeadline(date),
  deposit_amount: 1000,
  is_active: true
});
const menuForm = ref(emptyForm(today));
const selectedMenus = computed(() => menus.value.filter((menu) => menu.meal_date === selectedDate.value));

const openAddMenuModal = () => {
  isEditMode.value = false;
  menuForm.value = emptyForm(selectedDate.value);
  menuModalOpen.value = true;
};

const openEditMenuModal = (menu: Menu) => {
  isEditMode.value = true;
  menuForm.value = {
    ...menu,
    type: mapMenuType(menu.type),
    reservation_deadline: toKstDateTimeLocal(menu.reservation_deadline)
  };
  menuModalOpen.value = true;
};

const saveMenu = async () => {
  if (!menuForm.value.title_ko || !menuForm.value.title_en) {
    await showAlert(t("admin.menus.alerts.fill_both"), { type: "warning" });
    return;
  }

  const { id, ...input } = menuForm.value;
  const payload = { ...input, day_of_week: dayOfWeek(input.meal_date) };
  try {
    if (isEditMode.value) {
      await update(id, payload);
      await showAlert(t("admin.menus.alerts.updated"), { type: "success" });
    } else {
      await create({ ...payload, id: crypto.randomUUID() });
      await showAlert(t("admin.menus.alerts.saved"), { type: "success" });
    }
    menuModalOpen.value = false;
  } catch (error) {
    await showAlert(api.getErrorMessage(error), { type: "error" });
  }
};

const deleteMenu = async (id: string) => {
  if (!(await showConfirm(t("admin.menus.alerts.confirm_delete")))) return;
  try {
    await deactivate(id);
    await showAlert(t("admin.menus.alerts.deleted"), { type: "success" });
  } catch (error) {
    await showAlert(api.getErrorMessage(error), { type: "error" });
  }
};

onMounted(load);
</script>

<template>
  <section class="space-y-5">
    <div class="flex items-center justify-between rounded-2xl border border-gray-100 bg-white p-4 shadow-sm">
      <div>
        <label class="mb-1 block text-[11px] font-bold text-gray-400">{{ t("admin.menus.fields.date") }}</label>
        <input
          v-model="selectedDate"
          type="date"
          class="rounded-xl border border-gray-200 px-3 py-2 text-sm font-bold"
        />
      </div>
      <button
        class="flex items-center gap-1.5 rounded-xl bg-[#2E7D32] px-4 py-2.5 text-sm font-bold text-white shadow-md transition-colors hover:bg-[#1b5e20]"
        @click="openAddMenuModal"
      >
        <span>+</span> {{ t("admin.menus.add_menu") }}
      </button>
    </div>

    <div
      v-if="loading"
      class="rounded-3xl border border-gray-100 bg-white p-12 text-center text-sm font-semibold text-gray-500"
    >
      {{ t("admin.loading") }}
    </div>
    <div v-else-if="selectedMenus.length" class="grid grid-cols-1 gap-5 md:grid-cols-2 lg:grid-cols-3">
      <article
        v-for="menu in selectedMenus"
        :key="menu.id"
        class="flex flex-col justify-between rounded-3xl border border-gray-100 bg-white p-5 shadow-[0_2px_12px_rgba(0,0,0,0.03)]"
      >
        <div>
          <div class="mb-3 flex items-center justify-between">
            <span class="rounded-md border px-2.5 py-1 text-xs font-black" :class="menuBadgeClass(menu.type)">
              {{ t(`menu_types.${mapMenuType(menu.type)}`) }}
            </span>
            <span class="text-xs font-semibold text-gray-400">ID: {{ menu.id.slice(0, 8) }}</span>
          </div>
          <h3 class="text-lg font-black text-gray-900">{{ locale === "ko" ? menu.title_ko : menu.title_en }}</h3>
          <p class="mt-1 text-sm font-semibold text-gray-500">{{ locale === "ko" ? menu.title_en : menu.title_ko }}</p>
          <p class="mt-3 text-xs font-semibold text-gray-500">
            {{
              t("admin.menus.schedule_summary", {
                date: formatMealDate(menu.meal_date, locale),
                time: menu.meal_time.slice(0, 5),
                capacity: menu.capacity
              })
            }}
          </p>
          <p class="mt-1 text-[11px] text-gray-400">
            {{ t("admin.menus.reservation_deadline", { date: formatDateTime(menu.reservation_deadline, locale) }) }}
          </p>
        </div>
        <div class="mt-6 flex items-center justify-between border-t border-gray-50 pt-4">
          <span class="text-lg font-extrabold text-[#2E7D32]">{{ formatPoints(menu.price, locale) }}P</span>
          <div class="flex gap-2">
            <button
              class="rounded-lg border border-gray-200 bg-gray-50 px-3 py-1.5 text-xs font-bold text-gray-600"
              @click="openEditMenuModal(menu)"
            >
              {{ t("admin.menus.edit") }}
            </button>
            <button
              class="rounded-lg border border-red-100 bg-red-50 px-3 py-1.5 text-xs font-bold text-red-600"
              @click="deleteMenu(menu.id)"
            >
              {{ t("admin.menus.delete") }}
            </button>
          </div>
        </div>
      </article>
    </div>
    <div v-else class="rounded-3xl border border-gray-100 bg-white py-20 text-center">
      <div class="mb-4 text-4xl">🍽️</div>
      <p class="text-sm font-bold text-gray-500">{{ t("admin.menus.empty") }}</p>
      <button class="mt-4 text-xs font-bold text-[#2E7D32] hover:underline" @click="openAddMenuModal">
        {{ t("admin.menus.first_menu") }}
      </button>
    </div>

    <div
      v-if="menuModalOpen"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm"
      @click.self="menuModalOpen = false"
    >
      <div
        class="max-h-[90vh] w-full max-w-md overflow-y-auto rounded-3xl border border-gray-100 bg-white p-6 shadow-2xl"
      >
        <h3 class="mb-5 text-xl font-black text-gray-900">
          {{ isEditMode ? t("admin.menus.edit_menu") : t("admin.menus.new_menu") }}
        </h3>
        <form class="space-y-4 text-sm font-semibold" @submit.prevent="saveMenu">
          <label class="block"
            ><span class="mb-1 block text-xs text-gray-500">{{ t("admin.menus.fields.date") }}</span
            ><input
              v-model="menuForm.meal_date"
              type="date"
              required
              class="w-full rounded-xl border border-gray-200 px-3 py-2.5"
          /></label>
          <div class="grid grid-cols-2 gap-3">
            <label
              ><span class="mb-1 block text-xs text-gray-500">{{ t("admin.menus.fields.time") }}</span
              ><input
                v-model="menuForm.meal_time"
                type="time"
                required
                class="w-full rounded-xl border border-gray-200 px-3 py-2.5"
            /></label>
            <label
              ><span class="mb-1 block text-xs text-gray-500">{{ t("admin.menus.fields.capacity") }}</span
              ><input
                v-model.number="menuForm.capacity"
                type="number"
                min="1"
                required
                class="w-full rounded-xl border border-gray-200 px-3 py-2.5"
            /></label>
          </div>
          <label class="block"
            ><span class="mb-1 block text-xs text-gray-500">{{ t("admin.menus.fields.type") }}</span
            ><select v-model="menuForm.type" class="w-full rounded-xl border border-gray-200 px-3 py-2.5">
              <option value="kr">{{ t("menu_types.kr") }}</option>
              <option value="premium">{{ t("menu_types.premium") }}</option>
              <option value="takeout">{{ t("menu_types.takeout") }}</option>
            </select></label
          >
          <div class="grid grid-cols-2 gap-3">
            <label
              ><span class="mb-1 block text-xs text-gray-500">{{ t("admin.menus.fields.deadline") }}</span
              ><input
                v-model="menuForm.reservation_deadline"
                type="datetime-local"
                required
                class="w-full rounded-xl border border-gray-200 px-3 py-2.5"
            /></label>
            <label
              ><span class="mb-1 block text-xs text-gray-500">{{ t("admin.menus.fields.deposit") }}</span
              ><input
                v-model.number="menuForm.deposit_amount"
                type="number"
                min="0"
                required
                class="w-full rounded-xl border border-gray-200 px-3 py-2.5"
            /></label>
          </div>
          <label class="block"
            ><span class="mb-1 block text-xs text-gray-500">{{ t("admin.menus.fields.title_ko") }}</span
            ><input v-model="menuForm.title_ko" required class="w-full rounded-xl border border-gray-200 px-3 py-2.5"
          /></label>
          <label class="block"
            ><span class="mb-1 block text-xs text-gray-500">{{ t("admin.menus.fields.title_en") }}</span
            ><input v-model="menuForm.title_en" required class="w-full rounded-xl border border-gray-200 px-3 py-2.5"
          /></label>
          <label class="block"
            ><span class="mb-1 block text-xs text-gray-500">{{ t("admin.menus.fields.price") }}</span
            ><input
              v-model.number="menuForm.price"
              type="number"
              min="0"
              required
              class="w-full rounded-xl border border-gray-200 px-3 py-2.5"
          /></label>
          <div class="flex justify-end gap-3 pt-2">
            <button
              type="button"
              class="rounded-xl bg-gray-100 px-4 py-2 font-bold text-gray-600"
              @click="menuModalOpen = false"
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
