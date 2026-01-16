<template>
  <div class="p-8 bg-zinc-900 border-b border-zinc-800 animate-fade-in">
    <h3 class="text-2xl text-white mb-6 font-semibold bg-gradient-to-r from-white via-blue-200 to-purple-200 bg-clip-text text-transparent animate-gradient">Statistics</h3>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
      <StatsCard
        v-for="(stat, index) in stats"
        :key="index"
        :label="stat.label"
        :value="stat.value"
        :subtitle="stat.subtitle"
        :index="index"
      />
    </div>

    <div class="mt-8 pt-8 border-t border-zinc-800 animate-fade-in-up delay-300">
      <h4 class="text-lg text-white mb-5 font-semibold bg-gradient-to-r from-white to-blue-200 bg-clip-text text-transparent">Risk Level Distribution</h4>
      <div class="flex flex-col gap-4">
        <div
          v-for="(count, level, index) in riskLevelStats"
          :key="level"
          class="flex items-center gap-4 animate-slide-in-right"
          :style="{ animationDelay: `${index * 0.1}s` }"
        >
          <div class="min-w-[90px] font-medium capitalize text-sm text-zinc-400">{{ level }}</div>
          <div class="flex-1 h-2 bg-zinc-800 rounded-full overflow-hidden relative group">
            <div
              :class="{
                'bg-green-500 group-hover:bg-green-400': level === 'low',
                'bg-orange-500 group-hover:bg-orange-400': level === 'medium',
                'bg-red-500 group-hover:bg-red-400': level === 'high',
                'bg-red-600 group-hover:bg-red-500': level === 'critical'
              }"
              class="h-full rounded-full transition-all duration-1000 ease-out group-hover:shadow-lg"
              :style="{ width: `${(count / totalCount) * 100}%` }"
            ></div>
          </div>
          <div class="min-w-[100px] text-right text-sm text-zinc-500 font-medium group-hover:text-white transition-colors duration-300">
            {{ count }} ({{ filteredRiskLevelStats[level] }})
          </div>
        </div>
      </div>
    </div>

    <div v-if="Object.keys(typeStats).length > 0" class="mt-8 pt-8 border-t border-zinc-800 animate-fade-in-up delay-400">
      <h4 class="text-lg text-white mb-5 font-semibold bg-gradient-to-r from-white to-purple-200 bg-clip-text text-transparent">Transaction Type Distribution</h4>
      <div class="flex flex-col gap-2">
        <div
          v-for="(count, type, index) in typeStats"
          :key="type"
          class="flex justify-between items-center px-4 py-3 bg-zinc-800 rounded-lg border border-zinc-700 hover:bg-zinc-700 hover:border-blue-500/50 transition-all duration-300 hover:shadow-lg hover:shadow-blue-500/20 hover:-translate-x-1 animate-slide-in-right"
          :style="{ animationDelay: `${index * 0.05}s` }"
        >
          <span class="font-medium text-sm text-white group-hover:text-blue-400 transition-colors duration-300">{{ translateTransactionType(type) }}</span>
          <span class="text-sm text-blue-400 font-semibold group-hover:text-blue-300 transition-colors duration-300">
            {{ count }} ({{ filteredTypeStats[type] || 0 }})
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { translateTransactionType } from '../utils/translations';
import StatsCard from './StatsCard.vue';

export default {
  name: 'StatisticsPanel',
  components: {
    StatsCard
  },
  props: {
    totalCount: {
      type: Number,
      required: true
    },
    filteredCount: {
      type: Number,
      required: true
    },
    riskLevelStats: {
      type: Object,
      required: true
    },
    filteredRiskLevelStats: {
      type: Object,
      required: true
    },
    typeStats: {
      type: Object,
      required: true
    },
    filteredTypeStats: {
      type: Object,
      required: true
    },
    averageRiskScore: {
      type: Number,
      required: true
    },
    filteredAverageRiskScore: {
      type: Number,
      required: true
    },
    minRiskScore: {
      type: Number,
      required: true
    },
    maxRiskScore: {
      type: Number,
      required: true
    },
    filteredMinRiskScore: {
      type: Number,
      required: true
    },
    filteredMaxRiskScore: {
      type: Number,
      required: true
    },
    transactionsWithAnomalies: {
      type: Number,
      required: true
    },
    filteredTransactionsWithAnomalies: {
      type: Number,
      required: true
    },
    totalTokenUsage: {
      type: Number,
      required: true
    },
    filteredTokenUsage: {
      type: Number,
      required: true
    }
  },
  computed: {
    stats() {
      return [
        {
          label: 'Total Transactions',
          value: this.totalCount,
          subtitle: `${this.filteredCount} filtered`
        },
        {
          label: 'Average Score',
          value: this.averageRiskScore,
          subtitle: `Filtered: ${this.filteredAverageRiskScore}`
        },
        {
          label: 'Min Score',
          value: this.minRiskScore,
          subtitle: `Filtered: ${this.filteredMinRiskScore}`
        },
        {
          label: 'Max Score',
          value: this.maxRiskScore,
          subtitle: `Filtered: ${this.filteredMaxRiskScore}`
        },
        {
          label: 'With Anomalies',
          value: this.transactionsWithAnomalies,
          subtitle: `Filtered: ${this.filteredTransactionsWithAnomalies}`
        },
        {
          label: 'Tokens Used',
          value: this.formatNumber(this.totalTokenUsage),
          subtitle: `Filtered: ${this.formatNumber(this.filteredTokenUsage)}`
        }
      ];
    }
  },
  methods: {
    formatNumber(num) {
      return new Intl.NumberFormat('en-US').format(num);
    },
    translateTransactionType
  }
};
</script>
