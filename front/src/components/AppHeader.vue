<template>
  <header class="sticky top-0 z-50 bg-gradient-to-br from-zinc-900 to-black border-b border-zinc-800 backdrop-blur-xl">
    <div class="max-w-7xl mx-auto px-6 py-6">
      <div class="flex justify-between items-center">
        <div>
          <h1 class="text-3xl font-bold mb-1 bg-gradient-to-r from-white to-zinc-400 bg-clip-text text-transparent">
            Transaction Risk Monitor
          </h1>
          <p class="text-sm text-zinc-500">Real-time risk analysis dashboard</p>
        </div>
        <div class="flex gap-8">
          <div class="flex flex-col items-end gap-1">
            <span class="text-xs text-zinc-500 uppercase tracking-wider font-medium">Total</span>
            <span class="text-2xl font-bold text-white">{{ totalCount || 0 }}</span>
          </div>
          <div class="flex flex-col items-end gap-1">
            <span class="text-xs text-zinc-500 uppercase tracking-wider font-medium">Filtered</span>
            <span class="text-2xl font-bold text-white">{{ filteredCount || 0 }}</span>
          </div>
        </div>
      </div>
    </div>
  </header>
</template>

<script>
export default {
  name: 'AppHeader',
  props: {
    totalCount: {
      type: Number,
      default: 0
    },
    filteredCount: {
      type: Number,
      default: 0
    }
  }
};
</script>
