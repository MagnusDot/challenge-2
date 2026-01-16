<template>
  <div class="charts-panel">
    <h3 class="charts-title">Visualizations</h3>
    <div class="charts-grid">
      <div class="chart-card">
        <h4 class="chart-title">Risk Level Distribution</h4>
        <RiskLevelPieChart
          :risk-level-stats="riskLevelStats"
          :total-count="totalCount"
        />
      </div>
      <div class="chart-card">
        <h4 class="chart-title">Risk Score Distribution</h4>
        <RiskScoreDistribution :transactions="transactions" />
      </div>
      <div v-if="Object.keys(typeStats).length > 0" class="chart-card chart-card-full">
        <h4 class="chart-title">Transaction Types</h4>
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

<style scoped>
.charts-panel {
  background: #ffffff;
  border-radius: 0;
  padding: 32px;
  margin: 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.charts-title {
  font-size: 1.5rem;
  color: #1d1d1f;
  margin-bottom: 24px;
  font-weight: 600;
  letter-spacing: -0.02em;
}

.charts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 24px;
}

.chart-card {
  background: #fafafa;
  border-radius: 12px;
  padding: 24px;
  border: 1px solid rgba(0, 0, 0, 0.05);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.chart-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.chart-card-full {
  grid-column: 1 / -1;
}

.chart-title {
  font-size: 1.125rem;
  color: #1d1d1f;
  margin-bottom: 20px;
  font-weight: 600;
  letter-spacing: -0.01em;
}

@media (max-width: 768px) {
  .charts-grid {
    grid-template-columns: 1fr;
  }
  
  .chart-card-full {
    grid-column: 1;
  }
}
</style>
