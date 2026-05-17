<template>
  <el-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)" title="从模板创建规则" width="520px" class="modern-dialog">
    <div class="template-grid">
      <div v-for="tpl in ruleTemplates" :key="tpl.id" class="template-card" @click="$emit('select', tpl)">
        <div class="template-icon" :style="{ background: tpl.bg }">
          <el-icon :size="24" :color="tpl.color"><component :is="tpl.icon" /></el-icon>
        </div>
        <div class="template-info">
          <div class="template-name">{{ tpl.name }}</div>
          <div class="template-desc">{{ tpl.description }}</div>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { PriceTag, TrendCharts, ShoppingCart, Star, Bell } from "@element-plus/icons-vue";

defineProps<{ modelValue: boolean }>();
defineEmits<{
  (e: "update:modelValue", value: boolean): void;
  (e: "select", tpl: any): void;
}>();

const ruleTemplates = [
  { id: "price_alert_20", name: "价格下跌20%预警", description: "当商品价格跌幅超过20%时立即通知", rule_type: "price_drop", icon: PriceTag, color: "#F56C6C", bg: "#FEF0F0", conditions: { threshold: 20 } },
  { id: "price_below_50", name: "价格低于50元", description: "当商品价格跌破50元时通知", rule_type: "price_drop", icon: PriceTag, color: "#F56C6C", bg: "#FEF0F0", conditions: { threshold: 0, below_price: 50 } },
  { id: "sales_2x", name: "销量翻倍监控", description: "24小时内销量增长超过100%", rule_type: "sales_surge", icon: TrendCharts, color: "#67C23A", bg: "#F0F9EB", conditions: { threshold: 100, window_hours: 24 } },
  { id: "sales_surge_50", name: "销量激增50%", description: "6小时内销量增长超过50%", rule_type: "sales_surge", icon: TrendCharts, color: "#67C23A", bg: "#F0F9EB", conditions: { threshold: 50, window_hours: 6 } },
  { id: "stock_out", name: "缺货提醒", description: "商品变为缺货状态时通知", rule_type: "stock_change", icon: ShoppingCart, color: "#E6A23C", bg: "#FDF6EC", conditions: { stock_events: ["out_of_stock"] } },
  { id: "rating_below_4", name: "评分低于4.0", description: "商品评分降至4.0以下时预警", rule_type: "rating_drop", icon: Star, color: "#F56C6C", bg: "#FEF0F0", conditions: { below_rating: 4.0 } },
  { id: "rating_drop_05", name: "评分骤降0.5", description: "评分单次下降超过0.5分时通知", rule_type: "rating_drop", icon: PriceTag, color: "#E6A23C", bg: "#FDF6EC", conditions: { rating_decrease: 0.5 } },
  { id: "comprehensive", name: "综合监控", description: "价格跌10%+销量增50%+缺货+评分降", rule_type: "price_drop", icon: Bell, color: "#409EFF", bg: "#ECF5FF", conditions: { threshold: 10 } },
];
</script>

<style scoped>
.template-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.template-card { display: flex; align-items: center; gap: 12px; padding: 14px; border: 1px solid var(--color-border-light); border-radius: var(--radius-lg); cursor: pointer; transition: all 0.2s; }
.template-card:hover { border-color: var(--color-primary); box-shadow: 0 2px 8px rgba(79, 70, 229, 0.1); }
.template-icon { flex-shrink: 0; width: 44px; height: 44px; border-radius: var(--radius-base); display: flex; align-items: center; justify-content: center; }
.template-info { flex: 1; min-width: 0; }
.template-name { font-size: var(--text-sm); font-weight: 500; color: var(--color-text-primary); }
.template-desc { font-size: var(--text-xs); color: var(--color-text-tertiary); margin-top: 2px; }
.modern-dialog :deep(.el-dialog__header) { padding: 20px 24px; border-bottom: 1px solid var(--color-border-light); margin-right: 0; }
.modern-dialog :deep(.el-dialog__title) { font-size: var(--text-lg); font-weight: 600; color: var(--color-text-primary); }
.modern-dialog :deep(.el-dialog__body) { padding: 24px; }
.modern-dialog :deep(.el-dialog__footer) { padding: 16px 24px; border-top: 1px solid var(--color-border-light); }
</style>
