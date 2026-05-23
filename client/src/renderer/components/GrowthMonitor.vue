<template>
  <div class="growth-monitor">
    <div class="monitor-header">
      <h3 class="monitor-title">📊 24小时增长监控</h3>
      <div class="monitor-time">
        <span class="time-label">更新时间</span>
        <span class="time-value">{{ lastUpdateTime }}</span>
      </div>
    </div>

    <div class="growth-overview">
      <div
        v-for="metric in overviewMetrics"
        :key="metric.key"
        :class="['overview-card', `overview-card--${metric.type}`]"
      >
        <div class="card-icon">{{ metric.icon }}</div>
        <div class="card-content">
          <span class="card-label">{{ metric.label }}</span>
          <span class="card-value">{{ metric.value }}</span>
          <div :class="['card-trend', metric.growth >= 0 ? 'trend-up' : 'trend-down']">
            <span>{{ metric.growth >= 0 ? '↑' : '↓' }}</span>
            <span>{{ Math.abs(metric.growth) }}%</span>
            <span class="trend-period">vs 昨日</span>
          </div>
        </div>
      </div>
    </div>

    <div class="monitor-body">
      <div class="hourly-chart">
        <h4 class="section-title">📈 小时级趋势</h4>
        <div ref="hourlyChartRef" class="chart-container" />
        <div class="chart-legend">
          <div class="legend-item">
            <span class="legend-color" style="background: #667eea;" />
            <span>今日</span>
          </div>
          <div class="legend-item">
            <span class="legend-color" style="background: #e0e0e0;" />
            <span>昨日</span>
          </div>
        </div>
      </div>

      <div class="growth-details">
        <h4 class="section-title">📋 增长详情</h4>
        
        <div class="detail-section">
          <div class="detail-header">
            <span class="detail-label">时段分析</span>
            <span class="detail-badge">{{ peakHour }} 为峰值时段</span>
          </div>
          <div class="time-slots">
            <div
              v-for="slot in timeSlots"
              :key="slot.hour"
              :class="['time-slot', { 'slot-peak': slot.isPeak, 'slot-active': slot.isActive }]"
            >
              <span class="slot-hour">{{ formatHour(slot.hour) }}</span>
              <div class="slot-bar-container">
                <div
                  class="slot-bar slot-bar--today"
                  :style="{ height: `${(slot.today / maxSlotValue) * 100}%` }"
                />
                <div
                  class="slot-bar slot-bar--yesterday"
                  :style="{ height: `${(slot.yesterday / maxSlotValue) * 100}%` }"
                />
              </div>
              <span class="slot-value">{{ slot.today }}</span>
            </div>
          </div>
        </div>

        <div class="detail-section">
          <div class="detail-header">
            <span class="detail-label">增长驱动因素</span>
          </div>
          <div class="driver-list">
            <div
              v-for="driver in growthDrivers"
              :key="driver.name"
              class="driver-item"
            >
              <div class="driver-info">
                <span class="driver-name">{{ driver.name }}</span>
                <span :class="['driver-impact', driver.impact >= 0 ? 'positive' : 'negative']">
                  {{ driver.impact >= 0 ? '+' : '' }}{{ driver.impact }}%
                </span>
              </div>
              <div class="driver-bar">
                <div
                  class="driver-bar-fill"
                  :class="driver.impact >= 0 ? 'fill-positive' : 'fill-negative'"
                  :style="{ width: `${Math.abs(driver.impact)}%` }"
                />
              </div>
            </div>
          </div>
        </div>

        <div class="detail-section">
          <div class="detail-header">
            <span class="detail-label">异常预警</span>
            <span class="detail-badge detail-badge--warning">{{ alerts.length }} 条预警</span>
          </div>
          <div class="alert-list">
            <div
              v-for="(alert, index) in alerts"
              :key="index"
              :class="['alert-item', `alert-item--${alert.level}`]"
            >
              <span class="alert-icon">{{ alertIcon(alert.level) }}</span>
              <div class="alert-content">
                <span class="alert-title">{{ alert.title }}</span>
                <span class="alert-desc">{{ alert.description }}</span>
              </div>
              <span class="alert-time">{{ alert.time }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="monitor-footer">
      <el-button type="primary" @click="refreshData">
        <Refresh />
        刷新数据
      </el-button>
      <span class="refresh-hint">数据每5分钟自动刷新</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from "vue";
import { Refresh } from "@element-plus/icons-vue";
import * as echarts from "echarts";

interface OverviewMetric {
  key: string;
  label: string;
  value: string;
  growth: number;
  icon: string;
  type: "primary" | "success" | "warning" | "danger";
}

interface TimeSlot {
  hour: number;
  today: number;
  yesterday: number;
  isPeak: boolean;
  isActive: boolean;
}

interface GrowthDriver {
  name: string;
  impact: number;
}

interface Alert {
  level: "info" | "warning" | "error";
  title: string;
  description: string;
  time: string;
}

const hourlyChartRef = ref<HTMLDivElement | null>(null);
const lastUpdateTime = ref("");

const overviewMetrics = ref<OverviewMetric[]>([
  { key: "revenue", label: "销售额", value: "¥256,890", growth: 12.5, icon: "💰", type: "primary" },
  { key: "orders", label: "订单数", value: "3,842", growth: 8.3, icon: "📦", type: "success" },
  { key: "users", label: "访客数", value: "28,560", growth: -2.1, icon: "👥", type: "warning" },
  { key: "conversion", label: "转化率", value: "3.8%", growth: 5.6, icon: "📈", type: "success" },
]);

const timeSlots = ref<TimeSlot[]>([]);

const growthDrivers = ref<GrowthDriver[]>([
  { name: "新客增长", impact: 15.2 },
  { name: "复购率提升", impact: 8.7 },
  { name: "客单价提高", impact: 6.3 },
  { name: "活动引流", impact: 4.2 },
  { name: "渠道流量变化", impact: -3.5 },
]);

const alerts = ref<Alert[]>([
  { level: "warning", title: "流量异常", description: "14:00-15:00 访客数同比下降23%", time: "15:30" },
  { level: "info", title: "活动效果", description: "限时优惠带动销售额增长18%", time: "14:00" },
  { level: "error", title: "系统告警", description: "支付接口响应延迟", time: "13:45" },
]);

const maxSlotValue = computed(() => {
  if (timeSlots.value.length === 0) return 1;
  return Math.max(
    ...timeSlots.value.flatMap((slot) => [slot.today, slot.yesterday])
  );
});

const peakHour = computed(() => {
  if (timeSlots.value.length === 0) return "--:--";
  const peak = timeSlots.value.reduce((prev, curr) =>
    curr.today > prev.today ? curr : prev
  );
  return formatHour(peak.hour);
});

let hourlyChart: echarts.ECharts | null = null;
let refreshInterval: ReturnType<typeof setInterval> | null = null;

function formatHour(hour: number): string {
  return `${hour.toString().padStart(2, "0")}:00`;
}

function alertIcon(level: string): string {
  switch (level) {
    case "error":
      return "🔴";
    case "warning":
      return "🟡";
    case "info":
    default:
      return "🔵";
  }
}

function generateTimeSlots(): TimeSlot[] {
  const slots: TimeSlot[] = [];
  const now = new Date();
  const currentHour = now.getHours();

  for (let hour = 0; hour < 24; hour++) {
    const baseValue = 500 + Math.sin((hour / 24) * Math.PI * 2) * 300 + Math.random() * 200;
    const todayValue = Math.round(baseValue);
    const yesterdayValue = Math.round(baseValue * (0.9 + Math.random() * 0.2));
    
    slots.push({
      hour,
      today: hour > currentHour ? 0 : todayValue,
      yesterday: hour > currentHour ? 0 : yesterdayValue,
      isPeak: false,
      isActive: hour === currentHour,
    });
  }

  const maxToday = Math.max(...slots.map((s) => s.today));
  slots.forEach((slot) => {
    if (slot.today === maxToday && slot.today > 0) {
      slot.isPeak = true;
    }
  });

  return slots;
}

function initHourlyChart() {
  if (!hourlyChartRef.value) return;

  if (hourlyChart) {
    hourlyChart.dispose();
  }

  hourlyChart = echarts.init(hourlyChartRef.value);

  const hours = timeSlots.value.map((s) => formatHour(s.hour));
  const todayData = timeSlots.value.map((s) => s.today);
  const yesterdayData = timeSlots.value.map((s) => s.yesterday);

  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(255, 255, 255, 0.95)",
      borderColor: "#e8e8e8",
      borderWidth: 1,
      textStyle: { color: "#333" },
      axisPointer: {
        type: "cross",
        crossStyle: { color: "#999" },
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
      data: hours,
      axisLine: { lineStyle: { color: "#eee" } },
      axisLabel: {
        color: "#999",
        fontSize: 11,
        rotate: 45,
      },
      axisTick: { show: false },
    },
    yAxis: {
      type: "value",
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: "#f0f0f0", type: "dashed" } },
      axisLabel: { color: "#999", fontSize: 11 },
    },
    series: [
      {
        name: "今日",
        type: "line",
        smooth: true,
        symbol: "circle",
        symbolSize: 4,
        lineStyle: { width: 2, color: "#667eea" },
        itemStyle: { color: "#667eea" },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "rgba(102, 126, 234, 0.3)" },
            { offset: 1, color: "rgba(102, 126, 234, 0)" },
          ]),
        },
        data: todayData,
      },
      {
        name: "昨日",
        type: "line",
        smooth: true,
        symbol: "circle",
        symbolSize: 4,
        lineStyle: { width: 2, color: "#e0e0e0", type: "dashed" },
        itemStyle: { color: "#e0e0e0" },
        data: yesterdayData,
      },
    ],
  };

  hourlyChart.setOption(option);
}

function refreshData() {
  updateTime();
  timeSlots.value = generateTimeSlots();
  
  overviewMetrics.value = [
    { key: "revenue", label: "销售额", value: `¥${Math.round(250000 + Math.random() * 20000).toLocaleString()}`, growth: (Math.random() - 0.3) * 20, icon: "💰", type: "primary" },
    { key: "orders", label: "订单数", value: `${Math.round(3500 + Math.random() * 800).toLocaleString()}`, growth: (Math.random() - 0.3) * 15, icon: "📦", type: "success" },
    { key: "users", label: "访客数", value: `${Math.round(25000 + Math.random() * 8000).toLocaleString()}`, growth: (Math.random() - 0.5) * 10, icon: "👥", type: "warning" },
    { key: "conversion", label: "转化率", value: `${(3 + Math.random() * 2).toFixed(1)}%`, growth: (Math.random() - 0.3) * 10, icon: "📈", type: "success" },
  ];

  nextTick(() => {
    initHourlyChart();
  });
}

function updateTime() {
  const now = new Date();
  lastUpdateTime.value = now.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

onMounted(() => {
  updateTime();
  timeSlots.value = generateTimeSlots();

  nextTick(() => {
    initHourlyChart();
  });

  refreshInterval = setInterval(() => {
    updateTime();
  }, 5000);
});

onUnmounted(() => {
  hourlyChart?.dispose();
  if (refreshInterval) {
    clearInterval(refreshInterval);
  }
});
</script>

<style lang="scss" scoped>
.growth-monitor {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
}

.monitor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.monitor-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
}

.monitor-time {
  display: flex;
  align-items: center;
  gap: 8px;
}

.time-label {
  font-size: 12px;
  color: #999;
}

.time-value {
  font-size: 13px;
  font-weight: 500;
  color: #667eea;
}

.growth-overview {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.overview-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border-radius: 12px;

  &--primary {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  }

  &--success {
    background: linear-gradient(135deg, #67c23a 0%, #5eb838 100%);
  }

  &--warning {
    background: linear-gradient(135deg, #e6a23c 0%, #d4912f 100%);
  }

  &--danger {
    background: linear-gradient(135deg, #f56c6c 0%, #e45a5a 100%);
  }
}

.card-icon {
  font-size: 28px;
}

.card-content {
  color: #fff;
}

.card-label {
  display: block;
  font-size: 12px;
  opacity: 0.8;
}

.card-value {
  display: block;
  font-size: 20px;
  font-weight: 600;
}

.card-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  margin-top: 4px;

  &.trend-up {
    color: #a8e063;
  }

  &.trend-down {
    color: #ffd54f;
  }
}

.trend-period {
  opacity: 0.7;
}

.monitor-body {
  display: flex;
  gap: 16px;
}

.hourly-chart {
  flex: 1;
  background: #fafafa;
  border-radius: 8px;
  padding: 16px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 12px 0;
  color: #333;
}

.chart-container {
  height: 200px;
}

.chart-legend {
  display: flex;
  justify-content: center;
  gap: 24px;
  margin-top: 12px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #666;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 2px;
}

.growth-details {
  width: 320px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-section {
  background: #fafafa;
  border-radius: 8px;
  padding: 12px;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.detail-label {
  font-size: 13px;
  font-weight: 500;
  color: #333;
}

.detail-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: #e8e8ff;
  color: #667eea;

  &--warning {
    background: #fff3e0;
    color: #e65100;
  }
}

.time-slots {
  display: flex;
  gap: 4px;
  height: 100px;
  overflow-x: auto;
}

.time-slot {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  min-width: 32px;
}

.slot-hour {
  font-size: 10px;
  color: #999;
}

.slot-bar-container {
  flex: 1;
  width: 16px;
  display: flex;
  align-items: flex-end;
  gap: 2px;
}

.slot-bar {
  width: 7px;
  border-radius: 4px;
  transition: height 0.3s ease;

  &--today {
    background: #667eea;
  }

  &--yesterday {
    background: #e0e0e0;
  }
}

.slot-value {
  font-size: 10px;
  color: #666;
}

.time-slot.slot-peak .slot-bar--today {
  background: #f56c6c;
}

.time-slot.slot-active {
  background: #fff;
  border-radius: 4px;
  padding: 4px;
}

.driver-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.driver-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.driver-info {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

.driver-name {
  color: #666;
}

.driver-impact {
  font-weight: 600;

  &.positive {
    color: #67c23a;
  }

  &.negative {
    color: #f56c6c;
  }
}

.driver-bar {
  height: 6px;
  background: #e8e8e8;
  border-radius: 3px;
  overflow: hidden;
}

.driver-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;

  &.fill-positive {
    background: linear-gradient(90deg, #67c23a, #85ce61);
  }

  &.fill-negative {
    background: linear-gradient(90deg, #f56c6c, #f89898);
  }
}

.alert-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.alert-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border-radius: 8px;
  background: #fff;

  &--error {
    border-left: 4px solid #f56c6c;
  }

  &--warning {
    border-left: 4px solid #e6a23c;
  }

  &--info {
    border-left: 4px solid #667eea;
  }
}

.alert-icon {
  font-size: 18px;
}

.alert-content {
  flex: 1;
}

.alert-title {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: #333;
}

.alert-desc {
  display: block;
  font-size: 11px;
  color: #999;
  margin-top: 2px;
}

.alert-time {
  font-size: 11px;
  color: #bbb;
}

.monitor-footer {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #eee;
}

.refresh-hint {
  font-size: 12px;
  color: #999;
}
</style>