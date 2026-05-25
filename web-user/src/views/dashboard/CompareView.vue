<template>
  <div class="compare-view">
    <div class="compare-header">
      <h2>商品对比</h2>
      <p class="compare-desc">选择多个商品进行趋势对比分析</p>
    </div>

    <div class="compare-selector">
      <el-select
        v-model="selectedIds"
        multiple
        filterable
        placeholder="选择要对比的商品（2-5个）"
        style="width: 100%; max-width: 600px"
        :max-collapse-tags="3"
      >
        <el-option v-for="p in products" :key="p.id" :label="`${p.product_name} (${p.platform})`" :value="p.id" />
      </el-select>
      <el-select v-model="trendDays" style="width: 120px; margin-left: 12px">
        <el-option :value="7" label="近7天" />
        <el-option :value="14" label="近14天" />
        <el-option :value="30" label="近30天" />
      </el-select>
      <el-button type="primary" :disabled="selectedIds.length < 2" @click="doCompare" style="margin-left: 12px">
        开始对比
      </el-button>
    </div>

    <div v-if="loading" style="text-align: center; padding: 60px; color: #6a6a7a;">
      加载中...
    </div>

    <div v-else-if="compareData.length > 0" class="compare-content">
      <el-card shadow="never" class="compare-card">
        <template #header>
          <span>价格趋势对比</span>
        </template>
        <div ref="priceCompareRef" style="height: 320px" />
      </el-card>

      <el-card shadow="never" class="compare-card" style="margin-top: 16px">
        <template #header>
          <span>销量趋势对比</span>
        </template>
        <div ref="salesCompareRef" style="height: 320px" />
      </el-card>

      <el-card shadow="never" class="compare-card" style="margin-top: 16px">
        <template #header>
          <span>评论数趋势对比</span>
        </template>
        <div ref="reviewCompareRef" style="height: 320px" />
      </el-card>

      <el-card shadow="never" class="compare-card" style="margin-top: 16px">
        <template #header>
          <span>指标概览</span>
        </template>
        <el-table :data="compareData" style="width: 100%">
          <el-table-column prop="product_name" label="商品名称" min-width="180" />
          <el-table-column prop="platform" label="平台" width="100">
            <template #default="{ row }">{{ platformLabel(row.platform) }}</template>
          </el-table-column>
          <el-table-column label="最新价格" width="120">
            <template #default="{ row }">{{ row.latest_feature?.price ? `¥${row.latest_feature.price}` : '-' }}</template>
          </el-table-column>
          <el-table-column label="最新销量" width="120">
            <template #default="{ row }">{{ row.latest_feature?.sales_count ?? '-' }}</template>
          </el-table-column>
          <el-table-column label="评分" width="100">
            <template #default="{ row }">{{ row.latest_feature?.rating ?? '-' }}</template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <div v-else class="empty-state">
      <div class="empty-icon">⚖️</div>
      <p>选择至少 2 个商品开始对比</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from "vue";
import { ElMessage } from "element-plus";
import * as echarts from "echarts/core";
import { LineChart, BarChart } from "echarts/charts";
import { GridComponent, TooltipComponent, LegendComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer]);
import api from "../../utils/api";

const products = ref<any[]>([]);
const selectedIds = ref<string[]>([]);
const compareData = ref<any[]>([]);
const trendSeries = ref<any[]>([]);
const loading = ref(false);
const trendDays = ref(7);
const priceCompareRef = ref<HTMLElement>();
const salesCompareRef = ref<HTMLElement>();
const reviewCompareRef = ref<HTMLElement>();
let priceChart: echarts.ECharts | null = null;
let salesChart: echarts.ECharts | null = null;
let reviewChart: echarts.ECharts | null = null;

const COLORS = ["#6366f1", "#f472b6", "#22c55e", "#eab308", "#06b6d4"];

function platformLabel(p: string) {
  const map: Record<string, string> = { xhs: "小红书", taobao: "淘宝", jd: "京东", pdd: "拼多多", douyin: "抖音" };
  return map[p] || p;
}

async function fetchProducts() {
  try {
    const { data } = await api.get("/products", { params: { page_size: 100 } });
    products.value = data?.data?.items || [];
  } catch {}
}

async function doCompare() {
  if (selectedIds.value.length < 2) return;
  loading.value = true;
  try {
    const ids = selectedIds.value.join(",");
    const [compareRes, trendRes] = await Promise.all([
      api.get("/products/compare", { params: { product_ids: ids } }),
      api.post("/products/compare-trends", null, { params: { product_ids: ids, days: trendDays.value } }),
    ]);
    compareData.value = compareRes.data?.data?.items || [];
    trendSeries.value = trendRes.data?.data?.series || [];
    await nextTick();
    renderCharts();
  } catch {
    ElMessage.error("对比加载失败，请检查权限");
  } finally {
    loading.value = false;
  }
}

function renderCharts() {
  renderPriceCompare();
  renderSalesCompare();
  renderReviewCompare();
}

function renderPriceCompare() {
  if (!priceCompareRef.value || trendSeries.value.length === 0) return;
  if (!priceChart) priceChart = echarts.init(priceCompareRef.value);

  const series = trendSeries.value.map((s, i) => ({
    name: s.product_name,
    type: "line" as const,
    data: (s.data || []).map((d: any) => [new Date(d.collected_at).getTime(), d.price]),
    smooth: true,
    lineStyle: { color: COLORS[i % COLORS.length], width: 2 },
    itemStyle: { color: COLORS[i % COLORS.length] },
    symbol: "none",
  }));

  priceChart.setOption({
    backgroundColor: "transparent",
    legend: { textStyle: { color: "#8a8a9a" }, top: 0 },
    grid: { top: 40, right: 20, bottom: 30, left: 60 },
    xAxis: { type: "time", axisLabel: { color: "#8a8a9a" }, axisLine: { lineStyle: { color: "rgba(255,255,255,0.06)" } } },
    yAxis: { type: "value", axisLabel: { color: "#8a8a9a", formatter: "¥{value}" }, splitLine: { lineStyle: { color: "rgba(255,255,255,0.04)" } } },
    series,
    tooltip: { trigger: "axis", backgroundColor: "#1a1a24", borderColor: "rgba(255,255,255,0.1)", textStyle: { color: "#e0e0e6" } },
  }, true);
}

function renderSalesCompare() {
  if (!salesCompareRef.value || trendSeries.value.length === 0) return;
  if (!salesChart) salesChart = echarts.init(salesCompareRef.value);

  const series = trendSeries.value.map((s, i) => ({
    name: s.product_name,
    type: "line" as const,
    data: (s.data || []).map((d: any) => [new Date(d.collected_at).getTime(), d.sales_count]),
    smooth: true,
    lineStyle: { color: COLORS[i % COLORS.length], width: 2 },
    itemStyle: { color: COLORS[i % COLORS.length] },
    symbol: "none",
  }));

  salesChart.setOption({
    backgroundColor: "transparent",
    legend: { textStyle: { color: "#8a8a9a" }, top: 0 },
    grid: { top: 40, right: 20, bottom: 30, left: 60 },
    xAxis: { type: "time", axisLabel: { color: "#8a8a9a" }, axisLine: { lineStyle: { color: "rgba(255,255,255,0.06)" } } },
    yAxis: { type: "value", axisLabel: { color: "#8a8a9a" }, splitLine: { lineStyle: { color: "rgba(255,255,255,0.04)" } } },
    series,
    tooltip: { trigger: "axis", backgroundColor: "#1a1a24", borderColor: "rgba(255,255,255,0.1)", textStyle: { color: "#e0e0e6" } },
  }, true);
}

function renderReviewCompare() {
  if (!reviewCompareRef.value || trendSeries.value.length === 0) return;
  if (!reviewChart) reviewChart = echarts.init(reviewCompareRef.value);

  const series = trendSeries.value.map((s, i) => ({
    name: s.product_name,
    type: "line" as const,
    data: (s.data || []).map((d: any) => [new Date(d.collected_at).getTime(), d.review_count]),
    smooth: true,
    lineStyle: { color: COLORS[i % COLORS.length], width: 2 },
    itemStyle: { color: COLORS[i % COLORS.length] },
    symbol: "none",
  }));

  reviewChart.setOption({
    backgroundColor: "transparent",
    legend: { textStyle: { color: "#8a8a9a" }, top: 0 },
    grid: { top: 40, right: 20, bottom: 30, left: 60 },
    xAxis: { type: "time", axisLabel: { color: "#8a8a9a" }, axisLine: { lineStyle: { color: "rgba(255,255,255,0.06)" } } },
    yAxis: { type: "value", axisLabel: { color: "#8a8a9a" }, splitLine: { lineStyle: { color: "rgba(255,255,255,0.04)" } } },
    series,
    tooltip: { trigger: "axis", backgroundColor: "#1a1a24", borderColor: "rgba(255,255,255,0.1)", textStyle: { color: "#e0e0e6" } },
  }, true);
}

const handleResize = () => {
  priceChart?.resize();
  salesChart?.resize();
  reviewChart?.resize();
};

onMounted(() => {
  fetchProducts();
  window.addEventListener("resize", handleResize);
});

onUnmounted(() => {
  window.removeEventListener("resize", handleResize);
  priceChart?.dispose();
  salesChart?.dispose();
  reviewChart?.dispose();
});
</script>

<style scoped>
.compare-view {
  padding: 4px;
}

.compare-header {
  margin-bottom: 24px;
}

.compare-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: #e0e0e6;
  margin: 0 0 4px;
}

.compare-desc {
  color: #6a6a7a;
  font-size: 14px;
  margin: 0;
}

.compare-selector {
  display: flex;
  align-items: center;
  margin-bottom: 24px;
}

.compare-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.compare-card :deep(.el-card__header) {
  color: #e0e0e6;
  border-bottom-color: rgba(255, 255, 255, 0.06);
}

.empty-state {
  text-align: center;
  padding: 60px 0;
  color: #6a6a7a;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}
</style>
