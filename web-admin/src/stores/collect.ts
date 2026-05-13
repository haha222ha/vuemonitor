import { defineStore } from "pinia";
import { ref } from "vue";
import api from "../utils/api";

interface CollectTask {
  id: string;
  status: string;
  [key: string]: any;
}

export const useCollectStore = defineStore("collect", () => {
  const tasks = ref<CollectTask[]>([]);
  const total = ref(0);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function fetchTasks(params: Record<string, any> = {}) {
    loading.value = true;
    error.value = null;
    try {
      const { data } = await api.get("/admin/collect/tasks", { params });
      tasks.value = data.items || data || [];
      total.value = data.total || 0;
    } catch (err: any) {
      error.value = err.message || "Failed to fetch tasks";
    } finally {
      loading.value = false;
    }
  }

  async function cancelTask(id: string) {
    loading.value = true;
    error.value = null;
    try {
      await api.put(`/admin/collect/tasks/${id}/cancel`);
      const index = tasks.value.findIndex(t => t.id === id);
      if (index !== -1) {
        tasks.value[index].status = "cancelled";
      }
    } catch (err: any) {
      error.value = err.message || "Failed to cancel task";
    } finally {
      loading.value = false;
    }
  }

  async function createTask(payload: Record<string, any>) {
    loading.value = true;
    error.value = null;
    try {
      const { data: responseData } = await api.post("/admin/collect/tasks", payload);
      tasks.value.push(responseData as CollectTask);
      return responseData;
    } catch (err: any) {
      error.value = err.message || "Failed to create task";
      throw err;
    } finally {
      loading.value = false;
    }
  }

  return {
    tasks,
    total,
    loading,
    error,
    fetchTasks,
    cancelTask,
    createTask
  };
});
