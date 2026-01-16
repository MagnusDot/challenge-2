<template>
  <div class="app-container">
    <AppHeader />

    <div class="filters-section">
      <FilterGroup
        id="result-file"
        label="Result File"
        v-model="selectedFile"
        :options="fileOptions"
        :placeholder="''"
      />
      <FilterGroup
        id="risk-level"
        label="Risk Level"
        v-model="selectedRiskLevel"
        :options="riskLevelOptions"
      />
      <FilterGroup
        id="transaction-type"
        label="Transaction Type"
        v-model="selectedType"
        :options="typeOptions"
      />
    </div>

    <StatisticsPanel
      :total-count="totalCount"
      :filtered-count="filteredCount"
      :risk-level-stats="riskLevelStats"
      :filtered-risk-level-stats="filteredRiskLevelStats"
      :type-stats="typeStats"
      :filtered-type-stats="filteredTypeStats"
      :average-risk-score="averageRiskScore"
      :filtered-average-risk-score="filteredAverageRiskScore"
      :min-risk-score="minRiskScore"
      :max-risk-score="maxRiskScore"
      :filtered-min-risk-score="filteredMinRiskScore"
      :filtered-max-risk-score="filteredMaxRiskScore"
      :transactions-with-anomalies="transactionsWithAnomalies"
      :filtered-transactions-with-anomalies="filteredTransactionsWithAnomalies"
      :total-token-usage="totalTokenUsage"
      :filtered-token-usage="filteredTokenUsage"
    />

    <ChartsPanel
      v-if="!loading && !error"
      :transactions="transactions"
      :risk-level-stats="riskLevelStats"
      :type-stats="typeStats"
      :total-count="totalCount"
    />

    <div v-if="loading">
      <LoadingSpinner />
    </div>
    <div v-else-if="error">
      <ErrorMessage :message="error" />
    </div>
    <TransactionList
      v-else
      :transactions="filteredTransactions"
      @copy-all="copyAllIds"
      @transaction-click="copyId"
    />
  </div>
</template>

<script>
import { computed, onMounted, watch } from 'vue';
import AppHeader from './components/AppHeader.vue';
import ChartsPanel from './components/ChartsPanel.vue';
import ErrorMessage from './components/ErrorMessage.vue';
import FilterGroup from './components/FilterGroup.vue';
import LoadingSpinner from './components/LoadingSpinner.vue';
import StatisticsPanel from './components/StatisticsPanel.vue';
import TransactionList from './components/TransactionList.vue';
import { useStatistics } from './composables/useStatistics';
import { useTransactions } from './composables/useTransactions';

export default {
  name: 'App',
  components: {
    AppHeader,
    FilterGroup,
    StatisticsPanel,
    TransactionList,
    ChartsPanel,
    LoadingSpinner,
    ErrorMessage
  },
  setup() {
    const {
      transactions,
      loading,
      error,
      selectedRiskLevel,
      selectedType,
      selectedFile,
      availableFiles,
      availableTypes,
      filteredTransactions,
      loadTransactionTypes,
      loadResults,
      loadAvailableFiles,
      copyId,
      copyAllIds
    } = useTransactions();

    const statistics = useStatistics(transactions, filteredTransactions);

    const riskLevelOptions = computed(() => [
      { value: 'low', label: 'Low' },
      { value: 'medium', label: 'Medium' },
      { value: 'high', label: 'High' },
      { value: 'critical', label: 'Critical' }
    ]);

    const typeOptions = computed(() => {
      return availableTypes.value.map(type => ({
        value: type,
        label: type || '(empty)'
      }));
    });

    const fileOptions = computed(() => {
      const options = [{ value: 'all', label: 'All Files' }];
      availableFiles.value.forEach(file => {
        options.push({ value: file, label: file });
      });
      return options;
    });

    watch(selectedFile, async () => {
      if (selectedFile.value) {
        await loadResults();
      }
    });

    onMounted(async () => {
      await loadTransactionTypes();
      await loadAvailableFiles();
      await loadResults();
    });

    return {
      transactions,
      loading,
      error,
      selectedRiskLevel,
      selectedType,
      filteredTransactions,
      copyId,
      copyAllIds,
      riskLevelOptions,
      typeOptions,
      fileOptions,
      ...statistics
    };
  }
};
</script>

<style scoped>
.app-container {
  background: #ffffff;
  border-radius: 18px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  overflow: hidden;
  margin-bottom: 40px;
}

.filters-section {
  padding: 24px 32px;
  background: #fafafa;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
  align-items: flex-end;
}
</style>
