<template>
  <el-drawer
    v-model="visible"
    title="采集进度"
    size="420px"
    direction="rtl"
    :before-close="handleClose"
  >
    <div class="progress-panel">
      <div class="progress-panel__summary">
        <div class="progress-panel__header">
          <el-progress
            :percentage="progressPercent"
            :status="progressStatus"
            :stroke-width="8"
            text-inside
          />
        </div>
        <div class="progress-panel__stats">
          <el-statistic
            title="成功"
            :value="successCount"
            class="stat stat--success"
            suffix="个"
          />
          <el-statistic
            title="失败"
            :value="failedCount"
            class="stat stat--danger"
            suffix="个"
          />
          <el-statistic
            title="等待中"
            :value="pendingCount"
            class="stat stat--pending"
            suffix="个"
          />
        </div>
      </div>

      <div class="progress-panel__controls">
        <el-button
          v-if="collectStore.status.isRunning"
          size="small"
          type="primary"
          @click="pauseQueue"
        >
          ⏸ 暂停队列
        </el-button>
        <el-button
          v-else-if="collectStore.status.queueLength > 0"
          size="small"
          type="success"
          @click="resumeQueue"
        >
          ▶ 继续采集
        </el-button>
        <el-button size="small" type="danger" @click="stopQueue">
          ⏹ 停止采集
        </el-button>
        <el-button size="small" class="ml-auto" @click="clearResults">
          🗑 清空日志
        </el-button>
      </div>

      <div class="progress-panel__log">
        <div class="log-header">
          <span>采集日志</span>
          <span class="log-count">{{ collectStore.results.length }} 条记录</span>
        </div>
        <div class="log-content">
          <div
            v-for="result in collectStore.results"
            :key="result.taskId"
            :class="['log-item', `log-item--${result.status}`]"
          >
            <span class="log-item__time">{{ formatTime(result.collectedAt) }}</span>
            <span class="log-item__status">{{ statusIcon(result.status) }}</span>
            <span class="log-item__id">{{ truncateId(result.targetId) }}</span>
            <span v-if="result.error" class="log-item__error">{{ result.error }}</span>
          </div>
          <div v-if="collectStore.results.length === 0" class="log-empty">
            <el-empty description="暂无采集记录" />
          </div>
        </div>
      </div>

      <div v-if="failedCount > 0" class="progress-panel__footer">
        <el-button type="warning" @click="retryFailed">
          🔄 重试失败项 ({{ failedCount }})
        </el-button>
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useCollectStore } from "../stores/collect";

const props = defineProps<{
  visible: boolean;
}>();

const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
}>();

const collectStore = useCollectStore();

const visible = ref(props.visible);

const successCount = computed(() =>
  collectStore.results.filter((r) => r.status === "success").length
);

const failedCount = computed(() =>
  collectStore.results.filter((r) => r.status === "failed").length
);

const pendingCount = computed(() => collectStore.status.queueLength);

const totalProcessed = computed(() => successCount.value + failedCount.value);

const totalTasks = computed(() => totalProcessed.value + pendingCount.value);

const progressPercent = computed(() => {
  if (totalTasks.value === 0) return 0;
  return Math.round((totalProcessed.value / totalTasks.value) * 100);
});

const progressStatus = computed(() => {
  if (failedCount.value > 0 && successCount.value === 0) return "exception";
  if (collectStore.status.isRunning) return "active";
  if (failedCount.value > 0) return "warning";
  return "success";
});

function formatTime(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleTimeString("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function truncateId(id: string): string {
  if (!id) return "-";
  if (id.length <= 8) return id;
  return id.slice(0, 8) + "…";
}

function statusIcon(status: string): string {
  switch (status) {
    case "success":
      return "✅";
    case "failed":
      return "❌";
    case "risk_detected":
      return "⚠️";
    default:
      return "🔄";
  }
}

async function pauseQueue() {
  await collectStore.clearQueue();
}

async function resumeQueue() {
  // Resume logic will be handled by the collect system
}

async function stopQueue() {
  await collectStore.clearQueue();
  collectStore.clearResults();
}

function clearResults() {
  collectStore.clearResults();
}

function retryFailed() {
  const failedResults = collectStore.results.filter((r) => r.status === "failed");
  const tasks = failedResults.map((r) => ({
    targetId: r.targetId,
    targetType: "product",
  }));
  collectStore.startCollect(tasks);
}

function handleClose() {
  emit("update:visible", false);
}

onMounted(() => {
  collectStore.setupListeners();
});

onUnmounted(() => {
  collectStore.clearResults();
});
</script>

<style lang="scss" scoped>
.progress-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 0;
}

.progress-panel__summary {
  padding: 16px;
  border-bottom: 1px solid #eee;
}

.progress-panel__header {
  margin-bottom: 16px;
}

.progress-panel__stats {
  display: flex;
  gap: 12px;
}

.stat {
  flex: 1;
  text-align: center;
  padding: 8px;
  border-radius: 8px;

  &--success {
    background: #f0fdf4;
    color: #16a34a;
  }

  &--danger {
    background: #fef2f2;
    color: #dc2626;
  }

  &--pending {
    background: #fefce8;
    color: #ca8a04;
  }
}

.progress-panel__controls {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid #eee;
}

.progress-panel__log {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.log-header {
  display: flex;
  justify-content: space-between;
  padding: 12px 16px;
  font-size: 14px;
  font-weight: 600;
  border-bottom: 1px solid #eee;
}

.log-count {
  font-size: 12px;
  font-weight: normal;
  color: #999;
}

.log-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px 16px;
}

.log-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  font-size: 13px;
  border-bottom: 1px solid #f5f5f5;

  &--success {
    color: #16a34a;
  }

  &--failed {
    color: #dc2626;
  }

  &--risk_detected {
    color: #ca8a04;
  }
}

.log-item__time {
  font-size: 11px;
  color: #999;
  min-width: 70px;
}

.log-item__status {
  font-size: 14px;
}

.log-item__id {
  flex: 1;
  font-family: monospace;
}

.log-item__error {
  font-size: 11px;
  color: #dc2626;
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.log-empty {
  padding: 40px 0;
}

.progress-panel__footer {
  padding: 12px 16px;
  border-top: 1px solid #eee;
}
</style>