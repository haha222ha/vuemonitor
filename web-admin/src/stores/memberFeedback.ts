import { defineStore } from "pinia";
import { ref } from "vue";
import api from "../utils/api";

export interface MemberFeedbackItem {
  id: number;
  user_id?: number;
  username?: string;
  category?: string;
  content: string;
  contact?: string;
  app_version?: string;
  machine_id?: string;
  client_ip?: string;
  status: string;
  admin_note?: string;
  created_at: string;
  updated_at?: string;
}

export interface MemberKeywordRequestItem {
  id: number;
  user_id?: number;
  username?: string;
  keywords: string;
  note?: string;
  app_version?: string;
  machine_id?: string;
  client_ip?: string;
  status: string;
  admin_note?: string;
  created_at: string;
  updated_at?: string;
}

export const useMemberFeedbackStore = defineStore("memberFeedback", () => {
  const feedbackItems = ref<MemberFeedbackItem[]>([]);
  const keywordItems = ref<MemberKeywordRequestItem[]>([]);
  const feedbackLoading = ref(false);
  const keywordLoading = ref(false);

  async function fetchFeedback(limit = 100, status?: string) {
    feedbackLoading.value = true;
    try {
      const params: Record<string, string | number> = { limit };
      if (status) params.status = status;
      const { data } = await api.get("/xhs-cloud/admin/member-feedback", { params });
      feedbackItems.value = data?.items || [];
    } finally {
      feedbackLoading.value = false;
    }
  }

  async function fetchKeywords(limit = 100, status?: string) {
    keywordLoading.value = true;
    try {
      const params: Record<string, string | number> = { limit };
      if (status) params.status = status;
      const { data } = await api.get("/xhs-cloud/admin/member-keyword-requests", { params });
      keywordItems.value = data?.items || [];
    } finally {
      keywordLoading.value = false;
    }
  }

  async function updateFeedback(id: number, payload: { status?: string; admin_note?: string }) {
    await api.patch(`/xhs-cloud/admin/member-feedback/${id}`, payload);
  }

  async function updateKeyword(id: number, payload: { status?: string; admin_note?: string }) {
    await api.patch(`/xhs-cloud/admin/member-keyword-requests/${id}`, payload);
  }

  return {
    feedbackItems,
    keywordItems,
    feedbackLoading,
    keywordLoading,
    fetchFeedback,
    fetchKeywords,
    updateFeedback,
    updateKeyword,
  };
});
