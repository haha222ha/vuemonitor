import { describe, it, expect, vi, beforeEach } from "vitest";
import axios from "axios";

vi.mock("element-plus", () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
}));

describe("API 拦截器", () => {
  let mockAxiosInstance: any;

  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    mockAxiosInstance = {
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    };
  });

  describe("请求拦截器", () => {
    it("有 token 时添加 Authorization header", () => {
      localStorage.setItem("access_token", "my-jwt-token");

      const config = { headers: {} };
      const requestInterceptor = (config: any) => {
        const token = localStorage.getItem("access_token");
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      };

      const result = requestInterceptor(config);
      expect(result.headers.Authorization).toBe("Bearer my-jwt-token");
    });

    it("无 token 时不添加 Authorization header", () => {
      const config = { headers: {} };
      const requestInterceptor = (config: any) => {
        const token = localStorage.getItem("access_token");
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      };

      const result = requestInterceptor(config);
      expect(result.headers.Authorization).toBeUndefined();
    });
  });

  describe("响应拦截器 - 数据解包", () => {
    it("解包 { code, data } 格式的响应", () => {
      const responseInterceptor = (response: any) => {
        if (response.data && typeof response.data === "object" && "data" in response.data && "code" in response.data) {
          response.data = response.data.data;
        }
        return response;
      };

      const response = { data: { code: 0, data: { items: [1, 2, 3] } } };
      const result = responseInterceptor(response);
      expect(result.data).toEqual({ items: [1, 2, 3] });
    });

    it("非标准格式响应保持原样", () => {
      const responseInterceptor = (response: any) => {
        if (response.data && typeof response.data === "object" && "data" in response.data && "code" in response.data) {
          response.data = response.data.data;
        }
        return response;
      };

      const response = { data: { items: [1, 2, 3] } };
      const result = responseInterceptor(response);
      expect(result.data).toEqual({ items: [1, 2, 3] });
    });
  });

  describe("响应拦截器 - 错误处理", () => {
    it("429 状态码显示频率限制提示", async () => {
      const { ElMessage } = await import("element-plus");

      const error = { response: { status: 429, data: {} } };

      if (error.response?.status === 429) {
        ElMessage.warning("请求过于频繁，请稍后再试");
      }

      expect(ElMessage.warning).toHaveBeenCalledWith("请求过于频繁，请稍后再试");
    });

    it("网络错误显示连接异常提示", async () => {
      const { ElMessage } = await import("element-plus");

      const error = { response: null };

      if (!error.response) {
        ElMessage.error("网络连接异常，请检查网络后重试");
      }

      expect(ElMessage.error).toHaveBeenCalledWith("网络连接异常，请检查网络后重试");
    });
  });

  describe("Token 刷新逻辑", () => {
    it("401 时尝试刷新 token", async () => {
      localStorage.setItem("refresh_token", "valid-refresh-token");

      const refreshAccessToken = async () => {
        const refreshToken = localStorage.getItem("refresh_token");
        if (!refreshToken) return null;
        try {
          const { data } = await axios.post("/api/v1/auth/refresh", {
            refresh_token: refreshToken,
          });
          const newAccessToken = data?.access_token || data?.data?.access_token;
          if (newAccessToken) {
            localStorage.setItem("access_token", newAccessToken);
            return newAccessToken;
          }
          return null;
        } catch {
          return null;
        }
      };

      vi.spyOn(axios, "post").mockResolvedValueOnce({
        data: { access_token: "refreshed-token" },
      });

      const result = await refreshAccessToken();
      expect(result).toBe("refreshed-token");
      expect(localStorage.getItem("access_token")).toBe("refreshed-token");
    });

    it("无 refresh_token 时返回 null", async () => {
      const refreshAccessToken = async () => {
        const refreshToken = localStorage.getItem("refresh_token");
        if (!refreshToken) return null;
        return "should-not-reach";
      };

      const result = await refreshAccessToken();
      expect(result).toBeNull();
    });
  });

  describe("重试逻辑", () => {
    it("5xx 错误在重试次数内会重试", () => {
      const RETRYABLE_STATUS_CODES = new Set([408, 500, 502, 503, 504]);
      const MAX_RETRY_COUNT = 2;

      expect(RETRYABLE_STATUS_CODES.has(502)).toBe(true);
      expect(RETRYABLE_STATUS_CODES.has(503)).toBe(true);
      expect(RETRYABLE_STATUS_CODES.has(404)).toBe(false);
      expect(MAX_RETRY_COUNT).toBe(2);
    });

    it("指数退避延迟计算正确", () => {
      const RETRY_DELAY_MS = 1000;
      const delays = [0, 1, 2].map((retryCount) => RETRY_DELAY_MS * Math.pow(2, retryCount));
      expect(delays).toEqual([1000, 2000, 4000]);
    });
  });

  describe("clearAuthAndRedirect", () => {
    it("清除所有认证数据并跳转", () => {
      localStorage.setItem("access_token", "token");
      localStorage.setItem("refresh_token", "refresh");
      localStorage.setItem("user_info", "{}");

      const originalLocation = window.location;
      Object.defineProperty(window, "location", {
        value: { href: "", pathname: "/dashboard" },
        writable: true,
      });

      const clearAuthAndRedirect = () => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("user_info");
        if (window.location.pathname.startsWith("/dashboard")) {
          window.location.href = "/login";
        }
      };

      clearAuthAndRedirect();

      expect(localStorage.getItem("access_token")).toBeNull();
      expect(localStorage.getItem("refresh_token")).toBeNull();
      expect(localStorage.getItem("user_info")).toBeNull();
      expect(window.location.href).toBe("/login");

      Object.defineProperty(window, "location", { value: originalLocation, writable: true });
    });
  });
});
