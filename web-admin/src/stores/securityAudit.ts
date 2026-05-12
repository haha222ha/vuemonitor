import { defineStore } from "pinia";
import { ref } from "vue";
import api from "../utils/api";

interface SecurityAuditLog {
  id: number;
  user_id: number;
  username: string;
  action: string;
  resource: string;
  ip_address: string;
  user_agent: string;
  status: string; // e.g., 'success', 'failure'
  created_at: string;
}

export const useSecurityAuditStore = defineStore("securityAudit", () => {
  const logs = ref<SecurityAuditLog[]>([]);
  const total = ref(0);
  const loading = ref(false);

  async function fetchLogs(page: number, pageSize: number, filters?: Record<string, any>) {
    loading.value = true;
    try {
      const params: any = { page, pageSize, ...filters };
      const { data } = await api.get("/admin/security-audit", { params });
      // Assuming the API returns { logs: SecurityAuditLog[], total: number }
      logs.value = data.logs;
      total.value = data.total;
    } catch (error) {
      console.error("Failed to fetch security audit logs:", error);
    } finally {
      loading.value = false;
    }
  }

  return {
    logs,
    total,
    loading,
    fetchLogs
  };
});