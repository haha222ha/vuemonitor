import { defineStore } from "pinia";
import { ref } from "vue";
import api from "../utils/api";

export interface MemberAuthCode {
  id?: number;
  code: string;
  plan_code: string;
  plan_label?: string;
  duration_days: number;
  max_activations: number;
  current_activations: number;
  status: string;
  note: string;
  created_at: string;
  expires_at: string;
  first_activated_at?: string;
  activated_usernames?: string;
  membership_expires_at?: string;
  days_remaining?: number | null;
}

export interface MemberCloudStatus {
  configured: boolean;
  online: boolean;
  member_portal_url: string;
  message?: string;
  error?: string;
  health?: { status?: string };
  stats?: {
    active_members?: number;
    total_members?: number;
    auth_codes_unused?: number;
    auth_codes_active?: number;
    auth_codes_total?: number;
    latest_report_date?: string | null;
    archive_count?: number;
    monitor_pool_active?: number;
  };
}

export const useMemberCloudStore = defineStore("memberCloud", () => {
  const codes = ref<MemberAuthCode[]>([]);
  const total = ref(0);
  const loading = ref(false);
  const status = ref<MemberCloudStatus | null>(null);
  const statusLoading = ref(false);

  async function fetchStatus() {
    statusLoading.value = true;
    try {
      const { data } = await api.get("/xhs-cloud/admin/status");
      status.value = data as MemberCloudStatus;
    } catch {
      status.value = {
        configured: false,
        online: false,
        member_portal_url: "",
        message: "无法获取选品云服务状态",
      };
    } finally {
      statusLoading.value = false;
    }
  }

  async function fetchCodes(limit = 100, filterStatus?: string) {
    loading.value = true;
    try {
      const params: Record<string, string | number> = { limit };
      if (filterStatus) params.status = filterStatus;
      const { data } = await api.get("/xhs-cloud/admin/codes", { params });
      codes.value = data?.items || [];
      total.value = data?.total ?? codes.value.length;
    } finally {
      loading.value = false;
    }
  }

  async function generateCodes(payload: {
    plan_code: string;
    count: number;
    duration_days?: number;
    max_activations?: number;
    note?: string;
  }) {
    const { data } = await api.post("/xhs-cloud/admin/codes/generate", payload);
    return data as { codes: { code: string; plan_code: string; duration_days: number }[]; count: number };
  }

  async function revokeCode(code: string) {
    await api.post(`/xhs-cloud/admin/codes/${encodeURIComponent(code)}/revoke`);
  }

  return { codes, total, loading, status, statusLoading, fetchStatus, fetchCodes, generateCodes, revokeCode };
});
