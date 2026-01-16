<template>
  <div class="statistics-panel">
    <h3 class="statistics-title">Statistics</h3>
    <div class="statistics-grid">
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

    <div class="risk-level-breakdown">
      <h4 class="breakdown-title">Risk Level Distribution</h4>
      <div class="breakdown-grid">
        <div
          v-for="(count, level) in riskLevelStats"
          :key="level"
          class="breakdown-item"
        >
          <div class="breakdown-label">{{ level }}</div>
          <div class="breakdown-bar-container">
            <div
              class="breakdown-bar"
              :class="`breakdown-bar-${level}`"
              :style="{ width: `${(count / totalCount) * 100}%` }"
            ></div>
          </div>
          <div class="breakdown-value">
            {{ count }} ({{ filteredRiskLevelStats[level] }})
          </div>
        </div>
      </div>
    </div>

    <div v-if="Object.keys(typeStats).length > 0" class="type-breakdown">
      <h4 class="breakdown-title">Transaction Type Distribution</h4>
      <div class="type-list">
        <div
          v-for="(count, type) in typeStats"
          :key="type"
          class="type-item"
        >
          <span class="type-name">{{ translateTransactionType(type) }}</span>
          <span class="type-count">
            {{ count }} ({{ filteredTypeStats[type] || 0 }})
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import StatsCard from './StatsCard.vue';
import { translateTransactionType } from '../utils/translations';

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

<style scoped>
.statistics-panel {
  background: #fafafa;
  border-radius: 0;
  padding: 32px;
  margin: 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.statistics-title {
  font-size: 1.5rem;
  color: #1d1d1f;
  margin-bottom: 24px;
  font-weight: 600;
  letter-spacing: -0.02em;
}

.statistics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 32px;
}

.risk-level-breakdown,
.type-breakdown {
  margin-top: 32px;
  padding-top: 32px;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
}

.breakdown-title {
  font-size: 1.125rem;
  color: #1d1d1f;
  margin-bottom: 20px;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.breakdown-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.breakdown-item {
  display: flex;
  align-items: center;
  gap: 16px;
}

.breakdown-label {
  min-width: 90px;
  font-weight: 500;
  text-transform: capitalize;
  color: #1d1d1f;
  font-size: 0.875rem;
  letter-spacing: -0.01em;
}

.breakdown-bar-container {
  flex: 1;
  height: 8px;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 4px;
  overflow: hidden;
  position: relative;
}

.breakdown-bar {
  height: 100%;
  border-radius: 4px;
  transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.breakdown-bar-low {
  background: #34c759;
}

.breakdown-bar-medium {
  background: #ff9500;
}

.breakdown-bar-high {
  background: #ff3b30;
}

.breakdown-bar-critical {
  background: #8e0000;
}

.breakdown-value {
  min-width: 100px;
  text-align: right;
  font-size: 0.875rem;
  color: #86868b;
  font-weight: 500;
  letter-spacing: -0.01em;
}

.type-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.type-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #ffffff;
  border-radius: 10px;
  border: 1px solid rgba(0, 0, 0, 0.05);
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.type-item:hover {
  background: #f5f5f7;
  border-color: rgba(0, 0, 0, 0.1);
}

.type-name {
  font-weight: 500;
  color: #1d1d1f;
  font-size: 0.875rem;
  letter-spacing: -0.01em;
}

.type-count {
  font-size: 0.875rem;
  color: #007aff;
  font-weight: 600;
  letter-spacing: -0.01em;
}
</style>
