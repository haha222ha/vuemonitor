<template>
  <div class="alert-card">
    <div class="alert-card__header">
      <div class="alert-card__title-group">
        <el-icon class="alert-card__icon" :size="20"><Warning /></el-icon>
        <h3 class="alert-card__title">异动监控</h3>
        <el-badge v-if="events.length > 0" :value="events.length" :max="99" />
      </div>
      <el-button size="small" @click="$emit('refresh')">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>
    <div class="alert-card__body">
      <div v-if="loading" class="alert-card__loading">
        <el-skeleton :rows="3" animated />
      </div>
      <div v-else-if="events.length > 0" class="alert-list">
        <div
          v-for="evt in events.slice(0, 5)"
          :key="evt.id"
          :class="['alert-item', `alert-item--${evt.severity}`, { 'alert-item--acknowledged': evt.is_acknowledged }]"
        >
          <div class="alert-item__severity" :class="`alert-item__severity--${evt.severity}`" />
          <div class="alert-item__content">
            <div class="alert-item__header-row">
              <span class="alert-item__title">{{ evt.title }}</span>
              <el-tag
                :type="severityTagType(evt.severity)"
                size="small"
                effect="dark"
                class="alert-item__badge"
              >
                {{ severityLabel(evt.severity) }}
              </el-tag>
            </div>
            <div class="alert-item__detail">{{ evt.detail }}</div>
            <div class="alert-item__time">{{ formatAlertTime(evt.created_at) }}</div>
          </div>
          <el-button
            v-if="!evt.is_acknowledged"
            size="small"
            text
            type="primary"
            @click="$emit('acknowledge', String(evt.id))"
          >
            确认
          </el-button>
        </div>
      </div>
      <EmptyState
        v-else
        :icon="CircleCheck"
        title="一切正常"
        description="暂无异动，商品数据平稳"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { Warning, Refresh, CircleCheck } from "@element-plus/icons-vue";
import EmptyState from "./EmptyState.vue";

interface AlertEvent {
  id: string | number;
  title: string;
  detail?: string;
  severity: "critical" | "warning" | "info";
  is_acknowledged?: boolean;
  created_at?: string;
}

defineProps<{
  events: AlertEvent[];
  loading: boolean;
}>();

defineEmits<{
  refresh: [];
  acknowledge: [id: string];
}>();

function formatAlertTime(timestamp?: string): string {
  if (!timestamp) return "";
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes}分钟前`;
  if (hours < 24) return `${hours}小时前`;
  if (days < 7) return `${days}天前`;
  return date.toLocaleDateString("zh-CN");
}

function severityLabel(severity: string): string {
  const map: Record<string, string> = { critical: "严重", warning: "警告", info: "提示" };
  return map[severity] || severity;
}

function severityTagType(severity: string): "" | "success" | "warning" | "danger" | "info" {
  const map: Record<string, "" | "success" | "warning" | "danger" | "info"> = {
    critical: "danger",
    warning: "warning",
    info: "info",
  };
  return map[severity] || "info";
}
</script>

<style scoped>
.alert-card__header {
  padding: 20px 24px;
  border-bottom: 1px solid var(--color-border-light);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.alert-card__title-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.alert-card__icon {
  color: #EF4444;
}

.alert-card__title {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-text-primary);
}

.alert-card__body {
  padding: 20px 24px;
}

.alert-card__loading {
  padding: 16px 0;
}

.alert-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.alert-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 14px 16px;
  background: var(--color-bg-page);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-base);
  transition: all 0.2s;
}

.alert-item:hover {
  background: var(--color-bg-hover);
  border-color: var(--color-border);
}

.alert-item--critical {
  border-left: 3px solid #EF4444;
}

.alert-item--warning {
  border-left: 3px solid #F59E0B;
}

.alert-item--info {
  border-left: 3px solid #3B82F6;
}

.alert-item--acknowledged {
  opacity: 0.6;
}

.alert-item__severity {
  width: 4px;
  height: 100%;
  min-height: 36px;
  border-radius: 2px;
  flex-shrink: 0;
}

.alert-item__severity--critical {
  background: #EF4444;
}

.alert-item__severity--warning {
  background: #F59E0B;
}

.alert-item__severity--info {
  background: #3B82F6;
}

.alert-item__content {
  flex: 1;
  min-width: 0;
}

.alert-item__header-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.alert-item__title {
  font-size: var(--text-base);
  font-weight: 500;
  color: var(--color-text-primary);
}

.alert-item__badge {
  flex-shrink: 0;
}

.alert-item__detail {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  margin-top: 4px;
  line-height: 1.5;
}

.alert-item__time {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-top: 6px;
}
</style>
