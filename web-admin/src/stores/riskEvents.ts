import { defineStore } from "pinia";
import { ref } from "vue";
import api from "../utils/api";

interface RiskEvent {
  id: number;
  // Add other fields as needed; adjust based on actual API response
  [key: string]: any;
}

export const useRiskEventsStore = defineStore("riskEvents", () => {
  const events = ref<RiskEvent[]>([]);
  const total = ref(0);
  const loading = ref(false);

  async function fetchEvents(page: number, pageSize: number, filters?: Record<string, any>) {
    loading.value = true;
    try {
      const params = { page, pageSize, ...filters };
      const { data } = await api.get("/admin/risk-events", { params });
      events.value = data.items || data;
      total.value = data.total || events.value.length;
    } catch (error) {
      // Error handling silent; views can handle UI feedback
    } finally {
      loading.value = false;
    }
  }

  async function resolveEvent(id: number, note: string) {
    try {
      await api.put(`/admin/risk-events/${id}/resolve`, { note });
      // Optionally update local state: remove or mark resolved
      const index = events.value.findIndex(e => e.id === id);
      if (index !== -1) {
        events.value.splice(index, 1);
        total.value = Math.max(total.value - 1, 0);
      }
    } catch (error) {
      // Error handling silent; views can handle UI feedback
    }
  }

  return { events, total, loading, fetchEvents, resolveEvent };
});