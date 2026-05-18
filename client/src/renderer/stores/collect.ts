import { defineStore } from "pinia";
import { ref, computed } from "vue";
import api from "../utils/api";

export interface CollectStatus {
  isRunning: boolean;
  activeCount: number;
  queueLength: number;
  concurrency: number;
  resourceUsage: { cpu: number; memory: number; memoryMB: number };
}

export interface CollectResult {
  taskId: string;
  targetId: string;
  status: "success" | "failed" | "risk_detected";
  data?: Record<string, unknown>;
  error?: string;
  collectedAt: string;
}

export const useCollectStore = defineStore("collect", () => {
  const status = ref<CollectStatus>({
    isRunning: false,
    activeCount: 0,
    queueLength: 0,
    concurrency: 3,
    resourceUsage: { cpu: 0, memory: 0, memoryMB: 0 },
  });
  const results = ref<CollectResult[]>([]);
  const riskAlerts = ref<CollectResult[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  const isCollecting = computed(() => status.value.isRunning);
  const hasRisks = computed(() => riskAlerts.value.length > 0);

  async function fetchStatus() {
    try {
      if (window.electronAPI) {
        const result = await window.electronAPI.invoke("collect:status");
        status.value = result as CollectStatus;
      } else {
        const { data } = await api.get("/collect/tasks");
        if (data.code === 0 && data.data) {
          const tasks = data.data.items || data.data || [];
          status.value.activeCount = tasks.filter((t: any) => t.status === "running").length;
          status.value.queueLength = tasks.filter((t: any) => t.status === "pending").length;
          status.value.isRunning = status.value.activeCount > 0;
        }
      }
    } catch {}
  }

  async function startCollect(tasks: Array<{ targetId: string; targetType: string; targetUrl?: string }>) {
    loading.value = true;
    error.value = null;
    try {
      if (window.electronAPI) {
        const tasksWithId = tasks.map((t) => ({
          ...t,
          id: crypto.randomUUID(),
        }));
        const result = await window.electronAPI.invoke("collect:start", tasksWithId);
        status.value.activeCount = (result as { activeCount: number }).activeCount;
        status.value.queueLength = (result as { queueLength: number }).queueLength;
        status.value.isRunning = true;
      } else {
        for (const task of tasks) {
          await api.post("/collect/tasks", {
            target_id: task.targetId,
            target_type: task.targetType,
            target_url: task.targetUrl,
          });
        }
        await fetchStatus();
      }
    } catch (err) {
      error.value = String(err);
    } finally {
      loading.value = false;
    }
  }

  async function cancelCollect(taskId: string) {
    try {
      if (window.electronAPI) {
        await window.electronAPI.invoke("collect:cancel", taskId);
      } else {
        await api.post(`/collect/tasks/${taskId}/cancel`);
      }
    } catch {}
  }

  async function clearQueue() {
    try {
      if (window.electronAPI) {
        await window.electronAPI.invoke("collect:clear-queue");
        status.value.queueLength = 0;
      }
    } catch {}
  }

  async function setConcurrency(value: number) {
    try {
      if (window.electronAPI) {
        const result = await window.electronAPI.invoke("concurrency:set", value);
        status.value.concurrency = (result as { current: number }).current;
      } else {
        status.value.concurrency = value;
      }
    } catch {}
  }

  async function getConcurrency() {
    try {
      if (window.electronAPI) {
        const result = await window.electronAPI.invoke("concurrency:get");
        status.value.concurrency = (result as { current: number }).current;
        status.value.resourceUsage = (result as { resourceUsage: CollectStatus["resourceUsage"] }).resourceUsage;
      }
    } catch {}
  }

  function addResult(result: CollectResult) {
    results.value.unshift(result);
    if (results.value.length > 200) {
      results.value = results.value.slice(0, 200);
    }
    if (result.status === "risk_detected") {
      riskAlerts.value.unshift(result);
    }
  }

  function clearResults() {
    results.value = [];
    riskAlerts.value = [];
  }

  function setupListeners() {
    if (!window.electronAPI) return;
    window.electronAPI.on("collect:result", (result: unknown) => {
      addResult(result as CollectResult);
    });
    window.electronAPI.on("collect:risk_alert", (result: unknown) => {
      addResult(result as CollectResult);
    });
    window.electronAPI.on("concurrency:changed", (data: unknown) => {
      const d = data as { to: number };
      status.value.concurrency = d.to;
    });
    window.electronAPI.on("resource:warning", (data: unknown) => {
      console.warn("资源警告:", data);
    });
  }

  return {
    status,
    results,
    riskAlerts,
    loading,
    error,
    isCollecting,
    hasRisks,
    fetchStatus,
    startCollect,
    cancelCollect,
    clearQueue,
    setConcurrency,
    getConcurrency,
    addResult,
    clearResults,
    setupListeners,
  };
});
