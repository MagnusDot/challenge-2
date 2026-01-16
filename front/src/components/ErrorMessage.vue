<template>
  <div class="error-container">
    <div class="error-icon">⚠️</div>
    <p class="error-message">{{ message }}</p>
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

<style scoped>
.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  gap: 16px;
}

.error-icon {
  font-size: 3rem;
}

.error-message {
  color: #ff3b30;
  font-size: 1.125rem;
  text-align: center;
  font-weight: 500;
  letter-spacing: -0.01em;
}
</style>
