<template>
  <div class="p-8 bg-zinc-900 border-b border-zinc-800">
    <h3 class="text-2xl text-white mb-6 font-semibold">Statistics</h3>
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
      <StatsCard
        label="Total Transactions"
        :value="totalCount"
        :subtitle="`${filteredCount} filtered`"
      />
      <StatsCard
        label="Average Score"
        :value="averageRiskScore"
        :subtitle="`Filtered: ${filteredAverageRiskScore}`"
      />
      <StatsCard
        label="Min Score"
        :value="minRiskScore"
        :subtitle="`Filtered: ${filteredMinRiskScore}`"
      />
      <StatsCard
        label="Max Score"
        :value="maxRiskScore"
        :subtitle="`Filtered: ${filteredMaxRiskScore}`"
      />
      <StatsCard
        label="With Anomalies"
        :value="transactionsWithAnomalies"
        :subtitle="`Filtered: ${filteredTransactionsWithAnomalies}`"
      />
      <StatsCard
        label="Tokens Used"
        :value="formatNumber(totalTokenUsage)"
        :subtitle="`Filtered: ${formatNumber(filteredTokenUsage)}`"
      />
    </div>

    <div class="mt-8 pt-8 border-t border-zinc-800">
      <h4 class="text-lg text-white mb-5 font-semibold">Risk Level Distribution</h4>
      <div class="flex flex-col gap-4">
        <div
          v-for="(count, level) in riskLevelStats"
          :key="level"
          class="flex items-center gap-4"
        >
          <div class="min-w-[90px] font-medium capitalize text-sm text-zinc-400">{{ level }}</div>
          <div class="flex-1 h-2 bg-zinc-800 rounded-full overflow-hidden">
            <div
              :class="{
                'bg-green-500': level === 'low',
                'bg-orange-500': level === 'medium',
                'bg-red-500': level === 'high',
                'bg-red-600': level === 'critical'
              }"
              class="h-full rounded-full transition-all duration-500"
              :style="{ width: `${(count / totalCount) * 100}%` }"
            ></div>
          </div>
          <div class="min-w-[100px] text-right text-sm text-zinc-500 font-medium">
            {{ count }} ({{ filteredRiskLevelStats[level] }})
          </div>
        </div>
      </div>
    </div>

    <div v-if="Object.keys(typeStats).length > 0" class="mt-8 pt-8 border-t border-zinc-800">
      <h4 class="text-lg text-white mb-5 font-semibold">Transaction Type Distribution</h4>
      <div class="flex flex-col gap-2">
        <div
          v-for="(count, type) in typeStats"
          :key="type"
          class="flex justify-between items-center px-4 py-3 bg-zinc-800 rounded-lg border border-zinc-700 hover:bg-zinc-700 hover:border-zinc-600 transition-all"
        >
          <span class="font-medium text-sm text-white">{{ translateTransactionType(type) }}</span>
          <span class="text-sm text-blue-400 font-semibold">
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
  methods: {
    formatNumber(num) {
      return new Intl.NumberFormat('en-US').format(num);
    },
    translateTransactionType
  }
};
</script>
