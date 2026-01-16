<template>
  <div class="chart-container">
    <canvas ref="chartCanvas"></canvas>
  </div>
</template>

<script>
import {
    BarController,
    BarElement,
    CategoryScale,
    Chart as ChartJS,
    Legend,
    LinearScale,
    Tooltip
} from 'chart.js';
import { computed, onMounted, ref, watch } from 'vue';

ChartJS.register(CategoryScale, LinearScale, BarElement, BarController, Tooltip, Legend);

export default {
  name: 'RiskScoreDistribution',
  props: {
    transactions: {
      type: Array,
      required: true
    }
  },
  setup(props) {
    const chartCanvas = ref(null);
    let chartInstance = null;

    const scoreRanges = computed(() => {
      const ranges = [
        { label: '0-10', min: 0, max: 10, count: 0 },
        { label: '11-20', min: 11, max: 20, count: 0 },
        { label: '21-30', min: 21, max: 30, count: 0 },
        { label: '31-40', min: 31, max: 40, count: 0 },
        { label: '41-50', min: 41, max: 50, count: 0 },
        { label: '51-60', min: 51, max: 60, count: 0 },
        { label: '61-70', min: 61, max: 70, count: 0 },
        { label: '71-80', min: 71, max: 80, count: 0 },
        { label: '81-90', min: 81, max: 90, count: 0 },
        { label: '91-100', min: 91, max: 100, count: 0 }
      ];

      props.transactions.forEach(t => {
        const score = t.risk_score || 0;
        const range = ranges.find(r => score >= r.min && score <= r.max);
        if (range) range.count++;
      });

      return ranges;
    });

    const createChart = () => {
      if (chartInstance) {
        chartInstance.destroy();
      }

      if (!chartCanvas.value || props.transactions.length === 0) return;

      const labels = scoreRanges.value.map(r => r.label);
      const data = scoreRanges.value.map(r => r.count);

      chartInstance = new ChartJS(chartCanvas.value, {
        type: 'bar',
        data: {
          labels,
          datasets: [{
            label: 'Transactions',
            data,
            backgroundColor: (ctx) => {
              const value = ctx.parsed.y;
              if (value === 0) return 'rgba(0, 0, 0, 0.05)';
              const index = ctx.dataIndex;
              if (index <= 2) return 'rgba(52, 199, 89, 0.7)';
              if (index <= 5) return 'rgba(255, 149, 0, 0.7)';
              if (index <= 7) return 'rgba(255, 59, 48, 0.7)';
              return 'rgba(142, 0, 0, 0.7)';
            },
            borderColor: (ctx) => {
              const value = ctx.parsed.y;
              if (value === 0) return 'rgba(0, 0, 0, 0.1)';
              const index = ctx.dataIndex;
              if (index <= 2) return '#34c759';
              if (index <= 5) return '#ff9500';
              if (index <= 7) return '#ff3b30';
              return '#8e0000';
            },
            borderWidth: 1,
            borderRadius: 8,
            borderSkipped: false
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: false
            },
            tooltip: {
              backgroundColor: 'rgba(0, 0, 0, 0.8)',
              padding: 12,
              titleFont: {
                family: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", Arial, sans-serif',
                size: 13,
                weight: 600
              },
              bodyFont: {
                family: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", Arial, sans-serif',
                size: 12
              },
              callbacks: {
                label: (context) => {
                  return `${context.parsed.y} transactions`;
                }
              }
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              ticks: {
                font: {
                  family: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", Arial, sans-serif',
                  size: 11
                },
                color: '#86868b',
                precision: 0
              },
              grid: {
                color: 'rgba(0, 0, 0, 0.05)',
                drawBorder: false
              }
            },
            x: {
              ticks: {
                font: {
                  family: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", Arial, sans-serif',
                  size: 11
                },
                color: '#86868b'
              },
              grid: {
                display: false
              }
            }
          },
          animation: {
            duration: 1000,
            easing: 'easeOutCubic'
          }
        }
      });
    };

    watch(() => props.transactions, () => {
      createChart();
    }, { deep: true });

    onMounted(() => {
      createChart();
    });

    return {
      chartCanvas
    };
  }
};
</script>

<style scoped>
.chart-container {
  position: relative;
  height: 300px;
  width: 100%;
}
</style>
