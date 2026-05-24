import { defineStore } from "pinia";
import { ref, computed } from "vue";
import api from "../utils/api";

export const useAdminStore = defineStore("admin", () => {
  const token = ref(localStorage.getItem("admin_token") || "");
  const username = ref(localStorage.getItem("admin_username") || "管理员");
  const isLoggedIn = computed(() => !!token.value);

  function isTokenExpired(tokenStr: string): boolean {
    try {
      const payload = JSON.parse(atob(tokenStr.split(".")[1]));
      return payload.exp * 1000 < Date.now();
    } catch {
      return true;
    }
  }

  function hasAdminRole(tokenStr: string): boolean {
    try {
      const payload = JSON.parse(atob(tokenStr.split(".")[1]));
      const role = payload.role || "";
      return ["admin", "super_admin"].includes(role);
    } catch {
      return false;
    }
  }

  async function login(usernameInput: string, password: string) {
    const { data } = await api.post("/admin/login", { username: usernameInput, password });
    const accessToken = data.access_token || data?.access_token;
    const refreshToken = data.refresh_token || data?.refresh_token;

    token.value = accessToken;
    username.value = usernameInput;
    localStorage.setItem("admin_token", accessToken);
    localStorage.setItem("admin_username", usernameInput);
    if (refreshToken) {
      localStorage.setItem("admin_refresh_token", refreshToken);
    }
  }

  async function logout() {
    try {
      await api.post("/auth/logout");
    } catch {}
    token.value = "";
    username.value = "";
    localStorage.removeItem("admin_token");
    localStorage.removeItem("admin_refresh_token");
    localStorage.removeItem("admin_username");
  }

  function initFromStorage() {
    const storedToken = localStorage.getItem("admin_token");
    if (storedToken && !isTokenExpired(storedToken)) {
      token.value = storedToken;
      username.value = localStorage.getItem("admin_username") || "管理员";
    } else {
      logout();
    }
  }

  return { token, username, isLoggedIn, login, logout, initFromStorage, isTokenExpired, hasAdminRole };
});
