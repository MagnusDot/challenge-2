<template>
  <div class="chart-container">
    <canvas ref="chartCanvas"></canvas>
  </div>
</template>

<script>
import { ref, onMounted, watch } from 'vue';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  BarController,
  Tooltip,
  Legend
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, BarElement, BarController, Tooltip, Legend);

export default {
  name: 'TransactionTypeChart',
  props: {
    typeStats: {
      type: Object,
      required: true
    }
  },
  setup(props) {
    const chartCanvas = ref(null);
    let chartInstance = null;

    const createChart = () => {
      if (chartInstance) {
        chartInstance.destroy();
      }

      if (!chartCanvas.value || Object.keys(props.typeStats).length === 0) return;

      const entries = Object.entries(props.typeStats)
        .map(([type, count]) => ({ type: type || 'Not specified', count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 10);

      const labels = entries.map(e => e.type);
      const data = entries.map(e => e.count);

      chartInstance = new ChartJS(chartCanvas.value, {
        type: 'bar',
        data: {
          labels,
          datasets: [{
            label: 'Transactions',
            data,
            backgroundColor: 'rgba(0, 122, 255, 0.7)',
            borderColor: '#007aff',
            borderWidth: 1,
            borderRadius: 8,
            borderSkipped: false
          }]
        },
        options: {
          indexAxis: 'y',
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
                  return `${context.parsed.x} transactions`;
                }
              }
            }
          },
          scales: {
            x: {
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
            y: {
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

    watch(() => props.typeStats, () => {
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
