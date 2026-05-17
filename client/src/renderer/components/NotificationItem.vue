<template>
  <div
    class="notification-item"
    :class="{ unread: !item.is_read, [`severity-${item.severity}`]: item.severity }"
    @click="$emit('click', item)"
  >
    <div class="notification-dot" v-if="!item.is_read" />
    <div class="notification-icon" :style="{ background: iconBg(item.type) }">
      <el-icon :size="20" :color="typeIconColor(item.type)">
        <component :is="typeIcon(item.type)" />
      </el-icon>
    </div>
    <div class="notification-body">
      <div class="notification-header">
        <span class="notification-title">{{ item.title }}</span>
        <div class="notification-tags">
          <el-tag size="small" :type="typeTagType(item.type)" effect="plain">{{ typeLabel(item.type) }}</el-tag>
          <el-tag v-if="item.severity" size="small" :type="severityTagType(item.severity)" effect="dark">{{ severityLabel(item.severity) }}</el-tag>
          <el-tag size="small" :type="categoryTagType(item.type)" effect="plain" class="category-tag">
            {{ categoryLabel(item.type) }}
          </el-tag>
        </div>
      </div>
      <div class="notification-content">{{ item.content }}</div>
      <div class="notification-footer">
        <span class="notification-time">{{ formatTime(item.created_at) }}</span>
        <div class="notification-actions">
          <el-button
            v-if="item.source === 'alert_event' && !(item as any).is_acknowledged"
            link
            size="small"
            type="warning"
            @click.stop="$emit('acknowledge-alert', item)"
          >确认告警</el-button>
          <el-button
            v-if="!item.is_read && item.source !== 'alert_event'"
            link
            size="small"
            type="primary"
            @click.stop="$emit('mark-read', item.id, item.source === 'alert_event' ? 'cloud' : item.source)"
          >标为已读</el-button>
          <el-button
            link
            size="small"
            type="danger"
            @click.stop="$emit('delete', item.id, item.source === 'alert_event' ? 'cloud' : item.source)"
          >删除</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  Warning, TrendCharts, PriceTag, ShoppingCart,
  Star, InfoFilled, Bell, Monitor,
} from "@element-plus/icons-vue";
import type { NotificationItem } from "../stores/notification";

defineProps<{
  item: NotificationItem;
}>();

defineEmits<{
  click: [item: NotificationItem];
  "acknowledge-alert": [item: NotificationItem];
  "mark-read": [id: string, source: string];
  delete: [id: string, source: string];
}>();

const CATEGORY_MAP: Record<string, "alert" | "ai" | "system"> = {
  price_drop: "alert", sales_surge: "alert", stock_change: "alert", rating_drop: "alert",
  risk_warning: "alert", monitor_triggered: "alert", alert_event: "alert",
  ai_analysis: "ai", system: "system",
};

const TYPE_CONFIG: Record<string, { label: string; icon: typeof Warning; color: string; tagType: string; bg: string }> = {
  price_drop: { label: "降价", icon: PriceTag, color: "#F56C6C", tagType: "danger", bg: "#FEF0F0" },
  sales_surge: { label: "销量飙升", icon: TrendCharts, color: "#67C23A", tagType: "success", bg: "#F0F9EB" },
  stock_change: { label: "库存变化", icon: ShoppingCart, color: "#E6A23C", tagType: "warning", bg: "#FDF6EC" },
  rating_drop: { label: "评分下降", icon: Star, color: "#F56C6C", tagType: "danger", bg: "#FEF0F0" },
  risk_warning: { label: "风险预警", icon: Warning, color: "#F56C6C", tagType: "danger", bg: "#FEF0F0" },
  ai_analysis: { label: "AI分析", icon: InfoFilled, color: "#409EFF", tagType: "", bg: "#ECF5FF" },
  monitor_triggered: { label: "监控触发", icon: Monitor, color: "#E6A23C", tagType: "warning", bg: "#FDF6EC" },
  alert_event: { label: "异动告警", icon: Warning, color: "#F56C6C", tagType: "danger", bg: "#FEF0F0" },
  system: { label: "系统通知", icon: Bell, color: "#909399", tagType: "info", bg: "#F4F4F5" },
};

function typeIcon(type: string) { return TYPE_CONFIG[type]?.icon || Bell; }
function typeIconColor(type: string) { return TYPE_CONFIG[type]?.color || "#909399"; }
function iconBg(type: string) { return TYPE_CONFIG[type]?.bg || "#F5F7FA"; }
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

function categoryTagType(type: string): string {
  const cat = CATEGORY_MAP[type];
  if (cat === "alert") return "danger";
  if (cat === "ai") return "";
  return "info";
}

function categoryLabel(type: string): string {
  const cat = CATEGORY_MAP[type];
  if (cat === "alert") return "异动预警";
  if (cat === "ai") return "AI分析";
  return "系统";
}

function formatTime(dateStr: string | null): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  if (diff < 60000) return "刚刚";
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`;
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")}`;
}
</script>

<style scoped>
.notification-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
  background: var(--color-bg-card);
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.notification-item:hover {
  border-color: var(--color-primary);
  box-shadow: 0 2px 8px rgba(79, 70, 229, 0.1);
}

.notification-item.unread {
  background: #f0f4ff;
  border-color: #d0dfff;
}

.notification-dot {
  position: absolute;
  top: 16px;
  left: 6px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-primary);
}

.notification-icon {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-base);
  display: flex;
  align-items: center;
  justify-content: center;
}

.notification-body {
  flex: 1;
  min-width: 0;
}

.notification-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.notification-title {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-text-primary);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.notification-tags {
  display: flex;
  gap: 4px;
  align-items: center;
  flex-shrink: 0;
}

.notification-content {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.notification-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 6px;
}

.notification-time {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.notification-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.notification-item:hover .notification-actions {
  opacity: 1;
}

.category-tag {
  font-size: 11px;
  padding: 0 4px;
  height: 20px;
  line-height: 18px;
}

.notification-item.severity-critical {
  border-left: 3px solid #F56C6C;
}

.notification-item.severity-high {
  border-left: 3px solid #E6A23C;
}

.notification-item.severity-warning {
  border-left: 3px solid #E6A23C;
}

.notification-item.severity-info {
  border-left: 3px solid #909399;
}
</style>
