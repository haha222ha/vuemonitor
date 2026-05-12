import { defineStore } from "pinia";
import { ref } from "vue";
import api from "../utils/api";

interface TrendBar {
  label: string;
  value: number;
}

interface PlatformBar {
  name: string;
  value: number;
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
      stats.value = data;
    } catch (error) {
      // Error handling left to views
      console.error("Failed to fetch stats:", error);
    }
  }

  async function fetchWeeklyTrend() {
    try {
      const { data } = await api.get("/admin/stats/weekly-trend");
      weeklyTrend.value = data;
    } catch (error) {
      console.error("Failed to fetch weekly trend:", error);
    }
  }

  async function fetchPlatformDist() {
    try {
      const { data } = await api.get("/admin/stats/platform-distribution");
      platformDist.value = data;
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