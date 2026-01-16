<template>
  <div class="min-h-screen bg-black">
    <AppHeader :total-count="totalCount" :filtered-count="filteredCount" />

    <div class="max-w-7xl mx-auto px-6 py-8">
      <div class="bg-zinc-900 rounded-2xl border border-zinc-800 shadow-2xl mb-8 animate-fade-in-up delay-100">
        <div class="p-6 border-b border-zinc-800 bg-gradient-to-r from-zinc-900 to-zinc-800 animate-fade-in">
          <div class="flex flex-wrap gap-5 items-end">
            <FilterGroup
              id="result-file"
              label="Result File"
              v-model="selectedFile"
              :options="fileOptions"
              :placeholder="''"
              :index="0"
              @update:modelValue="handleFileChange"
            />
            <FilterGroup
              id="risk-level"
              label="Risk Level"
              v-model="selectedRiskLevel"
              :options="riskLevelOptions"
              :index="1"
            />
            <FilterGroup
              id="transaction-type"
              label="Transaction Type"
              v-model="selectedType"
              :options="typeOptions"
              :index="2"
            />
          </div>
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
    </div>
  </div>
</template>

<script>
import { computed, onMounted } from 'vue';
import AppHeader from './components/AppHeader.vue';
import ChartsPanel from './components/ChartsPanel.vue';
import ErrorMessage from './components/ErrorMessage.vue';
import FilterGroup from './components/FilterGroup.vue';
import LoadingSpinner from './components/LoadingSpinner.vue';
import StatisticsPanel from './components/StatisticsPanel.vue';
import TransactionList from './components/TransactionList.vue';
import { useStatistics } from './composables/useStatistics';
import { useTransactions } from './composables/useTransactions';
import { translateTransactionType } from './utils/translations';

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
        label: translateTransactionType(type) || '(empty)'
      }));
    });

    const fileOptions = computed(() => {
      const options = [{ value: 'all', label: 'All Files' }];
      availableFiles.value.forEach(file => {
        options.push({ value: file, label: file });
      });
      return options;
    });

    const handleFileChange = async (newValue) => {
      if (newValue) {
        selectedFile.value = newValue;
        await loadResults(newValue);
      }
    };

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
      handleFileChange,
      ...statistics
    };
  }
};
</script>
