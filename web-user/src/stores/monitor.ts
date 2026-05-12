import { defineStore } from "pinia";
import { ref, computed } from "vue";
import api from "../utils/api";
import { ElMessage } from "element-plus";

export interface MonitorRule {
  id: string;
  name: string;
  condition_type: 'price_drop' | 'sales_surge' | 'rating_drop' | 'out_of_stock' | 'custom';
  condition_config: Record<string, any>;
  action_type: 'notify' | 'ai_analysis' | 'export';
  is_active: boolean;
  product_ids: string[];
  created_at: string;
}

export const useMonitorStore = defineStore("monitor", () => {
  const rules = ref<MonitorRule[]>([]);
  const loading = ref<boolean>(false);
  const collectStatus = ref<{ status: 'idle' | 'collecting'; concurrency: number; queueSize: number; memoryUsage: number }>({
    status: 'idle',
    concurrency: 0,
    queueSize: 0,
    memoryUsage: 0
  });

  async function fetchRules() {
    loading.value = true;
    try {
      const { data } = await api.get("/monitor/rules");
      rules.value = data || [];
    } catch (error) {
      ElMessage.error("Failed to fetch monitor rules");
    } finally {
      loading.value = false;
    }
  }

  async function createRule(data: Partial<MonitorRule>) {
    try {
      await api.post("/monitor/rules", data);
    } catch (error) {
      ElMessage.error("Failed to create monitor rule");
    }
  }

  async function updateRule(id: string, data: Partial<MonitorRule>) {
    try {
      await api.put(`/monitor/rules/${id}`, data);
    } catch (error) {
      ElMessage.error("Failed to update monitor rule");
    }
  }

  async function deleteRule(id: string) {
    try {
      await api.delete(`/monitor/rules/${id}`);
    } catch (error) {
      ElMessage.error("Failed to delete monitor rule");
    }
  }

  async function toggleRule(id: string, active: boolean) {
    try {
      await api.put(`/monitor/rules/${id}/toggle`, { active });
    } catch (error) {
      ElMessage.error("Failed to toggle monitor rule");
    }
  }

  async function fetchCollectStatus() {
    try {
      const { data } = await api.get("/collect/status");
      collectStatus.value = data;
    } catch (error) {
      ElMessage.error("Failed to fetch collect status");
    }
  }

  return { rules, loading, collectStatus, fetchRules, createRule, updateRule, deleteRule, toggleRule, fetchCollectStatus };
});