import { computed } from 'vue';

export function useStatistics(transactions, filteredTransactions) {
  const totalCount = computed(() => transactions.value.length);
  const filteredCount = computed(() => filteredTransactions.value.length);

  const riskLevelStats = computed(() => {
    const stats = {
      low: 0,
      medium: 0,
      high: 0,
      critical: 0
    };
    transactions.value.forEach(t => {
      if (stats[t.risk_level] !== undefined) {
        stats[t.risk_level]++;
      }
    });
    return stats;
  });

  const filteredRiskLevelStats = computed(() => {
    const stats = {
      low: 0,
      medium: 0,
      high: 0,
      critical: 0
    };
    filteredTransactions.value.forEach(t => {
      if (stats[t.risk_level] !== undefined) {
        stats[t.risk_level]++;
      }
    });
    return stats;
  });

  const typeStats = computed(() => {
    const stats = {};
    transactions.value.forEach(t => {
      const type = t.transaction_type || 'Not specified';
      stats[type] = (stats[type] || 0) + 1;
    });
    return stats;
  });

  const filteredTypeStats = computed(() => {
    const stats = {};
    filteredTransactions.value.forEach(t => {
      const type = t.transaction_type || 'Not specified';
      stats[type] = (stats[type] || 0) + 1;
    });
    return stats;
  });

  const averageRiskScore = computed(() => {
    if (transactions.value.length === 0) return 0;
    const sum = transactions.value.reduce((acc, t) => acc + (t.risk_score || 0), 0);
    return Math.round((sum / transactions.value.length) * 10) / 10;
  });

  const filteredAverageRiskScore = computed(() => {
    if (filteredTransactions.value.length === 0) return 0;
    const sum = filteredTransactions.value.reduce((acc, t) => acc + (t.risk_score || 0), 0);
    return Math.round((sum / filteredTransactions.value.length) * 10) / 10;
  });

  const minRiskScore = computed(() => {
    if (transactions.value.length === 0) return 0;
    return Math.min(...transactions.value.map(t => t.risk_score || 0));
  });

  const maxRiskScore = computed(() => {
    if (transactions.value.length === 0) return 0;
    return Math.max(...transactions.value.map(t => t.risk_score || 0));
  });

  const filteredMinRiskScore = computed(() => {
    if (filteredTransactions.value.length === 0) return 0;
    return Math.min(...filteredTransactions.value.map(t => t.risk_score || 0));
  });

  const filteredMaxRiskScore = computed(() => {
    if (filteredTransactions.value.length === 0) return 0;
    return Math.max(...filteredTransactions.value.map(t => t.risk_score || 0));
  });

  const transactionsWithAnomalies = computed(() => {
    return transactions.value.filter(t => 
      t.anomalies && t.anomalies.length > 0
    ).length;
  });

  const filteredTransactionsWithAnomalies = computed(() => {
    return filteredTransactions.value.filter(t => 
      t.anomalies && t.anomalies.length > 0
    ).length;
  });

  const totalTokenUsage = computed(() => {
    return transactions.value.reduce((acc, t) => {
      if (t.token_usage && t.token_usage.total_tokens) {
        return acc + t.token_usage.total_tokens;
      }
      return acc;
    }, 0);
  });

  const filteredTokenUsage = computed(() => {
    return filteredTransactions.value.reduce((acc, t) => {
      if (t.token_usage && t.token_usage.total_tokens) {
        return acc + t.token_usage.total_tokens;
      }
      return acc;
    }, 0);
  });

  return {
    totalCount,
    filteredCount,
    riskLevelStats,
    filteredRiskLevelStats,
    typeStats,
    filteredTypeStats,
    averageRiskScore,
    filteredAverageRiskScore,
    minRiskScore,
    maxRiskScore,
    filteredMinRiskScore,
    filteredMaxRiskScore,
    transactionsWithAnomalies,
    filteredTransactionsWithAnomalies,
    totalTokenUsage,
    filteredTokenUsage
  };
}
