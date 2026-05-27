<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import type { Database, Menu, Reservation, User, Transaction } from '~/types/database.types'

// Admin middleware protection
definePageMeta({
  middleware: 'admin'
})

const { t, locale } = useI18n({ useScope: 'global' })
const supabase = useSupabaseClient<Database>()
const { profile: myProfile, refreshProfile, userId } = useUserProfile()

// Tabs
const tabs = ['menus', 'tickets', 'users', 'stats'] as const
type Tab = typeof tabs[number]
const activeTab = ref<Tab>('menus')

// Loading states
const loading = ref(false)
const processing = ref(false)

// 1. Menus Data & Modals
const dbMenus = ref<Menu[]>([])
const days = ['mon', 'tue', 'wed', 'thu', 'fri'] as const
const selectedDay = ref<'mon' | 'tue' | 'wed' | 'thu' | 'fri'>('mon')
const menuModalOpen = ref(false)
const isEditMode = ref(false)
const menuForm = ref<Omit<Menu, 'created_at'>>({
  id: '',
  day_of_week: 'mon',
  type: 'kr',
  title_ko: '',
  title_en: '',
  price: 4500
})

// 2. Reservations (Tickets) Data
const reservations = ref<Reservation[]>([])
const ticketSearch = ref('')
const ticketStatusFilter = ref<string>('all')

// 3. Users Data & Modals
const users = ref<User[]>([])
const userSearch = ref('')
const pointModalOpen = ref(false)
const selectedUser = ref<User | null>(null)
const pointAdjustAmount = ref<number>(10000)
const pointAdjustDesc = ref<string>('관리자 조정')

// 4. Stats & Transactions Data
const transactions = ref<Transaction[]>([])

// --- API Calls ---

// Load Menus
const loadMenus = async () => {
  loading.value = true
  const { data, error } = await supabase.from('menus').select('*')
  if (!error && data) {
    dbMenus.value = data.map(menu => ({
      id: menu.id,
      day_of_week: (menu.day_of_week || 'mon') as 'mon' | 'tue' | 'wed' | 'thu' | 'fri',
      type: (menu.type || 'kr') as 'kr' | 'premium' | 'takeout',
      title_ko: menu.title_ko,
      title_en: menu.title_en,
      price: menu.price || 4500,
      created_at: menu.created_at
    }))
  }
  loading.value = false
}

// Load Reservations
const loadReservations = async () => {
  loading.value = true
  const { data, error } = await supabase
    .from('reservations')
    .select('id, user_id, menu_id, options, total_price, status, created_at, users(name, student_id), menus(title_ko, title_en, price)')
    .order('created_at', { ascending: false })
  if (!error && data) {
    reservations.value = data.map(r => ({
      ...r,
      options: (r.options || {}) as { rice?: number; main?: number; [key: string]: any }
    }))
  }
  loading.value = false
}

// Load Users
const loadUsers = async () => {
  loading.value = true
  const { data, error } = await supabase
    .from('users')
    .select('*')
    .order('student_id', { ascending: true })
  if (!error && data) {
    users.value = data
  }
  loading.value = false
}

// Load Stats & Transactions
const loadTransactions = async () => {
  loading.value = true
  const { data, error } = await supabase
    .from('transactions')
    .select('id, user_id, amount, type, description, created_at, users(name, student_id)')
    .order('created_at', { ascending: false })
    .limit(50)
  if (!error && data) {
    transactions.value = data
  }
  loading.value = false
}

// Global data loading handler based on active tab
const loadTabDependencies = async () => {
  if (activeTab.value === 'menus') {
    await loadMenus()
  } else if (activeTab.value === 'tickets') {
    await loadReservations()
  } else if (activeTab.value === 'users') {
    await loadUsers()
  } else if (activeTab.value === 'stats') {
    await loadTransactions()
    await loadUsers() // stats summary depends on users count
  }
}

watch(activeTab, () => {
  loadTabDependencies()
}, { immediate: true })

onMounted(() => {
  loadTabDependencies()
})

// --- Menus Handlers ---
const openAddMenuModal = () => {
  isEditMode.value = false
  menuForm.value = {
    id: '',
    day_of_week: selectedDay.value,
    type: 'kr',
    title_ko: '',
    title_en: '',
    price: 4500
  }
  menuModalOpen.value = true
}

const openEditMenuModal = (menu: Menu) => {
  isEditMode.value = true
  menuForm.value = {
    id: menu.id,
    day_of_week: menu.day_of_week,
    type: mapMenuType(menu.type),
    title_ko: menu.title_ko,
    title_en: menu.title_en,
    price: Number(menu.price)
  }
  menuModalOpen.value = true
}

const saveMenu = async () => {
  if (!menuForm.value.title_ko || !menuForm.value.title_en) {
    alert(t('admin.menus.alerts.fill_both'))
    return
  }

  processing.value = true
  try {
    if (isEditMode.value) {
      // Update
      const { error } = await supabase
        .from('menus')
        .update({
          day_of_week: menuForm.value.day_of_week,
          type: menuForm.value.type,
          title_ko: menuForm.value.title_ko,
          title_en: menuForm.value.title_en,
          price: menuForm.value.price
        })
        .eq('id', menuForm.value.id)

      if (error) throw error
      alert(t('admin.menus.alerts.updated'))
    } else {
      // Create
      const { error } = await supabase
        .from('menus')
        .insert({
          id: crypto.randomUUID(),
          day_of_week: menuForm.value.day_of_week,
          type: menuForm.value.type,
          title_ko: menuForm.value.title_ko,
          title_en: menuForm.value.title_en,
          price: menuForm.value.price
        })

      if (error) throw error
      alert(t('admin.menus.alerts.saved'))
    }
    menuModalOpen.value = false
    await loadMenus()
  } catch (err: unknown) {
    alert(t('admin.menus.cancel') + ' ' + t('admin.tickets.table.action') + ' ' + t('status.cancelled') + ': ' + (err as Error).message)
  } finally {
    processing.value = false
  }
}

const deleteMenu = async (id: string) => {
  if (!confirm(t('admin.menus.alerts.confirm_delete'))) {
    return
  }

  processing.value = true
  try {
    const { error } = await supabase
      .from('menus')
      .delete()
      .eq('id', id)

    if (error) throw error
    alert(t('admin.menus.alerts.deleted'))
    await loadMenus()
  } catch (err: unknown) {
    alert(t('admin.menus.alerts.deleted') + ' ' + t('status.cancelled') + ': ' + (err as Error).message)
  } finally {
    processing.value = false
  }
}

// --- Ticket Handlers ---
const filteredReservations = computed(() => {
  return reservations.value.filter(res => {
    // 1. Status Filter
    if (ticketStatusFilter.value !== 'all' && res.status !== ticketStatusFilter.value) {
      return false
    }
    // 2. Search query filter
    const query = ticketSearch.value.trim().toLowerCase()
    if (!query) return true

    const name = res.users?.name?.toLowerCase() || ''
    const studentId = res.users?.student_id?.toLowerCase() || ''
    const menuTitleKo = res.menus?.title_ko?.toLowerCase() || ''
    const menuTitleEn = res.menus?.title_en?.toLowerCase() || ''
    const id = res.id.toLowerCase()

    return name.includes(query) || studentId.includes(query) || menuTitleKo.includes(query) || menuTitleEn.includes(query) || id.includes(query)
  })
})

const handleUseTicket = async (id: string) => {
  if (!confirm(t('admin.tickets.actions.confirm_meal'))) return
  processing.value = true
  try {
    const { error } = await supabase.rpc('admin_use_ticket', { p_reservation_id: id })
    if (error) throw error
    alert(t('admin.tickets.actions.success_meal'))
    await loadReservations()
  } catch (err: unknown) {
    alert('Error: ' + (err as Error).message)
  } finally {
    processing.value = false
  }
}

const handleCancelTicket = async (id: string) => {
  if (!confirm(t('admin.tickets.actions.confirm_cancel'))) return
  processing.value = true
  try {
    const { error } = await supabase.rpc('admin_cancel_ticket', { p_reservation_id: id })
    if (error) throw error
    alert(t('admin.tickets.actions.success_cancel'))
    await loadReservations()
  } catch (err: unknown) {
    alert('Error: ' + (err as Error).message)
  } finally {
    processing.value = false
  }
}

// --- User Handlers ---
const filteredUsers = computed(() => {
  return users.value.filter(u => {
    const query = userSearch.value.trim().toLowerCase()
    if (!query) return true

    const name = u.name?.toLowerCase() || ''
    const studentId = u.student_id?.toLowerCase() || ''
    return name.includes(query) || studentId.includes(query)
  })
})

const openPointModal = (userItem: User) => {
  selectedUser.value = userItem
  pointAdjustAmount.value = 10000
  pointAdjustDesc.value = t('admin.users.actions.adjust_desc_default')
  pointModalOpen.value = true
}

const adjustUserPoints = async () => {
  if (!selectedUser.value) return
  if (pointAdjustAmount.value === 0) {
    alert(t('admin.users.actions.adjust_alert_amount'))
    return
  }

  processing.value = true
  try {
    const { error } = await supabase.rpc('admin_adjust_points', {
      p_user_id: selectedUser.value.id,
      p_amount: pointAdjustAmount.value,
      p_description: pointAdjustDesc.value
    })

    if (error) throw error
    alert(t('admin.users.actions.adjust_success', { amount: `${pointAdjustAmount.value > 0 ? '+' : ''}${pointAdjustAmount.value.toLocaleString()}` }))
    pointModalOpen.value = false
    await loadUsers()
  } catch (err: unknown) {
    alert('Failed: ' + (err as Error).message)
  } finally {
    processing.value = false
  }
}

const toggleUserRole = async (userItem: User) => {
  const newRole = userItem.role === 'admin' ? 'student' : 'admin'
  
  // Prevent self-demotion
  if (userItem.id === userId.value) {
    alert(t('admin.users.actions.self_demotion_error'))
    return
  }
  
  const targetRoleName = newRole === 'admin' ? t('admin.users.roles.admin') : t('admin.users.roles.student')
  if (!confirm(t('admin.users.actions.confirm_role', { name: userItem.name, role: targetRoleName }))) {
    return
  }

  processing.value = true
  try {
    const { error } = await supabase.rpc('admin_update_user_role', {
      p_user_id: userItem.id,
      p_role: newRole
    })

    if (error) throw error
    alert(t('admin.users.actions.success_role'))
    await loadUsers()
    await refreshProfile()
  } catch (err: unknown) {
    alert('Error: ' + (err as Error).message)
  } finally {
    processing.value = false
  }
}

// --- Stats Computeds ---
const statsSummary = computed(() => {
  let totalUsersCount = users.value.length
  let totalAdminsCount = users.value.filter(u => u.role === 'admin').length

  let totalCharges = 0
  let totalSales = 0
  let totalRefunds = 0

  transactions.value.forEach(tx => {
    const amt = Number(tx.amount)
    if (tx.type === 'charge') {
      totalCharges += amt
    } else if (tx.type === 'deduct') {
      totalSales += Math.abs(amt)
    } else if (tx.type === 'refund') {
      totalRefunds += Math.abs(amt)
    }
  })

  // calculate active tickets
  let activeTicketsCount = reservations.value.filter(r => r.status === 'reserved').length

  return {
    totalUsersCount,
    totalAdminsCount,
    totalCharges,
    totalSales,
    totalRefunds,
    activeTicketsCount
  }
})

// UI formatting helpers
const mapMenuType = (koType: string): 'kr' | 'premium' | 'takeout' => {
  if (['kr', 'premium', 'takeout'].includes(koType)) return koType as 'kr' | 'premium' | 'takeout'
  if (koType === '한식') return 'kr'
  if (koType === '일품') return 'premium'
  if (koType === '포장') return 'takeout'
  return 'kr'
}

const getMenuBadgeClass = (koType: string) => {
  const type = mapMenuType(koType)
  if (type === 'premium') return 'bg-amber-100 text-amber-800 border-amber-200'
  if (type === 'takeout') return 'bg-blue-100 text-blue-800 border-blue-200'
  return 'bg-green-100 text-green-800 border-green-200'
}

const formatDate = (dateStr: string) => {
  return new Intl.DateTimeFormat(locale.value === 'ko' ? 'ko-KR' : 'en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(new Date(dateStr))
}

const statusClass: Record<string, string> = {
  reserved: 'bg-green-100 text-green-800 border-green-200',
  used: 'bg-blue-100 text-blue-800 border-blue-200',
  cancelled: 'bg-red-100 text-red-800 border-red-200'
}

const menuItemsByDay = computed(() => {
  const grouped: Record<'mon' | 'tue' | 'wed' | 'thu' | 'fri', Menu[]> = { mon: [], tue: [], wed: [], thu: [], fri: [] }
  dbMenus.value.forEach(menu => {
    const dayGroup = grouped[menu.day_of_week]
    if (dayGroup) {
      dayGroup.push(menu)
    }
  })
  return grouped
})
</script>

<template>
  <div class="pb-10">
    <!-- Header -->
    <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
      <div>
        <h1 class="text-2xl md:text-3xl font-black text-gray-900 flex items-center gap-2">
          🛠️ {{ t('nav_admin') }} <span class="text-base font-semibold text-gray-500 bg-gray-200/60 px-3 py-1 rounded-full">{{ t('admin.dashboard') }}</span>
        </h1>
        <p class="text-sm text-gray-500 mt-1">{{ t('admin.sub_desc') }}</p>
      </div>

      <!-- Tab Buttons -->
      <div class="flex bg-gray-100 p-1.5 rounded-xl border border-gray-200/80 w-full md:w-auto overflow-x-auto no-scrollbar">
        <button
          v-for="tab in tabs"
          :key="tab"
          @click="activeTab = tab"
          class="flex-1 md:flex-none px-4 py-2 text-xs md:text-sm font-black rounded-lg transition-all duration-200 whitespace-nowrap"
          :class="activeTab === tab ? 'bg-white text-[#2E7D32] shadow-sm' : 'text-gray-500 hover:text-gray-800'"
        >
          {{ t(`admin.tabs.${tab}`) }}
        </button>
      </div>
    </div>

    <!-- Active Content Area -->
    <div v-if="loading && !processing" class="bg-white rounded-3xl p-12 text-center border border-gray-100 shadow-[0_4px_20px_rgba(0,0,0,0.02)]">
      <div class="animate-spin rounded-full h-12 w-12 border-4 border-[#4ade80] border-t-transparent mx-auto mb-4"></div>
      <p class="text-sm text-gray-500 font-semibold">{{ t('admin.loading') }}</p>
    </div>

    <div v-else class="space-y-6">
      
      <!-- 1. TAB: MENUS (식단 관리) -->
      <div v-if="activeTab === 'menus'">
        <div class="flex justify-between items-center mb-5 bg-white p-4 rounded-2xl border border-gray-100 shadow-sm">
          <!-- Day switch tabs -->
          <div class="flex gap-2">
            <button
              v-for="day in days"
              :key="day"
              @click="selectedDay = day"
              class="px-3.5 py-2 text-sm font-bold rounded-xl transition-all"
              :class="selectedDay === day ? 'bg-[#E8F5E9] text-[#2E7D32]' : 'text-gray-500 hover:bg-gray-50'"
            >
              {{ t(`days.${day}`) }}{{ t('admin.menus.day_suffix') }}
            </button>
          </div>
          
          <button
            @click="openAddMenuModal"
            class="px-4 py-2.5 bg-[#2E7D32] text-white font-bold rounded-xl text-sm shadow-md hover:bg-[#1b5e20] transition-colors flex items-center gap-1.5"
          >
            <span>+</span> {{ t('admin.menus.add_menu') }}
          </button>
        </div>

        <!-- Menu Grid -->
        <div v-if="menuItemsByDay[selectedDay]?.length" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          <div
            v-for="menu in menuItemsByDay[selectedDay]"
            :key="menu.id"
            class="bg-white border border-gray-100 rounded-3xl p-5 shadow-[0_2px_12px_rgba(0,0,0,0.03)] hover:shadow-md transition-all flex flex-col justify-between"
          >
            <div>
              <div class="flex justify-between items-center mb-3">
                <span class="text-xs font-black px-2.5 py-1 rounded-md border" :class="getMenuBadgeClass(menu.type)">
                  {{ t(`menu_types.${mapMenuType(menu.type)}`) }}
                </span>
                <span class="text-xs text-gray-400 font-semibold">ID: {{ menu.id.substring(0, 8) }}</span>
              </div>
              <h3 class="text-lg font-black text-gray-900 leading-snug">
                {{ locale === 'ko' ? menu.title_ko : menu.title_en }}
              </h3>
              <p class="text-sm text-gray-500 font-semibold mt-1">
                {{ locale === 'ko' ? menu.title_en : menu.title_ko }}
              </p>
            </div>

            <div class="flex justify-between items-center mt-6 pt-4 border-t border-gray-50">
              <span class="font-extrabold text-[#2E7D32] text-lg">{{ menu.price.toLocaleString() }}P</span>
              <div class="flex gap-2">
                <button
                  @click="openEditMenuModal(menu)"
                  class="px-3 py-1.5 bg-gray-50 hover:bg-gray-100 text-gray-600 font-bold rounded-lg text-xs transition-colors border border-gray-200"
                >
                  {{ t('admin.menus.edit') }}
                </button>
                <button
                  @click="deleteMenu(menu.id)"
                  class="px-3 py-1.5 bg-red-50 hover:bg-red-100 text-red-600 font-bold rounded-lg text-xs transition-colors border border-red-100"
                >
                  {{ t('admin.menus.delete') }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <div v-else class="text-center py-20 bg-white rounded-3xl border border-gray-100 shadow-sm">
          <div class="text-4xl mb-4">🍽️</div>
          <p class="text-gray-500 font-bold text-sm">{{ t('admin.menus.no_menus', { day: t(`days.${selectedDay}`) }) }}</p>
          <button @click="openAddMenuModal" class="mt-4 px-4 py-2 text-xs font-bold text-[#2E7D32] hover:underline">
            {{ t('admin.menus.first_menu') }}
          </button>
        </div>
      </div>

      <!-- 2. TAB: TICKETS (식권 조회/사용) -->
      <div v-if="activeTab === 'tickets'" class="space-y-4">
        <!-- Filter bar -->
        <div class="bg-white p-4 rounded-3xl border border-gray-100 shadow-sm flex flex-col md:flex-row gap-4 items-center justify-between">
          <div class="relative w-full md:w-72">
            <span class="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 text-sm">🔍</span>
            <input
              v-model="ticketSearch"
              type="text"
              :placeholder="t('admin.tickets.search_placeholder')"
              class="w-full pl-9 pr-4 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#2E7D32] focus:border-transparent transition-all"
            />
          </div>

          <div class="flex gap-1.5 w-full md:w-auto overflow-x-auto no-scrollbar bg-gray-50 p-1 rounded-xl border border-gray-200/50">
            <button
              v-for="status in ['all', 'reserved', 'used', 'cancelled']"
              :key="status"
              @click="ticketStatusFilter = status"
              class="px-3.5 py-1.5 text-xs font-bold rounded-lg transition-all"
              :class="ticketStatusFilter === status ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-800'"
            >
              {{ t(`admin.tickets.filter_${status}`) }}
            </button>
          </div>
        </div>

        <!-- Tickets List -->
        <div v-if="filteredReservations.length" class="bg-white border border-gray-100 rounded-3xl overflow-hidden shadow-sm">
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-gray-50 border-b border-gray-100 text-gray-500 text-xs font-bold tracking-wider">
                  <th class="py-4 px-6">{{ t('admin.tickets.table.student') }}</th>
                  <th class="py-4 px-6">{{ t('admin.tickets.table.menu') }}</th>
                  <th class="py-4 px-6">{{ t('admin.tickets.table.price_opts') }}</th>
                  <th class="py-4 px-6">{{ t('admin.tickets.table.status') }}</th>
                  <th class="py-4 px-6 text-right">{{ t('admin.tickets.table.action') }}</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100 text-sm font-semibold text-gray-700">
                <tr v-for="res in filteredReservations" :key="res.id" class="hover:bg-gray-50/50 transition-colors">
                  <!-- Student info -->
                  <td class="py-4 px-6">
                    <div class="font-extrabold text-gray-950">{{ res.users?.name || t('admin.tickets.table.no_info') }}</div>
                    <div class="text-xs text-gray-400 mt-0.5">{{ t('student_id') }} {{ res.users?.student_id || '-' }}</div>
                  </td>
                  <!-- Menu info -->
                  <td class="py-4 px-6">
                    <div class="truncate max-w-[200px] font-bold text-gray-900">{{ locale === 'ko' ? (res.menus?.title_ko || t('admin.tickets.table.deleted_menu')) : (res.menus?.title_en || t('admin.tickets.table.deleted_menu')) }}</div>
                    <div class="text-xs text-gray-400 mt-0.5">{{ formatDate(res.created_at || '') }}</div>
                  </td>
                  <!-- Price & Options -->
                  <td class="py-4 px-6">
                    <div class="text-[#2E7D32] font-black">{{ res.total_price.toLocaleString() }}P</div>
                    <div class="text-[10px] text-gray-400 mt-0.5">
                      {{ t('admin.tickets.table.rice') }}: {{ t(`admin.tickets.table.rice_opt.${res.options?.rice || 0}`) }} |
                      {{ t('admin.tickets.table.main') }}: {{ t(`admin.tickets.table.main_opt.${res.options?.main || 0}`) }}
                    </div>
                  </td>
                  <!-- Status -->
                  <td class="py-4 px-6">
                    <span class="inline-flex text-[11px] font-extrabold px-2.5 py-1 rounded-full border" :class="statusClass[res.status || 'reserved']">
                      {{ t(`admin.tickets.filter_${res.status || 'reserved'}`) }}
                    </span>
                  </td>
                  <!-- Actions -->
                  <td class="py-4 px-6 text-right">
                    <div v-if="res.status === 'reserved'" class="flex justify-end gap-2">
                      <button
                        @click="handleUseTicket(res.id)"
                        class="px-3 py-1.5 bg-green-50 hover:bg-green-100 text-[#2E7D32] border border-green-200 rounded-lg text-xs transition-colors"
                      >
                        {{ t('admin.tickets.actions.complete_meal') }}
                      </button>
                      <button
                        @click="handleCancelTicket(res.id)"
                        class="px-3 py-1.5 bg-red-50 hover:bg-red-100 text-red-600 border border-red-200 rounded-lg text-xs transition-colors"
                      >
                        {{ t('admin.tickets.actions.cancel_refund') }}
                      </button>
                    </div>
                    <span v-else class="text-xs text-gray-400 font-medium">-</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div v-else class="text-center py-20 bg-white rounded-3xl border border-gray-100 shadow-sm">
          <div class="text-4xl mb-4">🎫</div>
          <p class="text-gray-500 font-bold text-sm">{{ t('admin.tickets.empty') }}</p>
        </div>
      </div>

      <!-- 3. TAB: USERS (사용자/포인트) -->
      <div v-if="activeTab === 'users'" class="space-y-4">
        <!-- Search bar -->
        <div class="bg-white p-4 rounded-3xl border border-gray-100 shadow-sm flex items-center">
          <div class="relative w-full md:w-72">
            <span class="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 text-sm">🔍</span>
            <input
              v-model="userSearch"
              type="text"
              :placeholder="t('admin.users.search_placeholder')"
              class="w-full pl-9 pr-4 py-2.5 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#2E7D32] focus:border-transparent transition-all"
            />
          </div>
        </div>

        <!-- Users Table -->
        <div v-if="filteredUsers.length" class="bg-white border border-gray-100 rounded-3xl overflow-hidden shadow-sm">
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
              <thead>
                <tr class="bg-gray-50 border-b border-gray-100 text-gray-500 text-xs font-bold tracking-wider">
                  <th class="py-4 px-6">{{ t('admin.users.table.name') }}</th>
                  <th class="py-4 px-6">{{ t('admin.users.table.student_id') }}</th>
                  <th class="py-4 px-6">{{ t('admin.users.table.role') }}</th>
                  <th class="py-4 px-6">{{ t('admin.users.table.points') }}</th>
                  <th class="py-4 px-6 text-right">{{ t('admin.users.table.actions') }}</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100 text-sm font-semibold text-gray-700">
                <tr v-for="u in filteredUsers" :key="u.id" class="hover:bg-gray-50/50 transition-colors">
                  <td class="py-4 px-6 font-extrabold text-gray-950">{{ u.name }}</td>
                  <td class="py-4 px-6 text-gray-500">{{ u.student_id }}</td>
                  <!-- Role badge -->
                  <td class="py-4 px-6">
                    <span
                      class="inline-flex text-[10px] font-black px-2 py-0.5 rounded border"
                      :class="u.role === 'admin' ? 'bg-purple-100 text-purple-800 border-purple-200' : 'bg-gray-100 text-gray-800 border-gray-200'"
                    >
                      {{ t(`admin.users.roles.${u.role}`) }}
                    </span>
                  </td>
                  <!-- Points -->
                  <td class="py-4 px-6 text-[#2E7D32] font-black">
                    {{ Number(u.current_point).toLocaleString() }} P
                  </td>
                  <!-- Admin Actions -->
                  <td class="py-4 px-6 text-right">
                    <div class="flex justify-end gap-2">
                      <button
                        @click="openPointModal(u)"
                        class="px-3 py-1.5 bg-[#E8F5E9] hover:bg-[#b2fab4] text-[#2E7D32] rounded-lg text-xs transition-colors border border-green-200"
                      >
                        {{ t('admin.users.actions.adjust_points') }}
                      </button>
                      <button
                        @click="toggleUserRole(u)"
                        class="px-3 py-1.5 bg-purple-50 hover:bg-purple-100 text-purple-600 rounded-lg text-xs transition-colors border border-purple-200"
                      >
                        {{ u.role === 'admin' ? t('admin.users.actions.demote_student') : t('admin.users.actions.promote_admin') }}
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div v-else class="text-center py-20 bg-white rounded-3xl border border-gray-100 shadow-sm">
          <div class="text-4xl mb-4">👤</div>
          <p class="text-gray-500 font-bold text-sm">{{ t('admin.users.empty') }}</p>
        </div>
      </div>

      <!-- 4. TAB: STATS (매출/통계) -->
      <div v-if="activeTab === 'stats'" class="space-y-6">
        <!-- Summary Cards Grid -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <!-- Stat Card 1 -->
          <div class="bg-white border border-gray-100 rounded-3xl p-5 shadow-sm flex flex-col justify-between">
            <span class="text-xs text-gray-400 font-bold uppercase tracking-wider">{{ t('admin.stats.users_count') }}</span>
            <div class="flex items-baseline gap-1 mt-3">
              <span class="text-3xl font-black text-gray-900">{{ statsSummary.totalUsersCount }}</span>
              <span class="text-sm text-gray-500 font-bold">{{ locale === 'ko' ? '명' : '' }}</span>
            </div>
            <div class="text-[11px] text-purple-600 font-bold mt-2">{{ locale === 'ko' ? `운영 관리자: ${statsSummary.totalAdminsCount}명 포함` : `Includes ${statsSummary.totalAdminsCount} admins` }}</div>
          </div>
          <!-- Stat Card 2 -->
          <div class="bg-white border border-gray-100 rounded-3xl p-5 shadow-sm flex flex-col justify-between">
            <span class="text-xs text-gray-400 font-bold uppercase tracking-wider">{{ t('admin.stats.active_tickets') }}</span>
            <div class="flex items-baseline gap-1 mt-3">
              <span class="text-3xl font-black text-amber-500">{{ statsSummary.activeTicketsCount }}</span>
              <span class="text-sm text-gray-500 font-bold">{{ locale === 'ko' ? '개' : '' }}</span>
            </div>
            <div class="text-[11px] text-gray-400 font-bold mt-2">{{ t('admin.stats.active_tickets_desc') }}</div>
          </div>
          <!-- Stat Card 3 -->
          <div class="bg-white border border-gray-100 rounded-3xl p-5 shadow-sm flex flex-col justify-between">
            <span class="text-xs text-gray-400 font-bold uppercase tracking-wider">{{ t('admin.stats.total_sales') }}</span>
            <div class="flex items-baseline gap-1 mt-3">
              <span class="text-2xl font-black text-[#2E7D32]">{{ statsSummary.totalSales.toLocaleString() }}</span>
              <span class="text-sm text-gray-500 font-bold">P</span>
            </div>
            <div class="text-[11px] text-gray-400 font-bold mt-2">{{ t('admin.stats.total_sales_desc') }}</div>
          </div>
          <!-- Stat Card 4 -->
          <div class="bg-white border border-gray-100 rounded-3xl p-5 shadow-sm flex flex-col justify-between">
            <span class="text-xs text-gray-400 font-bold uppercase tracking-wider">{{ t('admin.stats.total_charges') }}</span>
            <div class="flex items-baseline gap-1 mt-3">
              <span class="text-2xl font-black text-blue-600">{{ statsSummary.totalCharges.toLocaleString() }}</span>
              <span class="text-sm text-gray-500 font-bold">P</span>
            </div>
            <div class="text-[11px] text-red-500 font-bold mt-2">{{ t('admin.stats.total_charges_desc', { refunds: statsSummary.totalRefunds.toLocaleString() }) }}</div>
          </div>
        </div>

        <!-- Recent System-wide Transactions -->
        <div>
          <h2 class="text-lg font-black text-gray-900 mb-3">{{ t('admin.stats.log_title') }}</h2>
          <div v-if="transactions.length" class="bg-white border border-gray-100 rounded-3xl overflow-hidden shadow-sm">
            <div class="overflow-x-auto">
              <table class="w-full text-left border-collapse">
                <thead>
                  <tr class="bg-gray-50 border-b border-gray-100 text-gray-500 text-xs font-bold tracking-wider">
                    <th class="py-4 px-6">{{ t('admin.stats.log_table.date') }}</th>
                    <th class="py-4 px-6">{{ t('admin.stats.log_table.student') }}</th>
                    <th class="py-4 px-6">{{ t('admin.stats.log_table.amount') }}</th>
                    <th class="py-4 px-6">{{ t('admin.stats.log_table.type') }}</th>
                    <th class="py-4 px-6">{{ t('admin.stats.log_table.desc') }}</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-gray-100 text-xs font-bold text-gray-700">
                  <tr v-for="tx in transactions" :key="tx.id" class="hover:bg-gray-50/50">
                    <td class="py-3 px-6 text-gray-400">{{ formatDate(tx.created_at || '') }}</td>
                    <td class="py-3 px-6 text-gray-800">
                      {{ tx.users?.name || t('admin.stats.log_table.no_info') }} ({{ tx.users?.student_id || '-' }})
                    </td>
                    <td class="py-3 px-6" :class="tx.amount > 0 ? 'text-[#2E7D32]' : 'text-gray-950'">
                      {{ tx.amount > 0 ? '+' : '' }}{{ tx.amount.toLocaleString() }}P
                    </td>
                    <td class="py-3 px-6">
                      <span
                        class="inline-block text-[10px] px-1.5 py-0.5 rounded"
                        :class="tx.type === 'charge' ? 'bg-blue-50 text-blue-700 border border-blue-200' : tx.type === 'refund' ? 'bg-green-50 text-[#2E7D32] border border-green-200' : 'bg-gray-50 text-gray-700 border border-gray-200'"
                      >
                        {{ t(`admin.stats.log_table.${tx.type}`) }}
                      </span>
                    </td>
                    <td class="py-3 px-6 text-gray-500 font-semibold">
                      {{ tx.description === '포인트 충전' ? t('payment.charge') : (tx.description === '메뉴 예약' ? t('payment.use') : (tx.description === '예약 취소 환불' ? t('payment.refund') : (tx.description === '예약 취소 환불 (관리자)' ? t('payment.refund_admin') : (tx.description === '관리자 포인트 조정' ? t('payment.admin_adjust') : (tx.description || '-'))))) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <div v-else class="text-center py-20 bg-white rounded-3xl border border-gray-100 shadow-sm">
            <p class="text-gray-400 font-bold text-sm">{{ t('admin.stats.empty_logs') }}</p>
          </div>
        </div>
      </div>

    </div>

    <!-- === MODALS === -->

    <!-- Modal: Menu Add / Edit -->
    <div v-if="menuModalOpen" class="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-3xl max-w-md w-full shadow-2xl p-6 border border-gray-100 animate-in fade-in zoom-in-95 duration-200">
        <h3 class="text-xl font-black text-gray-900 mb-5">{{ isEditMode ? t('admin.menus.edit_menu') : t('admin.menus.new_menu') }}</h3>
        
        <form @submit.prevent="saveMenu" class="space-y-4 text-sm font-semibold">
          <!-- Day -->
          <div>
            <label class="block text-xs font-bold text-gray-500 mb-1">{{ t('admin.menus.fields.day') }}</label>
            <select
              v-model="menuForm.day_of_week"
              class="w-full px-3 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-[#2E7D32] focus:border-transparent transition-all"
            >
              <option v-for="day in days" :key="day" :value="day">{{ t(`days.${day}`) }}{{ t('admin.menus.day_suffix') }}</option>
            </select>
          </div>

          <!-- Type -->
          <div>
            <label class="block text-xs font-bold text-gray-500 mb-1">{{ t('admin.menus.fields.type') }}</label>
            <select
              v-model="menuForm.type"
              class="w-full px-3 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-[#2E7D32] focus:border-transparent transition-all"
            >
              <option value="kr">{{ t('menu_types.kr') }}</option>
              <option value="premium">{{ t('menu_types.premium') }}</option>
              <option value="takeout">{{ t('menu_types.takeout') }}</option>
            </select>
          </div>

          <!-- KO Title -->
          <div>
            <label class="block text-xs font-bold text-gray-500 mb-1">{{ t('admin.menus.fields.title_ko') }}</label>
            <input
              v-model="menuForm.title_ko"
              type="text"
              required
              :placeholder="t('admin.menus.fields.title_ko_placeholder')"
              class="w-full px-3 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-[#2E7D32] focus:border-transparent transition-all"
            />
          </div>

          <!-- EN Title -->
          <div>
            <label class="block text-xs font-bold text-gray-500 mb-1">{{ t('admin.menus.fields.title_en') }}</label>
            <input
              v-model="menuForm.title_en"
              type="text"
              required
              :placeholder="t('admin.menus.fields.title_en_placeholder')"
              class="w-full px-3 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-[#2E7D32] focus:border-transparent transition-all"
            />
          </div>

          <!-- Price -->
          <div>
            <label class="block text-xs font-bold text-gray-500 mb-1">{{ t('admin.menus.fields.price') }}</label>
            <input
              v-model.number="menuForm.price"
              type="number"
              required
              min="0"
              :placeholder="t('admin.menus.fields.price_placeholder')"
              class="w-full px-3 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-[#2E7D32] focus:border-transparent transition-all"
            />
          </div>

          <!-- Modal Actions -->
          <div class="flex justify-end gap-3 pt-4">
            <button
              type="button"
              @click="menuModalOpen = false"
              class="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-600 rounded-xl font-bold transition-colors"
            >
              {{ t('admin.menus.cancel') }}
            </button>
            <button
              type="submit"
              :disabled="processing"
              class="px-4 py-2 bg-[#2E7D32] hover:bg-[#1b5e20] text-white rounded-xl font-bold shadow-md transition-colors disabled:opacity-50"
            >
              {{ t('admin.menus.save') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Modal: Point Adjust -->
    <div v-if="pointModalOpen" class="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-3xl max-w-sm w-full shadow-2xl p-6 border border-gray-100 animate-in fade-in zoom-in-95 duration-200">
        <h3 class="text-xl font-black text-gray-900 mb-1">{{ t('admin.users.actions.adjust_modal_title') }}</h3>
        <p class="text-xs text-gray-400 font-bold mb-5">{{ t('admin.users.actions.adjust_modal_target', { name: selectedUser?.name, student_id: selectedUser?.student_id }) }}</p>

        <form @submit.prevent="adjustUserPoints" class="space-y-4 text-sm font-semibold">
          <div>
            <label class="block text-xs font-bold text-gray-500 mb-1">{{ t('admin.users.actions.adjust_amount') }}</label>
            <input
              v-model.number="pointAdjustAmount"
              type="number"
              required
              placeholder="e.g. 10000 or -5000"
              class="w-full px-3 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-[#2E7D32] focus:border-transparent transition-all"
            />
            <p class="text-[10px] text-gray-400 mt-1 font-bold">{{ t('admin.users.actions.adjust_amount_desc') }}</p>
          </div>

          <div>
            <label class="block text-xs font-bold text-gray-500 mb-1">{{ t('admin.users.actions.adjust_desc') }}</label>
            <input
              v-model="pointAdjustDesc"
              type="text"
              required
              :placeholder="t('admin.users.actions.adjust_desc_placeholder')"
              class="w-full px-3 py-2.5 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-[#2E7D32] focus:border-transparent transition-all"
            />
          </div>

          <!-- Modal Actions -->
          <div class="flex justify-end gap-3 pt-4">
            <button
              type="button"
              @click="pointModalOpen = false"
              class="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-600 rounded-xl font-bold transition-colors"
            >
              {{ t('admin.menus.cancel') }}
            </button>
            <button
              type="submit"
              :disabled="processing"
              class="px-4 py-2 bg-[#2E7D32] hover:bg-[#1b5e20] text-white rounded-xl font-bold shadow-md transition-colors disabled:opacity-50"
            >
              {{ t('admin.menus.save') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Processing Overlay spinner -->
    <div v-if="processing" class="fixed inset-0 bg-black/30 backdrop-blur-sm flex items-center justify-center z-50">
      <div class="bg-white p-6 rounded-2xl shadow-xl flex flex-col items-center">
        <div class="animate-spin rounded-full h-12 w-12 border-4 border-[#4ade80] border-t-transparent mb-4"></div>
        <div class="text-gray-700 font-bold">{{ t('admin.processing') }}</div>
      </div>
    </div>

  </div>
</template>

<style scoped>
/* Hide scrollbar for Chrome, Safari and Opera */
.no-scrollbar::-webkit-scrollbar {
  display: none;
}
/* Hide scrollbar for IE, Edge and Firefox */
.no-scrollbar {
  -ms-overflow-style: none;  /* IE and Edge */
  scrollbar-width: none;  /* Firefox */
}
</style>
