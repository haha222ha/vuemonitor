﻿﻿﻿﻿﻿﻿﻿<template>
  <div>
    <el-page-header @back="$router.back()" :content="productStore.currentProduct?.product_name || '商品详情'" />

    <div v-loading="productStore.loading" style="margin-top: 16px">
      <el-descriptions :column="3" border v-if="productStore.currentProduct">
        <el-descriptions-item label="平台">小红书</el-descriptions-item>
        <el-descriptions-item label="商品ID">{{ productStore.currentProduct.platform_product_id }}</el-descriptions-item>
        <el-descriptions-item label="作者">{{ productStore.currentProduct.shop_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="品类">{{ productStore.currentProduct.category || '未分类' }}</el-descriptions-item>
        <el-descriptions-item label="最新采集">{{ productStore.currentProduct.last_collected_at ? formatDate(productStore.currentProduct.last_collected_at) : '未采集' }}</el-descriptions-item>
        <el-descriptions-item label="商品链接">
          <el-link v-if="productStore.currentProduct.product_url" :href="productStore.currentProduct.product_url" target="_blank" type="primary">查看</el-link>
          <span v-else>-</span>
        </el-descriptions-item>
      </el-descriptions>
      <el-empty v-else-if="!productStore.loading" description="商品信息加载失败" />
    </div>

    <div style="margin-top: 24px; display: flex; gap: 12px; flex-wrap: wrap">
      <el-button type="primary" @click="collectNow">立即采集</el-button>
      <el-button v-permission="'gate:ai:basic_analysis'" @click="runAnalysis('basic_analysis')" :loading="aiStore.isAnalyzing">基础分析</el-button>
      <el-button v-permission="'gate:ai:trend_score'" @click="runAnalysis('trend_score')" :loading="aiStore.isAnalyzing">趋势评分</el-button>
      <el-button v-permission="'gate:ai:prediction'" @click="runAnalysis('prediction')" :loading="aiStore.isAnalyzing">爆品预测</el-button>
      <el-button v-permission="'gate:ai:risk_warning'" @click="runAnalysis('risk_warning')" :loading="aiStore.isAnalyzing">风险预警</el-button>
      <el-button v-permission="'gate:monitor:export'" @click="exportData">导出数据</el-button>
    </div>

    <el-row :gutter="20" style="margin-top: 24px" v-if="latestFeature">
      <el-col :span="6">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-label">当前价格</div>
          <div class="metric-value price">{{ latestFeature.price != null ? `¥${latestFeature.price}` : '-' }}</div>
          <div class="metric-change" v-if="priceChange !== null" :class="priceChange > 0 ? 'up' : 'down'">
            <el-icon v-if="priceChange > 0"><Top /></el-icon>
            <el-icon v-else><Bottom /></el-icon>
            {{ Math.abs(priceChange).toFixed(1) }}%
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-label">总销量</div>
          <div class="metric-value">{{ latestFeature.sales_count != null ? formatNumber(latestFeature.sales_count) : '-' }}</div>
          <div class="metric-change" v-if="salesChange !== null" :class="salesChange > 0 ? 'up' : 'down'">
            <el-icon v-if="salesChange > 0"><Top /></el-icon>
            <el-icon v-else><Bottom /></el-icon>
            {{ Math.abs(salesChange).toFixed(1) }}%
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-label">评分</div>
          <div class="metric-value rating">{{ latestFeature.rating != null ? latestFeature.rating.toFixed(1) : '-' }}</div>
          <el-rate
            v-if="latestFeature.rating"
            :model-value="latestFeature.rating"
            disabled
            size="small"
            style="margin-top: 4px"
          />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-label">评论 / 收藏</div>
          <div class="metric-value small">{{ latestFeature.review_count || 0 }} / {{ latestFeature.favorite_count || 0 }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 16px" v-if="ranking || benchmark">
      <el-col :span="12" v-if="ranking">
        <el-card>
          <template #header><span>品类排名</span></template>
          <div class="ranking-gauges">
            <div class="gauge-item">
              <div class="gauge-ring" :style="gaugeStyle(ranking.price_percentile, '#F56C6C')">
                <span class="gauge-value">{{ ranking.price_percentile || 0 }}</span>
              </div>
              <div class="gauge-label">价格百分位</div>
            </div>
            <div class="gauge-item">
              <div class="gauge-ring" :style="gaugeStyle(ranking.sales_percentile, '#409EFF')">
                <span class="gauge-value">{{ ranking.sales_percentile || 0 }}</span>
              </div>
              <div class="gauge-label">销量百分位</div>
            </div>
            <div class="gauge-item">
              <div class="gauge-ring" :style="gaugeStyle(ranking.rating_percentile, '#E6A23C')">
                <span class="gauge-value">{{ ranking.rating_percentile || 0 }}</span>
              </div>
              <div class="gauge-label">评分百分位</div>
            </div>
          </div>
          <div class="ranking-info" style="margin-top: 16px">
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
          <div class="ranking-tags" style="margin-top: 12px">
            <el-tag v-if="ranking.lifecycle_stage" size="small" :type="lifecycleTagType(ranking.lifecycle_stage)">
              {{ ranking.lifecycle_stage }}
            </el-tag>
            <el-tag v-if="ranking.trend_direction" size="small" :type="trendTagType(ranking.trend_direction)">
              {{ trendLabel(ranking.trend_direction) }}
            </el-tag>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12" v-if="benchmark">
        <el-card>
          <template #header><span>品类基准对比</span></template>
          <div ref="radarChartRef" style="width: 100%; height: 260px" v-if="radarData"></div>
          <div class="benchmark-list" style="margin-top: 12px">
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
        </el-card>
      </el-col>
    </el-row>

    <div v-if="aiStore.currentAnalysis" style="margin-top: 20px">
      <el-card>
        <template #header><span>AI分析结果</span></template>
        <div style="white-space: pre-wrap; line-height: 1.8">{{ formatAIResult(aiStore.currentAnalysis) }}</div>
      </el-card>
    </div>

    <h3 style="margin-top: 24px">数据趋势</h3>
    <div style="background: #fff; padding: 16px; border-radius: 8px; border: 1px solid #ebeef5">
      <MultiMetricChart
        v-if="chartData.length > 0"
        :data="chartData"
        :metrics="selectedMetrics"
        :height="350"
      />
      <el-empty v-else description="暂无趋势数据，请先采集" />
    </div>

    <div style="margin-top: 12px; display: flex; gap: 12px; align-items: center">
      <span style="font-size: 13px; color: #909399">显示指标：</span>
      <el-checkbox v-model="metricVisible.price" @change="updateMetrics">价格</el-checkbox>
      <el-checkbox v-model="metricVisible.sales" @change="updateMetrics">销量</el-checkbox>
      <el-checkbox v-model="metricVisible.rating" @change="updateMetrics">评分</el-checkbox>
      <el-checkbox v-model="metricVisible.review_count" @change="updateMetrics">评论数</el-checkbox>
      <el-checkbox v-model="metricVisible.favorite_count" @change="updateMetrics">收藏数</el-checkbox>
      <div style="flex: 1" />
      <el-radio-group v-model="chartRange" size="small" @change="updateChartRange">
        <el-radio-button value="7">7天</el-radio-button>
        <el-radio-button value="30">30天</el-radio-button>
        <el-radio-button value="0">全部</el-radio-button>
      </el-radio-group>
    </div>

    <h3 style="margin-top: 24px">历史特征</h3>
    <el-table :data="productStore.features" stripe v-loading="productStore.loading" max-height="400">
      <el-table-column prop="collected_at" label="采集时间" width="180">
        <template #default="{ row }">{{ formatDate(row.collected_at) }}</template>
      </el-table-column>
      <el-table-column prop="price" label="价格" width="100">
        <template #default="{ row }">
          <span :style="{ color: getPriceChangeColor(row) }">{{ row.price != null ? `¥${row.price}` : '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="sales_count" label="销量" width="100" />
      <el-table-column prop="rating" label="评分" width="80" />
      <el-table-column prop="review_count" label="评论" width="80" />
      <el-table-column prop="favorite_count" label="收藏" width="80" />
      <el-table-column prop="source" label="来源" width="80" />
    </el-table>
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
import { Top, Bottom } from "@element-plus/icons-vue";
import * as echarts from "echarts";
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
    background: `conic-gradient(${color} ${deg}deg, #EBEEF5 ${deg}deg)`,
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
      axisName: { color: "#606266", fontSize: 12 },
      splitArea: { areaStyle: { color: ["#F5F7FA", "#fff", "#F5F7FA", "#fff"] } },
    },
    series: [
      {
        type: "radar",
        data: [
          {
            value: radarData.value.values,
            name: "当前商品",
            areaStyle: { color: "rgba(64, 158, 255, 0.2)" },
            lineStyle: { color: "#409EFF", width: 2 },
            itemStyle: { color: "#409EFF" },
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

function getPriceChangeColor(row: any): string {
  const idx = productStore.features.indexOf(row);
  if (idx < 0 || idx >= productStore.features.length - 1) return "";
  const prev = productStore.features[idx + 1];
  if (row.price == null || prev?.price == null) return "";
  return row.price > prev.price ? "#F56C6C" : row.price < prev.price ? "#67C23A" : "";
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
.metric-card {
  text-align: center;
  padding: 8px 0;
}
.metric-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}
.metric-value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
}
.metric-value.price {
  color: #F56C6C;
}
.metric-value.rating {
  color: #E6A23C;
}
.metric-value.small {
  font-size: 22px;
}
.metric-change {
  font-size: 13px;
  margin-top: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
}
.metric-change.up {
  color: #F56C6C;
}
.metric-change.down {
  color: #67C23A;
}
.ranking-gauges {
  display: flex;
  justify-content: space-around;
  gap: 16px;
}
.gauge-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.gauge-ring {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}
.gauge-ring::before {
  content: "";
  position: absolute;
  inset: 8px;
  border-radius: 50%;
  background: #fff;
}
.gauge-value {
  position: relative;
  z-index: 1;
  font-size: 18px;
  font-weight: 700;
  color: #303133;
}
.gauge-label {
  font-size: 12px;
  color: #909399;
}
.ranking-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.ranking-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.ranking-info-label {
  font-size: 13px;
  color: #606266;
  min-width: 70px;
}
.rank-number {
  font-size: 20px;
  font-weight: 700;
  color: #409EFF;
}
.rank-total {
  font-size: 13px;
  color: #909399;
}
.ranking-tags {
  display: flex;
  gap: 8px;
}
.benchmark-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.benchmark-item {
  display: flex;
  align-items: center;
  gap: 12px;
}
.benchmark-label {
  font-size: 13px;
  color: #606266;
  min-width: 60px;
}
.benchmark-detail {
  font-size: 12px;
  color: #909399;
  margin-left: auto;
}
</style>
