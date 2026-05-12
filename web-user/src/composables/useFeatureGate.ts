import { computed } from "vue";
import { useAuthStore } from "../stores/auth";
import { FEATURE_GATES, isPlanSufficient, PLAN_LIMITS, type PlanTier, type FeatureGateDefinition } from "../../../shared/constants/feature-gates";
import { ElMessage } from "element-plus";

export function useFeatureGate() {
  const auth = useAuthStore();
  const userPlan = computed<PlanTier>(() => auth.userPlan as PlanTier || "free");

  // Check if user can access a feature gate
  function canAccess(gateKey: string): boolean {
    const gate = FEATURE_GATES.find(g => g.key === gateKey);
    if (!gate) return true; // unknown gate = allow by default
    return isPlanSufficient(userPlan.value, gate.requiredPlan);
  }

  // Check quota — returns { allowed: boolean, current: number, limit: number }
  function checkQuota(quotaType: "maxProducts" | "maxConcurrency" | "dailyCollectLimit" | "maxScheduleTasks" | "aiCallsPerDay", current: number): { allowed: boolean; current: number; limit: number } {
    const limits = PLAN_LIMITS[userPlan.value];
    const limit = limits[quotaType];
    if (limit === -1) return { allowed: true, current, limit: -1 }; // -1 = unlimited
    return { allowed: current < limit, current, limit };
  }

  // Guard: if user can't access, show upgrade prompt and return false
  function guard(gateKey: string): boolean {
    if (canAccess(gateKey)) return true;
    const gate = FEATURE_GATES.find(g => g.key === gateKey);
    const requiredPlan = gate?.requiredPlan || "pro";
    ElMessage.warning(`该功能需要${planLabel(requiredPlan)}及以上套餐`);
    return false;
  }

  function planLabel(plan: PlanTier): string {
    const labels: Record<PlanTier, string> = { free: "免费版", pro: "专业版", premium: "高级版", enterprise: "企业版" };
    return labels[plan];
  }

  // Get all gates the user currently has access to
  function accessibleGates(): FeatureGateDefinition[] {
    return FEATURE_GATES.filter(g => isPlanSufficient(userPlan.value, g.requiredPlan));
  }

  // Get gates the user does NOT have access to (for upgrade prompts)
  function lockedGates(): FeatureGateDefinition[] {
    return FEATURE_GATES.filter(g => !isPlanSufficient(userPlan.value, g.requiredPlan));
  }

  return { userPlan, canAccess, checkQuota, guard, accessibleGates, lockedGates };
}