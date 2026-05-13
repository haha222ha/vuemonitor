import { defineStore } from "pinia";
import { ref } from "vue";
import api from "../utils/api";

interface TrendBar {
  label: string;
  value: number;
  percentage: number;
}

interface PlatformBar {
  name: string;
  label: string;
  value: number;
  count: number;
  percentage: number;
}

export const useDashboardStore = defineStore("dashboard", () => {
  const stats = ref({
    totalUsers: 0,
    activeUsers: 0,
    todayTasks: 0,
    availableProxies: 0,
    monitoredProducts: 0,
    todayApiRequests: 0,
    healthScore: 0,
    pendingAlerts: 0
  });

  const weeklyTrend = ref<TrendBar[]>([]);
  const platformDist = ref<PlatformBar[]>([]);

  async function fetchStats() {
    try {
      const { data } = await api.get("/admin/stats");
      if (data) {
        stats.value = { ...stats.value, ...data };
      }
    } catch (error) {
      console.error("Failed to fetch stats:", error);
    }
  }

  async function fetchWeeklyTrend() {
    try {
      const { data } = await api.get("/admin/stats/weekly-trend");
      weeklyTrend.value = (data || []).map((item: any) => ({
        label: item.label || item.date || "",
        value: item.value || 0,
        percentage: item.percentage || (item.value ? Math.min((item.value / Math.max(...(data || []).map((d: any) => d.value || 0), 1)) * 100, 100) : 0)
      }));
    } catch (error) {
      console.error("Failed to fetch weekly trend:", error);
    }
  }

  async function fetchPlatformDist() {
    try {
      const { data } = await api.get("/admin/stats/platform-distribution");
      platformDist.value = (data || []).map((item: any) => ({
        name: item.name || item.platform || "",
        label: item.label || item.name || item.platform || "",
        value: item.value || 0,
        count: item.count || item.value || 0,
        percentage: item.percentage || 0
      }));
    } catch (error) {
      console.error("Failed to fetch platform distribution:", error);
    }
  }

  return {
    stats,
    weeklyTrend,
    platformDist,
    fetchStats,
    fetchWeeklyTrend,
    fetchPlatformDist
  };
});
