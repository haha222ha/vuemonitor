import { defineStore } from "pinia";
import { ref } from "vue";
import api from "../utils/api";

interface Health {
  status: string;
  latency_ms: number;
  pool: any;
}

interface SystemMetrics {
  cpuUsage: number;
  memoryUsage: number;
  diskUsage: number;
  activeWsConnections: number;
  todayApiRequests: number;
  todayCollectTasks: number;
  avgResponseTimeMs: number;
  errorRate: number;
}

interface SecurityEvent {
  id: string;
  type: string;
  message: string;
  severity: string;
  created_at: string;
  [key: string]: any;
}

export const useSystemMonitorStore = defineStore("systemMonitor", () => {
  const health = ref<Health>({
    status: "",
    latency_ms: 0,
    pool: {}
  });
  const dbStats = ref<any>({});
  const metrics = ref<SystemMetrics>({
    cpuUsage: 0,
    memoryUsage: 0,
    diskUsage: 0,
    activeWsConnections: 0,
    todayApiRequests: 0,
    todayCollectTasks: 0,
    avgResponseTimeMs: 0,
    errorRate: 0
  });
  const events = ref<SecurityEvent[]>([]);
  const eventsTotal = ref(0);
  const eventsLoading = ref(false);
  const loading = ref(false);

  async function fetchHealth() {
    try {
      const { data } = await api.get("/admin/system/health");
      health.value = data;
    } catch (error) {
      console.error("Failed to fetch system health:", error);
    }
  }

  async function fetchDbStats() {
    try {
      const { data } = await api.get("/admin/system/db-stats");
      dbStats.value = data;
    } catch (error) {
      console.error("Failed to fetch DB stats:", error);
    }
  }

  async function fetchMetrics() {
    loading.value = true;
    try {
      const { data } = await api.get("/admin/system/metrics");
      if (data) {
        metrics.value = { ...metrics.value, ...data };
      }
    } catch (error) {
      console.error("Failed to fetch metrics:", error);
    } finally {
      loading.value = false;
    }
  }

  async function fetchEvents(page: number = 1, pageSize: number = 20) {
    eventsLoading.value = true;
    try {
      const { data } = await api.get("/admin/security/events", {
        params: { page, pageSize }
      });
      events.value = data.items || data;
      eventsTotal.value = data.total || events.value.length;
    } catch (error) {
      console.error("Failed to fetch security events:", error);
    } finally {
      eventsLoading.value = false;
    }
  }

  return {
    health,
    dbStats,
    metrics,
    events,
    eventsTotal,
    eventsLoading,
    loading,
    fetchHealth,
    fetchDbStats,
    fetchMetrics,
    fetchEvents
  };
});
