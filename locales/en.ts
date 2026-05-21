export default {
  "app_name": "Uni Menu v8",
  "user_name": "Student Kim",
  "user_major": "Computer Science",
  "welcome": "Welcome, {name}!",
  "point": "My Balance",
  "charge": "+ Top-up",
  "policy": [
    "📍 Lunch Only (11:30~13:30)",
    "📍 Pre-order: 4,500P / Walk-in: 5,500P",
    "📍 No-show penalty: 1,000P deducted from refund"
  ],
  "btnLang": "한국어",
  "reserve": "Reserve & Pay Now",
  "optRice0": "Rice: Regular",
  "optRice1": "Rice: Small (Eco-friendly)",
  "optRice2": "Rice: Large",
  "optMain0": "Main: Regular",
  "optMain1": "Main: Extra (+1,000P)",
  "nav0": "Home",
  "nav1": "Tickets",
  "nav2": "History",
  "nav3": "Profile",
  "alert": "Would you like to reserve?",
  "days": {
    "mon": "Mon",
    "tue": "Tue",
    "wed": "Wed",
    "thu": "Thu",
    "fri": "Fri"
  },
  "days_full": {
    "mon": "Monday",
    "tue": "Tuesday",
    "wed": "Wednesday",
    "thu": "Thursday",
    "fri": "Friday"
  },
  "empty_menu": "No menus available.",
  "menu_types": {
    "kr": "Korean",
    "premium": "Premium",
    "takeout": "Take-out"
  },
  "my_tickets": "My Tickets",
  "point_history": "Point History",
  "my_profile": "My Profile",
  "coming_soon": "Page coming soon.",
  "empty_tickets": "You have no active tickets.",
  "empty_history": "No point history found.",
  "empty_profile": "Profile settings will be available soon.",
  "student": "Student",
  "student_id": "Student ID:",
  "logout": "Logout",
  "logout_error": "An error occurred during logout.",
  "status": {
    "reserved": "Reserved",
    "used": "Used",
    "cancelled": "Cancelled"
  },
  "options": {
    "rice": "Rice Option",
    "main": "Main Option"
  },
  "payment": {
    "total": "Payment Points",
    "charge": "Point Top-up",
    "use": "Point Usage",
    "complete": "Paid",
    "used": "Used",
    "loading_tickets": "Loading tickets...",
    "loading_history": "Loading history...",
    "deleted_menu": "Deleted Menu",
    "unit": "P"
  }
}

rMessage.value = error.message
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
          <strong class="text-[#2E7D32] text-[18px]">{{ reservation.total_price.toLocaleString() }}{{ t('payment.unit') }}</strong>
        </div>

      </article>
    </div>
  </div>
</template>
