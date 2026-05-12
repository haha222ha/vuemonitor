import { defineStore } from "pinia";
import { ref } from "vue";
import api from "../utils/api";

interface User {
  id: number;
  username: string;
  email: string;
  role: string;
  status: number; // Assuming status is a number (e.g., 0 for inactive, 1 for active)
  created_at: string;
  updated_at: string;
}

export const useUsersStore = defineStore("users", () => {
  const users = ref<User[]>([]);
  const total = ref(0);
  const loading = ref(false);

  async function fetchUsers(page: number, pageSize: number, keyword?: string) {
    loading.value = true;
    try {
      const params: any = { page, pageSize };
      if (keyword) {
        params.keyword = keyword;
      }
      const { data } = await api.get("/admin/users", { params });
      // Assuming the API returns { users: User[], total: number }
      users.value = data.users;
      total.value = data.total;
    } catch (error) {
      console.error("Failed to fetch users:", error);
    } finally {
      loading.value = false;
    }
  }

  async function updateUser(id: number, data: Partial<User>) {
    try {
      await api.put(`/admin/users/${id}`, data);
    } catch (error) {
      console.error(`Failed to update user ${id}:`, error);
      throw error; // Re-throw so the view can handle it if needed
    }
  }

  async function deleteUser(id: number) {
    try {
      await api.delete(`/admin/users/${id}`);
    } catch (error) {
      console.error(`Failed to delete user ${id}:`, error);
      throw error;
    }
  }

  return {
    users,
    total,
    loading,
    fetchUsers,
    updateUser,
    deleteUser
  };
});