<template>
  <header class="header">
    <h1>Transaction Risk Viewer</h1>
    <p class="subtitle">Filter and explore transaction risk analyses</p>
  </header>
</template>

<script>
export default {
  name: 'AppHeader'
};
</script>

<style scoped>
.header {
  background: linear-gradient(180deg, #ffffff 0%, #f5f5f7 100%);
  color: #1d1d1f;
  padding: 48px 32px;
  text-align: center;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.header h1 {
  font-size: 3rem;
  font-weight: 600;
  margin-bottom: 8px;
  letter-spacing: -0.02em;
  background: linear-gradient(135deg, #007aff 0%, #5856d6 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.subtitle {
  font-size: 1.125rem;
  color: #86868b;
  font-weight: 400;
  letter-spacing: -0.01em;
}
</style>
