import { defineStore } from "pinia";
import { ref } from "vue";
import api from "../utils/api";

interface DataRequest {
  id: number;
  // Add other fields as needed
  [key: string]: any;
}

export const useGdprStore = defineStore("gdpr", () => {
  const dataRequests = ref<DataRequest[]>([]);
  const total = ref(0);
  const loading = ref(false);

  async function fetchRequests(page: number, pageSize: number) {
    loading.value = true;
    try {
      const { data } = await api.get("/admin/gdpr/requests", { params: { page, pageSize } });
      dataRequests.value = data.items || data;
      total.value = data.total || dataRequests.value.length;
    } catch (error) {
      // Error handling silent; views can handle UI feedback
    } finally {
      loading.value = false;
    }
  }

  async function approveRequest(id: number) {
    try {
      await api.put(`/admin/gdpr/requests/${id}/approve`);
      // Optionally update local state: remove or mark approved
      const index = dataRequests.value.findIndex(req => req.id === id);
      if (index !== -1) {
        dataRequests.value.splice(index, 1);
        total.value = Math.max(total.value - 1, 0);
      }
    } catch (error) {
      // Error handling silent; views can handle UI feedback
    }
  }

  async function rejectRequest(id: number, reason: string) {
    try {
      await api.put(`/admin/gdpr/requests/${id}/reject`, { reason });
      // Optionally update local state: remove or mark rejected
      const index = dataRequests.value.findIndex(req => req.id === id);
      if (index !== -1) {
        dataRequests.value.splice(index, 1);
        total.value = Math.max(total.value - 1, 0);
      }
    } catch (error) {
      // Error handling silent; views can handle UI feedback
    }
  });

  return { dataRequests, total, loading, fetchRequests, approveRequest, rejectRequest };
});