<template>
  <div class="trend-chart">
    <div class="chart-header">
      <h3 class="chart-title">{{ title }}</h3>
      <div class="chart-tabs">
        <button
          v-for="tab in timeTabs"
          :key="tab.value"
          :class="['tab-btn', { active: activeTab === tab.value }]"
          @click="activeTab = tab.value; refreshChart()"
        >
          {{ tab.label }}
        </button>
      </div>
    </div>

    <div class="chart-content">
      <div ref="chartRef" class="main-chart" />

      <div class="anomaly-panel">
        <h4 class="panel-title">异常点检测</h4>
        <div v-if="anomalies.length > 0" class="anomaly-list">
          <div
            v-for="(anomaly, index) in anomalies"
            :key="index"
            :class="['anomaly-item', `anomaly-item--${anomaly.type}`]"
          >
            <span class="anomaly-indicator">{{ anomalyIcon(anomaly.type) }}</span>
            <div class="anomaly-info">
              <span class="anomaly-time">{{ formatDateTime(anomaly.time) }}</span>
              <span class="anomaly-desc">{{ anomaly.description }}</span>
            </div>
            <span class="anomaly-value">{{ anomaly.value }}</span>
          </div>
        </div>
        <div v-else class="anomaly-empty">
          <CircleCheck />
          <span>暂无异常数据</span>
        </div>
      </div>
    </div>

    <div class="sparkline-grid">
      <div
        v-for="metric in sparklineMetrics"
        :key="metric.key"
        class="sparkline-card"
      >
        <div class="sparkline-header">
          <span class="sparkline-label">{{ metric.label }}</span>
          <span class="sparkline-value">{{ metric.value }}</span>
        </div>
        <div ref="sparklineRefs[metric.key]" class="sparkline-chart" />
        <div class="sparkline-trend" :class="metric.trend > 0 ? 'trend-up' : 'trend-down'">
          {{ metric.trend > 0 ? '↑' : '↓' }} {{ Math.abs(metric.trend) }}%
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from "vue";
import { CircleCheck } from "@element-plus/icons-vue";
import * as echarts from "echarts";

interface Anomaly {
  time: string;
  type: "spike" | "drop" | "anomaly" | "warning";
  value: string;
  description: string;
}

interface SparklineMetric {
  key: string;
  label: string;
  value: string;
  trend: number;
  data: number[];
}

const props = defineProps<{
  title?: string;
  data?: { time: string; value: number }[];
  anomalies?: Anomaly[];
}>();

const chartRef = ref<HTMLDivElement | null>(null);
const sparklineRefs = ref<Record<string, HTMLDivElement | null>>({});
const activeTab = ref("7d");

const timeTabs = [
  { label: "7天", value: "7d" },
  { label: "30天", value: "30d" },
  { label: "90天", value: "90d" },
];

const anomalies = ref<Anomaly[]>(props.anomalies || []);

const sparklineMetrics = ref<SparklineMetric[]>([
  { key: "sales", label: "销售额", value: "¥125,680", trend: 12.5, data: [120, 132, 125, 148, 138, 156, 142, 168, 155, 172, 160, 185, 170, 195] },
  { key: "orders", label: "订单数", value: "2,340", trend: 8.3, data: [180, 195, 210, 190, 220, 215, 230, 225, 245, 235, 250, 240, 265, 255] },
  { key: "uv", label: "访问量", value: "15,680", trend: -2.1, data: [1200, 1350, 1280, 1400, 1320, 1450, 1380, 1500, 1420, 1550, 1480, 1600, 1520, 1580] },
  { key: "conversion", label: "转化率", value: "3.2%", trend: 5.6, data: [2.8, 3.0, 2.9, 3.1, 3.0, 3.2, 3.1, 3.3, 3.2, 3.4, 3.3, 3.5, 3.4, 3.6] },
]);

let mainChart: echarts.ECharts | null = null;
const sparklineCharts = ref<Record<string, echarts.ECharts | null>>({});

function anomalyIcon(type: string): string {
  switch (type) {
    case "spike":
      return "📈";
    case "drop":
      return "📉";
    case "anomaly":
      return "⚠️";
    case "warning":
      return "🔔";
    default:
      return "❓";
  }
}

function formatDateTime(timeStr: string): string {
  const date = new Date(timeStr);
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function initMainChart() {
  if (!chartRef.value) return;

  mainChart = echarts.init(chartRef.value);
  const chartData = props.data || generateMockData();

  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(255, 255, 255, 0.95)",
      borderColor: "#e8e8e8",
      borderWidth: 1,
      textStyle: {
        color: "#333",
      },
      formatter: (params: any) => {
        const data = params[0];
        if (!data) return "";
        let html = `<div style="font-weight: 600; margin-bottom: 8px;">${data.name}</div>`;
        html += `<div style="color: #67c23a;">📊 数值: ${data.value}</div>`;
        
        const anomaly = anomalies.value.find(
          (a) => a.time.includes(data.name.split(" ")[0])
        );
        if (anomaly) {
          html += `<div style="color: #f56c6c; margin-top: 8px;">${anomalyIcon(anomaly.type)} ${anomaly.description}</div>`;
        }
        return html;
      },
    },
    grid: {
      left: "3%",
      right: "4%",
      bottom: "3%",
      top: "10%",
      containLabel: true,
    },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: chartData.map((d) => d.time),
      axisLine: {
        lineStyle: { color: "#eee" },
      },
      axisLabel: {
        color: "#999",
        fontSize: 12,
      },
    },
    yAxis: {
      type: "value",
      axisLine: {
        show: false,
      },
      axisTick: {
        show: false,
      },
      splitLine: {
        lineStyle: {
          color: "#f0f0f0",
          type: "dashed",
        },
      },
      axisLabel: {
        color: "#999",
        fontSize: 12,
      },
    },
    series: [
      {
        name: "数值",
        type: "line",
        smooth: true,
        symbol: "circle",
        symbolSize: 6,
        lineStyle: {
          width: 3,
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: "#667eea" },
            { offset: 1, color: "#764ba2" },
          ]),
        },
        itemStyle: {
          color: "#fff",
          borderColor: "#667eea",
          borderWidth: 2,
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "rgba(102, 126, 234, 0.3)" },
            { offset: 1, color: "rgba(102, 126, 234, 0.05)" },
          ]),
        },
        data: chartData.map((d) => d.value),
        markPoint: {
          data: generateAnomalyMarkPoints(),
          symbol: "pin",
          symbolSize: 40,
          label: {
            show: false,
          },
          itemStyle: {
            color: "#f56c6c",
          },
        },
        markLine: {
          silent: true,
          data: [
            {
              yAxis: calculateMovingAverage(chartData),
              name: "平均值",
              lineStyle: {
                color: "#999",
                type: "dashed",
              },
              label: {
                formatter: "平均值",
                position: "end",
                color: "#999",
              },
            },
          ],
        },
      },
    ],
  };

  mainChart.setOption(option);
}

function generateMockData() {
  const data: { time: string; value: number }[] = [];
  const now = new Date();
  for (let i = 13; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);
    const time = date.toLocaleDateString("zh-CN", {
      month: "2-digit",
      day: "2-digit",
    });
    const baseValue = 500 + Math.random() * 300;
    let value = baseValue;
    
    if (i === 5) value = baseValue * 1.8;
    if (i === 8) value = baseValue * 0.4;
    if (i === 10) value = baseValue * 1.5;
    
    data.push({ time, value: Math.round(value) });
  }
  return data;
}

function generateAnomalyMarkPoints() {
  return anomalies.value.map((a) => ({
    name: a.type,
    coord: [a.time.split(" ")[0], 0] as (string | number)[],
    value: a.type,
  }));
}

function calculateMovingAverage(data: { time: string; value: number }[]): number {
  if (data.length === 0) return 0;
  const sum = data.reduce((acc, d) => acc + d.value, 0);
  return Math.round(sum / data.length);
}

function initSparkline(key: string, data: number[]) {
  const ref = sparklineRefs.value[key];
  if (!ref) return;

  const chart = echarts.init(ref);
  sparklineCharts.value[key] = chart;

  const option: echarts.EChartsOption = {
    grid: {
      left: 0,
      right: 0,
      top: 0,
      bottom: 0,
    },
    xAxis: {
      show: false,
      type: "category",
      data: data.map((_, i) => i),
    },
    yAxis: {
      show: false,
      type: "value",
    },
    series: [
      {
        type: "line",
        smooth: true,
        symbol: "none",
        lineStyle: {
          width: 2,
          color: "#667eea",
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "rgba(102, 126, 234, 0.3)" },
            { offset: 1, color: "rgba(102, 126, 234, 0)" },
          ]),
        },
        data,
      },
    ],
  };

  chart.setOption(option);
}

function refreshChart() {
  if (mainChart) {
    mainChart.dispose();
  }
  nextTick(() => {
    initMainChart();
  });
}

function handleResize() {
  mainChart?.resize();
  Object.values(sparklineCharts.value).forEach((chart) => chart?.resize());
}

onMounted(() => {
  if (!props.data) {
    anomalies.value = [
      { time: "05/15 14:30", type: "spike", value: "+180%", description: "销售额异常飙升" },
      { time: "05/12 09:15", type: "drop", value: "-60%", description: "订单量骤降" },
      { time: "05/10 20:00", type: "anomaly", value: "异常", description: "检测到异常波动" },
    ];
  }

  nextTick(() => {
    initMainChart();
    sparklineMetrics.value.forEach((metric) => {
      initSparkline(metric.key, metric.data);
    });
  });

  window.addEventListener("resize", handleResize);
});

onUnmounted(() => {
  mainChart?.dispose();
  Object.values(sparklineCharts.value).forEach((chart) => chart?.dispose());
  window.removeEventListener("resize", handleResize);
});

watch(activeTab, () => {
  refreshChart();
});
</script>

<style lang="scss" scoped>
.trend-chart {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.chart-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
}

.chart-tabs {
  display: flex;
  gap: 4px;
  background: #f5f5f5;
  border-radius: 6px;
  padding: 4px;
}

.tab-btn {
  padding: 6px 16px;
  border: none;
  border-radius: 4px;
  background: transparent;
  font-size: 13px;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: #eee;
  }

  &.active {
    background: #fff;
    color: #409eff;
    font-weight: 500;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  }
}

.chart-content {
  display: flex;
  gap: 16px;
}

.main-chart {
  flex: 1;
  height: 300px;
}

.anomaly-panel {
  width: 280px;
  flex-shrink: 0;
  background: #fafafa;
  border-radius: 8px;
  padding: 12px;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 12px 0;
  color: #333;
}

.anomaly-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.anomaly-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border-radius: 8px;
  background: #fff;

  &--spike {
    border-left: 4px solid #67c23a;
  }

  &--drop {
    border-left: 4px solid #f56c6c;
  }

  &--anomaly {
    border-left: 4px solid #e6a23c;
  }

  &--warning {
    border-left: 4px solid #909399;
  }
}

.anomaly-indicator {
  font-size: 20px;
}

.anomaly-info {
  flex: 1;
}

.anomaly-time {
  display: block;
  font-size: 12px;
  color: #999;
}

.anomaly-desc {
  display: block;
  font-size: 13px;
  color: #333;
  margin-top: 2px;
}

.anomaly-value {
  font-size: 14px;
  font-weight: 600;
  color: #409eff;
}

.anomaly-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px;
  color: #999;
  font-size: 13px;
}

.sparkline-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-top: 16px;
}

.sparkline-card {
  background: #fafafa;
  border-radius: 8px;
  padding: 12px;
}

.sparkline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.sparkline-label {
  font-size: 12px;
  color: #999;
}

.sparkline-value {
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.sparkline-chart {
  height: 40px;
}

.sparkline-trend {
  text-align: right;
  font-size: 12px;
  font-weight: 500;
  margin-top: 4px;

  &.trend-up {
    color: #67c23a;
  }

  &.trend-down {
    color: #f56c6c;
  }
}
</style>