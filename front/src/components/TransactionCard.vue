<template>
  <div
    @click="handleClick"
    class="p-6 bg-zinc-900 border border-zinc-800 rounded-xl cursor-pointer transition-all hover:border-blue-500/50 hover:shadow-xl hover:-translate-y-0.5"
  >
    <div class="font-mono text-xs text-zinc-500 mb-3 break-all font-medium">{{ transaction.transaction_id }}</div>
    <div class="flex gap-3 items-center mb-3 flex-wrap">
      <span
        :class="{
          'bg-green-500/20 text-green-400': transaction.risk_level === 'low',
          'bg-orange-500/20 text-orange-400': transaction.risk_level === 'medium',
          'bg-red-500/20 text-red-400': transaction.risk_level === 'high',
          'bg-red-600/20 text-red-500': transaction.risk_level === 'critical'
        }"
        class="px-3 py-1 rounded-md text-xs font-semibold uppercase tracking-wider"
      >
        {{ transaction.risk_level }}
      </span>
      <span class="text-sm text-zinc-500 font-medium">Score: {{ transaction.risk_score }}</span>
      <span v-if="transaction.transaction_type" class="text-sm text-blue-400 font-medium">
        {{ translatedType }}
      </span>
    </div>
    <div v-if="transaction.reason" class="text-sm text-zinc-400 mt-3 leading-relaxed italic">
      {{ transaction.reason }}
    </div>
    <div v-if="hasAnomalies" class="mt-4 pt-4 border-t border-zinc-800">
      <div class="flex items-center gap-2 mb-3">
        <span class="text-base">⚠️</span>
        <span class="text-sm font-semibold text-orange-400">
          {{ transaction.anomalies.length }} Anomal{{ transaction.anomalies.length > 1 ? 'ies' : 'y' }}
        </span>
      </div>
      <ul class="flex flex-col gap-2 list-none p-0 m-0">
        <li
          v-for="(anomaly, index) in transaction.anomalies"
          :key="index"
          class="p-3 bg-orange-500/10 border-l-4 border-orange-500 rounded-md text-xs text-white leading-relaxed"
        >
          {{ anomaly }}
        </li>
      </ul>
    </div>
  </div>
</template>

<script>
import { translateTransactionType } from '../utils/translations';

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
    translatedType() {
      return translateTransactionType(this.transaction.transaction_type);
    },
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
