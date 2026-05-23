<template>
  <div class="trend-chart">
    <div class="trend-chart__header">
      <div class="trend-chart__title-group">
        <el-icon :size="20" class="trend-chart__icon"><TrendCharts /></el-icon>
        <h3 class="trend-chart__title">数据趋势</h3>
      </div>
      <div class="trend-chart__controls">
        <el-radio-group v-model="chartRange" size="small">
          <el-radio-button value="7">7天</el-radio-button>
          <el-radio-button value="30">30天</el-radio-button>
          <el-radio-button value="0">全部</el-radio-button>
        </el-radio-group>
      </div>
    </div>
    <div class="trend-chart__toolbar">
      <span class="trend-chart__toolbar-label">显示指标：</span>
      <el-check-tag :checked="metricVisible.price" @change="metricVisible.price = !metricVisible.price">价格</el-check-tag>
      <el-check-tag :checked="metricVisible.sales" @change="metricVisible.sales = !metricVisible.sales">销量</el-check-tag>
      <el-check-tag :checked="metricVisible.rating" @change="metricVisible.rating = !metricVisible.rating">评分</el-check-tag>
      <el-check-tag :checked="metricVisible.review_count" @change="metricVisible.review_count = !metricVisible.review_count">评论数</el-check-tag>
      <el-check-tag :checked="metricVisible.favorite_count" @change="metricVisible.favorite_count = !metricVisible.favorite_count">收藏数</el-check-tag>
    </div>
    <div ref="chartRef" class="trend-chart__container" />
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from "vue";
import { TrendCharts } from "@element-plus/icons-vue";
import * as echarts from "echarts";

const props = defineProps<{
  data: Array<Record<string, any>>;
  metrics: string[];
}>();

const chartRef = ref<HTMLElement>();
const chartRange = ref("7");
const metricVisible = ref({
  price: true,
  sales: true,
  rating: true,
  review_count: true,
  favorite_count: true,
});

let chartInstance: echarts.ECharts | null = null;

const filteredData = computed(() => {
  if (!props.data.length) return [];
  const days = parseInt(chartRange.value);
  if (days === 0) return props.data;
  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - days);
  return props.data.filter((d) => new Date(d.collected_at || d.date) >= cutoff);
});

function renderChart() {
  if (!chartRef.value || !chartInstance) return;

  const series = [];
  const colors = ["#EF4444", "#4F46E5", "#F59E0B", "#10B981", "#8B5CF6"];
  const metricNames: Record<string, string> = {
    price: "价格",
    sales: "销量",
    rating: "评分",
    review_count: "评论数",
    favorite_count: "收藏数",
  };

  let colorIndex = 0;
  for (const key of props.metrics) {
    if (!metricVisible.value[key as keyof typeof metricVisible.value]) continue;
    series.push({
      name: metricNames[key] || key,
      type: "line",
      data: filteredData.value.map((d) => d[key] ?? null),
      smooth: true,
      symbol: "circle",
      symbolSize: 4,
      lineStyle: { width: 2 },
      itemStyle: { color: colors[colorIndex % colors.length] },
    });
    colorIndex++;
  }

  const option = {
    tooltip: { trigger: "axis" as const },
    legend: { data: series.map((s) => s.name), bottom: 0 },
    grid: { top: 16, right: 16, bottom: 48, left: 48 },
    xAxis: {
      type: "category" as const,
      data: filteredData.value.map((d) => {
        const date = new Date(d.collected_at || d.date);
        return `${date.getMonth() + 1}/${date.getDate()}`;
      }),
      axisLine: { lineStyle: { color: "#E2E8F0" } },
      axisLabel: { color: "#64748B", fontSize: 11 },
    },
    yAxis: {
      type: "value" as const,
      splitLine: { lineStyle: { color: "#F1F5F9", type: "dashed" as const } },
      axisLabel: { color: "#64748B", fontSize: 11 },
    },
    series,
  };

  chartInstance.setOption(option, true);
}

function handleResize() {
  chartInstance?.resize();
}

onMounted(() => {
  if (chartRef.value) {
    chartInstance = echarts.init(chartRef.value);
    renderChart();
  }
  window.addEventListener("resize", handleResize);
});

onUnmounted(() => {
  chartInstance?.dispose();
  window.removeEventListener("resize", handleResize);
});

watch([filteredData, () => props.metrics, metricVisible], renderChart, { deep: true });
</script>

<style scoped>
.trend-chart {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-sm);
}

.trend-chart__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-base);
}

.trend-chart__title-group {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
}

.trend-chart__icon {
  color: var(--color-primary);
}

.trend-chart__title {
  margin: 0;
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--color-text-primary);
}

.trend-chart__controls {
  display: flex;
  gap: var(--space-sm);
}

.trend-chart__toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  margin-bottom: var(--space-base);
  flex-wrap: wrap;
}

.trend-chart__toolbar-label {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.trend-chart__container {
  width: 100%;
  height: 350px;
}
</style>
