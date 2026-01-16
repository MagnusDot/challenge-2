<template>
  <div class="flex flex-col items-center justify-center py-20 gap-6 animate-fade-in">
    <div class="relative">
      <div class="w-16 h-16 border-4 border-zinc-800 border-t-blue-500 rounded-full animate-spin"></div>
      <div class="absolute inset-0 w-16 h-16 border-4 border-transparent border-r-purple-500 rounded-full animate-spin" style="animation-duration: 1.5s; animation-direction: reverse;"></div>
    </div>
    <p class="text-zinc-500 text-base font-medium animate-pulse">{{ message }}</p>
  </div>
</template>

<script>
export default {
  name: 'LoadingSpinner',
  props: {
    message: {
      type: String,
      default: 'Loading data...'
    }
  }
};
</script>
