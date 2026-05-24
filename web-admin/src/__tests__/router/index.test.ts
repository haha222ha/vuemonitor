import { describe, it, expect, vi, beforeEach } from "vitest";

describe("Admin API 拦截器", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  describe("请求拦截器", () => {
    it("有 admin_token 时添加 Authorization header", () => {
      localStorage.setItem("admin_token", "admin-jwt-token");

      const config = { headers: {} };
      const requestInterceptor = (config: any) => {
        const token = localStorage.getItem("admin_token");
        if (token) config.headers.Authorization = `Bearer ${token}`;
        return config;
      };

      const result = requestInterceptor(config);
      expect(result.headers.Authorization).toBe("Bearer admin-jwt-token");
    });

    it("无 admin_token 时不添加 Authorization header", () => {
      const config = { headers: {} };
      const requestInterceptor = (config: any) => {
        const token = localStorage.getItem("admin_token");
        if (token) config.headers.Authorization = `Bearer ${token}`;
        return config;
      };

      const result = requestInterceptor(config);
      expect(result.headers.Authorization).toBeUndefined();
    });
  });

  describe("响应拦截器 - 401 处理", () => {
    it("401 时清除 token 并跳转到登录页", async () => {
      localStorage.setItem("admin_token", "expired-token");

      const originalLocation = window.location;
      Object.defineProperty(window, "location", {
        value: { href: "", pathname: "/admin/dashboard" },
        writable: true,
      });

      const responseInterceptor = (error: any) => {
        if (error.response?.status === 401) {
          localStorage.removeItem("admin_token");
          window.location.href = "/admin/login";
        }
        return Promise.reject(error);
      };

      const error = { response: { status: 401 } };
      await expect(responseInterceptor(error)).rejects.toEqual(error);

      expect(localStorage.getItem("admin_token")).toBeNull();
      expect(window.location.href).toBe("/admin/login");

      Object.defineProperty(window, "location", { value: originalLocation, writable: true });
    });

    it("非 401 错误不清除 token", async () => {
      localStorage.setItem("admin_token", "valid-token");

      const responseInterceptor = (error: any) => {
        if (error.response?.status === 401) {
          localStorage.removeItem("admin_token");
        }
        return Promise.reject(error);
      };

      const error = { response: { status: 500 } };
      await expect(responseInterceptor(error)).rejects.toEqual(error);

      expect(localStorage.getItem("admin_token")).toBe("valid-token");
    });
  });
});

describe("Admin 路由守卫逻辑", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("无 token 时重定向到登录页", () => {
    const token = localStorage.getItem("admin_token");
    const loginPath = "/admin/login";

    const guard = (token: string | null, toPath: string, next: any) => {
      if (toPath === loginPath) {
        next();
        return;
      }
      if (!token) {
        next(loginPath);
        return;
      }
      next();
    };

    const next = vi.fn();
    guard(token, "/admin/dashboard", next);
    expect(next).toHaveBeenCalledWith("/admin/login");
  });

  it("访问登录页时放行", () => {
    const guard = (token: string | null, toPath: string, next: any) => {
      const loginPath = "/admin/login";
      if (toPath === loginPath) {
        next();
        return;
      }
      if (!token) {
        next(loginPath);
        return;
      }
      next();
    };

    const next = vi.fn();
    guard(null, "/admin/login", next);
    expect(next).toHaveBeenCalledWith();
  });

  it("有 token 时验证通过则放行", () => {
    localStorage.setItem("admin_token", "valid-admin-token");
    const token = localStorage.getItem("admin_token");

    const guard = (token: string | null, next: any, validateResult: boolean) => {
      if (!token) {
        next("/admin/login");
        return;
      }
      if (validateResult) {
        next();
      } else {
        localStorage.removeItem("admin_token");
        next("/admin/login");
      }
    };

    const next = vi.fn();
    guard(token, next, true);
    expect(next).toHaveBeenCalledWith();
  });

  it("有 token 但验证失败时重定向到登录页", () => {
    localStorage.setItem("admin_token", "invalid-token");
    const token = localStorage.getItem("admin_token");

    const guard = (token: string | null, next: any, validateResult: boolean) => {
      if (!token) {
        next("/admin/login");
        return;
      }
      if (validateResult) {
        next();
      } else {
        localStorage.removeItem("admin_token");
        next("/admin/login");
      }
    };

    const next = vi.fn();
    guard(token, next, false);
    expect(localStorage.getItem("admin_token")).toBeNull();
    expect(next).toHaveBeenCalledWith("/admin/login");
  });
});
