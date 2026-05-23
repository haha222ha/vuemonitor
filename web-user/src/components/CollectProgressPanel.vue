<template>
  <el-drawer v-model="visible" title="采集进度" size="420px" direction="rtl" @close="$emit('close')">
    <div class="progress-panel">
      <div class="progress-panel__summary">
        <el-progress :percentage="progressPercent" :status="progressStatus" :stroke-width="8" text-inside />
        <div class="progress-panel__stats">
          <div class="stat stat--success">
            <span class="stat__value">{{ successCount }}</span>
            <span class="stat__label">成功</span>
          </div>
          <div class="stat stat--danger">
            <span class="stat__value">{{ failedCount }}</span>
            <span class="stat__label">失败</span>
          </div>
          <div class="stat stat--pending">
            <span class="stat__value">{{ pendingCount }}</span>
            <span class="stat__label">等待中</span>
          </div>
        </div>
      </div>

      <div class="progress-panel__controls">
        <el-button size="small" type="primary" @click="pauseQueue" v-if="isRunning">⏸ 暂停</el-button>
        <el-button size="small" type="success" @click="resumeQueue" v-else-if="pendingCount > 0">▶ 继续</el-button>
        <el-button size="small" type="danger" @click="stopQueue">⏹ 停止</el-button>
      </div>

      <div class="progress-panel__log">
        <div class="log-header">
          <span>采集日志</span>
          <span>{{ results.length }} 条记录</span>
        </div>
        <div class="log-content">
          <div v-for="(r, i) in results.slice(-50)" :key="i" :class="['log-item', `log-item--${r.status}`]">
            <span class="log-item__time">{{ formatTime(r.collected_at || r.created_at) }}</span>
            <span class="log-item__status">{{ statusIcon(r.status) }}</span>
            <span class="log-item__id">{{ truncateId(r.target_id || r.product_id) }}</span>
            <span v-if="r.error_message || r.error" class="log-item__error">{{ r.error_message || r.error }}</span>
          </div>
          <div v-if="results.length === 0 && !loading" class="log-empty">暂无采集记录</div>
          <div v-if="loading" class="log-empty"><el-icon class="is-loading" :size="16" /><span style="margin-left:8px">加载中...</span></div>
        </div>
      </div>

      <div v-if="failedCount > 0" class="progress-panel__footer">
        <el-button type="warning" @click="retryFailed">🔄 重试失败项 ({{ failedCount }})</el-button>
      </div>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import api from "../utils/api";

const props = defineProps<{
  modelValue: boolean;
}>();

const emit = defineEmits<{
  "update:modelValue": [val: boolean];
  close: [];
}>();

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit("update:modelValue", v),
});

const loading = ref(false);
const isRunning = ref(false);
const results = ref<any[]>([]);
const pendingCount = ref(0);

const successCount = computed(() => results.value.filter((r) => r.status === "success").length);
const failedCount = computed(() => results.value.filter((r) => r.status === "failed").length);
const totalProcessed = computed(() => successCount.value + failedCount.value);
const totalTasks = computed(() => totalProcessed.value + pendingCount.value);

const progressPercent = computed(() => {
  if (totalTasks.value === 0) return 0;
  return Math.round((totalProcessed.value / totalTasks.value) * 100);
});

const progressStatus = computed(() => {
  if (failedCount.value > 0 && successCount.value === 0) return "exception";
  if (isRunning.value) return undefined;
  if (failedCount.value > 0) return "warning";
  return "success";
});

async function fetchStatus() {
  try {
    const { data } = await api.get("/collect/status");
    if (data.code === 0) {
      const d = data.data;
      isRunning.value = d.is_running ?? false;
      pendingCount.value = d.queue_length ?? 0;
    }
  } catch {}
}

async function fetchResults() {
  loading.value = true;
  try {
    const { data } = await api.get("/collect/results", { params: { limit: 50 } });
    if (data.code === 0) {
      results.value = data.data?.results || data.data || [];
    }
  } catch {} finally {
    loading.value = false;
  }
}

function formatTime(dateStr?: string): string {
  if (!dateStr) return "--:--:--";
  const date = new Date(dateStr);
  return date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function truncateId(id?: string): string {
  if (!id) return "-";
  return id.length > 10 ? id.slice(0, 8) + "…" : id;
}

function statusIcon(status: string): string {
  switch (status) {
    case "success": return "✅";
    case "failed": return "❌";
    case "risk_detected": return "⚠️";
    default: return "🔄";
  }
}

async function pauseQueue() {
  try { await api.post("/collect/pause"); isRunning.value = false; } catch {}
}

async function resumeQueue() {
  try { await api.post("/collect/resume"); isRunning.value = true; } catch {}
}

async function stopQueue() {
  try { await api.post("/collect/stop"); isRunning.value = false; pendingCount.value = 0; } catch {}
}

async function retryFailed() {
  try {
    const failedIds = results.value.filter((r) => r.status === "failed").map((r) => r.target_id || r.product_id).filter(Boolean);
    await api.post("/collect/retry", { task_ids: failedIds });
    fetchResults();
  } catch {}
}

let timer: ReturnType<typeof setInterval> | null = null;

watch(visible, (v) => {
  if (v) {
    fetchStatus();
    fetchResults();
    timer = setInterval(() => { fetchStatus(); fetchResults(); }, 3000);
  } else {
    if (timer) { clearInterval(timer); timer = null; }
  }
});
</script>

<style scoped>
.progress-panel { height: 100%; display: flex; flex-direction: column; padding: 0; }
.progress-panel__summary { padding: 16px; border-bottom: 1px solid rgba(255,255,255,0.08); }
.progress-panel__header { margin-bottom: 16px; }
.progress-panel__stats { display: flex; gap: 12px; margin-top: 12px; }
.stat { flex: 1; text-align: center; padding: 8px; border-radius: 8px; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); }
.stat--success .stat__value { color: #22c55e; font-size: 20px; font-weight: 700; display: block; }
.stat--danger .stat__value { color: #ef4444; font-size: 20px; font-weight: 700; display: block; }
.stat--pending .stat__value { color: #f59e0b; font-size: 20px; font-weight: 700; display: block; }
.stat__label { font-size: 11px; color: #6a6a7a; margin-top: 2px; display: block; }
.progress-panel__controls { display: flex; gap: 8px; padding: 12px 16px; border-bottom: 1px solid rgba(255,255,255,0.08); }
.progress-panel__log { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.log-header { display: flex; justify-content: space-between; padding: 12px 16px; font-size: 13px; font-weight: 600; color: #c0c0cc; border-bottom: 1px solid rgba(255,255,255,0.08); }
.log-content { flex: 1; overflow-y: auto; padding: 8px 16px; }
.log-item { display: flex; align-items: center; gap: 8px; padding: 5px 0; font-size: 12px; border-bottom: 1px solid rgba(255,255,255,0.04); }
.log-item--success { color: #22c55e; }
.log-item--failed { color: #ef4444; }
.log-item--risk_detected { color: #f59e0b; }
.log-item__time { font-size: 10px; color: #5a5a6a; min-width: 68px; }
.log-item__id { flex: 1; font-family: monospace; color: #9a9aaa; }
.log-item__error { font-size: 10px; color: #ef4444; max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.log-empty { padding: 40px 0; text-align: center; color: #5a5a6a; font-size: 13px; }
.progress-panel__footer { padding: 12px 16px; border-top: 1px solid rgba(255,255,255,0.08); }
</style>
