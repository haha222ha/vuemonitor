import { defineStore } from "pinia";
import { ref, computed } from "vue";
import api from "../utils/api";
import { ElMessage } from "element-plus";

export interface TeamMember {
  user_id: string;
  nickname: string;
  avatar_url?: string;
  role: 'owner' | 'admin' | 'member' | 'viewer';
  joined_at: string;
}

export interface Team {
  id: string;
  name: string;
  description: string;
  owner_id: string;
  invite_code: string;
  member_count: number;
  created_at: string;
  members: TeamMember[];
  shared_products: string[];
  shared_rules: string[];
}

export const useTeamsStore = defineStore("teams", () => {
  const myTeams = ref<Team[]>([]);
  const currentTeam = ref<Team | null>(null);
  const loading = ref<boolean>(false);

  async function fetchMyTeams() {
    loading.value = true;
    try {
      const { data } = await api.get("/teams");
      myTeams.value = data || [];
    } catch (error) {
      ElMessage.error("Failed to fetch teams");
    } finally {
      loading.value = false;
    }
  }

  async function createTeam(data: { name: string; description?: string }) {
    try {
      await api.post("/teams", data);
    } catch (error) {
      ElMessage.error("Failed to create team");
    }
  }

  async function updateTeam(id: string, data: { name?: string; description?: string }) {
    try {
      await api.put(`/teams/${id}`, data);
    } catch (error) {
      ElMessage.error("Failed to update team");
    }
  }

  async function dissolveTeam(id: string) {
    try {
      await api.delete(`/teams/${id}`);
    } catch (error) {
      ElMessage.error("Failed to dissolve team");
    }
  }

  async function joinTeam(inviteCode: string) {
    try {
      await api.post("/teams/join", { invite_code: inviteCode });
    } catch (error) {
      ElMessage.error("Failed to join team");
    }
  }

  async function removeMember(teamId: string, userId: string) {
    try {
      await api.delete(`/teams/${teamId}/members/${userId}`);
    } catch (error) {
      ElMessage.error("Failed to remove member");
    }
  }

  async function updateMemberRole(teamId: string, userId: string, role: string) {
    try {
      await api.put(`/teams/${teamId}/members/${userId}`, { role });
    } catch (error) {
      ElMessage.error("Failed to update member role");
    }
  }

  async function shareProduct(teamId: string, productId: string) {
    try {
      await api.post(`/teams/${teamId}/products`, { product_id: productId });
    } catch (error) {
      ElMessage.error("Failed to share product");
    }
  }

  async function unshareProduct(teamId: string, productId: string) {
    try {
      await api.delete(`/teams/${teamId}/products/${productId}`);
    } catch (error) {
      ElMessage.error("Failed to unshare product");
    }
  }

  return { myTeams, currentTeam, loading, fetchMyTeams, createTeam, updateTeam, dissolveTeam, joinTeam, removeMember, updateMemberRole, shareProduct, unshareProduct };
});