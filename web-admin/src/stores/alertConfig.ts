import { defineStore } from "pinia";
import { ref } from "vue";
import api from "../utils/api";

interface AlertRule {
  id: string;
  [key: string]: any;
}

interface AlertChannel {
  id: string;
  [key: string]: any;
}

export const useAlertConfigStore = defineStore("alertConfig", () => {
  const rules = ref<AlertRule[]>([]);
  const channels = ref<AlertChannel[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function fetchRules() {
    loading.value = true;
    error.value = null;
    try {
      const { data } = await api.get("/admin/alert-rules");
      rules.value = data.items || data || [];
    } catch (err: any) {
      error.value = err.message || "Failed to fetch alert rules";
    } finally {
      loading.value = false;
    }
  }

  async function fetchChannels() {
    loading.value = true;
    error.value = null;
    try {
      const { data } = await api.get("/admin/alert-channels");
      channels.value = data.items || data || [];
    } catch (err: any) {
      error.value = err.message || "Failed to fetch alert channels";
    } finally {
      loading.value = false;
    }
  }

  async function createRule(payload: Record<string, any>) {
    loading.value = true;
    error.value = null;
    try {
      await api.post("/admin/alert-rules", payload);
    } catch (err: any) {
      error.value = err.message || "Failed to create alert rule";
      throw err;
    } finally {
      loading.value = false;
    }
  }

  async function updateRule(id: string, payload: Record<string, any>) {
    loading.value = true;
    error.value = null;
    try {
      await api.put(`/admin/alert-rules/${id}`, payload);
      const index = rules.value.findIndex(r => r.id === id);
      if (index !== -1) {
        rules.value[index] = { ...rules.value[index], ...payload };
      }
    } catch (err: any) {
      error.value = err.message || "Failed to update alert rule";
      throw err;
    } finally {
      loading.value = false;
    }
  }

  async function deleteRule(id: string) {
    loading.value = true;
    error.value = null;
    try {
      await api.delete(`/admin/alert-rules/${id}`);
      const index = rules.value.findIndex(r => r.id === id);
      if (index !== -1) {
        rules.value.splice(index, 1);
      }
    } catch (err: any) {
      error.value = err.message || "Failed to delete alert rule";
      throw err;
    } finally {
      loading.value = false;
    }
  }

  async function createChannel(payload: Record<string, any>) {
    loading.value = true;
    error.value = null;
    try {
      await api.post("/admin/alert-channels", payload);
    } catch (err: any) {
      error.value = err.message || "Failed to create alert channel";
      throw err;
    } finally {
      loading.value = false;
    }
  }

  async function updateChannel(id: string, payload: Record<string, any>) {
    loading.value = true;
    error.value = null;
    try {
      await api.put(`/admin/alert-channels/${id}`, payload);
      const index = channels.value.findIndex(c => c.id === id);
      if (index !== -1) {
        channels.value[index] = { ...channels.value[index], ...payload };
      }
    } catch (err: any) {
      error.value = err.message || "Failed to update alert channel";
      throw err;
    } finally {
      loading.value = false;
    }
  }

  async function deleteChannel(id: string) {
    loading.value = true;
    error.value = null;
    try {
      await api.delete(`/admin/alert-channels/${id}`);
      const index = channels.value.findIndex(c => c.id === id);
      if (index !== -1) {
        channels.value.splice(index, 1);
      }
    } catch (err: any) {
      error.value = err.message || "Failed to delete alert channel";
      throw err;
    } finally {
      loading.value = false;
    }
  }

  async function testChannel(id: string) {
    loading.value = true;
    error.value = null;
    try {
      await api.post(`/admin/alert-channels/${id}/test`);
    } catch (err: any) {
      error.value = err.message || "Failed to test alert channel";
      throw err;
    } finally {
      loading.value = false;
    }
  }

  return {
    rules,
    channels,
    loading,
    error,
    fetchRules,
    fetchChannels,
    createRule,
    updateRule,
    deleteRule,
    createChannel,
    updateChannel,
    deleteChannel,
    testChannel
  };
});
