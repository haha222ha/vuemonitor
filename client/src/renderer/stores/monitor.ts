import { defineStore } from "pinia";
import { ref, computed } from "vue";
import api from "../utils/api";

export interface MonitorRule {
  id: string;
  product_id: string;
  rule_name: string;
  rule_type: string;
  conditions: Record<string, unknown>;
  is_active: boolean;
  last_triggered_at: string | null;
  trigger_count: number;
  created_at: string;
}

export const useMonitorStore = defineStore("monitor", () => {
  const rules = ref<MonitorRule[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  const activeRules = computed(() => rules.value.filter((r) => r.is_active));
  const ruleCount = computed(() => rules.value.length);

  async function fetchRules() {
    loading.value = true;
    error.value = null;
    try {
      if (window.electronAPI) {
        const result = await window.electronAPI.invoke("monitor:get-rules");
        rules.value = (result as MonitorRule[]).map((r) => ({
          ...r,
          conditions: typeof r.conditions === "string" ? JSON.parse(r.conditions as unknown as string) : r.conditions,
        }));
      } else {
        const { data } = await api.get("/alert-rules");
        if (data.code === 0 && data.data) {
          rules.value = data.data.items || data.data || [];
        }
      }
    } catch (err) {
      error.value = String(err);
    } finally {
      loading.value = false;
    }
  }

  async function addRule(rule: Omit<MonitorRule, "id" | "last_triggered_at" | "trigger_count" | "created_at">) {
    loading.value = true;
    try {
      if (window.electronAPI) {
        const id = crypto.randomUUID();
        await window.electronAPI.invoke("monitor:create-rule", {
          product_id: rule.product_id,
          rule_name: rule.rule_name,
          rule_type: rule.rule_type,
          conditions: rule.conditions,
          is_active: rule.is_active,
        });
        rules.value.push({ ...rule, id, last_triggered_at: null, trigger_count: 0, created_at: new Date().toISOString() });
      } else {
        const { data } = await api.post("/alert-rules", {
          product_id: rule.product_id,
          rule_name: rule.rule_name,
          rule_type: rule.rule_type,
          conditions: rule.conditions,
          is_active: rule.is_active,
        });
        if (data.code === 0 && data.data) {
          rules.value.push(data.data);
        }
      }
    } catch (err) {
      error.value = String(err);
    } finally {
      loading.value = false;
    }
  }

  async function removeRule(ruleId: string) {
    try {
      if (window.electronAPI) {
        await window.electronAPI.invoke("monitor:delete-rule", ruleId);
      } else {
        await api.delete(`/alert-rules/${ruleId}`);
      }
      rules.value = rules.value.filter((r) => r.id !== ruleId);
    } catch (err) {
      error.value = String(err);
    }
  }

  async function toggleRule(ruleId: string, active: boolean) {
    try {
      if (window.electronAPI) {
        await window.electronAPI.invoke("monitor:toggle-rule", ruleId, active);
      } else {
        await api.patch(`/alert-rules/${ruleId}`, { is_active: active });
      }
      const rule = rules.value.find((r) => r.id === ruleId);
      if (rule) rule.is_active = active;
    } catch (err) {
      error.value = String(err);
    }
  }

  return {
    rules,
    loading,
    error,
    activeRules,
    ruleCount,
    fetchRules,
    addRule,
    removeRule,
    toggleRule,
  };
});
