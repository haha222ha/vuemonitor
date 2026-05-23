<template>
  <div ref="chartRef" :style="{ width, height }" />
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from "vue";
import * as echarts from "echarts";

const props = withDefaults(defineProps<{
  data: number[];
  color?: string;
  width?: string;
  height?: string;
  fill?: boolean;
}>(), {
  color: "#6366f1",
  width: "80px",
  height: "32px",
  fill: true,
});

const chartRef = ref<HTMLElement>();
let chart: echarts.ECharts | null = null;

function renderChart() {
  if (!chartRef.value || props.data.length < 2) return;

  if (!chart) {
    chart = echarts.init(chartRef.value);
  }

  chart.setOption({
    grid: { left: 0, right: 0, top: 2, bottom: 2 },
    xAxis: { type: "category", show: false, data: props.data.map((_, i) => i) },
    yAxis: { type: "value", show: false, min: (value: { min: number }) => value.min * 0.95 },
    series: [
      {
        type: "line",
        data: props.data,
        smooth: true,
        symbol: "none",
        lineStyle: { width: 1.5, color: props.color },
        areaStyle: props.fill
          ? {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: props.color + "40" },
                { offset: 1, color: props.color + "05" },
              ]),
            }
          : undefined,
      },
    ],
    tooltip: { show: false },
    animation: true,
    animationDuration: 600,
  }, true);
}

const handleResize = () => chart?.resize();

onMounted(() => {
  renderChart();
  window.addEventListener("resize", handleResize);
});

onUnmounted(() => {
  window.removeEventListener("resize", handleResize);
  chart?.dispose();
  chart = null;
});

watch(() => props.data, renderChart, { deep: true });
</script>
