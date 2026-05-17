<template>
  <div class="category-insight fade-in">
    <PageHeader title="品类洞察" subtitle="深度解析品类表现，洞察市场行为模式与趋势">
      <el-select v-model="selectedCategory" placeholder="选择品类" clearable style="width: 200px" @change="onCategoryChange">
        <el-option v-for="cat in categoryList" :key="cat" :label="cat" :value="cat" />
      </el-select>
      <el-radio-group v-model="trendDays" size="small" @change="fetchTrendTimeseries">
        <el-radio-button :value="7">7天</el-radio-button>
        <el-radio-button :value="30">30天</el-radio-button>
        <el-radio-button :value="90">90天</el-radio-button>
      </el-radio-group>
      <el-button @click="refreshAll" :loading="refreshing">刷新</el-button>
    </PageHeader>

    <div class="category-insight__stats">
      <StatCard :icon="Grid" variant="primary" label="品类总数" :value="categoryStats.totalCategories" />
      <StatCard :icon="Goods" variant="success" label="商品总数" :value="categoryStats.totalProducts" />
      <StatCard :icon="TrendCharts" variant="amber" label="热门品类" :value="categoryStats.topCategory || '-'" />
      <StatCard :icon="DataLine" variant="info" label="平均热度" :value="categoryStats.avgHeat" />
    </div>

    <div class="category-insight__grid">
      <div class="card">
        <div class="card__header">
          <div class="card__title-group">
            <el-icon class="card__icon" :size="20"><Grid /></el-icon>
            <h3 class="card__title">品类热力图</h3>
          </div>
          <div class="card__actions">
            <el-radio-group v-model="heatmapMode" size="small">
              <el-radio-button value="treemap">矩阵</el-radio-button>
              <el-radio-button value="bar">排行</el-radio-button>
            </el-radio-group>
          </div>
        </div>
        <div v-if="heatmapLoading" class="category-insight__chart-loading">
          <el-skeleton :rows="6" animated />
        </div>
        <div v-else-if="heatmapData.length > 0" ref="heatmapChartRef" class="category-insight__chart category-insight__chart--heatmap"></div>
        <EmptyState v-else :icon="Grid" title="暂无品类热力数据" description="连接云端服务获取品类热度分析" compact />
      </div>

      <div class="card">
        <div class="card__header">
          <div class="card__title-group">
            <el-icon class="card__icon" :size="20"><PieChart /></el-icon>
            <h3 class="card__title">行为模式</h3>
          </div>
          <div class="card__actions">
            <el-tag v-if="selectedCategory" size="small" effect="plain" closable @close="selectedCategory = ''; onCategoryChange()">{{ selectedCategory }}</el-tag>
            <el-tag v-else type="info" size="small" effect="light">全品类</el-tag>
          </div>
        </div>
        <div v-if="patternsLoading" class="category-insight__chart-loading">
          <el-skeleton :rows="6" animated />
        </div>
        <template v-else-if="patterns">
          <div class="behavior-section">
            <h4 class="behavior-section__title">生命周期分布</h4>
            <div v-if="patterns.lifecycle_distribution?.length" ref="lifecycleChartRef" class="category-insight__chart category-insight__chart--small"></div>
            <div v-else class="behavior-section__empty">暂无数据</div>
          </div>
          <div class="behavior-section">
            <h4 class="behavior-section__title">趋势方向分布</h4>
            <div v-if="patterns.trend_distribution?.length" ref="trendDistChartRef" class="category-insight__chart category-insight__chart--small"></div>
            <div v-else class="behavior-section__empty">暂无数据</div>
          </div>
          <div class="behavior-section">
            <h4 class="behavior-section__title">价格带分析</h4>
            <div v-if="patterns.price_bands?.length" ref="priceBandChartRef" class="category-insight__chart category-insight__chart--small"></div>
            <div v-else class="behavior-section__empty">暂无数据</div>
          </div>
          <div class="behavior-summary" v-if="patterns.dominant_lifecycle || patterns.dominant_trend || patterns.best_seller_price_band">
            <div class="behavior-summary__item" v-if="patterns.dominant_lifecycle">
              <span class="behavior-summary__label">主流生命周期</span>
              <el-tag size="small" effect="light">{{ lifecycleLabel(patterns.dominant_lifecycle) }}</el-tag>
            </div>
            <div class="behavior-summary__item" v-if="patterns.dominant_trend">
              <span class="behavior-summary__label">主流趋势</span>
              <el-tag :type="trendTagType(patterns.dominant_trend)" size="small" effect="light">{{ trendLabel(patterns.dominant_trend) }}</el-tag>
            </div>
            <div class="behavior-summary__item" v-if="patterns.best_seller_price_band">
              <span class="behavior-summary__label">最佳价格带</span>
              <el-tag size="small" type="success" effect="light">{{ priceBandLabel(patterns.best_seller_price_band.band) }}</el-tag>
            </div>
          </div>
        </template>
        <EmptyState v-else :icon="PieChart" title="暂无行为模式数据" description="连接云端服务获取品类行为分析" compact />
      </div>
    </div>

    <div class="card" style="margin-top: 20px">
      <div class="card__header">
        <div class="card__title-group">
          <el-icon class="card__icon" :size="20"><DataLine /></el-icon>
          <h3 class="card__title">趋势时间序列</h3>
        </div>
        <div class="card__actions">
          <el-select v-model="trendMetric" size="small" style="width: 120px">
            <el-option label="平均销量" value="avg_sales" />
            <el-option label="平均价格" value="avg_price" />
            <el-option label="平均评分" value="avg_rating" />
            <el-option label="商品数" value="product_count" />
          </el-select>
        </div>
      </div>
      <div v-if="trendLoading" class="category-insight__chart-loading">
        <el-skeleton :rows="5" animated />
      </div>
      <div v-else-if="trendSeries && Object.keys(trendSeries).length > 0" ref="trendChartRef" class="category-insight__chart category-insight__chart--trend"></div>
      <EmptyState v-else :icon="DataLine" title="暂无趋势数据" description="选择品类和时间范围查看趋势变化" compact />
    </div>

    <div class="card" style="margin-top: 20px">
      <div class="card__header">
        <div class="card__title-group">
          <el-icon class="card__icon" :size="20"><DataBoard /></el-icon>
          <h3 class="card__title">品类详情</h3>
        </div>
      </div>
      <el-table v-if="categoryStatsList.length > 0" :data="categoryStatsList" stripe>
        <el-table-column prop="category" label="品类" min-width="140" sortable>
          <template #default="{ row }"><span class="category-name">{{ row.category }}</span></template>
        </el-table-column>
        <el-table-column prop="product_count" label="商品数" width="100" sortable />
        <el-table-column prop="avg_price" label="均价" width="110" sortable>
          <template #default="{ row }"><span>{{ row.avg_price != null ? `¥${row.avg_price.toFixed(0)}` : '-' }}</span></template>
        </el-table-column>
        <el-table-column prop="avg_sales" label="均销量" width="110" sortable>
          <template #default="{ row }"><span>{{ row.avg_sales != null ? formatNumber(row.avg_sales) : '-' }}</span></template>
        </el-table-column>
        <el-table-column prop="avg_rating" label="均评分" width="100" sortable>
          <template #default="{ row }"><span>{{ row.avg_rating != null ? row.avg_rating.toFixed(1) : '-' }}</span></template>
        </el-table-column>
        <el-table-column prop="heat_score" label="热度" width="130" sortable>
          <template #default="{ row }">
            <div class="heat-cell">
              <div class="heat-cell__bar">
                <div class="heat-cell__fill" :style="{ width: `${row.heat_score || 0}%` }" :class="heatLevel(row.heat_score)" />
              </div>
              <span class="heat-cell__value">{{ row.heat_score || 0 }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click="selectedCategory = row.category; onCategoryChange()">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
      <EmptyState v-else :icon="DataBoard" title="暂无品类统计数据" description="连接云端服务获取品类统计" compact />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from "vue";
import { Grid, Goods, TrendCharts, DataLine, PieChart, DataBoard } from "@element-plus/icons-vue";
import PageHeader from "../components/PageHeader.vue";
import StatCard from "../components/StatCard.vue";
import EmptyState from "../components/EmptyState.vue";
import { useCategoryInsightData } from "../composables/useCategoryInsightData";

const {
  selectedCategory, trendDays, trendMetric, heatmapMode, refreshing,
  heatmapData, heatmapLoading, patterns, patternsLoading,
  trendSeries, trendLoading, categoryStatsList,
  heatmapChartRef, lifecycleChartRef, trendDistChartRef, priceBandChartRef, trendChartRef,
  categoryList, categoryStats,
  formatNumber, heatLevel, lifecycleLabel, trendLabel, trendTagType, priceBandLabel,
  onCategoryChange, refreshAll, fetchTrendTimeseries,
  init, cleanup,
} = useCategoryInsightData();

onMounted(() => { init(); });
onUnmounted(() => { cleanup(); });
</script>

<style scoped>
.category-insight { padding: 24px; min-height: 100%; }
.category-insight__stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 24px; }
.category-insight__grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.card { background: var(--color-bg-card); border-radius: var(--radius-lg); box-shadow: var(--shadow-sm); border: 1px solid var(--color-border-light); overflow: hidden; transition: box-shadow 0.3s; }
.card:hover { box-shadow: var(--shadow-md); }
.card__header { padding: 20px 24px; border-bottom: 1px solid var(--color-border-light); display: flex; justify-content: space-between; align-items: center; }
.card__title-group { display: flex; align-items: center; gap: 10px; }
.card__icon { color: var(--color-primary); }
.card__title { margin: 0; font-size: var(--text-lg); font-weight: 600; color: var(--color-text-primary); }
.card__actions { display: flex; align-items: center; gap: 8px; }
.category-insight__chart { padding: 16px 24px; }
.category-insight__chart--heatmap { height: 360px; }
.category-insight__chart--small { height: 200px; }
.category-insight__chart--trend { height: 320px; }
.category-insight__chart-loading { padding: 24px; }
.behavior-section { padding: 16px 24px 8px; border-bottom: 1px solid var(--color-border-lighter); }
.behavior-section:last-of-type { border-bottom: none; }
.behavior-section__title { font-size: 13px; font-weight: 600; color: var(--color-text-secondary); margin: 0 0 8px; text-transform: uppercase; letter-spacing: 0.5px; }
.behavior-section__empty { padding: 16px 0; text-align: center; font-size: 13px; color: var(--color-text-tertiary); }
.behavior-summary { padding: 16px 24px; display: flex; flex-wrap: wrap; gap: 16px; background: var(--color-bg-page); border-top: 1px solid var(--color-border-lighter); }
.behavior-summary__item { display: flex; align-items: center; gap: 8px; }
.behavior-summary__label { font-size: 13px; color: var(--color-text-secondary); }
.category-name { font-weight: 500; color: var(--color-text-primary); }
.heat-cell { display: flex; align-items: center; gap: 8px; }
.heat-cell__bar { flex: 1; height: 6px; border-radius: 3px; background: var(--color-bg-page); overflow: hidden; }
.heat-cell__fill { height: 100%; border-radius: 3px; transition: width 0.6s ease; }
.heat-cell__fill.heat-hot { background: linear-gradient(90deg, #EF4444, #F97316); }
.heat-cell__fill.heat-warm { background: linear-gradient(90deg, #F59E0B, #EAB308); }
.heat-cell__fill.heat-cold { background: linear-gradient(90deg, #6366F1, #818CF8); }
.heat-cell__value { font-size: 12px; font-weight: 600; min-width: 28px; text-align: right; color: var(--color-text-secondary); }
@media (max-width: 1200px) {
  .category-insight__stats { grid-template-columns: repeat(2, 1fr); }
  .category-insight__grid { grid-template-columns: 1fr; }
}
@media (max-width: 768px) {
  .category-insight { padding: 16px; }
  .category-insight__stats { grid-template-columns: 1fr; }
}
</style>
