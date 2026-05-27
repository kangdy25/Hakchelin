<script setup lang="ts">
const { alertState, confirmState, closeAlert, closeConfirm } = useModal()
const { t } = useI18n()
</script>

<template>
  <div>
    <!-- Global Alert Modal -->
    <Transition name="modal-fade">
      <div 
        v-if="alertState.show" 
        class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/40 backdrop-blur-[4px]"
        @click.self="closeAlert"
      >
        <div class="bg-white rounded-[24px] p-6 max-w-sm w-full shadow-[0_20px_50px_rgba(0,0,0,0.15)] border border-gray-100 flex flex-col items-center text-center transform transition-all duration-300 scale-100">
          
          <!-- Icon by Type -->
          <div class="mb-4">
            <!-- Success Icon -->
            <div v-if="alertState.type === 'success'" class="w-16 h-16 bg-green-50 text-green-500 rounded-full flex items-center justify-center text-3xl shadow-inner">
              ✓
            </div>
            <!-- Error Icon -->
            <div v-else-if="alertState.type === 'error'" class="w-16 h-16 bg-red-50 text-red-500 rounded-full flex items-center justify-center text-3xl shadow-inner">
              ✕
            </div>
            <!-- Warning Icon -->
            <div v-else-if="alertState.type === 'warning'" class="w-16 h-16 bg-amber-50 text-amber-500 rounded-full flex items-center justify-center text-3xl shadow-inner">
              !
            </div>
            <!-- Info Icon -->
            <div v-else class="w-16 h-16 bg-blue-50 text-blue-500 rounded-full flex items-center justify-center text-3xl shadow-inner">
              i
            </div>
          </div>

          <!-- Title -->
          <h3 v-if="alertState.title" class="text-lg font-bold text-gray-800 mb-2">
            {{ alertState.title }}
          </h3>

          <!-- Message -->
          <p class="text-sm text-gray-600 font-medium whitespace-pre-line leading-relaxed mb-6">
            {{ alertState.message }}
          </p>

          <!-- Action Button -->
          <button 
            @click="closeAlert"
            class="w-full py-3.5 bg-primary hover:bg-primary-dark active:scale-[0.98] text-white font-bold rounded-xl shadow-lg shadow-green-100 transition-all duration-150 cursor-pointer"
          >
            {{ t('admin.menus.save') || '확인' }}
          </button>
        </div>
      </div>
    </Transition>

    <!-- Global Confirm Modal -->
    <Transition name="modal-fade">
      <div 
        v-if="confirmState.show" 
        class="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/40 backdrop-blur-[4px]"
        @click.self="closeConfirm(false)"
      >
        <div class="bg-white rounded-[24px] p-6 max-w-sm w-full shadow-[0_20px_50px_rgba(0,0,0,0.15)] border border-gray-100 flex flex-col items-center text-center transform transition-all duration-300 scale-100">
          
          <!-- Confirm Icon (Question Mark/Warning Style) -->
          <div class="mb-4">
            <div class="w-16 h-16 bg-amber-50 text-amber-500 rounded-full flex items-center justify-center text-3xl shadow-inner">
              ?
            </div>
          </div>

          <!-- Title -->
          <h3 v-if="confirmState.title" class="text-lg font-bold text-gray-800 mb-2">
            {{ confirmState.title }}
          </h3>

          <!-- Message -->
          <p class="text-sm text-gray-600 font-medium whitespace-pre-line leading-relaxed mb-6">
            {{ confirmState.message }}
          </p>

          <!-- Action Buttons -->
          <div class="flex gap-3 w-full">
            <button 
              @click="closeConfirm(false)"
              class="flex-1 py-3.5 bg-gray-100 hover:bg-gray-200 active:scale-[0.98] text-gray-600 font-bold rounded-xl transition-all duration-150 cursor-pointer"
            >
              {{ t('admin.menus.cancel') || '취소' }}
            </button>
            <button 
              @click="closeConfirm(true)"
              class="flex-1 py-3.5 bg-primary hover:bg-primary-dark active:scale-[0.98] text-white font-bold rounded-xl shadow-lg shadow-green-100 transition-all duration-150 cursor-pointer"
            >
              {{ t('admin.menus.save') || '확인' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.modal-fade-enter-active,
.modal-fade-leave-active {
  transition: opacity 0.25s ease;
}

.modal-fade-enter-from,
.modal-fade-leave-to {
  opacity: 0;
}

.modal-fade-enter-active .transform,
.modal-fade-leave-active .transform {
  transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.modal-fade-enter-from .transform {
  transform: scale(0.9) translateY(10px);
}

.modal-fade-leave-to .transform {
  transform: scale(0.95) translateY(0);
}
</style>
