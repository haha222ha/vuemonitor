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
  status: string;
  created_at: string;
}

interface SecurityEvent {
  id: string;
  type: string;
  message: string;
  severity: string;
  created_at: string;
  [key: string]: any;
}

export const useSecurityAuditStore = defineStore("securityAudit", () => {
  const logs = ref<SecurityAuditLog[]>([]);
  const events = ref<SecurityEvent[]>([]);
  const total = ref(0);
  const loading = ref(false);

  async function fetchLogs(page: number, pageSize: number, filters?: Record<string, any>) {
    loading.value = true;
    try {
      const params: any = { page, pageSize, ...filters };
      const { data } = await api.get("/admin/security-audit", { params });
      logs.value = data.logs || data.items || data;
      total.value = data.total || logs.value.length;
    } catch (error) {
      console.error("Failed to fetch security audit logs:", error);
    } finally {
      loading.value = false;
    }
  }

  async function fetchEvents(page: number = 1, pageSize: number = 20) {
    loading.value = true;
    try {
      const { data } = await api.get("/admin/security/events", {
        params: { page, pageSize }
      });
      events.value = data.items || data;
      total.value = data.total || events.value.length;
    } catch (error) {
      console.error("Failed to fetch security events:", error);
    } finally {
      loading.value = false;
    }
  }

  async function exportCsv(filters?: Record<string, any>) {
    try {
      const params: any = { ...filters, format: "csv" };
      const response = await api.get("/admin/security-audit/export", {
        params,
        responseType: "blob"
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `security-audit-${Date.now()}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Failed to export CSV:", error);
    }
  }

  return {
    logs,
    events,
    total,
    loading,
    fetchLogs,
    fetchEvents,
    exportCsv
  };
});
