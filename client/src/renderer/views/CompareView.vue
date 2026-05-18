<template>
  <div class="compare fade-in">
    <PageHeader title="商品对比" subtitle="多维度对比分析，结合品类基准与排名数据">
      <el-button type="primary" @click="showSelector = true" :disabled="selectedProducts.length >= 10">
        添加商品 ({{ selectedProducts.length }}/10)
      </el-button>
      <el-button v-if="compareData" @click="resetCompare">重置对比</el-button>
    </PageHeader>

    <el-dialog v-model="showSelector" title="选择商品" width="640px" class="modern-dialog">
      <el-input v-model="searchQuery" placeholder="搜索商品名称或平台..." clearable style="margin-bottom: 12px" />
      <div class="compare__product-list">
        <div
          v-for="p in filteredProducts"
          :key="p.id"
          class="compare__product-item"
          :class="{ selected: isSelected(p.id) }"
          @click="toggleSelect(p)"
        >
          <el-checkbox :model-value="isSelected(p.id)" @click.stop />
          <div class="compare__product-info">
            <span class="compare__product-name">{{ p.product_name || p.platform_product_id }}</span>
            <div class="compare__product-meta">
              <el-tag size="small">{{ p.platform }}</el-tag>
              <span v-if="p.latest_feature?.price != null" class="compare__product-price">¥{{ p.latest_feature.price }}</span>
              <span v-if="p.latest_feature?.sales_count != null" class="compare__product-sales">{{ formatNumber(p.latest_feature.sales_count) }}销量</span>
              <span v-if="p.latest_feature?.rating != null" class="compare__product-rating">{{ p.latest_feature.rating.toFixed(1) }}分</span>
            </div>
          </div>
          <div v-if="p._ranking" class="compare__product-rank">
            <span class="compare__product-rank-value">Top {{ p._ranking.percentile }}%</span>
          </div>
        </div>
        <EmptyState v-if="filteredProducts.length === 0" :icon="Goods" title="暂无商品" description="请先添加商品到监控列表" action-label="添加商品" :action-icon="Goods" @action="router.push('/products')" />
      </div>
      <template #footer>
        <el-button @click="showSelector = false">取消</el-button>
        <el-button type="primary" @click="runCompare" :disabled="selectedProducts.length < 2" :loading="loading">开始对比</el-button>
      </template>
    </el-dialog>

    <div v-if="compareData" class="compare__result">
      <div class="compare__selected-bar">
        <div class="compare__chips">
          <el-tag
            v-for="p in selectedProducts"
            :key="p.id"
            closable
            effect="plain"
            @close="removeProduct(p.id)"
          >
            {{ (p.product_name || p.platform_product_id || '').substring(0, 20) }}
          </el-tag>
        </div>
        <el-tag v-if="cloudAvailable" type="success" effect="light" size="small">已连接云端基准</el-tag>
        <el-tag v-else type="warning" effect="light" size="small">本地对比模式</el-tag>
      </div>

      <div class="card">
        <div class="card__header">
          <div class="card__title-group">
            <el-icon class="card__icon" :size="20"><DataBoard /></el-icon>
            <h3 class="card__title">对比概览</h3>
          </div>
          <div class="card__actions">
            <el-radio-group v-model="viewMode" size="small">
              <el-radio-button value="table">表格</el-radio-button>
              <el-radio-button value="card">卡片</el-radio-button>
            </el-radio-group>
          </div>
        </div>

        <el-table v-if="viewMode === 'table'" :data="compareData.items" stripe>
          <el-table-column prop="product_name" label="商品名称" min-width="160">
            <template #default="{ row }">
              <div class="table-product-name">{{ row.product_name || '-' }}</div>
              <div class="table-product-sub">{{ row.platform }} · {{ row.shop_name || '' }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="price" label="价格" width="130" sortable>
            <template #default="{ row }">
              <div :class="getMetricClass('price', row.price)">¥{{ row.price ?? '-' }}</div>
              <div v-if="row._benchmark?.price" class="table-benchmark">均值¥{{ row._benchmark.price.avg?.toFixed(0) }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="sales_count" label="销量" width="130" sortable>
            <template #default="{ row }">
              <div :class="getMetricClass('sales_count', row.sales_count)">{{ row.sales_count != null ? formatNumber(row.sales_count) : '-' }}</div>
              <div v-if="row._benchmark?.sales" class="table-benchmark">均值{{ formatNumber(row._benchmark.sales.avg) }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="rating" label="评分" width="110" sortable>
            <template #default="{ row }">
              <div :class="getMetricClass('rating', row.rating)">{{ row.rating ?? '-' }}</div>
              <div v-if="row._benchmark?.rating" class="table-benchmark">均值{{ row._benchmark.rating.avg?.toFixed(1) }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="review_count" label="评论" width="100" sortable>
            <template #default="{ row }"><span :class="getMetricClass('review_count', row.review_count)">{{ row.review_count ?? '-' }}</span></template>
          </el-table-column>
          <el-table-column prop="favorite_count" label="收藏" width="100" sortable>
            <template #default="{ row }"><span :class="getMetricClass('favorite_count', row.favorite_count)">{{ row.favorite_count != null ? formatNumber(row.favorite_count) : '-' }}</span></template>
          </el-table-column>
          <el-table-column label="排名" width="100" v-if="hasRankings">
            <template #default="{ row }">
              <el-tag v-if="row._ranking" :type="row._ranking.percentile >= 70 ? 'success' : row._ranking.percentile >= 40 ? 'warning' : 'danger'" size="small" effect="dark">
                Top {{ row._ranking.percentile }}%
              </el-tag>
              <span v-else class="text-muted">-</span>
            </template>
          </el-table-column>
        </el-table>

        <div v-else class="compare__cards-grid">
          <div v-for="(item, idx) in compareData.items" :key="idx" class="compare-product-card">
            <div class="compare-product-card__header">
              <div class="compare-product-card__name">{{ item.product_name || '-' }}</div>
              <el-tag size="small">{{ item.platform }}</el-tag>
            </div>
            <div v-if="item._ranking" class="compare-product-card__rank">
              <div class="rank-badge" :class="item._ranking.percentile >= 70 ? 'rank-badge--high' : item._ranking.percentile >= 40 ? 'rank-badge--mid' : 'rank-badge--low'">
                Top {{ item._ranking.percentile }}%
              </div>
            </div>
            <div class="compare-product-card__metrics">
              <div class="compare-product-card__metric">
                <span class="compare-product-card__metric-label">价格</span>
                <span class="compare-product-card__metric-value" :class="getMetricClass('price', item.price)">¥{{ item.price ?? '-' }}</span>
                <span v-if="item._benchmark?.price" class="compare-product-card__metric-benchmark">均值¥{{ item._benchmark.price.avg?.toFixed(0) }}</span>
              </div>
              <div class="compare-product-card__metric">
                <span class="compare-product-card__metric-label">销量</span>
                <span class="compare-product-card__metric-value" :class="getMetricClass('sales_count', item.sales_count)">{{ item.sales_count != null ? formatNumber(item.sales_count) : '-' }}</span>
                <span v-if="item._benchmark?.sales" class="compare-product-card__metric-benchmark">均值{{ formatNumber(item._benchmark.sales.avg) }}</span>
              </div>
              <div class="compare-product-card__metric">
                <span class="compare-product-card__metric-label">评分</span>
                <span class="compare-product-card__metric-value" :class="getMetricClass('rating', item.rating)">{{ item.rating ?? '-' }}</span>
                <span v-if="item._benchmark?.rating" class="compare-product-card__metric-benchmark">均值{{ item._benchmark.rating.avg?.toFixed(1) }}</span>
              </div>
              <div class="compare-product-card__metric">
                <span class="compare-product-card__metric-label">评论</span>
                <span class="compare-product-card__metric-value">{{ item.review_count ?? '-' }}</span>
              </div>
              <div class="compare-product-card__metric">
                <span class="compare-product-card__metric-label">收藏</span>
                <span class="compare-product-card__metric-value">{{ item.favorite_count != null ? formatNumber(item.favorite_count) : '-' }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="card" style="margin-top: 20px">
        <div class="card__header">
          <div class="card__title-group">
            <el-icon class="card__icon" :size="20"><TrendCharts /></el-icon>
            <h3 class="card__title">雷达分析</h3>
          </div>
          <div class="card__actions">
            <el-checkbox v-model="showBenchmarkLine" label="显示品类均值" v-if="hasBenchmark" />
          </div>
        </div>
        <div ref="radarChartRef" class="compare__chart"></div>
      </div>

      <div class="card" style="margin-top: 20px">
        <div class="card__header">
          <div class="card__title-group">
            <el-icon class="card__icon" :size="20"><Histogram /></el-icon>
            <h3 class="card__title">指标对比</h3>
          </div>
          <div class="card__actions">
            <el-radio-group v-model="barMetric" size="small">
              <el-radio-button v-for="m in barMetrics" :key="m.key" :value="m.key">{{ m.label }}</el-radio-button>
            </el-radio-group>
          </div>
        </div>
        <div ref="barChartRef" class="compare__chart compare__chart--bar"></div>
      </div>

      <div class="card" style="margin-top: 20px">
        <div class="card__header">
          <div class="card__title-group">
            <el-icon class="card__icon" :size="20"><DataBoard /></el-icon>
            <h3 class="card__title">优劣分析</h3>
          </div>
        </div>
        <div class="compare__metrics-grid">
          <div v-for="metric in metricLabels" :key="metric.key" class="metric-card">
            <div class="metric-card__label">{{ metric.label }}</div>
            <div v-if="compareData.comparison?.[metric.key]" class="metric-card__detail">
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

    <EmptyState v-else-if="!loading" :icon="Goods" title="请选择商品进行对比" description="选择至少2个商品，结合品类基准数据进行多维度对比分析" action-label="选择商品" :action-icon="Goods" @action="showSelector = true" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { Goods, DataBoard, TrendCharts, Histogram } from "@element-plus/icons-vue";
import PageHeader from "../components/PageHeader.vue";
import EmptyState from "../components/EmptyState.vue";
import { useCompareData } from "../composables/useCompareData";

const router = useRouter();

const {
  showSelector, searchQuery, selectedProducts, compareData,
  loading, cloudAvailable, viewMode, showBenchmarkLine, barMetric,
  radarChartRef, barChartRef,
  metricLabels, barMetrics, hasRankings, hasBenchmark, filteredProducts,
  isSelected, toggleSelect, removeProduct, resetCompare, formatNumber,
  runCompare, getMetricClass,
  init, cleanup,
} = useCompareData();

onMounted(() => { init(); });
onUnmounted(() => { cleanup(); });
</script>

<style scoped>
.compare { padding: 0; }
.compare__product-list { max-height: 400px; overflow-y: auto; }
.compare__product-item { display: flex; align-items: center; gap: 10px; padding: 10px 12px; cursor: pointer; border-radius: var(--radius-base); transition: background 0.2s; }
.compare__product-item:hover { background: var(--color-bg-page); }
.compare__product-item.selected { background: var(--color-primary-lightest); }
.compare__product-info { flex: 1; min-width: 0; }
.compare__product-name { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: var(--text-sm); color: var(--color-text-primary); font-weight: 500; }
.compare__product-meta { display: flex; gap: 8px; align-items: center; margin-top: 4px; }
.compare__product-price { color: #EF4444; font-weight: 600; font-size: var(--text-xs); }
.compare__product-sales { color: #10B981; font-size: var(--text-xs); }
.compare__product-rating { color: #F59E0B; font-size: var(--text-xs); }
.compare__product-rank { flex-shrink: 0; }
.compare__product-rank-value { font-size: 11px; font-weight: 700; color: var(--color-primary); background: var(--color-primary-lightest); padding: 2px 8px; border-radius: 10px; }
.compare__selected-bar { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.compare__chips { display: flex; gap: 6px; flex-wrap: wrap; flex: 1; }
.compare__chart { height: 400px; }
.compare__chart--bar { height: 320px; }
.compare__cards-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; padding: 4px; }
.compare-product-card { padding: 16px; border: 1px solid var(--color-border-light); border-radius: var(--radius-lg); background: var(--color-bg-card); transition: border-color 0.2s; }
.compare-product-card:hover { border-color: var(--color-primary); }
.compare-product-card__header { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.compare-product-card__name { flex: 1; font-size: var(--text-sm); font-weight: 600; color: var(--color-text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.compare-product-card__rank { margin-bottom: 12px; }
.rank-badge { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 700; }
.rank-badge--high { background: var(--color-success-bg); color: var(--color-success); }
.rank-badge--mid { background: var(--color-warning-bg); color: var(--color-warning); }
.rank-badge--low { background: var(--color-danger-bg); color: var(--color-danger); }
.compare-product-card__metrics { display: flex; flex-direction: column; gap: 8px; }
.compare-product-card__metric { display: flex; align-items: center; gap: 6px; }
.compare-product-card__metric-label { font-size: var(--text-xs); color: var(--color-text-tertiary); width: 32px; flex-shrink: 0; }
.compare-product-card__metric-value { font-size: var(--text-sm); font-weight: 600; color: var(--color-text-primary); }
.compare-product-card__metric-benchmark { font-size: 11px; color: var(--color-text-tertiary); margin-left: auto; }
.compare__metrics-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.metric-card { padding: 12px; border: 1px solid var(--color-border-light); border-radius: var(--radius-base); }
.metric-card__label { font-weight: 600; font-size: var(--text-sm); color: var(--color-text-primary); margin-bottom: 8px; }
.metric-card__detail { display: flex; gap: 8px; flex-wrap: wrap; }
.table-product-name { font-weight: 500; color: var(--color-text-primary); }
.table-product-sub { font-size: 11px; color: var(--color-text-tertiary); margin-top: 2px; }
.table-benchmark { font-size: 11px; color: var(--color-text-tertiary); margin-top: 2px; }
.text-muted { color: var(--color-text-tertiary); }
.metric-best { color: #10b981; font-weight: 700; }
.metric-worst { color: #f43f5e; font-weight: 700; }
.card { background: var(--color-bg-card); border: 1px solid var(--color-border-light); border-radius: var(--radius-lg); padding: 20px; }
.card__header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.card__title-group { display: flex; align-items: center; gap: 8px; }
.card__icon { color: var(--color-primary); }
.card__title { margin: 0; font-size: var(--text-base); font-weight: 600; color: var(--color-text-primary); }
.card__actions { display: flex; gap: 8px; }
.modern-dialog :deep(.el-dialog__header) { padding: 20px 24px; border-bottom: 1px solid var(--color-border-light); margin-right: 0; }
.modern-dialog :deep(.el-dialog__title) { font-size: var(--text-lg); font-weight: 600; color: var(--color-text-primary); }
.modern-dialog :deep(.el-dialog__body) { padding: 24px; }
.modern-dialog :deep(.el-dialog__footer) { padding: 16px 24px; border-top: 1px solid var(--color-border-light); }
@media (max-width: 768px) {
  .compare__metrics-grid { grid-template-columns: 1fr; }
  .compare__cards-grid { grid-template-columns: 1fr; }
}
</style>
