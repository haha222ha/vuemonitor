<template>
  <div class="alert-event-list">
    <div class="events__toolbar">
      <el-radio-group :model-value="severityFilter" size="small" @change="(v: string) => $emit('filter-change', v)">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="critical">紧急</el-radio-button>
        <el-radio-button value="warning">警告</el-radio-button>
        <el-radio-button value="info">提示</el-radio-button>
      </el-radio-group>
      <el-button size="small" :disabled="selectedIds.length === 0" @click="$emit('batch-acknowledge', selectedIds)">
        批量确认 ({{ selectedIds.length }})
      </el-button>
    </div>

    <EmptyState
      v-if="events.length === 0 && !loading"
      :icon="Warning"
      title="暂无告警事件"
      description="一切正常，异动触发时会在此显示"
    />

    <div v-else class="events__list">
      <div
        v-for="evt in events"
        :key="evt.id"
        :class="['event-item', `event-item--${evt.severity}`, { 'event-item--ack': evt.is_acknowledged }]"
      >
        <el-checkbox
          v-if="!evt.is_acknowledged"
          :model-value="selectedIds.includes(evt.id)"
          @change="(val: boolean) => toggleSelect(evt.id, val)"
          class="event-item__check"
        />
        <div class="event-item__severity" :class="`event-item__severity--${evt.severity}`" />
        <div class="event-item__body">
          <div class="event-item__header">
            <span class="event-item__title">{{ evt.title }}</span>
            <el-tag size="small" :type="severityTagType(evt.severity)" effect="dark">{{ severityLabel(evt.severity) }}</el-tag>
          </div>
          <div class="event-item__detail" v-if="evt.detail">{{ evt.detail }}</div>
          <div class="event-item__meta">
            <span v-if="evt.metric_value != null">指标值: {{ evt.metric_value }}</span>
            <span v-if="evt.threshold_value != null">阈值: {{ evt.threshold_value }}</span>
            <span class="event-item__time">{{ formatTime(evt.created_at) }}</span>
          </div>
        </div>
        <div class="event-item__actions">
          <el-button v-if="!evt.is_acknowledged" size="small" type="warning" plain @click="$emit('acknowledge', evt.id)">
            确认
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { Warning } from "@element-plus/icons-vue";
import EmptyState from "./EmptyState.vue";

interface AlertEvent {
  id: string;
  title: string;
  detail?: string;
  severity: string;
  metric_value?: number;
  threshold_value?: number;
  is_acknowledged: boolean;
  created_at: string;
  [key: string]: any;
}

defineProps<{
  events: AlertEvent[];
  loading: boolean;
  severityFilter: string;
}>();

defineEmits<{
  "filter-change": [value: string];
  acknowledge: [eventId: string];
  "batch-acknowledge": [ids: string[]];
}>();

const selectedIds = ref<string[]>([]);

function toggleSelect(eventId: string, checked: boolean) {
  if (checked) {
    if (!selectedIds.value.includes(eventId)) selectedIds.value.push(eventId);
  } else {
    selectedIds.value = selectedIds.value.filter(id => id !== eventId);
  }
}

function severityTagType(severity: string): string {
  const map: Record<string, string> = { critical: "danger", high: "danger", warning: "warning", info: "info", low: "info" };
  return map[severity] || "info";
}

function severityLabel(severity: string): string {
  const map: Record<string, string> = { critical: "紧急", high: "高", warning: "中", info: "低", low: "低" };
  return map[severity] || severity;
}

function formatTime(dateStr: string): string {
  const d = new Date(dateStr);
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")}`;
}
</script>

<style scoped>
.events__toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.events__list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.event-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  border-left: 4px solid transparent;
  transition: all 0.2s;
}

.event-item--critical { border-left-color: #EF4444; }
.event-item--warning { border-left-color: #F59E0B; }
.event-item--info { border-left-color: #10B981; }

.event-item--ack {
  opacity: 0.55;
  border-left-color: var(--color-border);
}

.event-item__check {
  margin-top: 2px;
}

.event-item__severity {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
}

.event-item__severity--critical { background: #EF4444; }
.event-item__severity--warning { background: #F59E0B; }
.event-item__severity--info { background: #10B981; }

.event-item__body {
  flex: 1;
  min-width: 0;
}

.event-item__header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.event-item__title {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-primary);
}

.event-item__detail {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  margin-bottom: 4px;
}

.event-item__meta {
  display: flex;
  gap: 12px;
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.event-item__time {
  margin-left: auto;
}

.event-item__actions {
  flex-shrink: 0;
}
</style>
