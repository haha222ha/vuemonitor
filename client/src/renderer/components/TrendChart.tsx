import { defineComponent, ref, onMounted, onUnmounted, watch, PropType } from "vue";
import * as echarts from "echarts";

export interface ChartDataPoint {
  date: string;
  value: number;
}

export default defineComponent({
  name: "TrendChart",
  props: {
    data: { type: Array as PropType<ChartDataPoint[]>, required: true },
    title: { type: String, default: "" },
    color: { type: String, default: "#409EFF" },
    unit: { type: String, default: "" },
    height: { type: Number, default: 300 },
  },
  setup(props) {
    const chartRef = ref<HTMLDivElement>();
    let chart: echarts.ECharts | null = null;

    const renderChart = () => {
      if (!chartRef.value || !props.data.length) return;

      if (!chart) {
        chart = echarts.init(chartRef.value);
      }

      const dates = props.data.map((d) => d.date);
      const values = props.data.map((d) => d.value);

      chart.setOption({
        title: {
          text: props.title,
          left: "center",
          textStyle: { fontSize: 14, color: "#606266" },
        },
        tooltip: {
          trigger: "axis",
          formatter: (params: unknown) => {
            const p = (params as Array<{ axisValue: string; value: number }>)[0];
            return `${p.axisValue}<br/>${props.title}: ${p.value}${props.unit}`;
          },
        },
        grid: { left: 50, right: 20, top: 40, bottom: 30 },
        xAxis: {
          type: "category",
          data: dates,
          axisLabel: { fontSize: 11, color: "#909399" },
          axisLine: { lineStyle: { color: "#DCDFE6" } },
        },
        yAxis: {
          type: "value",
          axisLabel: { fontSize: 11, color: "#909399" },
          splitLine: { lineStyle: { color: "#EBEEF5" } },
        },
        series: [
          {
            type: "line",
            data: values,
            smooth: true,
            symbol: "circle",
            symbolSize: 6,
            lineStyle: { width: 2, color: props.color },
            itemStyle: { color: props.color },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: props.color + "40" },
                { offset: 1, color: props.color + "05" },
              ]),
            },
          },
        ],
      });
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
    watch(() => props.title, renderChart);

    return () => <div ref={chartRef} style={{ width: "100%", height: `${props.height}px` }} />;
  },
});
