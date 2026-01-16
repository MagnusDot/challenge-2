<template>
  <div
    @click="handleClick"
    class="p-6 bg-zinc-900 border border-zinc-800 rounded-xl cursor-pointer transition-all duration-300 hover:border-blue-500/50 hover:shadow-2xl hover:shadow-blue-500/20 hover:-translate-y-1 group relative overflow-hidden animate-fade-in-up"
    :style="{ animationDelay: `${index * 0.05}s` }"
  >
    <div class="absolute inset-0 bg-gradient-to-r from-blue-600/0 via-blue-600/5 to-purple-600/0 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
    <div class="relative z-10">
      <div class="font-mono text-xs text-zinc-500 mb-3 break-all font-medium group-hover:text-blue-400 transition-colors duration-300">{{ transaction.transaction_id }}</div>
      <div class="flex gap-3 items-center mb-3 flex-wrap">
        <span
          :class="{
            'bg-green-500/20 text-green-400 group-hover:bg-green-500/30 group-hover:shadow-lg group-hover:shadow-green-500/20': transaction.risk_level === 'low',
            'bg-orange-500/20 text-orange-400 group-hover:bg-orange-500/30 group-hover:shadow-lg group-hover:shadow-orange-500/20': transaction.risk_level === 'medium',
            'bg-red-500/20 text-red-400 group-hover:bg-red-500/30 group-hover:shadow-lg group-hover:shadow-red-500/20': transaction.risk_level === 'high',
            'bg-red-600/20 text-red-500 group-hover:bg-red-600/30 group-hover:shadow-lg group-hover:shadow-red-600/20': transaction.risk_level === 'critical'
          }"
          class="px-3 py-1 rounded-md text-xs font-semibold uppercase tracking-wider transition-all duration-300 transform group-hover:scale-105"
        >
          {{ transaction.risk_level }}
        </span>
        <span class="text-sm text-zinc-500 font-medium group-hover:text-white transition-colors duration-300">Score: {{ transaction.risk_score }}</span>
        <span v-if="transaction.transaction_type" class="text-sm text-blue-400 font-medium group-hover:text-blue-300 transition-colors duration-300">
          {{ translatedType }}
        </span>
      </div>
      <div v-if="transaction.reason" class="text-sm text-zinc-400 mt-3 leading-relaxed italic group-hover:text-zinc-300 transition-colors duration-300">
        {{ transaction.reason }}
      </div>
      <div v-if="hasAnomalies" class="mt-4 pt-4 border-t border-zinc-800 group-hover:border-zinc-700 transition-colors duration-300">
        <div class="flex items-center gap-2 mb-3">
          <span class="text-base animate-float">⚠️</span>
          <span class="text-sm font-semibold text-orange-400 group-hover:text-orange-300 transition-colors duration-300">
            {{ transaction.anomalies.length }} Anomal{{ transaction.anomalies.length > 1 ? 'ies' : 'y' }}
          </span>
        </div>
        <ul class="flex flex-col gap-2 list-none p-0 m-0">
          <li
            v-for="(anomaly, index) in transaction.anomalies"
            :key="index"
            class="p-3 bg-orange-500/10 border-l-4 border-orange-500 rounded-md text-xs text-white leading-relaxed hover:bg-orange-500/20 hover:border-orange-400 transition-all duration-300 animate-slide-in-right"
            :style="{ animationDelay: `${index * 0.1}s` }"
          >
            {{ anomaly }}
          </li>
        </ul>
      </div>
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
    },
    index: {
      type: Number,
      default: 0
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
