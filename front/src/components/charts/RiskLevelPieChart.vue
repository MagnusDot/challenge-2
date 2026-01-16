<template>
  <div class="chart-container">
    <canvas ref="chartCanvas"></canvas>
  </div>
</template>

<script>
import {
    ArcElement,
    Chart as ChartJS,
    DoughnutController,
    Legend,
    Tooltip
} from 'chart.js';
import { onMounted, ref, watch } from 'vue';

ChartJS.register(ArcElement, Tooltip, Legend, DoughnutController);

export default {
  name: 'RiskLevelPieChart',
  props: {
    riskLevelStats: {
      type: Object,
      required: true
    },
    totalCount: {
      type: Number,
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

      if (!chartCanvas.value || props.totalCount === 0) return;

      const data = [
        { label: 'Low', value: props.riskLevelStats.low || 0, color: '#34c759' },
        { label: 'Medium', value: props.riskLevelStats.medium || 0, color: '#ff9500' },
        { label: 'High', value: props.riskLevelStats.high || 0, color: '#ff3b30' },
        { label: 'Critical', value: props.riskLevelStats.critical || 0, color: '#8e0000' }
      ].filter(item => item.value > 0);

      chartInstance = new ChartJS(chartCanvas.value, {
        type: 'doughnut',
        data: {
          labels: data.map(d => d.label),
          datasets: [{
            data: data.map(d => d.value),
            backgroundColor: data.map(d => d.color),
            borderWidth: 0,
            hoverOffset: 8
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'bottom',
              labels: {
                padding: 20,
                font: {
                  family: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", Arial, sans-serif',
                  size: 12,
                  weight: 500
                },
                color: '#1d1d1f',
                usePointStyle: true,
                pointStyle: 'circle'
              }
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
                  const label = context.label || '';
                  const value = context.parsed || 0;
                  const percentage = ((value / props.totalCount) * 100).toFixed(1);
                  return `${label}: ${value} (${percentage}%)`;
                }
              }
            }
          },
          cutout: '60%',
          animation: {
            animateRotate: true,
            animateScale: true,
            duration: 1000,
            easing: 'easeOutCubic'
          }
        }
      });
    };

    watch(() => [props.riskLevelStats, props.totalCount], () => {
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
