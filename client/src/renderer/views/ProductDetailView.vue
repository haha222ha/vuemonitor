<template>
  <div class="product-detail fade-in">
    <PageHeader :title="productStore.currentProduct?.product_name || '商品详情'" subtitle="深度分析商品数据、排名和AI决策洞察">
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
            <RankingGauge :gauges="rankingGauges" />
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
                {{ lifecycleLabel(ranking.lifecycle_stage) }}
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

        <AIAnalysisResult
          v-if="aiStore.currentAnalysis"
          style="margin-top: 20px"
          :analysis="aiStore.currentAnalysis"
          :analysis-type-label="analysisTypeLabel"
          :format-a-i-result="formatAIResult"
        />

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
import { onMounted, onUnmounted } from "vue";
import {
  ArrowLeft, Refresh, ArrowDown, Download, PriceTag, TrendCharts,
  Star, ChatDotRound, Histogram, DataBoard, List, Link, Goods
} from "@element-plus/icons-vue";
import PageHeader from "../components/PageHeader.vue";
import StatCard from "../components/StatCard.vue";
import EmptyState from "../components/EmptyState.vue";
import RankingGauge from "../components/RankingGauge.vue";
import MultiMetricChart from "../components/MultiMetricChart";
import AIAnalysisResult from "../components/AIAnalysisResult.vue";
import { useProductDetailData } from "../composables/useProductDetailData";

const {
  productStore, collectStore, aiStore,
  ranking, benchmark, chartRange, radarChartRef, metricVisible,
  selectedMetrics, latestFeature, priceChange, salesChange,
  radarData, chartData, rankingGauges,
  formatDate, formatNumber, formatAIResult,
  analysisTypeLabel, getPriceChangeClass,
  lifecycleTagType, trendTagType, trendLabel, lifecycleLabel,
  collectNow, runAnalysis, exportData, updateChartRange,
  init, cleanup,
} = useProductDetailData();

onMounted(() => { init(); });
onUnmounted(() => { cleanup(); });
</script>

<style scoped>
.product-detail { padding: 0; }
.product-detail__info-card { background: var(--color-bg-card); border-radius: var(--radius-lg); padding: 20px 24px; box-shadow: var(--shadow-sm); border: 1px solid var(--color-border-light); margin-bottom: 20px; }
.info-card__header { display: flex; flex-direction: column; gap: 16px; }
.info-card__platform { display: flex; align-items: center; gap: 8px; }
.info-card__meta { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px 24px; }
.info-card__meta-item { display: flex; flex-direction: column; gap: 4px; }
.info-card__meta-label { font-size: var(--text-xs); color: var(--color-text-tertiary); font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px; }
.info-card__meta-value { font-size: var(--text-base); color: var(--color-text-primary); font-weight: 500; }
.product-detail__stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px; }
.product-detail__analysis-row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.product-detail__ranking-card, .product-detail__benchmark-card { min-width: 0; }
.card { background: var(--color-bg-card); border: 1px solid var(--color-border-light); border-radius: var(--radius-lg); padding: 20px; }
.card__header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.card__title-group { display: flex; align-items: center; gap: 8px; }
.card__icon { color: var(--color-primary); }
.card__title { margin: 0; font-size: var(--text-base); font-weight: 600; color: var(--color-text-primary); }
.card__actions { display: flex; gap: 8px; }
.ranking-info { margin-top: 16px; display: flex; flex-direction: column; gap: 8px; }
.ranking-row { display: flex; align-items: baseline; gap: 8px; }
.ranking-info-label { font-size: var(--text-sm); color: var(--color-text-secondary); min-width: 64px; }
.rank-number { font-size: var(--text-xl); font-weight: 700; color: var(--color-primary); }
.rank-total { font-size: var(--text-sm); color: var(--color-text-tertiary); }
.ranking-tags { margin-top: 12px; display: flex; gap: 8px; }
.product-detail__radar { width: 100%; height: 260px; }
.benchmark-list { margin-top: 12px; display: flex; flex-direction: column; gap: 10px; }
.benchmark-item { display: flex; align-items: center; gap: 10px; padding: 8px 12px; background: var(--color-bg-page); border-radius: var(--radius-base); }
.benchmark-label { font-size: var(--text-sm); color: var(--color-text-secondary); min-width: 60px; font-weight: 500; }
.benchmark-detail { font-size: var(--text-sm); color: var(--color-text-tertiary); margin-left: auto; }
.product-detail__chart { padding: 8px 0; }
.chart-toolbar { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.chart-toolbar__label { font-size: var(--text-sm); color: var(--color-text-secondary); }
.price-cell { font-weight: 600; }
.price-cell.price-up { color: var(--color-danger); }
.price-cell.price-down { color: var(--color-success); }
@media (max-width: 1024px) {
  .product-detail__stats { grid-template-columns: repeat(2, 1fr); }
  .product-detail__analysis-row { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
  .product-detail__stats { grid-template-columns: 1fr; }
  .info-card__meta { grid-template-columns: 1fr; }
}
</style>
