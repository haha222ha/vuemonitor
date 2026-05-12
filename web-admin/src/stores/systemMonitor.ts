import { defineStore } from "pinia";
import { ref } from "vue";
import api from "../utils/api";

interface Health {
  status: string;
  latency_ms: number;
  pool: any; // Pool structure not specified, using any for flexibility
}

export const useSystemMonitorStore = defineStore("systemMonitor", () => {
  const health = ref<Health>({
    status: "",
    latency_ms: 0,
    pool: {}
  });
  const dbStats = ref<any>({});
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

  return {
    health,
    dbStats,
    loading,
    fetchHealth,
    fetchDbStats
  };
});