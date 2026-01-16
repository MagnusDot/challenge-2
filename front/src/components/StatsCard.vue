<template>
  <div
    class="p-6 bg-zinc-900 rounded-xl border border-zinc-800 transition-all duration-300 hover:border-blue-500/50 hover:-translate-y-1 hover:shadow-2xl hover:shadow-blue-500/20 group relative overflow-hidden animate-fade-in-up"
    :style="{ animationDelay: `${index * 0.1}s` }"
  >
    <div class="absolute inset-0 bg-gradient-to-r from-blue-600/0 via-blue-600/10 to-purple-600/0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 animate-shimmer"></div>
    <div class="relative z-10 flex flex-col gap-1">
      <div class="text-xs text-zinc-500 uppercase tracking-wider font-medium group-hover:text-blue-400 transition-colors duration-300">{{ label }}</div>
      <div class="text-3xl font-bold text-white group-hover:bg-gradient-to-r group-hover:from-blue-400 group-hover:to-purple-400 group-hover:bg-clip-text group-hover:text-transparent transition-all duration-300">
        {{ value }}
      </div>
      <div v-if="subtitle" class="text-xs text-zinc-500 mt-1 group-hover:text-zinc-400 transition-colors duration-300">{{ subtitle }}</div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'StatsCard',
  props: {
    icon: {
      type: String,
      default: ''
    },
    label: {
      type: String,
      required: true
    },
    value: {
      type: [String, Number],
      required: true
    },
    subtitle: {
      type: String,
      default: null
    },
    index: {
      type: Number,
      default: 0
    }
  }
};
</script>
