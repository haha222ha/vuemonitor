<template>
  <div class="rule-card">
    <div class="rule-card__header">
      <div class="rule-card__icon" :style="{ background: typeBg(rule.rule_type) }">
        <el-icon :size="18" :color="typeColor(rule.rule_type)">
          <component :is="typeIcon(rule.rule_type)" />
        </el-icon>
      </div>
      <div class="rule-card__info">
        <div class="rule-card__name">{{ rule.rule_name }}</div>
        <el-tag size="small" :type="typeTagType(rule.rule_type)">{{ typeLabel(rule.rule_type) }}</el-tag>
        <el-tag v-if="rule.severity && rule.severity !== 'warning'" size="small" :type="severityTagType(rule.severity)" effect="dark">{{ severityLabel(rule.severity) }}</el-tag>
      </div>
      <el-switch :model-value="rule.is_active" size="small" @change="$emit('toggle', rule)" />
    </div>

    <div class="rule-card__conditions">
      <span
        v-for="(cond, idx) in parseConditions(rule.conditions)"
        :key="idx"
        class="condition-chip"
        :style="{ background: cond.bg, color: cond.color }"
      >
        {{ cond.text }}
      </span>
    </div>

    <div class="rule-card__footer">
      <div class="rule-card__meta">
        <el-badge :value="rule.trigger_count" :type="rule.trigger_count > 0 ? 'danger' : 'info'" :hidden="rule.trigger_count === 0" />
        <span class="rule-card__time" v-if="rule.last_triggered_at">
          最近触发: {{ formatTime(rule.last_triggered_at) }}
        </span>
      </div>
      <div class="rule-card__actions">
        <el-button size="small" text type="primary" @click="$emit('edit', rule)">编辑</el-button>
        <el-button size="small" text type="danger" @click="$emit('delete', rule.id)">删除</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  PriceTag, TrendCharts, ShoppingCart, Star, Setting,
} from "@element-plus/icons-vue";

interface AlertRule {
  id: string;
  rule_name: string;
  rule_type: string;
  conditions: Record<string, any>;
  is_active: boolean;
  trigger_count: number;
  last_triggered_at?: string;
  severity?: string;
  [key: string]: any;
}

defineProps<{
  rule: AlertRule;
}>();

defineEmits<{
  toggle: [rule: AlertRule];
  edit: [rule: AlertRule];
  delete: [id: string];
}>();

const TYPE_CONFIG: Record<string, { label: string; icon: typeof PriceTag; color: string; tagType: string; bg: string }> = {
  price_drop: { label: "价格下跌", icon: PriceTag, color: "#F56C6C", tagType: "danger", bg: "#FEF0F0" },
  sales_surge: { label: "销量飙升", icon: TrendCharts, color: "#67C23A", tagType: "success", bg: "#F0F9EB" },
  stock_change: { label: "库存变化", icon: ShoppingCart, color: "#E6A23C", tagType: "warning", bg: "#FDF6EC" },
  rating_drop: { label: "评分下降", icon: Star, color: "#F56C6C", tagType: "danger", bg: "#FEF0F0" },
  custom: { label: "自定义", icon: Setting, color: "#909399", tagType: "info", bg: "#F4F4F5" },
};

function typeIcon(type: string) { return TYPE_CONFIG[type]?.icon || Setting; }
function typeColor(type: string) { return TYPE_CONFIG[type]?.color || "#909399"; }
function typeBg(type: string) { return TYPE_CONFIG[type]?.bg || "#F5F7FA"; }
function typeLabel(type: string) { return TYPE_CONFIG[type]?.label || type; }
function typeTagType(type: string) { return TYPE_CONFIG[type]?.tagType || "info"; }

function severityTagType(severity: string): string {
  const map: Record<string, string> = { critical: "danger", high: "danger", warning: "warning", info: "info", low: "info" };
  return map[severity] || "info";
}

function severityLabel(severity: string): string {
  const map: Record<string, string> = { critical: "紧急", high: "高", warning: "中", info: "低", low: "低" };
  return map[severity] || severity;
}

function parseConditions(conditions: Record<string, any>): Array<{ text: string; bg: string; color: string }> {
  if (!conditions) return [{ text: "-", bg: "#F5F7FA", color: "#909399" }];
  const chips: Array<{ text: string; bg: string; color: string }> = [];
  if (conditions.threshold) chips.push({ text: `阈值 ${conditions.threshold}%`, bg: "#FEF0F0", color: "#F56C6C" });
  if (conditions.below_price) chips.push({ text: `低于¥${conditions.below_price}`, bg: "#FEF0F0", color: "#F56C6C" });
  if (conditions.absolute_increase) chips.push({ text: `增量 ${conditions.absolute_increase}件`, bg: "#F0F9EB", color: "#67C23A" });
  if (conditions.below_rating) chips.push({ text: `低于${conditions.below_rating}分`, bg: "#FEF0F0", color: "#F56C6C" });
  if (conditions.rating_decrease) chips.push({ text: `下降${conditions.rating_decrease}分`, bg: "#FDF6EC", color: "#E6A23C" });
  if (conditions.stock_events?.length) chips.push({ text: conditions.stock_events.join("/"), bg: "#FDF6EC", color: "#E6A23C" });
  if (conditions.stock_drop_percent) chips.push({ text: `库存降${conditions.stock_drop_percent}%`, bg: "#FDF6EC", color: "#E6A23C" });
  if (conditions.window_hours) chips.push({ text: `窗口${conditions.window_hours}h`, bg: "#ECF5FF", color: "#409EFF" });
  if (conditions.review_count_above) chips.push({ text: `评论>${conditions.review_count_above}`, bg: "#F4F4F5", color: "#909399" });
  return chips.length > 0 ? chips : [{ text: "-", bg: "#F5F7FA", color: "#909399" }];
}

function formatTime(dateStr: string): string {
  const d = new Date(dateStr);
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")}`;
}
</script>

<style scoped>
.rule-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: 16px;
  transition: all 0.2s;
}

.rule-card:hover {
  border-color: var(--color-primary);
  box-shadow: 0 2px 12px rgba(79, 70, 229, 0.08);
}

.rule-card__header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.rule-card__icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-base);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.rule-card__info {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.rule-card__name {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rule-card__conditions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 12px;
}

.condition-chip {
  display: inline-block;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  line-height: 1.5;
}

.rule-card__footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid var(--color-border-light);
}

.rule-card__meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rule-card__time {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.rule-card__actions {
  display: flex;
  gap: 4px;
}
</style>
