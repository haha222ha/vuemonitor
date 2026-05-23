<template>
  <div class="product-card" @click="$emit('detail', product)">
    <div class="product-card__header">
      <el-image v-if="product.image_url" :src="product.image_url" class="product-card__image" fit="cover" lazy />
      <div v-else class="product-card__image product-card__image--placeholder">
        <el-icon :size="24"><Goods /></el-icon>
      </div>
      <div class="product-card__info">
        <div class="product-card__name">{{ product.product_name }}</div>
        <div v-if="product.shop_name" class="product-card__shop">{{ product.shop_name }}</div>
      </div>
      <div v-if="ranking" class="product-card__rank-badge">
        <span class="rank-badge__number">#{{ ranking.rank }}</span>
      </div>
    </div>
    <div class="product-card__body">
      <div class="product-card__metrics">
        <div class="product-card__metric">
          <span class="product-card__metric-label">价格</span>
          <span class="product-card__metric-value product-card__metric-value--price">
            {{ product.latest_feature?.price != null ? `¥${product.latest_feature.price}` : '-' }}
          </span>
        </div>
        <div class="product-card__metric">
          <span class="product-card__metric-label">销量</span>
          <span class="product-card__metric-value">
            {{ product.latest_feature?.sales_count != null ? formatNumber(product.latest_feature.sales_count) : '-' }}
          </span>
        </div>
        <div class="product-card__metric">
          <span class="product-card__metric-label">排名</span>
          <span class="product-card__metric-value">
            {{ ranking ? `#${ranking.rank}` : '-' }}
          </span>
        </div>
        <div v-if="product.growth_24h" class="product-card__metric">
          <span class="product-card__metric-label">24h增长</span>
          <span :class="['product-card__metric-value', growthClass]">
            {{ growthText }}
          </span>
        </div>
      </div>
      <div v-if="sparklineData.length >= 2 || priceSparklineData.length >= 2" class="product-card__sparkline">
        <div v-if="sparklineData.length >= 2" class="product-card__sparkline-item">
          <span class="product-card__sparkline-label">销量</span>
          <SparklineChart :data="sparklineData" color="#409EFF" width="100%" height="28px" />
        </div>
        <div v-if="priceSparklineData.length >= 2" class="product-card__sparkline-item">
          <span class="product-card__sparkline-label">价格</span>
          <SparklineChart :data="priceSparklineData" color="#F56C6C" width="100%" height="28px" />
        </div>
      </div>
    </div>
    <div class="product-card__actions" @click.stop>
      <el-button size="small" type="primary" @click="$emit('collect', product)">
        <el-icon><VideoPlay /></el-icon> 采集
      </el-button>
      <el-dropdown v-permission="'gate:ai:basic_analysis'" @command="(cmd: string) => $emit('ai-analysis', product, cmd)">
        <el-button size="small" type="warning" plain>
          <el-icon><MagicStick /></el-icon>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="trend_score">趋势评分</el-dropdown-item>
            <el-dropdown-item command="prediction">爆品预测</el-dropdown-item>
            <el-dropdown-item command="risk_warning">风险预警</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      <el-button size="small" type="danger" plain @click="$emit('delete', product.id)">
        <el-icon><Delete /></el-icon>
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { Goods, MagicStick, VideoPlay, Delete } from "@element-plus/icons-vue";
import SparklineChart from "./SparklineChart.vue";

export interface ProductRanking {
  rank: number;
  total: number;
  trend: string;
  lifecycle: string;
}

const props = defineProps<{
  product: any;
  ranking?: ProductRanking | null;
}>();

defineEmits<{
  detail: [product: any];
  collect: [product: any];
  'ai-analysis': [product: any, type: string];
  delete: [id: string];
}>();

const sparklineData = computed(() => {
  const features = props.product.features || [];
  return features.map((f: any) => f.sales_count).filter((v: any): v is number => v != null);
});

const priceSparklineData = computed(() => {
  const features = props.product.features || [];
  return features.map((f: any) => f.price).filter((v: any): v is number => v != null);
});

const growthText = computed(() => {
  const g = props.product.growth_24h;
  if (!g || g.sales_pct == null) return "-";
  const sign = g.sales_pct >= 0 ? "+" : "";
  return `${sign}${g.sales_pct}%`;
});

const growthClass = computed(() => {
  const g = props.product.growth_24h;
  if (!g || g.sales_pct == null) return "";
  if (g.sales_pct > 0) return "product-card__metric-value--up";
  if (g.sales_pct < 0) return "product-card__metric-value--down";
  return "";
});

function formatNumber(num: number): string {
  if (num >= 10000) return `${(num / 10000).toFixed(1)}万`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}k`;
  return String(num);
}
</script>

<style scoped>
.product-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-border-light);
  padding: var(--space-lg);
  transition: all var(--duration-normal) var(--ease-out);
  cursor: pointer;
}

.product-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.product-card__header {
  display: flex;
  align-items: flex-start;
  gap: var(--space-base);
  margin-bottom: var(--space-base);
}

.product-card__image {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-base);
  flex-shrink: 0;
  border: 1px solid var(--color-border-light);
}

.product-card__image--placeholder {
  background: var(--color-bg-page);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-tertiary);
}

.product-card__info {
  flex: 1;
  min-width: 0;
}

.product-card__name {
  font-weight: 500;
  font-size: var(--text-base);
  color: var(--color-text-primary);
  margin-bottom: var(--space-2xs);
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-height: var(--leading-sm);
}

.product-card__shop {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.product-card__rank-badge {
  flex-shrink: 0;
  background: linear-gradient(135deg, var(--color-warning-400), var(--color-warning-600));
  color: #fff;
  border-radius: var(--radius-sm);
  padding: var(--space-2xs) var(--space-sm);
  font-weight: 700;
}

.rank-badge__number {
  font-size: var(--text-sm);
}

.product-card__body {
  margin-bottom: var(--space-base);
}

.product-card__metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-sm);
}

.product-card__sparkline {
  margin-top: var(--space-sm);
  padding: var(--space-xs) var(--space-sm);
  background: var(--color-bg-page);
  border-radius: var(--radius-base);
  display: flex;
  gap: var(--space-sm);
}

.product-card__sparkline-item {
  flex: 1;
  min-width: 0;
}

.product-card__sparkline-label {
  font-size: 10px;
  color: var(--color-text-tertiary);
  font-weight: 500;
  letter-spacing: 0.5px;
}

.product-card__metric {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2xs);
  padding: var(--space-sm) var(--space-xs);
  background: var(--color-bg-page);
  border-radius: var(--radius-base);
}

.product-card__metric-label {
  font-size: 10px;
  color: var(--color-text-tertiary);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.product-card__metric-value {
  font-size: var(--text-sm);
  font-weight: 700;
  color: var(--color-text-primary);
}

.product-card__metric-value--price {
  color: var(--color-danger);
}

.product-card__metric-value--up {
  color: var(--color-success);
}

.product-card__metric-value--down {
  color: var(--color-danger);
}

.product-card__actions {
  display: flex;
  gap: var(--space-sm);
}

.product-card__actions .el-button {
  flex: 1;
}
</style>
