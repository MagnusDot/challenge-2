<template>
  <div class="p-8">
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-2xl text-white font-semibold">Filtered Transaction IDs</h2>
      <button
        @click="handleCopyAll"
        class="px-5 py-2.5 bg-blue-500 text-white rounded-lg text-sm font-medium cursor-pointer transition-all hover:bg-blue-600 hover:-translate-y-0.5 hover:shadow-lg active:translate-y-0"
      >
        Copy All IDs
      </button>
    </div>

    <div v-if="transactions.length === 0" class="text-center py-16 text-zinc-500 text-base">
      No transactions match the selected filters.
    </div>
    <div v-else class="grid gap-3">
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
