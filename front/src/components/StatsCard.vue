<template>
  <div class="p-6 bg-zinc-900 rounded-xl border border-zinc-800 transition-all hover:border-zinc-700 hover:-translate-y-0.5 hover:shadow-xl">
    <div class="flex flex-col gap-1">
      <div class="text-xs text-zinc-500 uppercase tracking-wider font-medium">{{ label }}</div>
      <div class="text-3xl font-bold text-white">{{ value }}</div>
      <div v-if="subtitle" class="text-xs text-zinc-500 mt-1">{{ subtitle }}</div>
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
    }
  }
};
</script>
