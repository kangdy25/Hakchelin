<template>
  <div class="min-h-screen bg-gray-50 flex flex-col md:flex-row font-sans text-gray-800">
    <BottomNav />
    <div class="flex-1 flex flex-col min-w-0 pb-20 md:pb-0 md:ml-64 lg:ml-72 transition-all duration-300">
      <AppHeader />
      <main class="flex-1 w-full max-w-5xl mx-auto p-4 md:p-8">
        <slot />
      </main>
    </div>
  </div>
</template>

<style>
body {
  margin: 0;
  padding: 0;
  background-color: #f9fafb;
}
</style>
