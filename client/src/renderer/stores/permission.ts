import { defineStore } from "pinia";
import { ref, computed } from "vue";
import type { PlanTier } from "../../../shared/constants/feature-gates";
import { FEATURE_GATES, PLAN_LIMITS, isPlanSufficient } from "../../../shared/constants/feature-gates";

export interface PermissionGate {
  key: string;
  name: string;
  type: "feature" | "quota" | "limit";
  requiredPlan: PlanTier;
  description: string;
  allowed: boolean;
}

export const usePermissionStore = defineStore("permission", () => {
  const plan = ref<PlanTier>("free");
  const gates = ref<Record<string, boolean>>({});
  const quotas = ref<Record<string, { used: number; limit: number }>>({});
  const loading = ref(false);

  const gateList = computed<PermissionGate[]>(() => {
    return FEATURE_GATES.map((gate) => ({
      ...gate,
      allowed: gates.value[gate.key] ?? false,
    }));
  });

  const canAddProduct = computed(() => {
    const quota = quotas.value["gate:monitor:add"];
    if (!quota) return true;
    return quota.used < quota.limit;
  });

  const canAutoRefresh = computed(() => gates.value["gate:monitor:auto_refresh"] ?? false);
  const canExport = computed(() => gates.value["gate:monitor:export"] ?? false);
  const canAITrend = computed(() => gates.value["gate:ai:trend_score"] ?? false);
  const canAIPrediction = computed(() => gates.value["gate:ai:prediction"] ?? false);
  const canAIRisk = computed(() => gates.value["gate:ai:risk_warning"] ?? false);
  const canCloudCollect = computed(() => gates.value["gate:collect:cloud"] ?? false);

  async function fetchPermissions() {
    loading.value = true;
    try {
      const result = await window.electronAPI.invoke("permission:get-all");
      gates.value = result as Record<string, boolean>;
    } catch {
      rebuildGatesFromPlan();
    } finally {
      loading.value = false;
    }
  }

  async function checkGate(gateKey: string): Promise<boolean> {
    try {
      const result = await window.electronAPI.invoke("permission:check", gateKey);
      gates.value[gateKey] = result as boolean;
      return result as boolean;
    } catch {
      return false;
    }
  }

  async function refreshFromServer() {
    try {
      await window.electronAPI.invoke("permission:refresh");
      await fetchPermissions();
    } catch {}
  }

  function setPlan(newPlan: PlanTier) {
    plan.value = newPlan;
    rebuildGatesFromPlan();
  }

  function rebuildGatesFromPlan() {
    const newGates: Record<string, boolean> = {};
    for (const gate of FEATURE_GATES) {
      newGates[gate.key] = isPlanSufficient(plan.value, gate.requiredPlan);
    }
    gates.value = newGates;
  }

  return {
    plan,
    gates,
    quotas,
    loading,
    gateList,
    canAddProduct,
    canAutoRefresh,
    canExport,
    canAITrend,
    canAIPrediction,
    canAIRisk,
    canCloudCollect,
    fetchPermissions,
    checkGate,
    refreshFromServer,
    setPlan,
  };
});
