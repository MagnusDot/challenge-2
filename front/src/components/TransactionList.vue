<template>
  <div class="transaction-list-container">
    <div class="list-header">
      <h2>Filtered Transaction IDs</h2>
      <button @click="handleCopyAll" class="copy-button">
        Copy All IDs
      </button>
    </div>

    <div v-if="transactions.length === 0" class="no-results">
      No transactions match the selected filters.
    </div>
    <div v-else class="transaction-list">
      <TransactionCard
        v-for="transaction in transactions"
        :key="transaction.transaction_id"
        :transaction="transaction"
        @click="handleTransactionClick"
      />
    </div>
  </div>
</template>

<script>
import TransactionCard from './TransactionCard.vue';

export default {
  name: 'TransactionList',
  components: {
    TransactionCard
  },
  props: {
    transactions: {
      type: Array,
      required: true
    }
  },
  emits: ['copy-all', 'transaction-click'],
  methods: {
    handleCopyAll() {
      this.$emit('copy-all');
    },
    handleTransactionClick(id) {
      this.$emit('transaction-click', id);
    }
  }
};
</script>

<style scoped>
.transaction-list-container {
  padding: 32px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.list-header h2 {
  color: #1d1d1f;
  font-size: 1.5rem;
  font-weight: 600;
  letter-spacing: -0.02em;
}

.copy-button {
  padding: 10px 20px;
  background: #007aff;
  color: #ffffff;
  border: none;
  border-radius: 10px;
  font-size: 0.9375rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  letter-spacing: -0.01em;
  font-family: inherit;
}

.copy-button:hover {
  background: #0051d5;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 122, 255, 0.3);
}

.copy-button:active {
  transform: translateY(0);
}

.no-results {
  text-align: center;
  padding: 60px 20px;
  color: #86868b;
  font-size: 1rem;
  letter-spacing: -0.01em;
}

.transaction-list {
  display: grid;
  gap: 12px;
}
</style>
