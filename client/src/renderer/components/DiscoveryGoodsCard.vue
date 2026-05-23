<template>
  <div :class="['discovery-card', { 'discovery-card--compact': compact }]">
    <div class="discovery-card__body">
      <div class="discovery-card__title" :title="item.title">{{ item.title }}</div>
      <div v-if="item.store_name" class="discovery-card__store">
        <el-icon :size="12"><Shop /></el-icon>
        <span>{{ item.store_name }}</span>
      </div>
      <div v-if="item.keyword" class="discovery-card__keyword">
        <el-tag size="small" type="info" effect="plain">{{ item.keyword }}</el-tag>
      </div>

      <div class="discovery-card__meta">
        <template v-if="item.deal_price_masked">
          <div class="discovery-card__masked" @click="showUpgradeTip('price')">
            <span class="discovery-card__masked-value">¥**</span>
            <span class="discovery-card__masked-hint">🔒 升级查看</span>
          </div>
        </template>
        <template v-else-if="item.deal_price != null">
          <span class="discovery-card__meta-item discovery-card__meta-item--price">
            ¥{{ item.deal_price }}
          </span>
        </template>

        <template v-if="item.sold_num_masked">
          <div class="discovery-card__masked" @click="showUpgradeTip('sales')">
            <span class="discovery-card__masked-value">
              {{ item.sold_num_approx ? `已售 ${item.sold_num_approx}` : '已售 ***' }}
            </span>
            <span class="discovery-card__masked-hint">🔒 升级查看</span>
          </div>
        </template>
        <template v-else-if="item.sold_num != null">
          <span class="discovery-card__meta-item">
            已售 {{ formatNumber(item.sold_num) }}
          </span>
        </template>
      </div>
    </div>

    <div class="discovery-card__actions">
      <el-button type="primary" size="small" @click="$emit('add-to-monitor', item)">
        <el-icon><Plus /></el-icon> 加入监控
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Shop, Plus } from "@element-plus/icons-vue";
import type { DiscoveryGoodsItem } from "../composables/useDiscoveryData";
import { useUpgradePrompt } from "../directives/permission";

const props = defineProps<{
  item: DiscoveryGoodsItem;
  compact?: boolean;
}>();

defineEmits<{ "add-to-monitor": [item: DiscoveryGoodsItem] }>();

const { promptUpgradeForField } = useUpgradePrompt();

function formatNumber(num: number): string {
  if (num >= 10000) return `${(num / 10000).toFixed(1)}万`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}k`;
  return String(num);
}

function showUpgradeTip(field: string) {
  promptUpgradeForField(field as "price" | "sales");
}
</script>

<style scoped>
.discovery-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
}

.discovery-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.discovery-card--compact {
  flex-direction: row;
  align-items: center;
}

.discovery-card--compact .discovery-card__body {
  padding: 8px 12px;
}

.discovery-card--compact .discovery-card__actions {
  padding: 8px 12px;
}

.discovery-card__body {
  padding: 16px;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.discovery-card__title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-primary);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.discovery-card__store {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.discovery-card__keyword {
  display: flex;
}

.discovery-card__meta {
  display: flex;
  gap: var(--space-sm);
  align-items: center;
  flex-wrap: wrap;
  margin-top: 4px;
}

.discovery-card__meta-item {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}

.discovery-card__meta-item--price {
  color: var(--color-danger);
  font-weight: 600;
  font-size: var(--text-sm);
}

.discovery-card__masked {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  background: var(--color-bg-page);
  transition: background 0.2s;
}

.discovery-card__masked:hover {
  background: var(--color-bg-hover);
}

.discovery-card__masked-value {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  font-style: italic;
}

.discovery-card__masked-hint {
  font-size: 10px;
  color: var(--color-primary);
  white-space: nowrap;
}

.discovery-card__actions {
  padding: 8px 16px 12px;
}
</style>
