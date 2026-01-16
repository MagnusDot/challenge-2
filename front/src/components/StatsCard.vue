<template>
  <div class="stats-card">
    <div class="stats-card-content">
      <div class="stats-card-label">{{ label }}</div>
      <div class="stats-card-value">{{ value }}</div>
      <div v-if="subtitle" class="stats-card-subtitle">{{ subtitle }}</div>
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

<style scoped>
.stats-card {
  padding: 20px 24px;
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.05);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.stats-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  border-color: rgba(0, 0, 0, 0.1);
}

.stats-card-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stats-card-label {
  font-size: 0.8125rem;
  color: #86868b;
  font-weight: 500;
  letter-spacing: -0.01em;
  text-transform: uppercase;
}

.stats-card-value {
  font-size: 2rem;
  font-weight: 600;
  color: #1d1d1f;
  line-height: 1.2;
  letter-spacing: -0.02em;
}

.stats-card-subtitle {
  font-size: 0.75rem;
  color: #86868b;
  margin-top: 2px;
  font-weight: 400;
}
</style>
