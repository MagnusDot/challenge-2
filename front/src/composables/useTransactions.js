import { computed, ref } from 'vue';

export function useTransactions() {
  const transactions = ref([]);
  const loading = ref(true);
  const error = ref(null);
  const transactionTypes = ref({});
  const selectedRiskLevel = ref('');
  const selectedType = ref('');
  const availableFiles = ref([]);
  const selectedFile = ref('all');

  const availableTypes = computed(() => {
    const types = new Set();
    Object.values(transactionTypes.value).forEach(type => {
      if (type) types.add(type);
    });
    return Array.from(types).sort();
  });

  const filteredTransactions = computed(() => {
    let filtered = transactions.value;

    if (selectedRiskLevel.value) {
      filtered = filtered.filter(
        t => t.risk_level === selectedRiskLevel.value
      );
    }

    if (selectedType.value) {
      filtered = filtered.filter(
        t => transactionTypes.value[t.transaction_id] === selectedType.value
      );
    }

    return filtered;
  });

  const loadTransactionTypes = async () => {
    try {
      const response = await fetch('/api/transactions');
      if (response.ok) {
        const data = await response.json();
        const typesMap = {};
        data.forEach(t => {
          if (t.transaction_type) {
            typesMap[t.transaction_id] = t.transaction_type;
          }
        });
        transactionTypes.value = typesMap;
      }
    } catch (err) {
    }
  };

  const loadAvailableFiles = async () => {
    try {
      const response = await fetch('/api/results');
      if (response.ok) {
        const files = await response.json();
        availableFiles.value = files;
        if (files.length > 0 && (!selectedFile.value || selectedFile.value === '')) {
          selectedFile.value = 'all';
        }
      }
    } catch (err) {
    }
  };

  const loadResults = async (fileToLoad = null) => {
    try {
      loading.value = true;
      error.value = null;
      transactions.value = [];

      const fileToUse = fileToLoad || selectedFile.value;

      if (availableFiles.value.length === 0) {
        await loadAvailableFiles();
      }

      if (availableFiles.value.length === 0) {
        transactions.value = [];
        loading.value = false;
        return;
      }

      if (!fileToUse || fileToUse === '') {
        if (availableFiles.value.length > 0) {
          selectedFile.value = 'all';
          return await loadResults('all');
        } else {
          transactions.value = [];
          loading.value = false;
          return;
        }
      }

      let filesToLoad = [];
      if (fileToUse === 'all') {
        filesToLoad = availableFiles.value;
      } else {
        filesToLoad = [fileToUse];
      }

      let allTransactions = [];

      for (const file of filesToLoad) {
        const fileResponse = await fetch(`/api/results/${file}`);
        if (fileResponse.ok) {
          const data = await fileResponse.json();
          if (Array.isArray(data)) {
            allTransactions = allTransactions.concat(data);
          }
        }
      }

      allTransactions = allTransactions.map(t => ({
        ...t,
        transaction_type: transactionTypes.value[t.transaction_id] || null
      }));

      transactions.value = allTransactions;
    } catch (err) {
      error.value = err.message || 'Error loading data';
    } finally {
      loading.value = false;
    }
  };

  const copyId = (id) => {
    navigator.clipboard.writeText(id);
  };

  const copyAllIds = () => {
    const ids = filteredTransactions.value
      .map(t => t.transaction_id)
      .join('\n');
    navigator.clipboard.writeText(ids).then(() => {
      alert(`${filteredTransactions.value.length} IDs copied to clipboard!`);
    });
  };

  return {
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
  };
}
