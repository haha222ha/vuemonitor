<template>
  <div class="compare fade-in">
    <PageHeader title="商品对比" subtitle="选择多个商品进行多维度对比分析">
      <el-button type="primary" @click="showSelector = true" :disabled="selectedProducts.length >= 10">
        添加商品 ({{ selectedProducts.length }}/10)
      </el-button>
    </PageHeader>

    <el-dialog v-model="showSelector" title="选择商品" width="600px" class="modern-dialog">
      <el-input v-model="searchQuery" placeholder="搜索商品名称..." clearable style="margin-bottom: 12px" />
      <div class="compare__product-list">
        <div
          v-for="p in filteredProducts"
          :key="p.id"
          class="compare__product-item"
          :class="{ selected: isSelected(p.id) }"
          @click="toggleSelect(p)"
        >
          <el-checkbox :model-value="isSelected(p.id)" @click.stop />
          <span class="compare__product-name">{{ p.product_name }}</span>
          <el-tag size="small">{{ p.platform }}</el-tag>
          <span v-if="p.latest_feature" class="compare__product-price">¥{{ p.latest_feature.price ?? '-' }}</span>
        </div>
        <EmptyState v-if="filteredProducts.length === 0" :icon="Goods" title="暂无商品" description="请先添加商品到监控列表" />
      </div>
      <template #footer>
        <el-button @click="showSelector = false">取消</el-button>
        <el-button type="primary" @click="runCompare" :disabled="selectedProducts.length < 2">开始对比</el-button>
      </template>
    </el-dialog>

    <div v-if="compareData" class="compare__result">
      <div class="card">
        <div class="card__header">
          <div class="card__title-group">
            <el-icon class="card__icon" :size="20"><DataBoard /></el-icon>
            <h3 class="card__title">对比概览</h3>
          </div>
        </div>
        <el-table :data="compareData.items" stripe>
          <el-table-column prop="product_name" label="商品名称" min-width="180" />
          <el-table-column prop="platform" label="平台" width="100">
            <template #default="{ row }"><el-tag size="small">{{ row.platform }}</el-tag></template>
          </el-table-column>
          <el-table-column prop="shop_name" label="店铺" width="150" />
          <el-table-column prop="price" label="价格" width="120" sortable>
            <template #default="{ row }"><span :class="getMetricClass('price', row.price)">¥{{ row.price ?? '-' }}</span></template>
          </el-table-column>
          <el-table-column prop="sales_count" label="销量" width="120" sortable>
            <template #default="{ row }"><span :class="getMetricClass('sales_count', row.sales_count)">{{ row.sales_count ?? '-' }}</span></template>
          </el-table-column>
          <el-table-column prop="monthly_sales" label="月销" width="120" sortable>
            <template #default="{ row }"><span :class="getMetricClass('monthly_sales', row.monthly_sales)">{{ row.monthly_sales ?? '-' }}</span></template>
          </el-table-column>
          <el-table-column prop="rating" label="评分" width="100" sortable>
            <template #default="{ row }"><span :class="getMetricClass('rating', row.rating)">{{ row.rating ?? '-' }}</span></template>
          </el-table-column>
          <el-table-column prop="review_count" label="评论" width="100" sortable>
            <template #default="{ row }"><span :class="getMetricClass('review_count', row.review_count)">{{ row.review_count ?? '-' }}</span></template>
          </el-table-column>
          <el-table-column prop="favorite_count" label="收藏" width="100" sortable>
            <template #default="{ row }"><span :class="getMetricClass('favorite_count', row.favorite_count)">{{ row.favorite_count ?? '-' }}</span></template>
          </el-table-column>
        </el-table>
      </div>

      <div class="card" style="margin-top: 20px">
        <div class="card__header">
          <div class="card__title-group">
            <el-icon class="card__icon" :size="20"><TrendCharts /></el-icon>
            <h3 class="card__title">指标分析</h3>
          </div>
        </div>
        <div ref="radarChartRef" class="compare__chart"></div>
      </div>

      <div class="card" style="margin-top: 20px">
        <div class="card__header">
          <div class="card__title-group">
            <el-icon class="card__icon" :size="20"><Histogram /></el-icon>
            <h3 class="card__title">优劣分析</h3>
          </div>
        </div>
        <div class="compare__metrics-grid">
          <div v-for="metric in metricLabels" :key="metric.key" class="metric-card">
            <div class="metric-card__label">{{ metric.label }}</div>
            <div v-if="compareData.comparison[metric.key]" class="metric-card__detail">
              <el-tag type="success" v-if="compareData.comparison[metric.key].best">
                最优: {{ compareData.comparison[metric.key].best[0] }} ({{ compareData.comparison[metric.key].best[1] }})
              </el-tag>
              <el-tag type="danger" v-if="compareData.comparison[metric.key].worst">
                最差: {{ compareData.comparison[metric.key].worst[0] }} ({{ compareData.comparison[metric.key].worst[1] }})
              </el-tag>
            </div>
            <div v-else class="metric-card__detail"><el-text type="info">数据不足</el-text></div>
          </div>
        </div>
      </div>
    </div>

    <EmptyState v-else-if="!loading" :icon="Goods" title="请选择商品进行对比" description="选择至少2个商品，即可开始多维度对比分析" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from "vue";
import * as echarts from "echarts";
import PageHeader from "../components/PageHeader.vue";
import EmptyState from "../components/EmptyState.vue";
import { Goods, DataBoard, TrendCharts, Histogram } from "@element-plus/icons-vue";

const showSelector = ref(false);
const searchQuery = ref("");
const allProducts = ref<any[]>([]);
const selectedProducts = ref<any[]>([]);
const compareData = ref<any>(null);
const loading = ref(false);
const radarChartRef = ref<HTMLElement>();
let radarChart: echarts.ECharts | null = null;

const metricLabels = [
  { key: "price", label: "价格" },
  { key: "sales_count", label: "销量" },
  { key: "monthly_sales", label: "月销" },
  { key: "rating", label: "评分" },
  { key: "review_count", label: "评论数" },
  { key: "favorite_count", label: "收藏数" },
];

const filteredProducts = computed(() => {
  if (!searchQuery.value) return allProducts.value;
  const q = searchQuery.value.toLowerCase();
  return allProducts.value.filter((p) => p.product_name?.toLowerCase().includes(q) || p.platform?.toLowerCase().includes(q));
});

function isSelected(id: string) { return selectedProducts.value.some((p) => p.id === id); }

function toggleSelect(p: any) {
  const idx = selectedProducts.value.findIndex((s) => s.id === p.id);
  if (idx !== -1) selectedProducts.value.splice(idx, 1);
  else if (selectedProducts.value.length < 10) selectedProducts.value.push(p);
}

async function fetchProducts() {
  try {
    const result = await window.electronAPI.invoke("products:list", { page: 1, pageSize: 100 });
    allProducts.value = result?.data?.items || [];
  } catch {}
}

async function runCompare() {
  if (selectedProducts.value.length < 2) return;
  loading.value = true;
  showSelector.value = false;
  try {
    const ids = selectedProducts.value.map((p) => p.id);
    const result = await window.electronAPI.invoke("products:compare", { productIds: ids });
    compareData.value = result?.data;
    await nextTick();
    renderRadarChart();
  } catch {}
  loading.value = false;
}

function getMetricClass(metric: string, value: number | null) {
  if (!compareData.value?.comparison?.[metric] || value === null) return "";
  const comp = compareData.value.comparison[metric];
  if (comp.best && comp.best[1] === value) return "metric-best";
  if (comp.worst && comp.worst[1] === value) return "metric-worst";
  return "";
}

function renderRadarChart() {
  if (!radarChartRef.value || !compareData.value) return;
  if (!radarChart) radarChart = echarts.init(radarChartRef.value);
  const indicators = [{ name: "价格", max: 0 }, { name: "销量", max: 0 }, { name: "月销", max: 0 }, { name: "评分", max: 5 }, { name: "评论", max: 0 }, { name: "收藏", max: 0 }];
  const items = compareData.value.items;
  for (const item of items) {
    if (item.price && item.price > indicators[0].max) indicators[0].max = item.price;
    if (item.sales_count && item.sales_count > indicators[1].max) indicators[1].max = item.sales_count;
    if (item.monthly_sales && item.monthly_sales > indicators[2].max) indicators[2].max = item.monthly_sales;
    if (item.review_count && item.review_count > indicators[4].max) indicators[4].max = item.review_count;
    if (item.favorite_count && item.favorite_count > indicators[5].max) indicators[5].max = item.favorite_count;
  }
  for (const ind of indicators) { if (ind.max === 0) ind.max = 1; }
  const colors = ["#6366f1", "#f43f5e", "#10b981", "#f59e0b", "#8b5cf6", "#06b6d4", "#ec4899", "#14b8a6", "#a855f7", "#ef4444"];
  const series = items.map((item: any, i: number) => ({
    value: [item.price ?? 0, item.sales_count ?? 0, item.monthly_sales ?? 0, item.rating ?? 0, item.review_count ?? 0, item.favorite_count ?? 0],
    name: item.product_name?.substring(0, 15) || `商品${i + 1}`,
    lineStyle: { color: colors[i % colors.length] },
    areaStyle: { color: colors[i % colors.length], opacity: 0.1 },
    itemStyle: { color: colors[i % colors.length] },
  }));
  radarChart.setOption({ backgroundColor: "transparent", legend: { bottom: 0, textStyle: { fontSize: 12 } }, radar: { indicator: indicators, radius: "65%" }, series: [{ type: "radar", data: series }] });
}

onMounted(fetchProducts);
</script>

<style scoped>
.compare {
  padding: 0;
}

.compare__product-list {
  max-height: 400px;
  overflow-y: auto;
}

.compare__product-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  border-radius: var(--radius-base);
  transition: background 0.2s;
}

.compare__product-item:hover {
  background: var(--color-bg-page);
}

.compare__product-item.selected {
  background: #eef2ff;
}

.compare__product-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: var(--text-sm);
  color: var(--color-text-primary);
}

.compare__product-price {
  color: var(--color-danger);
  font-weight: 600;
  font-size: var(--text-sm);
}

.compare__chart {
  height: 400px;
}

.compare__metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.metric-card {
  padding: 12px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-base);
}

.metric-card__label {
  font-weight: 600;
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  margin-bottom: 8px;
}

.metric-card__detail {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.metric-best {
  color: #10b981;
  font-weight: 700;
}

.metric-worst {
  color: #f43f5e;
  font-weight: 700;
}

.modern-dialog :deep(.el-dialog__header) {
  padding: 20px 24px;
  border-bottom: 1px solid var(--color-border-light);
  margin-right: 0;
}

.modern-dialog :deep(.el-dialog__title) {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-text-primary);
}

.modern-dialog :deep(.el-dialog__body) {
  padding: 24px;
}

.modern-dialog :deep(.el-dialog__footer) {
  padding: 16px 24px;
  border-top: 1px solid var(--color-border-light);
}

@media (max-width: 768px) {
  .compare__metrics-grid {
    grid-template-columns: 1fr;
  }
}
</style>
