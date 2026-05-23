import { defineComponent, ref, onMounted, onUnmounted, watch, PropType } from "vue";
import * as echarts from "echarts";

export interface MultiMetricDataPoint {
  date: string;
  price?: number | null;
  sales?: number | null;
  rating?: number | null;
  review_count?: number | null;
  favorite_count?: number | null;
}

interface AnomalyInfo {
  coord: [number, number];
  value: number;
  type: "price_spike" | "price_drop" | "sales_surge" | "sales_drop" | "other";
  changeRate: number;
}

function detectAnomalies(values: (number | null)[], metricType: string): AnomalyInfo[] {
  const valid = values.filter((v): v is number => v !== null);
  if (valid.length < 3) return [];

  const mean = valid.reduce((a, b) => a + b, 0) / valid.length;
  const std = Math.sqrt(valid.reduce((a, b) => a + (b - mean) ** 2, 0) / valid.length);
  if (std === 0) return [];

  const anomalies: AnomalyInfo[] = [];
  const THRESHOLD = 2;

  values.forEach((v, i) => {
    if (v === null) return;

    const zScore = Math.abs(v - mean) / std;
    if (zScore <= THRESHOLD) return;

    let prevVal: number | null = null;
    for (let j = i - 1; j >= 0; j--) {
      if (values[j] !== null) { prevVal = values[j]; break; }
    }

    let changeRate = 0;
    if (prevVal !== null && prevVal !== 0) {
      changeRate = ((v - prevVal) / Math.abs(prevVal)) * 100;
    } else if (prevVal === 0 && v > 0) {
      changeRate = 100;
    }

    let type: AnomalyInfo["type"] = "other";
    if (metricType === "price") {
      type = v > mean ? "price_spike" : "price_drop";
    } else if (metricType === "sales") {
      type = v > mean ? "sales_surge" : "sales_drop";
    } else {
      type = v > mean ? "other" : "other";
    }

    anomalies.push({ coord: [i, v], value: v, type, changeRate });
  });

  return anomalies;
}

const MAX_RENDER_POINTS = 500;

function downsampleData<T>(data: T[], maxPoints: number): T[] {
  if (data.length <= maxPoints) return data;
  const step = data.length / maxPoints;
  const result: T[] = [data[0]];
  for (let i = 1; i < maxPoints - 1; i++) {
    result.push(data[Math.round(i * step)]);
  }
  result.push(data[data.length - 1]);
  return result;
}

const ANOMEMY_LABELS: Record<AnomalyInfo["type"], string> = {
  price_spike: "价格突变↑",
  price_drop: "价格骤降↓",
  sales_surge: "销量暴增↑",
  sales_drop: "销量骤降↓",
  other: "异常",
};

const ANOMEMY_COLORS: Record<AnomalyInfo["type"], string> = {
  price_spike: "#EF4444",
  price_drop: "#F97316",
  sales_surge: "#EF4444",
  sales_drop: "#F97316",
  other: "#E6A23C",
};

export default defineComponent({
  name: "MultiMetricChart",
  props: {
    data: { type: Array as PropType<MultiMetricDataPoint[]>, required: true },
    metrics: { type: Array as PropType<string[]>, default: () => ["price", "sales"] },
    height: { type: Number, default: 400 },
  },
  setup(props) {
    const chartRef = ref<HTMLDivElement>();
    let chart: echarts.ECharts | null = null;

    const METRIC_CONFIG: Record<string, { label: string; color: string; unit: string; yAxisIndex: number }> = {
      price: { label: "价格", color: "#F56C6C", unit: "元", yAxisIndex: 0 },
      sales: { label: "销量", color: "#409EFF", unit: "", yAxisIndex: 1 },
      rating: { label: "评分", color: "#E6A23C", unit: "分", yAxisIndex: 0 },
      review_count: { label: "评论数", color: "#67C23A", unit: "", yAxisIndex: 1 },
      favorite_count: { label: "收藏数", color: "#909399", unit: "", yAxisIndex: 1 },
    };

    const renderChart = () => {
      if (!chartRef.value || !props.data.length) return;

      if (!chart) {
        chart = echarts.init(chartRef.value);
      }

      const needsDownsample = props.data.length > MAX_RENDER_POINTS;
      const chartData = needsDownsample ? downsampleData(props.data, MAX_RENDER_POINTS) : props.data;

      const dates = chartData.map((d) => d.date);
      const series: Record<string, unknown>[] = [];
      const yAxes: Record<string, Record<string, unknown>> = {};
      const markLineData: Record<string, unknown>[] = [];

      let hasLeftAxis = false;
      let hasRightAxis = false;

      for (const metric of props.metrics) {
        const config = METRIC_CONFIG[metric];
        if (!config) continue;

        const values = chartData.map((d) => (d as unknown as Record<string, unknown>)[metric] as number | null ?? null);

        const anomalies = detectAnomalies(values, metric);

        const markPointData = anomalies.map((a) => ({
          coord: a.coord,
          value: a.value,
          symbol: a.type.includes("spike") || a.type.includes("surge") ? "triangle" : "diamond",
          symbolSize: 28,
          symbolRotate: a.type.includes("spike") || a.type.includes("surge") ? 0 : 180,
          itemStyle: { color: ANOMEMY_COLORS[a.type] },
          label: {
            show: true,
            fontSize: 9,
            color: "#fff",
            fontWeight: "bold",
            formatter: () => {
              const sign = a.changeRate >= 0 ? "+" : "";
              return `${sign}${a.changeRate.toFixed(0)}%`;
            },
          },
        }));

        const markAreaData = anomalies.map((a) => ({
          xAxis: dates[a.coord[0]],
          itemStyle: {
            color: ANOMEMY_COLORS[a.type],
            opacity: 0.08,
          },
        }));

        series.push({
          type: "line",
          name: config.label,
          data: values,
          smooth: true,
          symbol: "circle",
          symbolSize: 5,
          lineStyle: { width: 2, color: config.color },
          itemStyle: { color: config.color },
          yAxisIndex: config.yAxisIndex,
          markPoint: markPointData.length > 0 ? {
            data: markPointData,
            animation: true,
          } : undefined,
          markArea: markAreaData.length > 0 ? {
            data: markAreaData.map((d) => [d]),
            silent: true,
          } : undefined,
        } as Record<string, unknown>);

        if (config.yAxisIndex === 0) hasLeftAxis = true;
        if (config.yAxisIndex === 1) hasRightAxis = true;
      }

      const anomalyAnnotations: Record<string, unknown>[] = [];
      for (const metric of props.metrics) {
        const config = METRIC_CONFIG[metric];
        if (!config) continue;
        const values = chartData.map((d) => (d as unknown as Record<string, unknown>)[metric] as number | null ?? null);
        const anomalies = detectAnomalies(values, metric);
        for (const a of anomalies) {
          anomalyAnnotations.push({
            xAxis: dates[a.coord[0]],
            yAxis: a.value,
            seriesName: config.label,
          });
        }
      }

      chart.setOption(
        {
          animation: chartData.length <= 200,
          tooltip: {
            trigger: "axis",
            formatter: (params: unknown) => {
              const ps = params as { seriesName: string; value: number | null; axisValue: string; marker: string }[];
              if (!ps || !ps.length) return "";
              let html = `<div style="font-weight:600;margin-bottom:4px">${ps[0].axisValue}</div>`;
              for (const p of ps) {
                if (p.value == null) continue;
                html += `<div>${p.marker} ${p.seriesName}: <b>${p.value}</b></div>`;
              }
              return html;
            },
          },
          legend: { top: 0 },
          grid: { left: 60, right: hasRightAxis ? 60 : 20, top: 40, bottom: 30 },
          xAxis: {
            type: "category",
            data: dates,
            axisLabel: { fontSize: 11, color: "#909399" },
          },
          yAxis: [
            hasLeftAxis
              ? {
                  type: "value",
                  position: "left",
                  axisLabel: { fontSize: 11, color: "#909399" },
                  splitLine: { lineStyle: { color: "#EBEEF5" } },
                }
              : undefined,
            hasRightAxis
              ? {
                  type: "value",
                  position: "right",
                  axisLabel: { fontSize: 11, color: "#909399" },
                  splitLine: { show: false },
                }
              : undefined,
          ].filter(Boolean),
          series,
        },
        true
      );
    };

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
    watch(() => props.metrics, renderChart, { deep: true });

    return () => <div ref={chartRef} style={{ width: "100%", height: `${props.height}px` }} />;
  },
});
