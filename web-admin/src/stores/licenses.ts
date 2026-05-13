import { defineStore } from "pinia";
import { ref } from "vue";
import api from "../utils/api";

interface License {
  id: number;
  // Add other fields as needed
  [key: string]: any;
}

export const useLicensesStore = defineStore("licenses", () => {
  const licenses = ref<License[]>([]);
  const total = ref(0);
  const loading = ref(false);

  async function fetchLicenses(page: number, pageSize: number, status?: string) {
    loading.value = true;
    try {
      const params: Record<string, any> = { page, pageSize };
      if (status) {
        params.status = status;
      }
      const { data } = await api.get("/admin/licenses", { params });
      licenses.value = data.items || data;
      total.value = data.total || licenses.value.length;
    } catch (error) {
      // Error handling silent; views can handle UI feedback
    } finally {
      loading.value = false;
    }
  }

  async function generateLicense(data: Record<string, any>) {
    try {
      await api.post("/admin/licenses/generate", data);
      // Optionally refetch licenses
      await fetchLicenses(1, 10); // Reset to first page, adjust as needed
    } catch (error) {
      // Error handling silent; views can handle UI feedback
    }
  }

  async function revokeLicense(id: number) {
    try {
      await api.put(`/admin/licenses/${id}/revoke`);
      // Optionally update local state: remove or mark revoked
      const index = licenses.value.findIndex(license => license.id === id);
      if (index !== -1) {
        licenses.value.splice(index, 1);
        total.value = Math.max(total.value - 1, 0);
      }
    } catch (error) {
      // Error handling silent; views can handle UI feedback
    }
  }

  return { licenses, total, loading, fetchLicenses, generateLicense, revokeLicense };
});