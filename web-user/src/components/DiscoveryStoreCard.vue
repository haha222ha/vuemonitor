<template>
  <div class="discovery-store-card" @click="$emit('view-goods', store)">
    <div class="discovery-store-card__body">
      <div class="discovery-store-card__name">{{ store.store_name }}</div>
      <div class="discovery-store-card__stats">
        <span>{{ store.product_count }} 个商品</span>
        <template v-if="store.total_sold_masked">
          <span class="discovery-store-card__masked-stat" @click.stop="showUpgradeTip">总销量 *** 🔒</span>
        </template>
        <template v-else-if="store.total_sold != null">
          <span>总销量 {{ formatNumber(store.total_sold) }}</span>
        </template>
        <template v-if="store.avg_price_masked">
          <span class="discovery-store-card__masked-stat" @click.stop="showUpgradeTip">均价 *** 🔒</span>
        </template>
        <template v-else-if="store.avg_price != null">
          <span>均价 ¥{{ store.avg_price }}</span>
        </template>
      </div>
    </div>
    <div class="discovery-store-card__action">
      <el-icon><ArrowRight /></el-icon>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ArrowRight } from "@element-plus/icons-vue";
import { ElMessageBox } from "element-plus";
import type { DiscoveryStoreItem } from "../composables/useDiscoveryData";

defineProps<{
  store: DiscoveryStoreItem;
}>();

defineEmits<{ "view-goods": [store: DiscoveryStoreItem] }>();

function formatNumber(num: number): string {
  if (num >= 10000) return `${(num / 10000).toFixed(1)}万`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}k`;
  return String(num);
}

function showUpgradeTip() {
  ElMessageBox.alert(
    "升级Pro即可查看店铺完整销量和均价信息",
    "数据已隐藏",
    { confirmButtonText: "了解Pro套餐", type: "info" }
  ).then(() => {
    window.location.hash = "#/pricing";
  }).catch(() => {});
}
</script>

<style scoped>
.discovery-store-card {
  background: rgba(255,255,255,0.04);
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.08);
  padding: 16px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  transition: all 0.2s;
}
.discovery-store-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.3); transform: translateY(-1px); }
.discovery-store-card__body { flex: 1; display: flex; flex-direction: column; gap: 6px; }
.discovery-store-card__name { font-size: 14px; font-weight: 600; color: #e0e0e6; }
.discovery-store-card__stats { display: flex; gap: 16px; font-size: 12px; color: #9a9aaa; }
.discovery-store-card__masked-stat { color: #6a6a7a; font-style: italic; cursor: pointer; }
.discovery-store-card__action { color: #6a6a7a; flex-shrink: 0; }
</style>
