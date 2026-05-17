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

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
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
      console.warn("[API] 网络不可达，服务可能离线");
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
      const refreshToken = localStorage.getItem("refresh_token");

      if (refreshToken) {
        try {
          const { data } = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          localStorage.setItem("access_token", data.access_token);
          localStorage.setItem("refresh_token", data.refresh_token);
          onTokenRefreshed(data.access_token);
          originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
          return api.request(originalRequest);
        } catch {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          window.location.hash = "#/login";
          return Promise.reject(error);
        } finally {
          isRefreshing = false;
        }
      } else {
        localStorage.removeItem("access_token");
        window.location.hash = "#/login";
      }
    }

    if (error.response?.status === 503) {
      console.warn("[API] 服务暂时不可用 (503)");
    }

    return Promise.reject(error);
  }
);

export function isNetworkError(error: any): boolean {
  return !error.response && (error.code === "ERR_NETWORK" || error.code === "ECONNREFUSED" || error.code === "ECONNRESET" || error.message?.includes("Network Error"));
}

export default api;
