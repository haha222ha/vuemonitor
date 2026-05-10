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

      const dates = props.data.map((d) => d.date);
      const series: echarts.EChartOption.Series[] = [];
      const yAxes: Record<string, echarts.EChartOption.YAxis> = {};

      let hasLeftAxis = false;
      let hasRightAxis = false;

      for (const metric of props.metrics) {
        const config = METRIC_CONFIG[metric];
        if (!config) continue;

        const values = props.data.map((d) => (d as Record<string, unknown>)[metric] as number | null ?? null);

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
        } as unknown as echarts.EChartOption.Series);

        if (config.yAxisIndex === 0) hasLeftAxis = true;
        if (config.yAxisIndex === 1) hasRightAxis = true;
      }

      chart.setOption(
        {
          tooltip: { trigger: "axis" },
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
