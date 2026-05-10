import { defineStore } from "pinia";
import { ref, computed } from "vue";
import api from "../utils/api";

export const useAuthStore = defineStore("auth", () => {
  const token = ref(localStorage.getItem("access_token") || "");
  const user = ref<any>(null);

  const isLoggedIn = computed(() => !!token.value);
  const userPlan = computed(() => user.value?.plan || "free");

  async function login(email: string, password: string) {
    const { data } = await api.post("/auth/login", { email, password });
    token.value = data.access_token;
    localStorage.setItem("access_token", data.access_token);
    if (data.refresh_token) {
      localStorage.setItem("refresh_token", data.refresh_token);
    }
    await fetchUser();
  }

  async function register(email: string, password: string, nickname: string) {
    await api.post("/auth/register", { email, password, nickname });
    await login(email, password);
  }

  async function fetchUser() {
    if (!token.value) return;
    try {
      const { data } = await api.get("/auth/me");
      user.value = data?.data || data;
      localStorage.setItem("user_info", JSON.stringify(user.value));
    } catch {
      user.value = null;
    }
  }

  function logout() {
    token.value = "";
    user.value = null;
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user_info");
  }

  function initFromStorage() {
    const saved = localStorage.getItem("user_info");
    if (saved) {
      try {
        user.value = JSON.parse(saved);
      } catch {}
    }
  }

  return { token, user, isLoggedIn, userPlan, login, register, fetchUser, logout, initFromStorage };
});
