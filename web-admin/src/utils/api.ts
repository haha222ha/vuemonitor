import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";
import { ElMessage } from "element-plus";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "/api/v1";
const BASE_PATH = import.meta.env.BASE_URL || "/";

const MAX_RETRY_COUNT = 2;
const RETRY_DELAY_MS = 1000;
const RETRYABLE_STATUS_CODES = new Set([408, 500, 502, 503, 504]);

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

let isRefreshing = false;
let pendingRequests: Array<{
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}> = [];

function processPendingRequests(token: string | null, error: unknown = null) {
  pendingRequests.forEach(({ resolve, reject }) => {
    if (token) {
      resolve(token);
    } else {
      reject(error);
    }
  });
  pendingRequests = [];
}

async function refreshAdminToken(): Promise<string | null> {
  const refreshToken = localStorage.getItem("admin_refresh_token");
  if (!refreshToken) return null;

  try {
    const { data } = await axios.post(`${API_BASE_URL}/auth/refresh`, {
      refresh_token: refreshToken,
    });

    const newAccessToken = data?.access_token || data?.data?.access_token;
    const newRefreshToken = data?.refresh_token || data?.data?.refresh_token;

    if (newAccessToken) {
      localStorage.setItem("admin_token", newAccessToken);
      if (newRefreshToken) {
        localStorage.setItem("admin_refresh_token", newRefreshToken);
      }
      return newAccessToken;
    }
    return null;
  } catch {
    return null;
  }
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem("admin_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => {
    if (response.data && typeof response.data === "object" && "data" in response.data && "code" in response.data) {
      response.data = response.data.data;
    }
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: number; _auth_retry?: boolean };

    if (error.response?.status === 401 && !originalRequest._auth_retry) {
      if (originalRequest.url?.includes("/auth/refresh") || originalRequest.url?.includes("/admin/login")) {
        clearAdminAuthAndRedirect();
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          pendingRequests.push({
            resolve: (newToken: string) => {
              originalRequest.headers.Authorization = `Bearer ${newToken}`;
              resolve(api(originalRequest));
            },
            reject,
          });
        });
      }

      originalRequest._auth_retry = true;
      isRefreshing = true;

      try {
        const newToken = await refreshAdminToken();

        if (newToken) {
          processPendingRequests(newToken);
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return api(originalRequest);
        } else {
          processPendingRequests(null, error);
          clearAdminAuthAndRedirect();
          return Promise.reject(error);
        }
      } catch (refreshError) {
        processPendingRequests(null, refreshError);
        clearAdminAuthAndRedirect();
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    const retryCount = originalRequest._retry || 0;
    const isRetryable = !error.response || RETRYABLE_STATUS_CODES.has(error.response?.status);
    const isNotAuthRefresh = !originalRequest.url?.includes("/auth/") && !originalRequest.url?.includes("/admin/login");

    if (isRetryable && retryCount < MAX_RETRY_COUNT && isNotAuthRefresh) {
      originalRequest._retry = retryCount + 1;
      const backoffDelay = RETRY_DELAY_MS * Math.pow(2, retryCount);
      await delay(backoffDelay);
      return api(originalRequest);
    }

    if (error.response?.status === 429) {
      ElMessage.warning("请求过于频繁，请稍后再试");
    } else if ((error.response?.data as { message?: string })?.message && error.response?.status !== 401) {
      ElMessage.error((error.response!.data as { message: string }).message);
    } else if (!error.response) {
      ElMessage.error("网络连接异常，请检查网络后重试");
    }

    return Promise.reject(error);
  }
);

function clearAdminAuthAndRedirect() {
  localStorage.removeItem("admin_token");
  localStorage.removeItem("admin_refresh_token");
  localStorage.removeItem("admin_username");
  const loginPath = `${BASE_PATH}login`.replace(/\/+/g, "/");
  if (!window.location.pathname.endsWith("/login")) {
    window.location.href = loginPath;
  }
}

export default api;
export { BASE_PATH, API_BASE_URL };
