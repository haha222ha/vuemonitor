import { ref, computed, nextTick, watch } from "vue";
import * as echarts from "echarts";
import api, { isNetworkError } from "../utils/api";

const TREND_COLORS = ["#6366F1", "#EF4444", "#10B981", "#F59E0B", "#8B5CF6", "#06B6D4", "#EC4899", "#14B8A6", "#A855F7", "#F97316"];

export function useCategoryInsightData() {
  const selectedCategory = ref("");
  const trendDays = ref(30);
  const trendMetric = ref("avg_sales");
  const heatmapMode = ref("treemap");
  const refreshing = ref(false);

  const heatmapData = ref<any[]>([]);
  const heatmapLoading = ref(false);
  const patterns = ref<any>(null);
  const patternsLoading = ref(false);
  const trendSeries = ref<Record<string, any[]>>({});
  const trendLoading = ref(false);
  const categoryStatsList = ref<any[]>([]);

  const heatmapChartRef = ref<HTMLElement>();
  const lifecycleChartRef = ref<HTMLElement>();
  const trendDistChartRef = ref<HTMLElement>();
  const priceBandChartRef = ref<HTMLElement>();
  const trendChartRef = ref<HTMLElement>();

  let heatmapChart: echarts.ECharts | null = null;
  let lifecycleChart: echarts.ECharts | null = null;
  let trendDistChart: echarts.ECharts | null = null;
  let priceBandChart: echarts.ECharts | null = null;
  let trendChart: echarts.ECharts | null = null;

  const categoryList = computed(() => {
    const cats = new Set<string>();
    for (const item of heatmapData.value) { if (item.category) cats.add(item.category); }
    for (const item of categoryStatsList.value) { if (item.category) cats.add(item.category); }
    return [...cats].sort();
  });

  const categoryStats = computed(() => {
    const items = categoryStatsList.value;
    const totalCategories = items.length;
    const totalProducts = items.reduce((s, i) => s + (i.product_count || 0), 0);
    const topItem = items.length > 0 ? items.reduce((a, b) => (a.heat_score || 0) > (b.heat_score || 0) ? a : b) : null;
    const avgHeat = items.length > 0 ? (items.reduce((s, i) => s + (i.heat_score || 0), 0) / items.length).toFixed(1) : "0";
    return {
      totalCategories,
      totalProducts: totalProducts > 10000 ? `${(totalProducts / 10000).toFixed(1)}w` : String(totalProducts),
      topCategory: topItem?.category || "",
      avgHeat,
    };
  });

  function formatNumber(n: number): string {
    if (n >= 10000) return (n / 10000).toFixed(1) + "w";
    if (n >= 1000) return (n / 1000).toFixed(1) + "k";
    return String(Math.round(n));
  }

  function heatLevel(score: number): string {
    if (score >= 70) return "heat-hot";
    if (score >= 40) return "heat-warm";
    return "heat-cold";
  }

  function lifecycleLabel(stage: string): string {
    const map: Record<string, string> = { new: "新品期", growth: "成长期", rising: "上升期", stable: "稳定期", declining: "衰退期", decline: "衰退期", mature: "成熟期" };
    return map[stage] || stage;
  }

  function trendLabel(trend: string): string {
    const map: Record<string, string> = { up: "上升", down: "下降", stable: "平稳", unknown: "未知" };
    return map[trend] || trend;
  }

  function trendTagType(trend: string): "" | "success" | "danger" | "info" {
    const map: Record<string, "" | "success" | "danger" | "info"> = { up: "success", down: "danger", stable: "info", unknown: "info" };
    return map[trend] || "info";
  }

  function priceBandLabel(band: string): string {
    const map: Record<string, string> = { under_50: "¥50以下", "50_100": "¥50-100", "100_200": "¥100-200", "200_500": "¥200-500", over_500: "¥500+" };
    return map[band] || band;
  }

  async function fetchCategoryStats() {
    try {
      const params: Record<string, any> = {};
      if (selectedCategory.value) params.category = selectedCategory.value;
      const { data } = await api.get("/feature/category-stats", { params });
      if (data?.categories) categoryStatsList.value = data.categories;
    } catch (err) { if (isNetworkError(err)) categoryStatsList.value = []; }
  }

  async function fetchHeatmap() {
    heatmapLoading.value = true;
    try {
      const { data } = await api.get("/feature/crowd/category-heatmap");
      if (data?.heatmap) {
        heatmapData.value = data.heatmap;
        await nextTick();
        renderHeatmapChart();
      }
    } catch (err) { if (isNetworkError(err)) heatmapData.value = []; }
    finally { heatmapLoading.value = false; }
  }

  async function fetchBehaviorPatterns() {
    patternsLoading.value = true;
    try {
      const params: Record<string, any> = {};
      if (selectedCategory.value) params.category = selectedCategory.value;
      const { data } = await api.get("/feature/crowd/behavior-patterns", { params });
      if (data) {
        patterns.value = data;
        await nextTick();
        renderLifecycleChart();
        renderTrendDistChart();
        renderPriceBandChart();
      }
    } catch (err) { if (isNetworkError(err)) patterns.value = null; }
    finally { patternsLoading.value = false; }
  }

  async function fetchTrendTimeseries() {
    trendLoading.value = true;
    try {
      const params: Record<string, any> = { days: trendDays.value };
      if (selectedCategory.value) params.category = selectedCategory.value;
      const { data } = await api.get("/feature/crowd/trend-timeseries", { params });
      if (data?.series) {
        trendSeries.value = data.series;
        await nextTick();
        renderTrendChart();
      }
    } catch (err) { if (isNetworkError(err)) trendSeries.value = {}; }
    finally { trendLoading.value = false; }
  }

  function onCategoryChange() {
    fetchBehaviorPatterns();
    fetchTrendTimeseries();
    fetchCategoryStats();
  }

  async function refreshAll() {
    refreshing.value = true;
    await Promise.all([fetchCategoryStats(), fetchHeatmap(), fetchBehaviorPatterns(), fetchTrendTimeseries()]);
    refreshing.value = false;
  }

  function renderHeatmapChart() {
    if (!heatmapChartRef.value || heatmapData.value.length === 0) return;
    if (!heatmapChart) heatmapChart = echarts.init(heatmapChartRef.value);
    if (heatmapMode.value === "treemap") {
      const treemapData = heatmapData.value.map((item) => ({
        name: item.category, value: item.heat_score || 0,
        itemStyle: { color: item.heat_level === "hot" ? "#EF4444" : item.heat_level === "warm" ? "#F59E0B" : "#6366F1" },
        _meta: item,
      }));
      heatmapChart.setOption({
        backgroundColor: "transparent",
        tooltip: {
          formatter(params: any) {
            const d = params.data; const meta = d._meta || {};
            return `<strong>${d.name}</strong><br/>热度: ${d.value}<br/>商品数: ${meta.product_count || '-'}<br/>均价: ${meta.avg_price != null ? '¥' + meta.avg_price.toFixed(0) : '-'}<br/>均销量: ${meta.avg_sales != null ? formatNumber(meta.avg_sales) : '-'}<br/>均评分: ${meta.avg_rating != null ? meta.avg_rating.toFixed(1) : '-'}`;
          },
        },
        series: [{
          type: "treemap", data: treemapData, width: "95%", height: "90%", top: 10, roam: false, nodeClick: false,
          breadcrumb: { show: false }, label: { show: true, formatter: "{b}", fontSize: 12, color: "#fff" }, upperLabel: { show: false },
          itemStyle: { borderColor: "rgba(0,0,0,0.15)", borderWidth: 2, gapWidth: 2 },
          levels: [{ itemStyle: { borderColor: "rgba(0,0,0,0.15)", borderWidth: 2, gapWidth: 2 } }],
        }],
      }, true);
    } else {
      const sorted = [...heatmapData.value].sort((a, b) => (b.heat_score || 0) - (a.heat_score || 0));
      const names = sorted.map((i) => i.category);
      const values = sorted.map((i) => i.heat_score || 0);
      const colors = sorted.map((i) => i.heat_level === "hot" ? "#EF4444" : i.heat_level === "warm" ? "#F59E0B" : "#6366F1");
      heatmapChart.setOption({
        backgroundColor: "transparent", tooltip: { trigger: "axis" },
        grid: { left: 100, right: 30, top: 20, bottom: 30 },
        xAxis: { type: "value", axisLabel: { color: "#94A3B8", fontSize: 11 } },
        yAxis: { type: "category", data: names, axisLabel: { color: "#94A3B8", fontSize: 11 } },
        series: [{ type: "bar", data: values.map((v, i) => ({ value: v, itemStyle: { color: colors[i], borderRadius: [0, 4, 4, 0] } })), barMaxWidth: 24, label: { show: true, position: "right", fontSize: 11, color: "#94A3B8" } }],
      }, true);
    }
  }

  function renderLifecycleChart() {
    if (!lifecycleChartRef.value || !patterns.value?.lifecycle_distribution?.length) return;
    if (!lifecycleChart) lifecycleChart = echarts.init(lifecycleChartRef.value);
    const dist = patterns.value.lifecycle_distribution;
    const data = dist.map((d: any) => ({ name: lifecycleLabel(d.stage) || d.stage, value: d.count }));
    lifecycleChart.setOption({
      backgroundColor: "transparent", tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
      series: [{ type: "pie", radius: ["40%", "70%"], center: ["50%", "50%"], data, label: { fontSize: 11, color: "#94A3B8" }, itemStyle: { borderRadius: 4, borderColor: "var(--color-bg-card)", borderWidth: 2 }, emphasis: { label: { fontSize: 13, fontWeight: "bold" } }, color: ["#6366F1", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6", "#06B6D4"] }],
    }, true);
  }

  function renderTrendDistChart() {
    if (!trendDistChartRef.value || !patterns.value?.trend_distribution?.length) return;
    if (!trendDistChart) trendDistChart = echarts.init(trendDistChartRef.value);
    const dist = patterns.value.trend_distribution;
    const data = dist.map((d: any) => ({ name: trendLabel(d.trend) || d.trend, value: d.count, itemStyle: { color: d.trend === "up" ? "#10B981" : d.trend === "down" ? "#EF4444" : "#6366F1" } }));
    trendDistChart.setOption({
      backgroundColor: "transparent", tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
      series: [{ type: "pie", radius: ["40%", "70%"], center: ["50%", "50%"], data, label: { fontSize: 11, color: "#94A3B8" }, itemStyle: { borderRadius: 4, borderColor: "var(--color-bg-card)", borderWidth: 2 }, emphasis: { label: { fontSize: 13, fontWeight: "bold" } } }],
    }, true);
  }

  function renderPriceBandChart() {
    if (!priceBandChartRef.value || !patterns.value?.price_bands?.length) return;
    if (!priceBandChart) priceBandChart = echarts.init(priceBandChartRef.value);
    const bands = patterns.value.price_bands;
    const names = bands.map((b: any) => priceBandLabel(b.band));
    const counts = bands.map((b: any) => b.count);
    const avgSales = bands.map((b: any) => b.avg_sales || 0);
    priceBandChart.setOption({
      backgroundColor: "transparent", tooltip: { trigger: "axis" }, legend: { bottom: 0, textStyle: { fontSize: 11 } },
      grid: { left: 50, right: 30, top: 20, bottom: 40 },
      xAxis: { type: "category", data: names, axisLabel: { fontSize: 10, color: "#94A3B8" } },
      yAxis: [{ type: "value", name: "商品数", axisLabel: { fontSize: 10, color: "#94A3B8" } }, { type: "value", name: "均销量", axisLabel: { fontSize: 10, color: "#94A3B8" } }],
      series: [
        { name: "商品数", type: "bar", data: counts, itemStyle: { color: "#6366F1", borderRadius: [4, 4, 0, 0] }, barMaxWidth: 36 },
        { name: "均销量", type: "line", yAxisIndex: 1, data: avgSales, lineStyle: { color: "#10B981", width: 2 }, itemStyle: { color: "#10B981" }, symbol: "circle", symbolSize: 6 },
      ],
    }, true);
  }

  function renderTrendChart() {
    if (!trendChartRef.value || !trendSeries.value || Object.keys(trendSeries.value).length === 0) return;
    if (!trendChart) trendChart = echarts.init(trendChartRef.value);
    const metric = trendMetric.value;
    const metricLabels: Record<string, string> = { avg_sales: "平均销量", avg_price: "平均价格", avg_rating: "平均评分", product_count: "商品数" };
    const categories = Object.keys(trendSeries.value);
    const series: any[] = [];
    let allDates: string[] = [];
    for (const cat of categories) {
      const points = trendSeries.value[cat];
      if (points.length === 0) continue;
      const dates = points.map((p: any) => p.period?.substring(0, 10) || "");
      if (dates.length > allDates.length) allDates = dates;
    }
    for (let i = 0; i < categories.length; i++) {
      const cat = categories[i];
      const points = trendSeries.value[cat];
      const values = points.map((p: any) => p[metric] ?? null);
      series.push({
        name: cat, type: "line", data: values, smooth: true,
        lineStyle: { width: 2, color: TREND_COLORS[i % TREND_COLORS.length] },
        itemStyle: { color: TREND_COLORS[i % TREND_COLORS.length] },
        symbol: "circle", symbolSize: 4, showSymbol: points.length < 30,
      });
    }
    trendChart.setOption({
      backgroundColor: "transparent", tooltip: { trigger: "axis" },
      legend: { bottom: 0, textStyle: { fontSize: 11 }, type: "scroll" },
      grid: { left: 60, right: 30, top: 20, bottom: 50 },
      xAxis: { type: "category", data: allDates, axisLabel: { color: "#94A3B8", fontSize: 10, rotate: allDates.length > 15 ? 30 : 0 } },
      yAxis: { type: "value", name: metricLabels[metric] || metric, axisLabel: { color: "#94A3B8", fontSize: 10 } },
      series,
    }, true);
  }

  watch(heatmapMode, () => { if (heatmapData.value.length > 0) renderHeatmapChart(); });
  watch(trendMetric, () => { if (trendSeries.value && Object.keys(trendSeries.value).length > 0) renderTrendChart(); });

  function handleResize() {
    heatmapChart?.resize();
    lifecycleChart?.resize();
    trendDistChart?.resize();
    priceBandChart?.resize();
    trendChart?.resize();
  }

  function init() {
    refreshAll();
    window.addEventListener("resize", handleResize);
  }

  function cleanup() {
    window.removeEventListener("resize", handleResize);
    heatmapChart?.dispose();
    lifecycleChart?.dispose();
    trendDistChart?.dispose();
    priceBandChart?.dispose();
    trendChart?.dispose();
    heatmapChart = null;
    lifecycleChart = null;
    trendDistChart = null;
    priceBandChart = null;
    trendChart = null;
  }

  return {
    selectedCategory, trendDays, trendMetric, heatmapMode, refreshing,
    heatmapData, heatmapLoading, patterns, patternsLoading,
    trendSeries, trendLoading, categoryStatsList,
    heatmapChartRef, lifecycleChartRef, trendDistChartRef, priceBandChartRef, trendChartRef,
    categoryList, categoryStats,
    formatNumber, heatLevel, lifecycleLabel, trendLabel, trendTagType, priceBandLabel,
    onCategoryChange, refreshAll, fetchTrendTimeseries,
    init, cleanup,
  };
}
