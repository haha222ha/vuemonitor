<template>
  <div class="discovery-store-card" @click="$emit('view-goods', store)">
    <div class="discovery-store-card__body">
      <div class="discovery-store-card__name">{{ store.store_name }}</div>
      <div class="discovery-store-card__stats">
        <span>{{ store.product_count }} 个商品</span>
        <template v-if="store.total_sold_masked">
          <span class="discovery-store-card__masked-stat" @click.stop="showUpgradeTip">
            总销量 *** 🔒
          </span>
        </template>
        <template v-else-if="store.total_sold != null">
          <span>总销量 {{ formatNumber(store.total_sold) }}</span>
        </template>
        <template v-if="store.avg_price_masked">
          <span class="discovery-store-card__masked-stat" @click.stop="showUpgradeTip">
            均价 *** 🔒
          </span>
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
import type { DiscoveryStoreItem } from "../composables/useDiscoveryData";
import { useUpgradePrompt } from "../directives/permission";

defineProps<{
  store: DiscoveryStoreItem;
}>();

defineEmits<{ "view-goods": [store: DiscoveryStoreItem] }>();

const { promptUpgrade } = useUpgradePrompt();

function formatNumber(num: number): string {
  if (num >= 10000) return `${(num / 10000).toFixed(1)}万`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}k`;
  return String(num);
}

function showUpgradeTip() {
  promptUpgrade("gate:discovery:search");
}
</script>

<style scoped>
.discovery-store-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-sm);
  padding: 16px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  transition: all 0.2s;
}
.discovery-store-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}
.discovery-store-card__body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.discovery-store-card__name {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--color-text-primary);
}
.discovery-store-card__stats {
  display: flex;
  gap: 16px;
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}
.discovery-store-card__masked-stat {
  color: var(--color-text-tertiary);
  font-style: italic;
  cursor: pointer;
}
.discovery-store-card__action {
  color: var(--color-text-tertiary);
  flex-shrink: 0;
}
</style>
