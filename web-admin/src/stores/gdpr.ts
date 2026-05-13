import { defineStore } from "pinia";
import { ref } from "vue";
import api from "../utils/api";

interface DataRequest {
  id: number;
  [key: string]: any;
}

interface GdprStats {
  pendingExports: number;
  pendingDeletions: number;
  completedThisMonth: number;
  avgProcessingHours: number;
}

export const useGdprStore = defineStore("gdpr", () => {
  const dataRequests = ref<DataRequest[]>([]);
  const exports = ref<DataRequest[]>([]);
  const deletions = ref<DataRequest[]>([]);
  const stats = ref<GdprStats>({
    pendingExports: 0,
    pendingDeletions: 0,
    completedThisMonth: 0,
    avgProcessingHours: 0
  });
  const total = ref(0);
  const exportsTotal = ref(0);
  const deletionsTotal = ref(0);
  const exportsLoading = ref(false);
  const deletionsLoading = ref(false);
  const loading = ref(false);

  async function fetchRequests(page: number, pageSize: number) {
    loading.value = true;
    try {
      const { data } = await api.get("/admin/gdpr/requests", { params: { page, pageSize } });
      dataRequests.value = data.items || data;
      total.value = data.total || dataRequests.value.length;
    } catch (error) {
      console.error("Failed to fetch GDPR requests:", error);
    } finally {
      loading.value = false;
    }
  }

  async function fetchExports(page: number, pageSize: number, status?: string) {
    exportsLoading.value = true;
    try {
      const params: Record<string, any> = { page, pageSize, type: "export" };
      if (status) params.status = status;
      const { data } = await api.get("/admin/gdpr/requests", { params });
      exports.value = data.items || data;
      exportsTotal.value = data.total || exports.value.length;
    } catch (error) {
      console.error("Failed to fetch export requests:", error);
    } finally {
      exportsLoading.value = false;
    }
  }

  async function fetchDeletions(page: number, pageSize: number, status?: string) {
    deletionsLoading.value = true;
    try {
      const params: Record<string, any> = { page, pageSize, type: "deletion" };
      if (status) params.status = status;
      const { data } = await api.get("/admin/gdpr/requests", { params });
      deletions.value = data.items || data;
      deletionsTotal.value = data.total || deletions.value.length;
    } catch (error) {
      console.error("Failed to fetch deletion requests:", error);
    } finally {
      deletionsLoading.value = false;
    }
  }

  async function fetchStats() {
    try {
      const { data } = await api.get("/admin/gdpr/stats");
      if (data) {
        stats.value = { ...stats.value, ...data };
      }
    } catch (error) {
      console.error("Failed to fetch GDPR stats:", error);
    }
  }

  async function approveRequest(id: number) {
    try {
      await api.put(`/admin/gdpr/requests/${id}/approve`);
    } catch (error) {
      console.error("Failed to approve request:", error);
      throw error;
    }
  }

  async function rejectRequest(id: number, reason?: string) {
    try {
      await api.put(`/admin/gdpr/requests/${id}/reject`, { reason });
    } catch (error) {
      console.error("Failed to reject request:", error);
      throw error;
    }
  }

  async function downloadExport(id: number) {
    try {
      const response = await api.get(`/admin/gdpr/exports/${id}/download`, {
        responseType: "blob"
      });
      return response.data;
    } catch (error) {
      console.error("Failed to download export:", error);
      throw error;
    }
  }

  return {
    dataRequests,
    exports,
    deletions,
    stats,
    total,
    exportsTotal,
    deletionsTotal,
    exportsLoading,
    deletionsLoading,
    loading,
    fetchRequests,
    fetchExports,
    fetchDeletions,
    fetchStats,
    approveRequest,
    rejectRequest,
    downloadExport
  };
});
