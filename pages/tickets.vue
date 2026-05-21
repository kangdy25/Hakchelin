<script setup lang="ts">
const { t, locale } = useI18n({ useScope: 'global' })
const supabase = useSupabaseClient<any>()
const { userId } = useUserProfile()

type Reservation = {
  id: string
  menu_id: string
  options: {
    rice?: number
    main?: number
  }
  total_price: number
  status: 'reserved' | 'used' | 'cancelled'
  created_at: string
  menus?: {
    type: string
    title_ko: string
    title_en: string
    day_of_week: string
    price: number
  } | null
}

const loading = ref(true)
const errorMessage = ref('')
const reservations = ref<Reservation[]>([])

const statusLabel = computed(() => ({
  reserved: t('status.reserved'),
  used: t('status.used'),
  cancelled: t('status.cancelled')
}))

const statusClass: Record<string, string> = {
  reserved: 'bg-[#E8F5E9] text-[#2E7D32]',
  used: 'bg-[#E3F2FD] text-[#1565C0]',
  cancelled: 'bg-[#FCE4EC] text-[#C2185B]'
}

const riceLabel = (value?: number) => {
  if (value === 1) return t('optRice1')
  if (value === 2) return t('optRice2')
  return t('optRice0')
}

const mainLabel = (value?: number) => {
  if (value === 1) return t('optMain1')
  return t('optMain0')
}

const formatDate = (value: string) => {
  return new Intl.DateTimeFormat(locale.value === 'ko' ? 'ko-KR' : 'en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(new Date(value))
}

const menuTitle = (reservation: Reservation) => {
  if (!reservation.menus) return t('payment.deleted_menu')
  return locale.value === 'ko' ? reservation.menus.title_ko : reservation.menus.title_en
}

const fetchReservations = async () => {
  if (!userId.value) {
    loading.value = false
    return
  }

  loading.value = true
  errorMessage.value = ''

  const { data, error } = await supabase
    .from('reservations')
    .select('id, menu_id, options, total_price, status, created_at')
    .eq('user_id', userId.value)
    .order('created_at', { ascending: false })

  if (error) {
    errorMessage.value = error.message
  } else {
    const rows = data || []
    const menuIds = [...new Set(rows.map((reservation: Reservation) => reservation.menu_id).filter(Boolean))]

    if (!menuIds.length) {
      reservations.value = rows
      loading.value = false
      return
    }

    const { data: menus, error: menuError } = await supabase
      .from('menus')
      .select('id, type, title_ko, title_en, day_of_week, price')
      .in('id', menuIds)

    if (menuError) {
      errorMessage.value = menuError.message
    } else {
      const menuMap = new Map((menus || []).map((menu: any) => [menu.id, menu]))
      reservations.value = rows.map((reservation: Reservation) => ({
        ...reservation,
        menus: menuMap.get(reservation.menu_id) || null
      }))
    }
  }

  loading.value = false
}

watch(
  () => userId.value,
  () => fetchReservations(),
  { immediate: true }
)
</script>

<template>
  <div>
    <h1 class="text-2xl md:text-3xl font-black text-gray-800 mb-6">{{ t('my_tickets') }}</h1>

    <div v-if="loading" class="bg-white rounded-[15px] p-8 text-center border border-[#eee]">
      <div class="animate-spin rounded-full h-10 w-10 border-4 border-[#4ade80] border-t-transparent mx-auto mb-4"></div>
      <p class="text-sm text-gray-500">{{ t('payment.loading_tickets') }}</p>
    </div>

    <div v-else-if="errorMessage" class="bg-red-50 text-red-600 rounded-[15px] p-5 border border-red-100 text-sm font-bold">
      {{ errorMessage }}
    </div>

    <div v-else-if="!reservations.length" class="bg-white rounded-[15px] p-8 text-center shadow-[0_2px_8px_rgba(0,0,0,0.05)] border border-[#eee] flex flex-col items-center justify-center min-h-[40vh]">
      <div class="text-5xl mb-6">🎫</div>
      <p class="text-[#777] font-medium">{{ t('empty_tickets') }}</p>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-[15px]">
      <article
        v-for="reservation in reservations"
        :key="reservation.id"
        class="bg-white border border-[#eee] rounded-[15px] p-5 shadow-[0_2px_8px_rgba(0,0,0,0.05)]"
      >
        <div class="flex items-start justify-between gap-3 mb-4">
          <div>
            <div class="text-[12px] text-[#777] font-bold mb-1">{{ formatDate(reservation.created_at) }}</div>
            <h2 class="text-[18px] font-black text-gray-800 leading-snug">{{ menuTitle(reservation) }}</h2>
          </div>
          <span class="shrink-0 text-[12px] font-bold px-3 py-1.5 rounded-lg" :class="statusClass[reservation.status]">
            {{ statusLabel[reservation.status] }}
          </span>
        </div>

        <div class="grid grid-cols-2 gap-2 mb-4">
          <div class="bg-[#f8f9fa] rounded-[8px] p-3">
            <div class="text-[11px] text-[#777] mb-1">{{ t('options.rice') }}</div>
            <div class="text-[13px] font-bold text-gray-800">{{ riceLabel(reservation.options?.rice) }}</div>
          </div>
          <div class="bg-[#f8f9fa] rounded-[8px] p-3">
            <div class="text-[11px] text-[#777] mb-1">{{ t('options.main') }}</div>
            <div class="text-[13px] font-bold text-gray-800">{{ mainLabel(reservation.options?.main) }}</div>
          </div>
        </div>

        <div class="flex items-center justify-between border-t border-[#eee] pt-4">
          <span class="text-[12px] text-[#777] font-bold">{{ t('payment.total') }}</span>
          <strong class="text-[#2E7D32] text-[18px]">{{ reservation.total_price.toLocaleString() }}P</strong>
        </div>
      </article>
    </div>
  </div>
</template>
