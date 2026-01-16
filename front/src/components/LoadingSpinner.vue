<template>
  <div class="flex flex-col items-center justify-center py-20 gap-6">
    <div class="w-10 h-10 border-4 border-zinc-800 border-t-blue-500 rounded-full animate-spin"></div>
    <p class="text-zinc-500 text-base font-medium">{{ message }}</p>
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
