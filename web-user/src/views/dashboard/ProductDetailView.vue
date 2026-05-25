<template>
  <div class="product-detail-page">
    <div class="page-header">
      <el-button :icon="ArrowLeft" @click="$router.back()" text>返回</el-button>
      <h2 v-if="product">{{ product.product_name }}</h2>
      <el-skeleton v-else :rows="1" animated style="width: 200px" />
    </div>

    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="8" animated />
    </div>

    <template v-else-if="product">
      <el-row :gutter="20">
        <el-col :span="16">
          <el-card shadow="never" class="info-card">
            <template #header><span>基本信息</span></template>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="平台">
                <el-tag size="small">{{ platformLabel(product.platform) }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="商品ID">{{ product.platform_product_id }}</el-descriptions-item>
              <el-descriptions-item label="价格">
                <span class="price-value">¥{{ latestFeature?.price ?? "-" }}</span>
              </el-descriptions-item>
              <el-descriptions-item label="月销量">{{ latestFeature?.monthly_sales ?? "-" }}</el-descriptions-item>
              <el-descriptions-item label="评分">{{ latestFeature?.rating ?? "-" }}</el-descriptions-item>
              <el-descriptions-item label="评论数">{{ latestFeature?.review_count ?? "-" }}</el-descriptions-item>
              <el-descriptions-item label="收藏数">{{ latestFeature?.favorite_count ?? "-" }}</el-descriptions-item>
              <el-descriptions-item label="最后采集">{{ formatTime(product.last_collected_at) }}</el-descriptions-item>
            </el-descriptions>
          </el-card>

          <el-card shadow="never" class="chart-card" style="margin-top: 16px">
            <template #header>
              <div class="card-header">
                <span>价格趋势</span>
                <el-radio-group v-model="trendRange" size="small">
                  <el-radio-button value="7d">7天</el-radio-button>
                  <el-radio-button value="30d">30天</el-radio-button>
                  <el-radio-button value="90d">90天</el-radio-button>
                </el-radio-group>
              </div>
            </template>
            <div ref="priceChartRef" class="chart-container"></div>
          </el-card>

          <el-card shadow="never" class="chart-card" style="margin-top: 16px">
            <template #header><span>销量趋势</span></template>
            <div ref="salesChartRef" class="chart-container"></div>
          </el-card>
        </el-col>

        <el-col :span="8">
          <el-card shadow="never" class="rank-card">
            <template #header><span>排名百分位</span></template>
            <div v-if="latestFeature" class="rank-gauges">
              <div class="rank-item">
                <span class="rank-label">价格竞争力</span>
                <el-progress :percentage="latestFeature.price_percentile || 0" :stroke-width="12" :color="getPercentileColor(latestFeature.price_percentile)" />
              </div>
              <div class="rank-item">
                <span class="rank-label">销量排名</span>
                <el-progress :percentage="latestFeature.sales_percentile || 0" :stroke-width="12" :color="getPercentileColor(latestFeature.sales_percentile)" />
              </div>
              <div class="rank-item">
                <span class="rank-label">评分排名</span>
                <el-progress :percentage="latestFeature.rating_percentile || 0" :stroke-width="12" :color="getPercentileColor(latestFeature.rating_percentile)" />
              </div>
            </div>
            <div v-else class="empty-hint">暂无排名数据</div>
          </el-card>

          <el-card shadow="never" class="benchmark-card" style="margin-top: 16px">
            <template #header><span>类目基准对比</span></template>
            <div ref="radarChartRef" class="chart-container-sm"></div>
          </el-card>

          <el-card shadow="never" class="growth-card" style="margin-top: 16px">
            <template #header><span>24小时增长</span></template>
            <div v-if="growth24h" class="growth-items">
              <div v-for="(val, key) in growth24h" :key="key" class="growth-item">
                <span class="growth-label">{{ growthLabel(key as string) }}</span>
                <span :class="['growth-value', val.change > 0 ? 'growth-up' : val.change < 0 ? 'growth-down' : 'growth-flat']">
                  {{ val.change > 0 ? '+' : '' }}{{ val.change }}
                  <small v-if="val.change_pct != null">({{ val.change_pct > 0 ? '+' : '' }}{{ val.change_pct }}%)</small>
                </span>
              </div>
            </div>
            <div v-else class="empty-hint">暂无24小时增长数据</div>
          </el-card>

          <el-card shadow="never" class="ai-card" style="margin-top: 16px">
            <template #header>
              <div class="card-header">
                <span>AI 分析</span>
                <el-button type="primary" size="small" @click="requestAnalysis" :loading="aiLoading">生成分析</el-button>
              </div>
            </template>
            <div v-if="aiResult" class="ai-result">
              <div class="ai-section" v-html="formatAIResult(aiResult)"></div>
            </div>
            <div v-else class="empty-hint">点击"生成分析"获取 AI 洞察</div>
          </el-card>
        </el-col>
      </el-row>
    </template>

    <el-empty v-else description="商品不存在" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch, nextTick } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { ArrowLeft } from "@element-plus/icons-vue";
import * as echarts from "echarts/core";
import { LineChart, RadarChart, BarChart } from "echarts/charts";
import { GridComponent, TooltipComponent, LegendComponent, RadarComponent, GraphicComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([LineChart, RadarChart, BarChart, GridComponent, TooltipComponent, LegendComponent, RadarComponent, GraphicComponent, CanvasRenderer]);
import api from "../../utils/api";

const route = useRoute();
const productId = ref(route.params.id as string);

const product = ref<any>(null);
const features = ref<any[]>([]);
const latestFeature = ref<any>(null);
const loading = ref(true);
const trendRange = ref("30d");
const aiResult = ref("");
const aiLoading = ref(false);
const growth24h = ref<Record<string, { old_value: number; new_value: number; change: number; change_pct: number | null }> | null>(null);

const priceChartRef = ref<HTMLElement>();
const salesChartRef = ref<HTMLElement>();
const radarChartRef = ref<HTMLElement>();
let priceChart: echarts.ECharts | null = null;
let salesChart: echarts.ECharts | null = null;
let radarChart: echarts.ECharts | null = null;

function platformLabel(p: string) {
  const map: Record<string, string> = { xhs: "小红书", douyin: "抖音", taobao: "淘宝", jd: "京东", pdd: "拼多多" };
  return map[p] || p;
}

function formatTime(dateStr: string) {
  if (!dateStr) return "-";
  return new Date(dateStr).toLocaleString("zh-CN");
}

function getPercentileColor(val?: number) {
  if (!val) return "#6366f1";
  if (val >= 80) return "#22c55e";
  if (val >= 50) return "#f97316";
  return "#ef4444";
}

function formatAIResult(text: string) {
  const escaped = text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  return escaped.replace(/\n/g, "<br/>").replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
}

function growthLabel(key: string) {
  const map: Record<string, string> = { price: "价格", sales_count: "销量", monthly_sales: "月销", review_count: "评论", favorite_count: "收藏" };
  return map[key] || key;
}

async function fetchProduct() {
  loading.value = true;
  try {
    const [prodRes, featRes, growthRes] = await Promise.all([
      api.get(`/products/${productId.value}`),
      api.get(`/products/${productId.value}/features`, { params: { limit: 90 } }),
      api.get(`/products/${productId.value}/growth-24h`).catch(() => null),
    ]);
    product.value = prodRes.data?.data;
    features.value = featRes.data?.data?.items || featRes.data?.data || [];
    if (features.value.length > 0) {
      latestFeature.value = features.value[features.value.length - 1];
    }
    if (growthRes?.data?.data?.growth) {
      growth24h.value = growthRes.data.data.growth;
    }
  } catch {
    product.value = null;
  } finally {
    loading.value = false;
  }
}

function detectAnomalies(values: (number | null)[]): { coord: [number, number]; value: number }[] {
  const valid = values.filter((v): v is number => v != null);
  if (valid.length < 3) return [];
  const mean = valid.reduce((a, b) => a + b, 0) / valid.length;
  const std = Math.sqrt(valid.reduce((a, b) => a + (b - mean) ** 2, 0) / valid.length);
  const threshold = mean + 2 * std;
  const lowerThreshold = mean - 2 * std;
  return values
    .map((v, i) => (v != null && (v > threshold || v < lowerThreshold) ? { coord: [i, v], value: v } : null))
    .filter((x): x is { coord: [number, number]; value: number } => x != null);
}

function renderPriceChart() {
  if (!priceChartRef.value || features.value.length === 0) return;
  if (!priceChart) priceChart = echarts.init(priceChartRef.value);
  const data = features.value.map((f) => [new Date(f.collected_at).getTime(), f.price]);
  const priceValues = features.value.map((f) => f.price);
  const anomalies = detectAnomalies(priceValues);
  const anomalyData = anomalies.map((a) => {
    const f = features.value[a.coord[0]];
    return f ? { coord: [new Date(f.collected_at).getTime(), a.value], value: a.value } : null;
  }).filter(Boolean);

  priceChart.setOption({
    backgroundColor: "transparent",
    grid: { top: 20, right: 20, bottom: 30, left: 60 },
    xAxis: { type: "time", axisLabel: { color: "#8a8a9a", fontSize: 11 }, axisLine: { lineStyle: { color: "rgba(255,255,255,0.06)" } } },
    yAxis: { type: "value", axisLabel: { color: "#8a8a9a", fontSize: 11, formatter: "¥{value}" }, splitLine: { lineStyle: { color: "rgba(255,255,255,0.04)" } } },
    series: [{
      type: "line",
      data,
      smooth: true,
      lineStyle: { color: "#6366f1", width: 2 },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: "rgba(99,102,241,0.3)" }, { offset: 1, color: "rgba(99,102,241,0)" }]) },
      itemStyle: { color: "#6366f1" },
      symbol: "none",
      markPoint: anomalyData.length > 0 ? {
        data: anomalyData.map((d: any) => ({ coord: d.coord, value: d.value, symbol: "circle", symbolSize: 10, itemStyle: { color: "#ef4444" } })),
        label: { show: false },
      } : undefined,
    }],
    tooltip: { trigger: "axis", backgroundColor: "#1a1a24", borderColor: "rgba(255,255,255,0.1)", textStyle: { color: "#e0e0e6" } },
  });
}

function renderSalesChart() {
  if (!salesChartRef.value || features.value.length === 0) return;
  if (!salesChart) salesChart = echarts.init(salesChartRef.value);
  const data = features.value.map((f) => [new Date(f.collected_at).getTime(), f.monthly_sales]);
  salesChart.setOption({
    backgroundColor: "transparent",
    grid: { top: 20, right: 20, bottom: 30, left: 60 },
    xAxis: { type: "time", axisLabel: { color: "#8a8a9a", fontSize: 11 }, axisLine: { lineStyle: { color: "rgba(255,255,255,0.06)" } } },
    yAxis: { type: "value", axisLabel: { color: "#8a8a9a", fontSize: 11 }, splitLine: { lineStyle: { color: "rgba(255,255,255,0.04)" } } },
    series: [{ type: "bar", data, itemStyle: { color: "#8b5cf6", borderRadius: [4, 4, 0, 0] } }],
    tooltip: { trigger: "axis", backgroundColor: "#1a1a24", borderColor: "rgba(255,255,255,0.1)", textStyle: { color: "#e0e0e6" } },
  });
}

function renderRadarChart() {
  if (!radarChartRef.value || !latestFeature.value) return;
  if (!radarChart) radarChart = echarts.init(radarChartRef.value);
  const f = latestFeature.value;
  radarChart.setOption({
    backgroundColor: "transparent",
    radar: {
      indicator: [
        { name: "价格", max: 100 },
        { name: "销量", max: 100 },
        { name: "评分", max: 100 },
        { name: "评论", max: 100 },
        { name: "收藏", max: 100 },
      ],
      axisName: { color: "#8a8a9a", fontSize: 11 },
      splitArea: { areaStyle: { color: ["rgba(255,255,255,0.02)", "rgba(255,255,255,0.04)"] } },
      splitLine: { lineStyle: { color: "rgba(255,255,255,0.06)" } },
      axisLine: { lineStyle: { color: "rgba(255,255,255,0.06)" } },
    },
    series: [{
      type: "radar",
      data: [
        { value: [f.price_percentile || 0, f.sales_percentile || 0, f.rating_percentile || 0, f.review_percentile || 0, f.favorite_percentile || 0], name: "当前商品", areaStyle: { color: "rgba(99,102,241,0.2)" }, lineStyle: { color: "#6366f1" }, itemStyle: { color: "#6366f1" } },
        { value: [50, 50, 50, 50, 50], name: "类目平均", areaStyle: { color: "rgba(255,255,255,0.05)" }, lineStyle: { color: "#5a5a6a", type: "dashed" }, itemStyle: { color: "#5a5a6a" } },
      ],
    }],
    legend: { bottom: 0, textStyle: { color: "#8a8a9a", fontSize: 11 } },
  });
}

async function requestAnalysis() {
  aiLoading.value = true;
  try {
    const { data } = await api.post("/ai/analyze", {
      product_id: productId.value,
      analysis_type: "basic_analysis",
    });
    aiResult.value = data?.data?.result || data?.data?.content || JSON.stringify(data?.data || {});
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || "AI 分析请求失败");
  } finally {
    aiLoading.value = false;
  }
}

watch(trendRange, () => {
  const days = trendRange.value === "7d" ? 7 : trendRange.value === "90d" ? 90 : 30;
  const cutoff = Date.now() - days * 86400000;
  features.value = features.value.filter((f) => new Date(f.collected_at).getTime() >= cutoff);
  nextTick(() => {
    renderPriceChart();
    renderSalesChart();
  });
});

onMounted(async () => {
  await fetchProduct();
  await nextTick();
  renderPriceChart();
  renderSalesChart();
  renderRadarChart();

  window.addEventListener("resize", () => {
    priceChart?.resize();
    salesChart?.resize();
    radarChart?.resize();
  });
});
</script>

<style scoped>
.product-detail-page {
  padding: 0;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.page-header h2 {
  color: #e0e0e6;
  font-size: 20px;
  margin: 0;
}

.loading-state {
  padding: 20px 0;
}

.info-card,
.chart-card,
.rank-card,
.benchmark-card,
.ai-card {
  background: #1a1a24;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.info-card :deep(.el-card__header),
.chart-card :deep(.el-card__header),
.rank-card :deep(.el-card__header),
.benchmark-card :deep(.el-card__header),
.ai-card :deep(.el-card__header) {
  border-bottom-color: rgba(255, 255, 255, 0.06);
  color: #e0e0e6;
}

.info-card :deep(.el-descriptions) {
  --el-descriptions-table-border: rgba(255, 255, 255, 0.06);
}

.info-card :deep(.el-descriptions__label) {
  color: #8a8a9a;
  background: rgba(255, 255, 255, 0.02);
}

.info-card :deep(.el-descriptions__content) {
  color: #e0e0e6;
}

.price-value {
  color: #f97316;
  font-weight: 600;
  font-size: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart-container {
  height: 280px;
}

.chart-container-sm {
  height: 220px;
}

.rank-gauges {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.rank-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.rank-label {
  color: #8a8a9a;
  font-size: 13px;
}

.empty-hint {
  color: #6a6a7a;
  font-size: 13px;
  text-align: center;
  padding: 20px 0;
}

.growth-items {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.growth-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.growth-item:last-child {
  border-bottom: none;
}

.growth-label {
  color: #8a8a9a;
  font-size: 13px;
}

.growth-value {
  font-size: 14px;
  font-weight: 600;
}

.growth-value small {
  font-weight: 400;
  font-size: 11px;
  margin-left: 4px;
}

.growth-up { color: #ef4444; }
.growth-down { color: #22c55e; }
.growth-flat { color: #8a8a9a; }

.ai-result {
  color: #c0c0cc;
  font-size: 13px;
  line-height: 1.8;
}

.ai-result :deep(strong) {
  color: #a5b4fc;
}
</style>
