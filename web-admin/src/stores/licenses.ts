import { defineStore } from "pinia";
import { ref } from "vue";
import api from "../utils/api";

export interface License {
  id: string;
  code: string;
  plan: string;
  duration_days: number;
  status: string;
  batch_id?: string;
  created_at?: string;
}

export interface GenerateResult {
  codes: string[];
  count: number;
  batch_id: string | null;
}

export const useLicensesStore = defineStore("licenses", () => {
  const licenses = ref<License[]>([]);
  const total = ref(0);
  const loading = ref(false);

  async function fetchLicenses(page: number, pageSize: number, status?: string) {
    loading.value = true;
    try {
      const params: Record<string, unknown> = { page, page_size: pageSize };
      if (status) params.status = status;
      const { data } = await api.get("/admin/licenses", { params });
      licenses.value = data?.items || [];
      total.value = data?.total ?? licenses.value.length;
    } finally {
      loading.value = false;
    }
  }

  async function generateLicense(body: Record<string, unknown>): Promise<GenerateResult> {
    const { data } = await api.post("/admin/licenses/generate", body);
    return data as GenerateResult;
  }

  async function revokeLicense(id: string) {
    await api.post(`/admin/licenses/${id}/revoke`);
    const index = licenses.value.findIndex((l) => l.id === id);
    if (index !== -1) licenses.value.splice(index, 1);
  }

  return { licenses, total, loading, fetchLicenses, generateLicense, revokeLicense };
});
