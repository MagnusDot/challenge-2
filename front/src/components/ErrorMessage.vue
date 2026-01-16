<template>
  <div class="flex flex-col items-center justify-center py-20 gap-4">
    <div class="text-5xl">⚠️</div>
    <p class="text-red-400 text-lg text-center font-medium">{{ message }}</p>
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
