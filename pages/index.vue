<script setup lang="ts">
import { ref } from 'vue'
import { mockMenus } from '~/constants/MockMenus'

const { t, tm, rt } = useI18n({ useScope: 'global' })

const days = ['mon', 'tue', 'wed', 'thu', 'fri']
const selectedDay = ref('mon')


const onReserve = (payload: any) => {
  alert('예약 처리가 진행됩니다 (Mock)')
  console.log('Reservation Payload:', payload)
}
</script>

<template>
  <div>
    <div class="bg-[#FFF3E0] rounded-[10px] p-[12px] mb-[15px] text-[12px] text-[#E65100] border border-[#FFE0B2] leading-[1.6]">
      <div v-for="item in tm('policy')" :key="item">
    {{ rt(item) }}
  </div>
    </div>

    <div class="flex justify-between bg-[#f8f9fa] p-[5px] rounded-[10px] mb-[15px]">
      <button 
        v-for="day in days" :key="day"
        @click="selectedDay = day"
        class="flex-1 border-none bg-transparent py-[10px] text-[13px] rounded-[8px] text-[#777] font-bold cursor-pointer transition-colors"
        :class="{ 'bg-[#b2fab4] text-black': selectedDay === day }"
      >
        <span>{{ t(`days.${day}`) }}</span>
      </button>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-[15px] pb-6">
      <MenuCard 
        v-for="menu in mockMenus[selectedDay]" 
        :key="menu.id" 
        :menu="menu" 
        @reserve="onReserve"
      />
    </div>
    
    <div v-if="!mockMenus[selectedDay]?.length" class="text-center py-[40px] bg-white rounded-[15px] border border-[#eee] mb-6">
      <div class="text-[#777] font-bold text-[13px]">{{ t('empty_menu') }}</div>
    </div>
  </div>
</template>
