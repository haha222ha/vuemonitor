<template>
  <div class="waterfall-card" @click="$emit('detail', product)">
    <div class="waterfall-card__image-wrap">
      <el-image v-if="product.image_url" :src="product.image_url" class="waterfall-card__image" fit="cover" lazy />
      <div v-else class="waterfall-card__image waterfall-card__image--placeholder">
        <el-icon :size="32"><Goods /></el-icon>
      </div>
      <div v-if="product.latest_feature?.price != null" class="waterfall-card__price-tag">
        ¥{{ product.latest_feature.price }}
      </div>
    </div>
    <div class="waterfall-card__body">
      <div class="waterfall-card__name">{{ product.product_name }}</div>
      <div v-if="product.shop_name" class="waterfall-card__shop">{{ product.shop_name }}</div>
      <div class="waterfall-card__stats">
        <span v-if="product.latest_feature?.sales_count != null">
          销量 {{ formatNumber(product.latest_feature.sales_count) }}
        </span>
        <span v-if="product.latest_feature?.favorite_count != null">
          收藏 {{ formatNumber(product.latest_feature.favorite_count) }}
        </span>
      </div>
      <div v-if="sparklineData.length >= 2" class="waterfall-card__sparkline">
        <SparklineChart :data="sparklineData" color="#409EFF" width="100%" height="24px" />
      </div>
    </div>
    <div class="waterfall-card__actions" @click.stop>
      <el-button size="small" type="primary" text @click="$emit('collect', product)">
        <el-icon><VideoPlay /></el-icon> 采集
      </el-button>
      <el-button size="small" type="danger" text @click="$emit('delete', product.id)">
        <el-icon><Delete /></el-icon>
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { Goods, VideoPlay, Delete } from "@element-plus/icons-vue";
import SparklineChart from "./SparklineChart.vue";

const props = defineProps<{
  product: any;
}>();

defineEmits<{
  detail: [product: any];
  collect: [product: any];
  delete: [id: string];
}>();

const sparklineData = computed(() => {
  const features = props.product.features || [];
  return features.map((f: any) => f.sales_count).filter((v: any): v is number => v != null);
});

function formatNumber(num: number): string {
  if (num >= 10000) return `${(num / 10000).toFixed(1)}万`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}k`;
  return String(num);
}
</script>

<style scoped>
.waterfall-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-border-light);
  overflow: hidden;
  transition: all var(--duration-normal) var(--ease-out);
  cursor: pointer;
  break-inside: avoid;
  margin-bottom: var(--space-base);
}

.waterfall-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.waterfall-card__image-wrap {
  position: relative;
  width: 100%;
  overflow: hidden;
}

.waterfall-card__image {
  width: 100%;
  display: block;
}

.waterfall-card__image--placeholder {
  height: 160px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-page);
  color: var(--color-text-tertiary);
}

.waterfall-card__price-tag {
  position: absolute;
  bottom: 8px;
  right: 8px;
  background: rgba(239, 68, 68, 0.9);
  color: #fff;
  font-size: var(--text-sm);
  font-weight: 700;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
}

.waterfall-card__body {
  padding: var(--space-sm) var(--space-base);
}

.waterfall-card__name {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-text-primary);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.waterfall-card__shop {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-top: var(--space-2xs);
}

.waterfall-card__stats {
  display: flex;
  gap: var(--space-sm);
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  margin-top: var(--space-xs);
}

.waterfall-card__sparkline {
  margin-top: var(--space-xs);
}

.waterfall-card__actions {
  display: flex;
  justify-content: flex-end;
  padding: var(--space-2xs) var(--space-base) var(--space-sm);
  gap: var(--space-2xs);
}
</style>
