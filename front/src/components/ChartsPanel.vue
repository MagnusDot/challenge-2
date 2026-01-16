<template>
  <div class="p-8 bg-zinc-900 border-b border-zinc-800 animate-fade-in">
    <h3 class="text-2xl text-white mb-6 font-semibold bg-gradient-to-r from-white to-blue-200 bg-clip-text text-transparent">Visualizations</h3>
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div class="bg-zinc-800 rounded-xl p-6 border border-zinc-700 transition-all duration-500 hover:border-blue-500/50 hover:shadow-2xl hover:shadow-blue-500/20 hover:-translate-y-1 group animate-fade-in-up delay-100">
        <h4 class="text-lg text-white mb-5 font-semibold group-hover:text-blue-400 transition-colors duration-300">Risk Level Distribution</h4>
        <div class="transform group-hover:scale-105 transition-transform duration-300">
          <RiskLevelPieChart
            :risk-level-stats="riskLevelStats"
            :total-count="totalCount"
          />
        </div>
      </div>
      <div class="bg-zinc-800 rounded-xl p-6 border border-zinc-700 transition-all duration-500 hover:border-purple-500/50 hover:shadow-2xl hover:shadow-purple-500/20 hover:-translate-y-1 group animate-fade-in-up delay-200">
        <h4 class="text-lg text-white mb-5 font-semibold group-hover:text-purple-400 transition-colors duration-300">Risk Score Distribution</h4>
        <div class="transform group-hover:scale-105 transition-transform duration-300">
          <RiskScoreDistribution :transactions="transactions" />
        </div>
      </div>
      <div
        v-if="Object.keys(typeStats).length > 0"
        class="bg-zinc-800 rounded-xl p-6 border border-zinc-700 transition-all duration-500 hover:border-blue-500/50 hover:shadow-2xl hover:shadow-blue-500/20 hover:-translate-y-1 group animate-fade-in-up delay-300 lg:col-span-2"
      >
        <h4 class="text-lg text-white mb-5 font-semibold group-hover:text-blue-400 transition-colors duration-300">Transaction Types</h4>
        <div class="transform group-hover:scale-[1.02] transition-transform duration-300">
          <TransactionTypeChart :type-stats="typeStats" />
        </div>
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
