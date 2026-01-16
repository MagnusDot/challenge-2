<template>
  <div class="p-8 animate-fade-in">
    <div class="flex justify-between items-center mb-6 animate-fade-in-up">
      <h2 class="text-2xl text-white font-semibold bg-gradient-to-r from-white to-blue-200 bg-clip-text text-transparent">Filtered Transaction IDs</h2>
      <button
        @click="handleCopyAll"
        class="px-5 py-2.5 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg text-sm font-medium cursor-pointer transition-all duration-300 hover:from-blue-600 hover:to-purple-700 hover:-translate-y-1 hover:shadow-2xl hover:shadow-blue-500/50 active:translate-y-0 transform hover:scale-105"
      >
        Copy All IDs
      </button>
    </div>

    <div v-if="transactions.length === 0" class="text-center py-16 text-zinc-500 text-base animate-fade-in">
      No transactions match the selected filters.
    </div>
    <div v-else class="grid gap-3">
      <TransactionCard
        v-for="(transaction, index) in transactions"
        :key="transaction.transaction_id"
        :transaction="transaction"
        :index="index"
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
