<template>
  <div class="flex flex-col items-center justify-center py-20 gap-4 animate-fade-in">
    <div class="text-5xl animate-float">⚠️</div>
    <p class="text-red-400 text-lg text-center font-medium animate-pulse">{{ message }}</p>
  </div>
</template>

<script>
export default {
  name: 'ErrorMessage',
  props: {
    message: {
      type: String,
      required: true
    }
  }
};
</script>
