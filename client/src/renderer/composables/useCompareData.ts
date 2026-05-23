import { ref, computed, nextTick, watch } from "vue";
import * as echarts from "echarts";
import api, { isNetworkError } from "../utils/api";
import type { Product } from "@shared/types";

interface CompareItem {
  id?: string;
  product_id?: string;
  product_name?: string;
  title?: string;
  category?: string;
  price?: number;
  sales_count?: number;
  monthly_sales?: number;
  rating?: number;
  review_count?: number;
  favorite_count?: number;
  _ranking?: { percentile?: number; rank?: number; total?: number };
  _benchmark?: Record<string, { avg?: number; median?: number }>;
  [key: string]: unknown;
}

interface MetricComparison {
  best?: [string, number];
  worst?: [string, number];
  avg?: number;
}

interface CompareResult {
  items: CompareItem[];
  comparison?: Record<string, MetricComparison>;
  [key: string]: unknown;
}

const CHART_COLORS = ["#6366f1", "#f43f5e", "#10b981", "#f59e0b", "#8b5cf6", "#06b6d4", "#ec4899", "#14b8a6", "#a855f7", "#ef4444"];

export function useCompareData() {
  const showSelector = ref(false);
  const searchQuery = ref("");
  const allProducts = ref<Product[]>([]);
  const selectedProducts = ref<Product[]>([]);
  const compareData = ref<CompareResult | null>(null);
  const loading = ref(false);
  const cloudAvailable = ref(true);
  const viewMode = ref<"table" | "card">("table");
  const showBenchmarkLine = ref(true);
  const barMetric = ref("price");
  const trendMetric = ref("sales_count");
  const trendDays = ref(7);
  const radarChartRef = ref<HTMLElement>();
  const barChartRef = ref<HTMLElement>();
  const trendChartRef = ref<HTMLElement>();
  let radarChart: echarts.ECharts | null = null;
  let barChart: echarts.ECharts | null = null;
  let trendChart: echarts.ECharts | null = null;

  const metricLabels = [
    { key: "price", label: "价格" },
    { key: "sales_count", label: "销量" },
    { key: "monthly_sales", label: "月销" },
    { key: "rating", label: "评分" },
    { key: "review_count", label: "评论数" },
    { key: "favorite_count", label: "收藏数" },
  ];

  const barMetrics = [
    { key: "price", label: "价格" },
    { key: "sales_count", label: "销量" },
    { key: "rating", label: "评分" },
    { key: "favorite_count", label: "收藏" },
  ];

  const hasRankings = computed(() => compareData.value?.items?.some((i) => i._ranking));
  const hasBenchmark = computed(() => compareData.value?.items?.some((i) => i._benchmark));

  const filteredProducts = computed(() => {
    if (!searchQuery.value) return allProducts.value;
    const q = searchQuery.value.toLowerCase();
    return allProducts.value.filter((p) =>
      (p.product_name || "").toLowerCase().includes(q) ||
      (p.platform || "").toLowerCase().includes(q) ||
      (p.platform_product_id || "").toLowerCase().includes(q)
    );
  });

  function isSelected(id: string) { return selectedProducts.value.some((p) => p.id === id); }

  function toggleSelect(p: Product) {
    const idx = selectedProducts.value.findIndex((s) => s.id === p.id);
    if (idx !== -1) selectedProducts.value.splice(idx, 1);
    else if (selectedProducts.value.length < 10) selectedProducts.value.push(p);
  }

  function removeProduct(id: string) {
    const idx = selectedProducts.value.findIndex((p) => p.id === id);
    if (idx !== -1) {
      selectedProducts.value.splice(idx, 1);
      if (selectedProducts.value.length < 2) compareData.value = null;
      else runCompare();
    }
  }

  function resetCompare() {
    selectedProducts.value = [];
    compareData.value = null;
  }

  function formatNumber(n: number | null | undefined): string {
    if (n == null) return "-";
    if (n >= 10000) return (n / 10000).toFixed(1) + "w";
    if (n >= 1000) return (n / 1000).toFixed(1) + "k";
    return String(n);
  }

  async function fetchProducts() {
    try {
      const { data } = await api.get("/products", { params: { page: 1, page_size: 200 } });
      if (data?.items) {
        allProducts.value = data.items;
        cloudAvailable.value = true;
        return;
      }
    } catch (err) {
      if (isNetworkError(err)) cloudAvailable.value = false;
    }
    try {
      if (window.electronAPI) {
        const result = await window.electronAPI.invoke("products:list", { page: 1, pageSize: 200 }) as { data?: { items?: Product[] } } | null;
        allProducts.value = result?.data?.items || [];
      }
    } catch { allProducts.value = []; }
  }

  async function fetchRankings(): Promise<Record<string, any>> {
    try {
      const { data } = await api.get("/feature/product-rankings", { params: { limit: 200 } });
      if (data?.rankings) {
        const map: Record<string, any> = {};
        for (const r of data.rankings) map[r.product_id] = r;
        return map;
      }
    } catch (err) { console.warn("[Composable] operation failed:", err); }
    return {};
  }

  async function fetchBenchmark(category: string, price?: number, salesCount?: number): Promise<any> {
    if (!category) return null;
    const result: Record<string, any> = {};
    try {
      if (price != null) {
        const { data } = await api.get("/feature/anonymous/price-benchmark", { params: { category, price } });
        if (data?.benchmark) result.price = data.benchmark;
      }
    } catch (err) { console.warn("[Composable] operation failed:", err); }
    try {
      if (salesCount != null) {
        const { data } = await api.get("/feature/anonymous/sales-benchmark", { params: { category, sales_count: salesCount } });
        if (data?.benchmark) result.sales = data.benchmark;
      }
    } catch (err) { console.warn("[Composable] operation failed:", err); }
    return Object.keys(result).length > 0 ? result : null;
  }

  async function runCompare() {
    if (selectedProducts.value.length < 2) return;
    loading.value = true;
    showSelector.value = false;
    try {
      const ids = selectedProducts.value.map((p) => p.id);
      let result: any = null;
      if (cloudAvailable.value) {
        try {
          const { data } = await api.post("/products/compare", { product_ids: ids });
          if (data) result = { data };
        } catch { cloudAvailable.value = false; }
      }
      if (!result && window.electronAPI) {
        try {
          const localResult = await window.electronAPI.invoke("products:compare", { productIds: ids });
          result = localResult;
        } catch (err) { console.warn("[Composable] operation failed:", err); }
      }
      if (!result?.data) { loading.value = false; return; }

      compareData.value = result.data;
      const rankingMap = await fetchRankings();
      const categories = new Set<string>();
      for (const item of (compareData.value?.items || [])) {
        const productId = item.id || item.product_id;
        if (productId && rankingMap[productId]) item._ranking = rankingMap[productId];
        if (item.category) categories.add(item.category);
      }
      if (categories.size > 0 && cloudAvailable.value) {
        for (const item of (compareData.value?.items || [])) {
          const cat = item.category || [...categories][0];
          const benchmark = await fetchBenchmark(cat, item.price, item.sales_count);
          if (benchmark) item._benchmark = benchmark;
        }
      }

      await nextTick();
      renderRadarChart();
      renderBarChart();
      renderTrendChart();
    } catch (err) { console.warn("[Composable] operation failed:", err); }
    loading.value = false;
  }

  function getMetricClass(metric: string, value: number | null | undefined) {
    if (!compareData.value?.comparison?.[metric] || value == null) return "";
    const comp = compareData.value.comparison[metric];
    if (comp.best && comp.best[1] === value) return "metric-best";
    if (comp.worst && comp.worst[1] === value) return "metric-worst";
    return "";
  }

  function renderRadarChart() {
    if (!radarChartRef.value || !compareData.value) return;
    if (!radarChart) radarChart = echarts.init(radarChartRef.value);
    const items = compareData.value.items;
    const indicators = [
      { name: "价格", max: 0 }, { name: "销量", max: 0 }, { name: "月销", max: 0 },
      { name: "评分", max: 5 }, { name: "评论", max: 0 }, { name: "收藏", max: 0 },
    ];
    for (const item of items) {
      if (item.price && item.price > indicators[0].max) indicators[0].max = item.price;
      if (item.sales_count && item.sales_count > indicators[1].max) indicators[1].max = item.sales_count;
      if (item.monthly_sales && item.monthly_sales > indicators[2].max) indicators[2].max = item.monthly_sales;
      if (item.review_count && item.review_count > indicators[4].max) indicators[4].max = item.review_count;
      if (item.favorite_count && item.favorite_count > indicators[5].max) indicators[5].max = item.favorite_count;
    }
    for (const ind of indicators) { if (ind.max === 0) ind.max = 1; }
    const series: Array<Record<string, unknown>> = items.map((item, i) => ({
      value: [item.price ?? 0, item.sales_count ?? 0, item.monthly_sales ?? 0, item.rating ?? 0, item.review_count ?? 0, item.favorite_count ?? 0],
      name: (item.product_name || "").substring(0, 15) || `商品${i + 1}`,
      lineStyle: { color: CHART_COLORS[i % CHART_COLORS.length] },
      areaStyle: { color: CHART_COLORS[i % CHART_COLORS.length], opacity: 0.1 },
      itemStyle: { color: CHART_COLORS[i % CHART_COLORS.length] },
    }));
    if (showBenchmarkLine.value && hasBenchmark.value) {
      const benchmarkValues = [0, 1, 2, 4, 5].map((idx) => {
        const keys = ["price", "sales_count", "monthly_sales", "review_count", "favorite_count"];
        const key = keys[idx];
        let sum = 0, count = 0;
        for (const item of items) {
          const bKey = key === "price" ? "price" : key === "sales_count" ? "sales" : "";
          if (bKey && item._benchmark?.[bKey]?.avg) { sum += item._benchmark[bKey].avg; count++; }
        }
        return count > 0 ? sum / count : 0;
      });
      const ratingBench = items.reduce((s, i) => s + (i._benchmark?.rating?.avg || 0), 0) / (items.filter((i) => i._benchmark?.rating?.avg).length || 1);
      benchmarkValues.splice(3, 0, ratingBench);
      if (benchmarkValues.some((v) => v > 0)) {
        series.push({
          value: benchmarkValues, name: "品类均值",
          lineStyle: { color: "#94a3b8", width: 2 },
          areaStyle: { color: "#94a3b8", opacity: 0.05 },
          itemStyle: { color: "#94a3b8" }, symbol: "diamond", symbolSize: 6,
        });
      }
    }
    radarChart.setOption({
      backgroundColor: "transparent",
      legend: { bottom: 0, textStyle: { fontSize: 12 } },
      radar: { indicator: indicators, radius: "65%" },
      series: [{ type: "radar", data: series }],
    }, true);
  }

  function renderBarChart() {
    if (!barChartRef.value || !compareData.value) return;
    if (!barChart) barChart = echarts.init(barChartRef.value);
    const items = compareData.value.items;
    const metric = barMetric.value;
    const metricKey = metric as string;
    const names = items.map((item: any, i: number) => (item.product_name || "").substring(0, 12) || `商品${i + 1}`);
    const values = items.map((item: any) => item[metricKey] ?? 0);
    const seriesData: any[] = [{
      name: metricLabels.find((m) => m.key === metric)?.label || metric,
      type: "bar", data: values,
      itemStyle: { color: (params: any) => CHART_COLORS[params.dataIndex % CHART_COLORS.length], borderRadius: [4, 4, 0, 0] },
      barMaxWidth: 48,
      label: {
        show: true, position: "top", fontSize: 12,
        formatter: (params: any) => {
          const v = params.value;
          if (metricKey === "price") return `¥${v}`;
          if (v >= 10000) return `${(v / 10000).toFixed(1)}w`;
          return String(v);
        },
      },
    }];
    const benchmarkValues: (number | null)[] = items.map((item: any) => {
      const bKey = metricKey === "price" ? "price" : metricKey === "sales_count" ? "sales" : metricKey === "rating" ? "rating" : "";
      return item._benchmark?.[bKey]?.avg ?? null;
    });
    if (benchmarkValues.some((v) => v !== null)) {
      seriesData.push({
        name: "品类均值", type: "line", data: benchmarkValues,
        lineStyle: { color: "#94a3b8", type: "dashed", width: 2 },
        itemStyle: { color: "#94a3b8" }, symbol: "diamond", symbolSize: 8,
        label: {
          show: true, position: "top", fontSize: 11, color: "#94a3b8",
          formatter: (params: any) => params.value != null ? `均值${metricKey === "price" ? "¥" : ""}${metricKey === "price" ? params.value?.toFixed(0) : params.value >= 10000 ? (params.value / 10000).toFixed(1) + "w" : params.value?.toFixed(1)}` : "",
        },
      });
    }
    barChart.setOption({
      backgroundColor: "transparent",
      tooltip: { trigger: "axis" },
      legend: { bottom: 0, textStyle: { fontSize: 12 } },
      grid: { left: 60, right: 30, top: 30, bottom: 50 },
      xAxis: { type: "category", data: names, axisLabel: { fontSize: 11, rotate: names.some((n: string) => n.length > 6) ? 30 : 0 } },
      yAxis: { type: "value", axisLabel: { fontSize: 11 } },
      series: seriesData,
    }, true);
  }

  async function renderTrendChart() {
    if (!trendChartRef.value || !compareData.value) return;
    if (!trendChart) trendChart = echarts.init(trendChartRef.value);

    const ids = compareData.value.items.map((item) => item.id || item.product_id).filter(Boolean) as string[];
    if (ids.length < 2) return;

    try {
      const { data } = await api.post("/products/compare-trends", null, {
        params: { product_ids: ids, days: trendDays.value },
      });

      if (!data?.series) { trendChart.setOption({ title: { text: "暂无趋势数据", left: "center", top: "center", textStyle: { fontSize: 14, color: "#94a3b8" } } }, true); return; }

      const metricKey = trendMetric.value;
      const metricLabel = metricLabels.find((m) => m.key === metricKey)?.label || metricKey;
      const seriesData = data.series.map((s: any, i: number) => ({
        name: (s.product_name || "").substring(0, 15) || `商品${i + 1}`,
        type: "line",
        data: s.data.map((d: any) => [d.collected_at, d[metricKey]]),
        smooth: true,
        symbol: "circle",
        symbolSize: 4,
        lineStyle: { width: 2, color: CHART_COLORS[i % CHART_COLORS.length] },
        itemStyle: { color: CHART_COLORS[i % CHART_COLORS.length] },
      }));

      trendChart.setOption({
        backgroundColor: "transparent",
        tooltip: {
          trigger: "axis",
          formatter: (params: any) => {
            let html = `<div style="font-size:12px;color:#666">${new Date(params[0].value[0]).toLocaleDateString()}</div>`;
            for (const p of params) {
              const v = p.value[1];
              html += `<div style="display:flex;align-items:center;gap:6px;margin-top:4px">
                <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color}"></span>
                <span style="flex:1">${p.seriesName}</span>
                <span style="font-weight:600">${metricKey === "price" ? "¥" : ""}${v != null ? (v >= 10000 ? (v / 10000).toFixed(1) + "w" : v) : "-"}</span>
              </div>`;
            }
            return html;
          },
        },
        legend: { bottom: 0, textStyle: { fontSize: 12 } },
        grid: { left: 60, right: 30, top: 30, bottom: 50 },
        xAxis: { type: "time", axisLabel: { fontSize: 11, formatter: "{M}/{d}" } },
        yAxis: { type: "value", name: metricLabel, axisLabel: { fontSize: 11, formatter: (v: number) => v >= 10000 ? (v / 10000).toFixed(1) + "w" : String(v) } },
        series: seriesData,
      }, true);
    } catch (err) {
      console.warn("[Composable] trend chart failed:", err);
      trendChart.setOption({ title: { text: "趋势数据加载失败", left: "center", top: "center", textStyle: { fontSize: 14, color: "#94a3b8" } } }, true);
    }
  }

  watch(showBenchmarkLine, () => { if (compareData.value) renderRadarChart(); });
  watch(barMetric, () => { if (compareData.value) renderBarChart(); });
  watch([trendMetric, trendDays], () => { if (compareData.value) renderTrendChart(); });

  function init() { fetchProducts(); }

  function cleanup() {
    radarChart?.dispose();
    barChart?.dispose();
    trendChart?.dispose();
    radarChart = null;
    barChart = null;
    trendChart = null;
  }

  return {
    showSelector, searchQuery, allProducts, selectedProducts, compareData,
    loading, cloudAvailable, viewMode, showBenchmarkLine, barMetric,
    trendMetric, trendDays,
    radarChartRef, barChartRef, trendChartRef,
    metricLabels, barMetrics, hasRankings, hasBenchmark, filteredProducts,
    isSelected, toggleSelect, removeProduct, resetCompare, formatNumber,
    runCompare, getMetricClass, renderRadarChart, renderBarChart, renderTrendChart,
    init, cleanup,
  };
}
