<template>
  <div class="p-8 bg-zinc-900 border-b border-zinc-800">
    <h3 class="text-2xl text-white mb-6 font-semibold">Visualizations</h3>
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div class="bg-zinc-800 rounded-xl p-6 border border-zinc-700 transition-all hover:border-zinc-600 hover:shadow-xl hover:-translate-y-0.5">
        <h4 class="text-lg text-white mb-5 font-semibold">Risk Level Distribution</h4>
        <RiskLevelPieChart
          :risk-level-stats="riskLevelStats"
          :total-count="totalCount"
        />
      </div>
      <div class="bg-zinc-800 rounded-xl p-6 border border-zinc-700 transition-all hover:border-zinc-600 hover:shadow-xl hover:-translate-y-0.5">
        <h4 class="text-lg text-white mb-5 font-semibold">Risk Score Distribution</h4>
        <RiskScoreDistribution :transactions="transactions" />
      </div>
      <div
        v-if="Object.keys(typeStats).length > 0"
        class="bg-zinc-800 rounded-xl p-6 border border-zinc-700 transition-all hover:border-zinc-600 hover:shadow-xl hover:-translate-y-0.5 lg:col-span-2"
      >
        <h4 class="text-lg text-white mb-5 font-semibold">Transaction Types</h4>
        <TransactionTypeChart :type-stats="typeStats" />
      </div>
    </div>
  </div>
</template>

<script>
import RiskLevelPieChart from './charts/RiskLevelPieChart.vue';
import RiskScoreDistribution from './charts/RiskScoreDistribution.vue';
import TransactionTypeChart from './charts/TransactionTypeChart.vue';

export default {
  name: 'ChartsPanel',
  components: {
    RiskLevelPieChart,
    RiskScoreDistribution,
    TransactionTypeChart
  },
  props: {
    transactions: {
      type: Array,
      required: true
    },
    riskLevelStats: {
      type: Object,
      required: true
    },
    typeStats: {
      type: Object,
      required: true
    },
    totalCount: {
      type: Number,
      required: true
    }
  }
};
</script>
