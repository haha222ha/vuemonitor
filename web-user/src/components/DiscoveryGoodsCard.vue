<template>
  <div :class="['discovery-card', { 'discovery-card--compact': compact }]">
    <div class="discovery-card__body">
      <div class="discovery-card__title" :title="item.title">{{ item.title }}</div>
      <div class="discovery-card__store" v-if="item.store_name">
        <el-icon :size="12"><Shop /></el-icon>
        <span>{{ item.store_name }}</span>
      </div>
      <div class="discovery-card__keyword" v-if="item.keyword">
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
          <span class="discovery-card__meta-item discovery-card__meta-item--price">¥{{ item.deal_price }}</span>
        </template>

        <template v-if="item.sold_num_masked">
          <div class="discovery-card__masked" @click="showUpgradeTip('sales')">
            <span class="discovery-card__masked-value">{{ item.sold_num_approx ? `已售 ${item.sold_num_approx}` : '已售 ***' }}</span>
            <span class="discovery-card__masked-hint">🔒 升级查看</span>
          </div>
        </template>
        <template v-else-if="item.sold_num != null">
          <span class="discovery-card__meta-item">已售 {{ formatNumber(item.sold_num) }}</span>
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
import { ElMessageBox } from "element-plus";
import type { DiscoveryGoodsItem } from "../composables/useDiscoveryData";

const props = defineProps<{
  item: DiscoveryGoodsItem;
  compact?: boolean;
}>();

defineEmits<{ "add-to-monitor": [item: DiscoveryGoodsItem] }>();

function formatNumber(num: number): string {
  if (num >= 10000) return `${(num / 10000).toFixed(1)}万`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}k`;
  return String(num);
}

function showUpgradeTip(field: string) {
  const fieldLabel = field === "price" ? "价格" : "销量";
  ElMessageBox.alert(
    `升级Pro即可查看完整${fieldLabel}信息，还可享受更多搜索次数和高级筛选功能`,
    `${fieldLabel}数据已隐藏`,
    { confirmButtonText: "了解Pro套餐", type: "info" }
  ).then(() => {
    window.location.hash = "#/pricing";
  }).catch(() => {});
}
</script>

<style scoped>
.discovery-card {
  background: rgba(255,255,255,0.04);
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.08);
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
}
.discovery-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.3); transform: translateY(-2px); }
.discovery-card--compact { flex-direction: row; align-items: center; }
.discovery-card--compact .discovery-card__body { padding: 8px 12px; }
.discovery-card--compact .discovery-card__actions { padding: 8px 12px; }
.discovery-card__body { padding: 16px; flex: 1; display: flex; flex-direction: column; gap: 8px; }
.discovery-card__title { font-size: 13px; font-weight: 600; color: #e0e0e6; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.discovery-card__store { display: flex; align-items: center; gap: 4px; font-size: 12px; color: #6a6a7a; }
.discovery-card__keyword { display: flex; }
.discovery-card__meta { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-top: 4px; }
.discovery-card__meta-item { font-size: 12px; color: #9a9aaa; }
.discovery-card__meta-item--price { color: #ef4444; font-weight: 600; font-size: 14px; }
.discovery-card__masked { display: flex; align-items: center; gap: 6px; cursor: pointer; padding: 2px 8px; border-radius: 6px; background: rgba(255,255,255,0.04); transition: background 0.2s; }
.discovery-card__masked:hover { background: rgba(255,255,255,0.08); }
.discovery-card__masked-value { font-size: 12px; color: #6a6a7a; font-style: italic; }
.discovery-card__masked-hint { font-size: 10px; color: #409EFF; white-space: nowrap; }
.discovery-card__actions { padding: 8px 16px 12px; }
</style>
