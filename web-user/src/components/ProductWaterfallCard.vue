<template>
  <div class="waterfall-card" @click="$emit('detail', product)">
    <div class="waterfall-card__image-wrap">
      <el-image v-if="product.image_url" :src="product.image_url" class="waterfall-card__image" fit="cover" lazy />
      <div v-else class="waterfall-card__image waterfall-card__image--placeholder">
        {{ platformEmoji(product.platform) }}
      </div>
      <div v-if="product.latest_feature?.price != null" class="waterfall-card__price-tag">
        ¥{{ product.latest_feature.price }}
      </div>
    </div>
    <div class="waterfall-card__body">
      <div class="waterfall-card__name">{{ product.product_name }}</div>
      <div class="waterfall-card__shop" v-if="product.shop_name">{{ product.shop_name }}</div>
      <div class="waterfall-card__stats">
        <span v-if="product.latest_feature?.sales_count != null">
          销量 {{ formatNumber(product.latest_feature.sales_count) }}
        </span>
        <span v-if="product.latest_feature?.favorite_count != null">
          收藏 {{ formatNumber(product.latest_feature.favorite_count) }}
        </span>
      </div>
      <div v-if="sparklineData.length >= 2" class="waterfall-card__sparkline">
        <SparklineChart :data="sparklineData" color="#6366f1" width="100%" height="24px" />
      </div>
    </div>
    <div class="waterfall-card__actions" @click.stop>
      <el-button size="small" type="primary" text @click="$emit('delete', product.id)">
        删除
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import SparklineChart from "./SparklineChart.vue";

const props = defineProps<{
  product: any;
}>();

defineEmits<{
  detail: [product: any];
  delete: [id: string];
}>();

const sparklineData = computed(() => {
  const features = props.product.features || [];
  return features.map((f: any) => f.sales_count).filter((v: any): v is number => v != null);
});

function platformEmoji(p: string) {
  const map: Record<string, string> = { xhs: "📕", taobao: "🛒", jd: "🏪", pdd: "🛍️", douyin: "🎵" };
  return map[p] || "📦";
}

function formatNumber(num: number): string {
  if (num >= 10000) return `${(num / 10000).toFixed(1)}万`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}k`;
  return String(num);
}
</script>

<style scoped>
.waterfall-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s;
}

.waterfall-card:hover {
  border-color: rgba(99, 102, 241, 0.3);
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
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
  font-size: 48px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(244, 114, 182, 0.08));
}

.waterfall-card__price-tag {
  position: absolute;
  bottom: 8px;
  right: 8px;
  background: rgba(239, 68, 68, 0.9);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 4px;
}

.waterfall-card__body {
  padding: 12px 14px;
}

.waterfall-card__name {
  font-size: 14px;
  font-weight: 500;
  color: #e0e0e6;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.waterfall-card__shop {
  font-size: 12px;
  color: #6a6a7a;
  margin-top: 4px;
}

.waterfall-card__stats {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #8a8a9a;
  margin-top: 8px;
}

.waterfall-card__sparkline {
  margin-top: 8px;
}

.waterfall-card__actions {
  display: flex;
  justify-content: flex-end;
  padding: 4px 14px 10px;
}
</style>
