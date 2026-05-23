import { defineStore } from "pinia";
import { ref, computed } from "vue";
import api from "../utils/api";
import type { PlanTier } from "@shared/constants/feature-gates";
import { FEATURE_GATES, PLAN_LIMITS, isPlanSufficient } from "@shared/constants/feature-gates";

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
  const canDiscoverySearch = computed(() => gates.value["gate:discovery:search"] ?? false);
  const canDiscoveryBurst = computed(() => gates.value["gate:discovery:burst"] ?? false);
  const canExcelImport = computed(() => gates.value["gate:import:excel"] ?? false);
  const canCategoryManage = computed(() => gates.value["gate:monitor:category"] ?? false);
  const canGrowth24h = computed(() => gates.value["gate:monitor:growth_24h"] ?? false);
  const canAnomalyDetect = computed(() => gates.value["gate:monitor:anomaly"] ?? false);
  const canCompareTrend = computed(() => gates.value["gate:monitor:compare"] ?? false);
  const canWaterfall = computed(() => gates.value["gate:monitor:waterfall"] ?? false);

  async function fetchPermissions() {
    loading.value = true;
    try {
      if (window.electronAPI) {
        const result = await window.electronAPI.invoke("permission:get-all");
        gates.value = result as Record<string, boolean>;
      } else {
        const { data } = await api.get("/auth/me");
        if (data.code === 0 && data.data) {
          const userPlan = (data.data.plan || "free") as PlanTier;
          plan.value = userPlan;
          rebuildGatesFromPlan();
        }
      }
    } catch {
      rebuildGatesFromPlan();
    } finally {
      loading.value = false;
    }
  }

  async function checkGate(gateKey: string): Promise<boolean> {
    try {
      if (window.electronAPI) {
        const result = await window.electronAPI.invoke("permission:check", gateKey);
        gates.value[gateKey] = result as boolean;
        return result as boolean;
      } else {
        const gate = FEATURE_GATES.find((g) => g.key === gateKey);
        if (gate) {
          const allowed = isPlanSufficient(plan.value, gate.requiredPlan);
          gates.value[gateKey] = allowed;
          return allowed;
        }
        return false;
      }
    } catch {
      return false;
    }
  }

  async function refreshFromServer() {
    try {
      if (window.electronAPI) {
        await window.electronAPI.invoke("permission:refresh");
        await fetchPermissions();
      } else {
        await fetchPermissions();
      }
    } catch (err) {
      console.warn("[Permission] refresh failed:", err);
    }
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
    canDiscoverySearch,
    canDiscoveryBurst,
    canExcelImport,
    canCategoryManage,
    canGrowth24h,
    canAnomalyDetect,
    canCompareTrend,
    canWaterfall,
    fetchPermissions,
    checkGate,
    refreshFromServer,
    setPlan,
  };
});
