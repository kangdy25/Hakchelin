<script setup lang="ts">
import { computed, ref } from 'vue'
const { t, locale } = useI18n({ useScope: 'global' })

const props = defineProps<{
  menu: {
    id: string
    type: string
    title_ko: string
    title_en: string
    price: number
  },
  disabled?: boolean
}>()

const emit = defineEmits(['reserve'])

const selectedRice = ref(0)
const selectedMain = ref(0)

const typeClass = computed(() => {
  if (props.menu.type === 'kr') return 'bg-[#E8F5E9] text-[#2E7D32]'
  if (props.menu.type === 'premium') return 'bg-[#E3F2FD] text-[#1565C0]'
  return 'bg-[#FCE4EC] text-[#C2185B]'
})

const title = computed(() => locale.value === 'ko' ? props.menu.title_ko : props.menu.title_en)
const finalPrice = computed(() => props.menu.price + (selectedMain.value === 1 ? 1000 : 0))

const handleReserve = () => {
  if (props.disabled) return

  if (confirm(t('alert'))) {
    emit('reserve', { 
      menu_id: props.menu.id, 
      price: finalPrice.value,
      options: {
        rice: selectedRice.value,
        main: selectedMain.value
      }
    })
  }
}
</script>

<template>
  <div class="border border-[#eee] rounded-[15px] p-[15px] bg-white shadow-[0_2px_8px_rgba(0,0,0,0.05)] flex flex-col h-full">
    <div class="flex justify-between items-start">
      <span class="text-[12px] font-bold px-3 py-1.5 rounded-lg" :class="typeClass">
        {{ t(`menu_types.${menu.type}`) }}
      </span>
    </div>
    
    <div class="text-[17px] font-bold my-[8px]">{{ title }}</div>
    <div class="text-[#2E7D32] font-bold text-[14px] mb-[10px]">{{ finalPrice.toLocaleString() }}P</div>
    
    <div class="mt-auto">
      <select v-model="selectedRice" class="w-full p-[10px] mt-[5px] rounded-[8px] border border-[#ddd] text-[13px] bg-[#fafafa] focus:outline-none focus:border-[#2E7D32] cursor-pointer">
        <option :value="0">{{ t('optRice0') }}</option>
        <option :value="1">{{ t('optRice1') }}</option>
        <option :value="2">{{ t('optRice2') }}</option>
      </select>
      
      <select v-model="selectedMain" class="w-full p-[10px] mt-[5px] rounded-[8px] border border-[#ddd] text-[13px] bg-[#fafafa] focus:outline-none focus:border-[#2E7D32] cursor-pointer">
        <option :value="0">{{ t('optMain0') }}</option>
        <option :value="1">{{ t('optMain1') }}</option>
      </select>
      
      <button
        @click="handleReserve"
        :disabled="disabled"
        class="w-full bg-[#2E7D32] text-white border-none p-[14px] rounded-[8px] font-bold cursor-pointer mt-[15px] text-[15px] disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {{ t('reserve') }}
      </button>
    </div>
  </div>
</template>
