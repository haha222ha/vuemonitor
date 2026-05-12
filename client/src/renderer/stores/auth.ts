import { defineStore } from "pinia";
import { ref } from "vue";
import api from "../utils/api";

declare global {
  interface Window {
    electronAPI?: {
      invoke: (channel: string, ...args: unknown[]) => Promise<unknown>;
      on: (channel: string, callback: (...args: unknown[]) => void) => () => void;
      getAppVersion: () => Promise<string>;
      getPlatform: () => string;
    };
  }
}

export const useAuthStore = defineStore("auth", () => {
  const user = ref<Record<string, unknown> | null>(null);
  const isAuthenticated = ref(!!localStorage.getItem("access_token"));

  async function login(account: string, password: string) {
    const serverUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";
    const baseUrl = serverUrl.replace(/\/api\/v1\/?$/, "");

    if (window.electronAPI) {
      const result = await window.electronAPI.invoke("auth:login", account, password, baseUrl) as Record<string, unknown>;
      if (result.access_token) {
        localStorage.setItem("access_token", result.access_token as string);
        if (result.refresh_token) {
          localStorage.setItem("refresh_token", result.refresh_token as string);
        }
        isAuthenticated.value = true;
        await fetchUser();
      } else {
        throw new Error((result.message as string) || "登录失败");
      }
    } else {
      const { data } = await api.post("/auth/login", { account, password });
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      isAuthenticated.value = true;
      await fetchUser();
    }
  }

  async function register(email: string | undefined, nickname: string, password: string) {
    const serverUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";
    const baseUrl = serverUrl.replace(/\/api\/v1\/?$/, "");

    if (window.electronAPI) {
      const result = await window.electronAPI.invoke("auth:register", nickname, password, email, baseUrl) as Record<string, unknown>;
      if ((result as any).error) {
        throw new Error((result.message as string) || "注册失败");
      }
    } else {
      const payload: Record<string, unknown> = { nickname, password };
      if (email && email.trim()) {
        payload.email = email.trim();
      }
      await api.post("/auth/register", payload);
    }
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
    if (window.electronAPI) {
      window.electronAPI.invoke("auth:logout");
    }
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    user.value = null;
    isAuthenticated.value = false;
  }

  return { user, isAuthenticated, login, register, fetchUser, logout };
});
