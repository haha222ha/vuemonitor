import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

let isRefreshing = false;
let refreshSubscribers: Array<(token: string) => void> = [];

function subscribeTokenRefresh(cb: (token: string) => void) {
  refreshSubscribers.push(cb);
}

function onTokenRefreshed(newToken: string) {
  refreshSubscribers.forEach((cb) => cb(newToken));
  refreshSubscribers = [];
}

async function getAccessToken(): Promise<string | null> {
  if (window.electronAPI) {
    return await window.electronAPI.invoke("secure-storage:get", "access_token");
  }
  return localStorage.getItem("access_token");
}

async function setTokens(access: string, refresh?: string): Promise<void> {
  if (window.electronAPI) {
    await window.electronAPI.invoke("secure-storage:set", "access_token", access);
    if (refresh) await window.electronAPI.invoke("secure-storage:set", "refresh_token", refresh);
  } else {
    localStorage.setItem("access_token", access);
    if (refresh) localStorage.setItem("refresh_token", refresh);
  }
}

async function clearTokens(): Promise<void> {
  if (window.electronAPI) {
    await window.electronAPI.invoke("secure-storage:delete", "access_token");
    await window.electronAPI.invoke("secure-storage:delete", "refresh_token");
  } else {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  }
}

api.interceptors.request.use(async (config) => {
  const token = await getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (!error.response && error.code === "ERR_NETWORK") {
      return Promise.reject(error);
    }

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      if (isRefreshing) {
        return new Promise((resolve) => {
          subscribeTokenRefresh((newToken: string) => {
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            resolve(api.request(originalRequest));
          });
        });
      }

      isRefreshing = true;
      let refreshToken: string | null = null;
      if (window.electronAPI) {
        refreshToken = await window.electronAPI.invoke("secure-storage:get", "refresh_token");
      } else {
        refreshToken = localStorage.getItem("refresh_token");
      }

      if (refreshToken) {
        try {
          const { data } = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          await setTokens(data.access_token, data.refresh_token);
          onTokenRefreshed(data.access_token);
          originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
          return api.request(originalRequest);
        } catch {
          await clearTokens();
          window.location.hash = "#/login";
          return Promise.reject(error);
        } finally {
          isRefreshing = false;
        }
      } else {
        await clearTokens();
        window.location.hash = "#/login";
      }
    }

    return Promise.reject(error);
  }
);

export function isNetworkError(error: unknown): boolean {
  const e = error as { response?: unknown; code?: string; message?: string };
  return !e.response && (e.code === "ERR_NETWORK" || e.code === "ECONNREFUSED" || e.code === "ECONNRESET" || !!e.message?.includes("Network Error"));
}

export default api;
