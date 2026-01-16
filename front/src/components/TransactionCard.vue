<template>
  <div class="transaction-card" @click="handleClick">
    <div class="transaction-id">{{ transaction.transaction_id }}</div>
    <div class="transaction-meta">
      <span class="badge" :class="`badge-${transaction.risk_level}`">
        {{ transaction.risk_level }}
      </span>
      <span class="score">Score: {{ transaction.risk_score }}</span>
      <span v-if="transaction.transaction_type" class="type">
        {{ transaction.transaction_type }}
      </span>
    </div>
    <div v-if="transaction.reason" class="reason">
      {{ transaction.reason }}
    </div>
    <div v-if="hasAnomalies" class="anomalies">
      <span class="anomalies-badge">{{ transaction.anomalies.length }} anomaly{{ transaction.anomalies.length > 1 ? 'ies' : '' }}</span>
    </div>
  </div>
</template>

<script>
export default {
  name: 'TransactionCard',
  props: {
    transaction: {
      type: Object,
      required: true
    }
  },
  emits: ['click'],
  computed: {
    hasAnomalies() {
      return this.transaction.anomalies && this.transaction.anomalies.length > 0;
    }
  },
  methods: {
    handleClick() {
      this.$emit('click', this.transaction.transaction_id);
    }
  }
};
</script>

<style scoped>
.transaction-card {
  padding: 20px 24px;
  border: 1px solid rgba(0, 0, 0, 0.05);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  background: #ffffff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.transaction-card:hover {
  border-color: rgba(0, 122, 255, 0.3);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
  background: #fafafa;
}

.transaction-id {
  font-family: 'SF Mono', 'Monaco', 'Courier New', monospace;
  font-size: 0.8125rem;
  color: #86868b;
  margin-bottom: 12px;
  word-break: break-all;
  letter-spacing: -0.01em;
  font-weight: 500;
}

.transaction-meta {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.badge {
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.badge-low {
  background: rgba(52, 199, 89, 0.15);
  color: #34c759;
}

.badge-medium {
  background: rgba(255, 149, 0, 0.15);
  color: #ff9500;
}

.badge-high {
  background: rgba(255, 59, 48, 0.15);
  color: #ff3b30;
}

.badge-critical {
  background: rgba(142, 0, 0, 0.15);
  color: #8e0000;
}

.score {
  color: #86868b;
  font-size: 0.875rem;
  font-weight: 500;
  letter-spacing: -0.01em;
}

.type {
  color: #007aff;
  font-size: 0.875rem;
  font-weight: 500;
  letter-spacing: -0.01em;
}

.reason {
  color: #86868b;
  font-size: 0.875rem;
  margin-top: 12px;
  line-height: 1.5;
  font-style: italic;
  letter-spacing: -0.01em;
}

.anomalies {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
}

.anomalies-badge {
  display: inline-block;
  padding: 4px 10px;
  background: rgba(255, 149, 0, 0.15);
  color: #ff9500;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}
</style>
