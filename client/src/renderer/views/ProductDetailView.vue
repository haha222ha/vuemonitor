<template>
  <div class="product-detail fade-in">
    <PageHeader :title="productStore.currentProduct?.product_name || '商品详情'" subtitle="查看商品详细数据、趋势分析和AI洞察">
      <el-button @click="$router.back()">
        <el-icon><ArrowLeft /></el-icon>返回
      </el-button>
      <el-button type="primary" @click="collectNow" :loading="collectStore.loading">
        <el-icon><Refresh /></el-icon>立即采集
      </el-button>
      <el-dropdown v-permission="'gate:ai:basic_analysis'" @command="runAnalysis" :loading="aiStore.isAnalyzing">
        <el-button :loading="aiStore.isAnalyzing">
          AI分析<el-icon class="el-icon--right"><ArrowDown /></el-icon>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item v-permission="'gate:ai:basic_analysis'" command="basic_analysis">基础分析</el-dropdown-item>
            <el-dropdown-item v-permission="'gate:ai:trend_score'" command="trend_score">趋势评分</el-dropdown-item>
            <el-dropdown-item v-permission="'gate:ai:prediction'" command="prediction">爆品预测</el-dropdown-item>
            <el-dropdown-item v-permission="'gate:ai:risk_warning'" command="risk_warning">风险预警</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      <el-button v-permission="'gate:monitor:export'" @click="exportData">
        <el-icon><Download /></el-icon>导出
      </el-button>
    </PageHeader>

    <div v-loading="productStore.loading">
      <EmptyState
        v-if="!productStore.currentProduct && !productStore.loading"
        :icon="Goods"
        title="商品信息加载失败"
        description="请检查商品是否存在或稍后重试"
      />

      <template v-if="productStore.currentProduct">
        <div class="product-detail__info-card">
          <div class="info-card__header">
            <div class="info-card__platform">
              <el-tag size="small" type="danger">小红书</el-tag>
            </div>
            <div class="info-card__meta">
              <div class="info-card__meta-item">
                <span class="info-card__meta-label">商品ID</span>
                <span class="info-card__meta-value">{{ productStore.currentProduct.platform_product_id }}</span>
              </div>
              <div class="info-card__meta-item">
                <span class="info-card__meta-label">作者</span>
                <span class="info-card__meta-value">{{ productStore.currentProduct.shop_name || '-' }}</span>
              </div>
              <div class="info-card__meta-item">
                <span class="info-card__meta-label">品类</span>
                <span class="info-card__meta-value">{{ productStore.currentProduct.category || '未分类' }}</span>
              </div>
              <div class="info-card__meta-item">
                <span class="info-card__meta-label">最新采集</span>
                <span class="info-card__meta-value">{{ productStore.currentProduct.last_collected_at ? formatDate(productStore.currentProduct.last_collected_at) : '未采集' }}</span>
              </div>
              <div class="info-card__meta-item" v-if="productStore.currentProduct.product_url">
                <span class="info-card__meta-label">链接</span>
                <el-link :href="productStore.currentProduct.product_url" target="_blank" type="primary" :underline="false">
                  查看原商品 <el-icon><Link /></el-icon>
                </el-link>
              </div>
            </div>
          </div>
        </div>

        <div v-if="latestFeature" class="product-detail__stats">
          <StatCard
            :icon="PriceTag"
            variant="danger"
            label="当前价格"
            :value="latestFeature.price != null ? `¥${latestFeature.price}` : '-'"
            :trend="priceChange !== null ? `${Math.abs(priceChange).toFixed(1)}%` : undefined"
            :trendType="priceChange !== null ? (priceChange > 0 ? 'up' : 'down') : undefined"
          />
          <StatCard
            :icon="TrendCharts"
            variant="primary"
            label="总销量"
            :value="latestFeature.sales_count != null ? formatNumber(latestFeature.sales_count) : '-'"
            :trend="salesChange !== null ? `${Math.abs(salesChange).toFixed(1)}%` : undefined"
            :trendType="salesChange !== null ? (salesChange > 0 ? 'up' : 'down') : undefined"
          />
          <StatCard
            :icon="Star"
            variant="warning"
            label="评分"
            :value="latestFeature.rating != null ? latestFeature.rating.toFixed(1) : '-'"
          />
          <StatCard
            :icon="ChatDotRound"
            variant="info"
            label="评论 / 收藏"
            :value="`${latestFeature.review_count || 0} / ${latestFeature.favorite_count || 0}`"
          />
        </div>

        <div v-if="ranking || benchmark" class="product-detail__analysis-row">
          <div v-if="ranking" class="card product-detail__ranking-card">
            <div class="card__header">
              <div class="card__title-group">
                <el-icon class="card__icon" :size="20"><Histogram /></el-icon>
                <h3 class="card__title">品类排名</h3>
              </div>
            </div>
            <div class="ranking-gauges">
              <div class="gauge-item">
                <div class="gauge-ring" :style="gaugeStyle(ranking.price_percentile, 'var(--color-danger)')">
                  <span class="gauge-value">{{ ranking.price_percentile || 0 }}</span>
                </div>
                <div class="gauge-label">价格百分位</div>
              </div>
              <div class="gauge-item">
                <div class="gauge-ring" :style="gaugeStyle(ranking.sales_percentile, 'var(--color-primary)')">
                  <span class="gauge-value">{{ ranking.sales_percentile || 0 }}</span>
                </div>
                <div class="gauge-label">销量百分位</div>
              </div>
              <div class="gauge-item">
                <div class="gauge-ring" :style="gaugeStyle(ranking.rating_percentile, 'var(--color-warning)')">
                  <span class="gauge-value">{{ ranking.rating_percentile || 0 }}</span>
                </div>
                <div class="gauge-label">评分百分位</div>
              </div>
            </div>
            <div class="ranking-info">
              <div class="ranking-row">
                <span class="ranking-info-label">综合排名</span>
                <span class="rank-number">#{{ ranking.overall_rank || '-' }}</span>
                <span class="rank-total" v-if="ranking.total_in_category">/ {{ ranking.total_in_category }}</span>
              </div>
              <div class="ranking-row">
                <span class="ranking-info-label">品类排名</span>
                <span class="rank-number">#{{ ranking.category_rank || '-' }}</span>
                <span class="rank-total" v-if="ranking.category_total">/ {{ ranking.category_total }}</span>
              </div>
            </div>
            <div class="ranking-tags">
              <el-tag v-if="ranking.lifecycle_stage" size="small" :type="lifecycleTagType(ranking.lifecycle_stage)">
                {{ ranking.lifecycle_stage }}
              </el-tag>
              <el-tag v-if="ranking.trend_direction" size="small" :type="trendTagType(ranking.trend_direction)">
                {{ trendLabel(ranking.trend_direction) }}
              </el-tag>
            </div>
          </div>

          <div v-if="benchmark" class="card product-detail__benchmark-card">
            <div class="card__header">
              <div class="card__title-group">
                <el-icon class="card__icon" :size="20"><DataBoard /></el-icon>
                <h3 class="card__title">品类基准对比</h3>
              </div>
            </div>
            <div ref="radarChartRef" class="product-detail__radar" v-if="radarData"></div>
            <div class="benchmark-list">
              <div class="benchmark-item" v-if="benchmark.price_level">
                <span class="benchmark-label">价格水平</span>
                <el-tag :type="benchmark.price_level === '偏高' ? 'danger' : benchmark.price_level === '偏低' ? 'success' : 'warning'" size="small">
                  {{ benchmark.price_level }}
                </el-tag>
                <span class="benchmark-detail">品类均价 ¥{{ benchmark.category_avg_price || '-' }}</span>
              </div>
              <div class="benchmark-item" v-if="benchmark.sales_level">
                <span class="benchmark-label">销量水平</span>
                <el-tag :type="benchmark.sales_level === '领先' ? 'success' : benchmark.sales_level === '落后' ? 'danger' : 'warning'" size="small">
                  {{ benchmark.sales_level }}
                </el-tag>
                <span class="benchmark-detail">品类均销 {{ benchmark.category_avg_sales || '-' }}</span>
              </div>
              <div class="benchmark-item" v-if="benchmark.price_percentile != null">
                <span class="benchmark-label">价格分位</span>
                <span class="benchmark-detail">超过 {{ benchmark.price_percentile }}% 的同类商品</span>
              </div>
              <div class="benchmark-item" v-if="benchmark.sales_percentile != null">
                <span class="benchmark-label">销量分位</span>
                <span class="benchmark-detail">超过 {{ benchmark.sales_percentile }}% 的同类商品</span>
              </div>
            </div>
          </div>
        </div>

        <div v-if="aiStore.currentAnalysis" class="card" style="margin-top: 20px">
          <div class="card__header">
            <div class="card__title-group">
              <el-icon class="card__icon" :size="20"><MagicStick /></el-icon>
              <h3 class="card__title">AI分析结果</h3>
            </div>
          </div>
          <div class="ai-result">{{ formatAIResult(aiStore.currentAnalysis) }}</div>
        </div>

        <div class="card" style="margin-top: 20px">
          <div class="card__header">
            <div class="card__title-group">
              <el-icon class="card__icon" :size="20"><TrendCharts /></el-icon>
              <h3 class="card__title">数据趋势</h3>
            </div>
            <div class="card__actions">
              <el-radio-group v-model="chartRange" size="small" @change="updateChartRange">
                <el-radio-button value="7">7天</el-radio-button>
                <el-radio-button value="30">30天</el-radio-button>
                <el-radio-button value="0">全部</el-radio-button>
              </el-radio-group>
            </div>
          </div>
          <div class="chart-toolbar">
            <span class="chart-toolbar__label">显示指标：</span>
            <el-check-tag :checked="metricVisible.price" @change="metricVisible.price = !metricVisible.price">价格</el-check-tag>
            <el-check-tag :checked="metricVisible.sales" @change="metricVisible.sales = !metricVisible.sales">销量</el-check-tag>
            <el-check-tag :checked="metricVisible.rating" @change="metricVisible.rating = !metricVisible.rating">评分</el-check-tag>
            <el-check-tag :checked="metricVisible.review_count" @change="metricVisible.review_count = !metricVisible.review_count">评论数</el-check-tag>
            <el-check-tag :checked="metricVisible.favorite_count" @change="metricVisible.favorite_count = !metricVisible.favorite_count">收藏数</el-check-tag>
          </div>
          <div class="product-detail__chart">
            <MultiMetricChart
              v-if="chartData.length > 0"
              :data="chartData"
              :metrics="selectedMetrics"
              :height="350"
            />
            <EmptyState v-else :icon="TrendCharts" title="暂无趋势数据" description="请先采集商品数据以查看趋势" />
          </div>
        </div>

        <div class="card" style="margin-top: 20px">
          <div class="card__header">
            <div class="card__title-group">
              <el-icon class="card__icon" :size="20"><List /></el-icon>
              <h3 class="card__title">历史特征</h3>
            </div>
          </div>
          <el-table :data="productStore.features" stripe v-loading="productStore.loading" max-height="400">
            <el-table-column prop="collected_at" label="采集时间" width="180">
              <template #default="{ row }">{{ formatDate(row.collected_at) }}</template>
            </el-table-column>
            <el-table-column prop="price" label="价格" width="100">
              <template #default="{ row }">
                <span :class="['price-cell', getPriceChangeClass(row)]">{{ row.price != null ? `¥${row.price}` : '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="sales_count" label="销量" width="100" />
            <el-table-column prop="rating" label="评分" width="80" />
            <el-table-column prop="review_count" label="评论" width="80" />
            <el-table-column prop="favorite_count" label="收藏" width="80" />
            <el-table-column prop="source" label="来源" width="80">
              <template #default="{ row }">
                <el-tag size="small" :type="row.source === 'local' ? 'warning' : 'primary'" effect="plain">
                  {{ row.source === 'local' ? '本地' : '云端' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, reactive, nextTick, watch } from "vue";
import { useRoute } from "vue-router";
import { useProductStore } from "../stores/product";
import { useCollectStore } from "../stores/collect";
import { useAIStore } from "../stores/ai";
import { usePermissionStore } from "../stores/permission";
import { ElMessage } from "element-plus";
import {
  ArrowLeft, Refresh, ArrowDown, Download, PriceTag, TrendCharts,
  Star, ChatDotRound, Histogram, DataBoard, MagicStick, List, Link, Goods
} from "@element-plus/icons-vue";
import * as echarts from "echarts";
import PageHeader from "../components/PageHeader.vue";
import StatCard from "../components/StatCard.vue";
import EmptyState from "../components/EmptyState.vue";
import MultiMetricChart from "../components/MultiMetricChart";
import type { MultiMetricDataPoint } from "../components/MultiMetricChart";
import api from "../utils/api";

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

function updateMetrics() {}

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

function updateChartRange() {}

function gaugeStyle(percentile: number | undefined, color: string) {
  const pct = percentile || 0;
  const deg = (pct / 100) * 360;
  return {
    background: `conic-gradient(${color} ${deg}deg, var(--color-border-light) ${deg}deg)`,
  };
}

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

function getPriceChangeClass(row: any): string {
  const idx = productStore.features.indexOf(row);
  if (idx < 0 || idx >= productStore.features.length - 1) return "";
  const prev = productStore.features[idx + 1];
  if (row.price == null || prev?.price == null) return "";
  return row.price > prev.price ? "price-up" : row.price < prev.price ? "price-down" : "";
}

function lifecycleTagType(stage: string): string {
  const map: Record<string, string> = { 新品期: "success", 成长期: "", 成熟期: "warning", 衰退期: "danger" };
  return map[stage] || "info";
}

function trendTagType(direction: string): string {
  const map: Record<string, string> = { 上升: "success", 下降: "danger", 平稳: "info" };
  return map[direction] || "info";
}

function trendLabel(direction: string): string {
  const map: Record<string, string> = { 上升: "📈 上升趋势", 下降: "📉 下降趋势", 平稳: "➡️ 平稳" };
  return map[direction] || direction;
}

async function fetchRanking(productId: string) {
  try {
    const { data } = await api.get(`/feature/product-ranking/${productId}`);
    ranking.value = data?.ranking || null;
  } catch {
    ranking.value = null;
  }
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
  } catch {
    benchmark.value = null;
  }
}

async function collectNow() {
  const p = productStore.currentProduct;
  if (!p) return;
  await collectStore.startCollect([
    { targetId: p.platform_product_id, targetType: "goods" },
  ]);
  ElMessage.success("采集任务已提交");
}

async function runAnalysis(type: string) {
  const productId = route.params.id as string;
  const result = await aiStore.analyzeProduct(productId, type);
  if (result) {
    ElMessage.success("分析完成");
  }
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
  } catch {
    ElMessage.error("导出失败");
  }
}

watch(radarData, () => {
  nextTick(() => renderRadarChart());
});

onMounted(async () => {
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
});

onUnmounted(() => {
  radarChart?.dispose();
  radarChart = null;
});
</script>

<style scoped>
.product-detail {
  padding: 0;
}

.product-detail__info-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  padding: 20px 24px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-border-light);
  margin-bottom: 20px;
}

.info-card__header {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.info-card__platform {
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-card__meta {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px 24px;
}

.info-card__meta-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-card__meta-label {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.info-card__meta-value {
  font-size: var(--text-base);
  color: var(--color-text-primary);
  font-weight: 500;
}

.product-detail__stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.product-detail__analysis-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.product-detail__ranking-card,
.product-detail__benchmark-card {
  min-width: 0;
}

.ranking-gauges {
  display: flex;
  justify-content: space-around;
  padding: 16px 0;
}

.gauge-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.gauge-ring {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.gauge-ring::before {
  content: "";
  position: absolute;
  inset: 6px;
  border-radius: 50%;
  background: var(--color-bg-card);
}

.gauge-value {
  position: relative;
  z-index: 1;
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--color-text-primary);
}

.gauge-label {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}

.ranking-info {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ranking-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.ranking-info-label {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  min-width: 64px;
}

.rank-number {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--color-primary);
}

.rank-total {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
}

.ranking-tags {
  margin-top: 12px;
  display: flex;
  gap: 8px;
}

.product-detail__radar {
  width: 100%;
  height: 260px;
}

.benchmark-list {
  margin-top: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.benchmark-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: var(--color-bg-page);
  border-radius: var(--radius-base);
}

.benchmark-label {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  min-width: 60px;
  font-weight: 500;
}

.benchmark-detail {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
  margin-left: auto;
}

.ai-result {
  white-space: pre-wrap;
  line-height: 1.8;
  font-size: var(--text-base);
  color: var(--color-text-primary);
  padding: 4px 0;
}

.product-detail__chart {
  padding: 8px 0;
}

.chart-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.chart-toolbar__metrics {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.price-cell {
  font-weight: 600;
}

.price-cell.price-up {
  color: var(--color-danger);
}

.price-cell.price-down {
  color: var(--color-success);
}

@media (max-width: 1024px) {
  .product-detail__stats {
    grid-template-columns: repeat(2, 1fr);
  }

  .product-detail__analysis-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .product-detail__stats {
    grid-template-columns: 1fr;
  }

  .info-card__meta {
    grid-template-columns: 1fr;
  }
}
</style>
