import { defineStore } from "pinia";
import { ref } from "vue";
import api from "../utils/api";

export const useAuthStore = defineStore("auth", () => {
  const user = ref<Record<string, unknown> | null>(null);
  const isAuthenticated = ref(!!localStorage.getItem("access_token"));

  async function login(email: string, password: string) {
    const { data } = await api.post("/auth/login", { email, password });
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
    isAuthenticated.value = true;
    await fetchUser();
  }

  async function register(email: string, nickname: string, password: string) {
    await api.post("/auth/register", { email, nickname, password });
  }

  async function fetchUser() {
    try {
      const { data } = await api.get("/auth/me");
      user.value = data;
    } catch {
      logout();
    }
  }

  function logout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    user.value = null;
    isAuthenticated.value = false;
  }

  return { user, isAuthenticated, login, register, fetchUser, logout };
});
