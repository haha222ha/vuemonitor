import { defineStore } from "pinia";
import { ref } from "vue";
import api from "../utils/api";

interface AuditLog {
  id: number;
  [key: string]: any;
}

export const useAuditLogsStore = defineStore("auditLogs", () => {
  const logs = ref<AuditLog[]>([]);
  const total = ref(0);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function fetchLogs(page: number = 1, pageSize: number = 20, filters?: Record<string, any>) {
    loading.value = true;
    error.value = null;
    try {
      const params: Record<string, any> = { page, pageSize, ...filters };
      const { data } = await api.get("/admin/audit-logs", { params });
      logs.value = data.items || data || [];
      total.value = data.total || 0;
    } catch (err: any) {
      error.value = err.message || "Failed to fetch audit logs";
    } finally {
      loading.value = false;
    }
  }

  return {
    logs,
    total,
    loading,
    error,
    fetchLogs
  };
});
