<template>
  <header class="sticky top-0 z-50 bg-gradient-to-br from-zinc-900 to-black border-b border-zinc-800 backdrop-blur-xl animate-fade-in">
    <div class="max-w-7xl mx-auto px-6 py-6">
      <div class="flex justify-between items-center">
        <div>
          <div class="flex items-center gap-3 mb-1">
            <h1 class="text-3xl font-bold bg-gradient-to-r from-white via-blue-200 to-purple-200 bg-clip-text text-transparent animate-gradient">
              Transaction Risk Monitor
            </h1>
            <span class="px-3 py-1 bg-gradient-to-r from-blue-600 to-purple-600 text-white text-xs font-bold rounded-full uppercase tracking-wider shadow-lg hover:shadow-blue-500/50 transition-all duration-300 hover:scale-110 animate-pulse-glow">
              Aivengers
            </span>
          </div>
          <p class="text-sm text-zinc-500 animate-slide-in-right">Real-time risk analysis dashboard</p>
        </div>
        <div class="flex gap-8">
          <div class="flex flex-col items-end gap-1 animate-fade-in-up delay-200">
            <span class="text-xs text-zinc-500 uppercase tracking-wider font-medium">Total</span>
            <span class="text-2xl font-bold text-white bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">{{ totalCount || 0 }}</span>
          </div>
          <div class="flex flex-col items-end gap-1 animate-fade-in-up delay-300">
            <span class="text-xs text-zinc-500 uppercase tracking-wider font-medium">Filtered</span>
            <span class="text-2xl font-bold text-white bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">{{ filteredCount || 0 }}</span>
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
