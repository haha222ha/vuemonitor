<template>
  <div class="task-item" :class="`task-item--${task.status}`">
    <div class="task-item__left">
      <div :class="['task-item__dot', `task-item__dot--${task.status}`]" />
    </div>
    <div class="task-item__body">
      <div class="task-item__header">
        <span class="task-item__name">{{ taskLabel }}</span>
        <el-tag size="small" :type="platformTagType(task.platform)">{{ task.platform }}</el-tag>
        <el-tag size="small" :type="statusTagType(task.status)">{{ statusLabel(task.status) }}</el-tag>
        <span class="task-item__time">{{ formatTime(task.created_at) }}</span>
      </div>
      <div class="task-item__meta">
        <span>类型: {{ taskTypeLabel(task.task_type) }}</span>
        <span>目标: {{ task.target_ids?.length || 0 }}个</span>
        <span v-if="task.result_summary">{{ task.result_summary }}</span>
        <span v-if="task.error_message" class="task-item__error">{{ task.error_message }}</span>
      </div>
      <el-progress
        v-if="task.status === 'running' && task.progress > 0"
        :percentage="task.progress"
        :stroke-width="4"
        :show-text="true"
        :color="progressColor(task.status)"
        style="margin-top: 6px"
      />
    </div>
    <div class="task-item__actions">
      <el-button v-if="task.status === 'running' || task.status === 'pending'" size="small" text type="danger" @click="$emit('cancel', task.id)">取消</el-button>
      <el-button v-if="task.status === 'failed' || task.status === 'cancelled'" size="small" text type="primary" @click="$emit('retry', task.id)">重试</el-button>
      <el-button size="small" text @click="$emit('detail', task.id)">详情</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

export interface SchedulerTask {
  id: string;
  task_type: string;
  platform: string;
  target_ids?: string[];
  status: string;
  progress?: number;
  created_at?: string;
  completed_at?: string;
  result_summary?: string;
  error_message?: string;
}

const props = defineProps<{ task: SchedulerTask }>();

defineEmits<{
  cancel: [id: string];
  retry: [id: string];
  detail: [id: string];
}>();

const taskLabel = computed(() => `${taskTypeLabel(props.task.task_type)} - ${props.task.platform}`);

function platformTagType(platform: string) {
  const map: Record<string, string> = { xhs: "danger", taobao: "warning", jd: "primary", pdd: "success", douyin: "" };
  return map[platform] || "info";
}

function statusTagType(status: string) {
  const map: Record<string, string> = { pending: "info", running: "", completed: "success", failed: "danger", cancelled: "warning" };
  return map[status] || "info";
}

function statusLabel(status: string) {
  const map: Record<string, string> = { pending: "待执行", running: "运行中", completed: "已完成", failed: "失败", cancelled: "已取消" };
  return map[status] || status;
}

function taskTypeLabel(type: string) {
  const map: Record<string, string> = { product: "商品采集", shop: "店铺采集", category: "品类采集" };
  return map[type] || type;
}

function progressColor(status: string) {
  const map: Record<string, string> = { running: "#4F46E5", pending: "#94A3B8", completed: "#10B981", failed: "#EF4444" };
  return map[status] || "#4F46E5";
}

function formatTime(dateStr: string | null | undefined) {
  if (!dateStr) return "-";
  const d = new Date(dateStr);
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")}`;
}
</script>

<style scoped>
.task-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
  background: var(--color-bg-card);
  transition: border-color 0.2s;
}

.task-item:hover {
  border-color: var(--color-primary);
}

.task-item--running {
  border-left: 3px solid #4F46E5;
}

.task-item--failed {
  border-left: 3px solid #EF4444;
}

.task-item--completed {
  border-left: 3px solid #10B981;
}

.task-item__left {
  padding-top: 4px;
}

.task-item__dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.task-item__dot--pending { background: #94A3B8; }
.task-item__dot--running { background: #4F46E5; animation: pulse 2s infinite; }
.task-item__dot--completed { background: #10B981; }
.task-item__dot--failed { background: #EF4444; }
.task-item__dot--cancelled { background: #F59E0B; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.task-item__body {
  flex: 1;
  min-width: 0;
}

.task-item__header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.task-item__name {
  font-weight: 600;
  font-size: var(--text-sm);
  color: var(--color-text-primary);
}

.task-item__time {
  margin-left: auto;
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.task-item__meta {
  display: flex;
  gap: 16px;
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  flex-wrap: wrap;
}

.task-item__error {
  color: #EF4444;
}

.task-item__actions {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex-shrink: 0;
}
</style>
