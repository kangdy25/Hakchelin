<script setup lang="ts">
definePageMeta({ middleware: "admin" });

const { t } = useI18n({ useScope: "global" });
const tabs = ["menus", "tickets", "users", "stats", "ai"] as const;
type AdminTab = (typeof tabs)[number];
const activeTab = ref<AdminTab>("menus");
</script>

<template>
  <div class="pb-10">
    <header class="mb-6 flex flex-col items-start justify-between gap-4 md:flex-row md:items-center">
      <div>
        <h1 class="flex items-center gap-2 text-2xl font-black text-gray-900 md:text-3xl">
          🛠️ {{ t("nav_admin") }}
          <span class="rounded-full bg-gray-200/60 px-3 py-1 text-base font-semibold text-gray-500">{{
            t("admin.dashboard")
          }}</span>
        </h1>
        <p class="mt-1 text-sm text-gray-500">{{ t("admin.sub_desc") }}</p>
      </div>
      <nav class="flex w-full overflow-x-auto rounded-xl border border-gray-200/80 bg-gray-100 p-1.5 md:w-auto">
        <button
          v-for="tab in tabs"
          :key="tab"
          class="whitespace-nowrap rounded-lg px-4 py-2 text-xs font-black transition-all md:text-sm"
          :class="activeTab === tab ? 'bg-white text-[#2E7D32] shadow-sm' : 'text-gray-500 hover:text-gray-800'"
          @click="activeTab = tab"
        >
          {{ t(`admin.tabs.${tab}`) }}
        </button>
      </nav>
    </header>

    <ClientOnly>
      <NuxtErrorBoundary>
        <AdminMenusTab v-if="activeTab === 'menus'" />
        <AdminTicketsTab v-else-if="activeTab === 'tickets'" />
        <AdminUsersTab v-else-if="activeTab === 'users'" />
        <AdminStatsTab v-else-if="activeTab === 'stats'" />
        <AdminAiLogsTab v-else />

        <template #error="{ clearError }">
          <div class="rounded-3xl border border-red-100 bg-red-50 p-6 text-center">
            <p class="text-sm font-bold text-red-600">{{ t("admin.load_error") }}</p>
            <button
              class="mt-4 rounded-xl bg-white px-4 py-2 text-sm font-bold text-red-600 shadow-sm"
              @click="clearError"
            >
              {{ t("common.retry") }}
            </button>
          </div>
        </template>
      </NuxtErrorBoundary>

      <template #fallback>
        <div class="rounded-3xl border border-gray-100 bg-white p-12 text-center text-sm font-semibold text-gray-500">
          {{ t("admin.loading") }}
        </div>
      </template>
    </ClientOnly>
  </div>
</template>
