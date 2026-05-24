import { defineStore } from "pinia";
import { ref } from "vue";
import api from "../utils/api";

interface IntelCode {
  id: string;
  code: string;
  plan: string;
  duration_days: number;
  max_activations: number;
  current_activations: number;
  status: string;
  batch_id: string | null;
  note: string | null;
  created_at: string | null;
  activated_at: string | null;
  expires_at: string | null;
}

export const useIntelCodesStore = defineStore("intelCodes", () => {
  const codes = ref<IntelCode[]>([]);
  const total = ref(0);
  const loading = ref(false);

  async function fetchCodes(page: number, pageSize: number, filters?: { plan?: string; status?: string; batch_id?: string }) {
    loading.value = true;
    try {
      const params: Record<string, any> = { page, page_size: pageSize };
      if (filters?.plan) params.plan = filters.plan;
      if (filters?.status) params.status = filters.status;
      if (filters?.batch_id) params.batch_id = filters.batch_id;
      const { data } = await api.get("/intel/admin/codes", { params });
      codes.value = data.items || [];
      total.value = data.total || 0;
    } catch {} finally {
      loading.value = false;
    }
  }

  async function generateCodes(payload: { plan: string; count: number; max_activations?: number; note?: string }) {
    const { data } = await api.post("/intel/admin/codes/generate", payload);
    return data;
  }

  async function revokeCode(codeId: string) {
    await api.post(`/intel/admin/codes/${codeId}/revoke`);
  }

  async function fetchStats() {
    const { data } = await api.get("/intel/admin/stats");
    return data;
  }

  return { codes, total, loading, fetchCodes, generateCodes, revokeCode, fetchStats };
});
