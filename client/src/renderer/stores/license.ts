import { defineStore } from "pinia";
import { ref, computed } from "vue";
import api from "../utils/api";

export interface LicenseInfo {
  licenseKey: string;
  deviceId: string;
  plan: "free" | "pro" | "premium" | "enterprise";
  expiresAt: string | null;
  activatedAt: string;
  features: string[];
  machineFingerprint: string;
  isValid: boolean;
  lastVerified: string;
}

export interface QuotaCheckResult {
  allowed: boolean;
  limit: number;
  remaining: number;
}

export const useLicenseStore = defineStore("license", () => {
  const license = ref<LicenseInfo | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const quotas = ref<Record<string, number>>({});

  const plan = computed(() => license.value?.isValid ? license.value.plan : "free");
  const planLabel = computed(() => {
    const labels: Record<string, string> = {
      free: "免费版",
      pro: "专业版",
      premium: "高级版",
      enterprise: "企业版",
    };
    return labels[plan.value] || "免费版";
  });
  const isActivated = computed(() => license.value?.isValid === true);
  const isExpired = computed(() => {
    if (!license.value?.expiresAt) return false;
    return new Date(license.value.expiresAt) < new Date();
  });
  const expiresAtFormatted = computed(() => {
    if (!license.value?.expiresAt) return "永久";
    return new Date(license.value.expiresAt).toLocaleDateString("zh-CN");
  });

  async function fetchLicense() {
    try {
      if (window.electronAPI) {
        const result = await window.electronAPI.invoke("license:get-current");
        license.value = result as LicenseInfo | null;
      } else {
        const { data } = await api.get("/license/status");
        if (data.code === 0 && data.data) {
          license.value = data.data as LicenseInfo;
        }
      }
    } catch {}
  }

  async function fetchPlan() {
    try {
      if (window.electronAPI) {
        const result = await window.electronAPI.invoke("license:get-plan") as {
          plan: string;
          features: string[];
          quotas: Record<string, number>;
        };
        if (license.value) {
          license.value.plan = result.plan as LicenseInfo["plan"];
          license.value.features = result.features;
        }
        quotas.value = result.quotas || {};
      } else {
        const { data } = await api.get("/auth/me");
        if (data.code === 0 && data.data) {
          const userPlan = data.data.plan || "free";
          if (license.value) {
            license.value.plan = userPlan;
          } else {
            license.value = {
              licenseKey: "",
              deviceId: "",
              plan: userPlan,
              expiresAt: null,
              activatedAt: new Date().toISOString(),
              features: [],
              machineFingerprint: "",
              isValid: true,
              lastVerified: new Date().toISOString(),
            };
          }
        }
      }
    } catch {}
  }

  async function activate(licenseKey: string, serverUrl?: string) {
    loading.value = true;
    error.value = null;
    try {
      if (window.electronAPI) {
        const result = await window.electronAPI.invoke("license:activate", licenseKey, serverUrl) as {
          success: boolean;
          license?: LicenseInfo;
          error?: string;
        };
        if (result.success && result.license) {
          license.value = result.license;
          return true;
        } else {
          error.value = result.error || "激活失败";
          return false;
        }
      } else {
        const { data } = await api.post("/auth/license/activate", { license_key: licenseKey });
        if (data.code === 0 && data.data) {
          license.value = data.data as LicenseInfo;
          return true;
        }
        error.value = data.message || "激活失败";
        return false;
      }
    } catch (err) {
      error.value = String(err);
      return false;
    } finally {
      loading.value = false;
    }
  }

  async function deactivate() {
    try {
      if (window.electronAPI) {
        await window.electronAPI.invoke("license:deactivate");
      }
      license.value = null;
      return true;
    } catch {
      return false;
    }
  }

  async function getDeviceInfo() {
    try {
      if (window.electronAPI) {
        return await window.electronAPI.invoke("license:get-device-id") as {
          deviceId: string;
          fingerprint: string;
        };
      }
      return null;
    } catch {
      return null;
    }
  }

  async function checkFeature(gateKey: string): Promise<boolean> {
    try {
      if (window.electronAPI) {
        return await window.electronAPI.invoke("license:check-feature", gateKey) as boolean;
      }
      return true;
    } catch {
      return false;
    }
  }

  async function checkQuota(quotaKey: string, currentUsage: number): Promise<QuotaCheckResult> {
    try {
      if (window.electronAPI) {
        return await window.electronAPI.invoke("license:check-quota", quotaKey, currentUsage) as QuotaCheckResult;
      }
      return { allowed: true, limit: -1, remaining: -1 };
    } catch {
      return { allowed: true, limit: -1, remaining: -1 };
    }
  }

  async function checkExpired(): Promise<boolean> {
    try {
      if (window.electronAPI) {
        return await window.electronAPI.invoke("license:is-expired") as boolean;
      }
      return false;
    } catch {
      return false;
    }
  }

  return {
    license,
    loading,
    error,
    quotas,
    plan,
    planLabel,
    isActivated,
    isExpired,
    expiresAtFormatted,
    fetchLicense,
    fetchPlan,
    activate,
    deactivate,
    getDeviceInfo,
    checkFeature,
    checkQuota,
    checkExpired,
  };
});
