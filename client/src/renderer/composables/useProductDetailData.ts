import { ref, computed, reactive, nextTick, watch } from "vue";
import { useRoute } from "vue-router";
import { useProductStore } from "../stores/product";
import { useCollectStore } from "../stores/collect";
import { useAIStore } from "../stores/ai";
import { usePermissionStore } from "../stores/permission";
import { ElMessage } from "element-plus";
import * as echarts from "echarts";
import api from "../utils/api";
import type { MultiMetricDataPoint } from "../components/MultiMetricChart";

export function useProductDetailData() {
  const route = useRoute();
  const productStore = useProductStore();
  const collectStore = useCollectStore();
  const aiStore = useAIStore();
  const permissionStore = usePermissionStore();

  const ranking = ref<Record<string, any> | null>(null);
  const benchmark = ref<Record<string, any> | null>(null);
  const chartRange = ref(0);
  const radarChartRef = ref<HTMLDivElement>();
  let radarChart: echarts.ECharts | null = null;

  const metricVisible = reactive({
    price: true,
    sales: true,
    rating: false,
    review_count: false,
    favorite_count: false,
  });

  const selectedMetrics = computed(() => {
    return Object.entries(metricVisible)
      .filter(([, visible]) => visible)
      .map(([key]) => key);
  });

  const latestFeature = computed(() => {
    return productStore.features.length > 0 ? productStore.features[0] : null;
  });

  const priceChange = computed(() => {
    const features = productStore.features;
    if (features.length < 2 || features[0].price == null || features[1].price == null) return null;
    if (features[1].price === 0) return null;
    return ((features[0].price! - features[1].price!) / features[1].price!) * 100;
  });

  const salesChange = computed(() => {
    const features = productStore.features;
    if (features.length < 2 || features[0].sales_count == null || features[1].sales_count == null) return null;
    if (features[1].sales_count === 0) return null;
    return ((features[0].sales_count! - features[1].sales_count!) / features[1].sales_count!) * 100;
  });

  const radarData = computed(() => {
    if (!ranking.value) return null;
    return {
      indicators: [
        { name: "价格百分位", max: 100 },
        { name: "销量百分位", max: 100 },
        { name: "评分百分位", max: 100 },
      ],
      values: [
        ranking.value.price_percentile || 0,
        ranking.value.sales_percentile || 0,
        ranking.value.rating_percentile || 0,
      ],
    };
  });

  const chartData = computed<MultiMetricDataPoint[]>(() => {
    let features = productStore.features.slice();
    if (chartRange.value > 0) {
      const cutoff = new Date(Date.now() - chartRange.value * 24 * 60 * 60 * 1000);
      features = features.filter((f) => f.collected_at && new Date(f.collected_at) >= cutoff);
    }
    return features
      .slice()
      .reverse()
      .map((f) => ({
        date: f.collected_at ? formatDate(f.collected_at) : "",
        price: f.price,
        sales: f.sales_count,
        rating: f.rating,
        review_count: f.review_count,
        favorite_count: f.favorite_count,
      }));
  });

  const rankingGauges = computed(() => {
    if (!ranking.value) return [];
    return [
      { value: ranking.value.price_percentile, label: "价格百分位", color: "var(--color-danger)" },
      { value: ranking.value.sales_percentile, label: "销量百分位", color: "var(--color-primary)" },
      { value: ranking.value.rating_percentile, label: "评分百分位", color: "var(--color-warning)" },
    ];
  });

  function renderRadarChart() {
    if (!radarChartRef.value || !radarData.value) return;
    if (!radarChart) {
      radarChart = echarts.init(radarChartRef.value);
    }
    radarChart.setOption({
      tooltip: {},
      radar: {
        indicator: radarData.value.indicators,
        shape: "circle",
        splitNumber: 4,
        axisName: { color: "var(--color-text-secondary)", fontSize: 12 },
        splitArea: { areaStyle: { color: ["var(--color-bg-page)", "#fff", "var(--color-bg-page)", "#fff"] } },
      },
      series: [
        {
          type: "radar",
          data: [
            {
              value: radarData.value.values,
              name: "当前商品",
              areaStyle: { color: "rgba(79, 70, 229, 0.15)" },
              lineStyle: { color: "var(--color-primary)", width: 2 },
              itemStyle: { color: "var(--color-primary)" },
            },
          ],
        },
      ],
    });
  }

  function formatDate(dateStr: string): string {
    const d = new Date(dateStr);
    return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")}`;
  }

  function formatNumber(num: number): string {
    if (num >= 10000) return `${(num / 10000).toFixed(1)}万`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}k`;
    return String(num);
  }

  function formatAIResult(result: Record<string, unknown>): string {
    if (typeof result === "string") return result;
    if (result.result) return String(result.result);
    if (result.analysis) return String(result.analysis);
    return JSON.stringify(result, null, 2);
  }

  function analysisTypeLabel(type: string): string {
    const map: Record<string, string> = {
      basic_analysis: "基础分析", trend_score: "趋势评分", prediction: "爆品预测", risk_warning: "风险预警",
    };
    return map[type] || type;
  }

  function getPriceChangeClass(row: any): string {
    const idx = productStore.features.indexOf(row);
    if (idx < 0 || idx >= productStore.features.length - 1) return "";
    const prev = productStore.features[idx + 1];
    if (row.price == null || prev?.price == null) return "";
    return row.price > prev.price ? "price-up" : row.price < prev.price ? "price-down" : "";
  }

  function lifecycleTagType(stage: string): string {
    const map: Record<string, string> = {
      新品期: "warning", 成长期: "success", 成熟期: "info", 衰退期: "danger",
      new: "warning", growth: "success", rising: "success", stable: "info", mature: "info", declining: "danger", decline: "danger",
    };
    return map[stage] || "info";
  }

  function trendTagType(direction: string): string {
    const map: Record<string, string> = { 上升: "success", 下降: "danger", 平稳: "info", rising: "success", declining: "danger", stable: "info" };
    return map[direction] || "info";
  }

  function trendLabel(direction: string): string {
    const map: Record<string, string> = { 上升: "📈 上升趋势", 下降: "📉 下降趋势", 平稳: "➡️ 平稳", rising: "📈 上升趋势", declining: "📉 下降趋势", stable: "➡️ 平稳" };
    return map[direction] || direction;
  }

  function lifecycleLabel(stage: string): string {
    const map: Record<string, string> = {
      新品期: "新品期", 成长期: "成长期", 成熟期: "成熟期", 衰退期: "衰退期",
      new: "新品期", growth: "成长期", rising: "上升期", stable: "稳定期", mature: "成熟期", declining: "衰退期", decline: "衰退期",
    };
    return map[stage] || stage;
  }

  async function fetchRanking(productId: string) {
    try {
      const { data } = await api.get(`/feature/product-ranking/${productId}`);
      ranking.value = data?.ranking || null;
    } catch { ranking.value = null; }
  }

  async function fetchBenchmark(category: string, price?: number | null, salesCount?: number | null) {
    try {
      const params: Record<string, unknown> = { category };
      const results: Record<string, any> = {};
      if (price != null) {
        const { data } = await api.get("/feature/anonymous/price-benchmark", { params: { ...params, price } });
        if (data?.benchmark) Object.assign(results, data.benchmark);
      }
      if (salesCount != null) {
        const { data } = await api.get("/feature/anonymous/sales-benchmark", { params: { ...params, sales_count: salesCount } });
        if (data?.benchmark) Object.assign(results, data.benchmark);
      }
      benchmark.value = Object.keys(results).length > 0 ? results : null;
    } catch { benchmark.value = null; }
  }

  async function collectNow() {
    const p = productStore.currentProduct;
    if (!p) return;
    await collectStore.startCollect([{ targetId: p.platform_product_id, targetType: "goods" }]);
    ElMessage.success("采集任务已提交");
  }

  async function runAnalysis(type: string) {
    const productId = route.params.id as string;
    const result = await aiStore.analyzeProduct(productId, type);
    if (result) ElMessage.success("分析完成");
  }

  async function exportData() {
    try {
      const productId = route.params.id as string;
      const features = productStore.features;
      const csvHeader = "采集时间,价格,销量,评分,评论数,收藏数,来源\n";
      const csvRows = features
        .map((f) => `${f.collected_at},${f.price ?? ""},${f.sales_count ?? ""},${f.rating ?? ""},${f.review_count ?? ""},${f.favorite_count ?? ""},${f.source}`)
        .join("\n");
      const blob = new Blob([csvHeader + csvRows], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `product_${productId}_features.csv`;
      a.click();
      URL.revokeObjectURL(url);
      ElMessage.success("导出成功");
    } catch { ElMessage.error("导出失败"); }
  }

  function updateChartRange() {}

  watch(radarData, () => { nextTick(() => renderRadarChart()); });

  async function init() {
    const productId = route.params.id as string;
    await productStore.fetchProductDetail(productId);
    await productStore.fetchFeatures(productId);
    permissionStore.fetchPermissions();
    await fetchRanking(productId);
    const product = productStore.currentProduct;
    if (product?.category) {
      const latest = productStore.features[0];
      await fetchBenchmark(product.category, latest?.price, latest?.sales_count);
    }
    nextTick(() => renderRadarChart());
  }

  function cleanup() {
    radarChart?.dispose();
    radarChart = null;
  }

  return {
    route, productStore, collectStore, aiStore, permissionStore,
    ranking, benchmark, chartRange, radarChartRef, metricVisible,
    selectedMetrics, latestFeature, priceChange, salesChange,
    radarData, chartData, rankingGauges,
    renderRadarChart, formatDate, formatNumber, formatAIResult,
    analysisTypeLabel, getPriceChangeClass,
    lifecycleTagType, trendTagType, trendLabel, lifecycleLabel,
    collectNow, runAnalysis, exportData, updateChartRange,
    init, cleanup,
  };
}
