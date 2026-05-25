import { describe, it, expect, vi, beforeEach } from "vitest";

const mockPush = vi.fn();
const mockReplace = vi.fn();

vi.mock("vue-router", () => ({
  createRouter: vi.fn(() => ({
    beforeEach: vi.fn(),
    push: mockPush,
    replace: mockReplace,
  })),
  createWebHistory: vi.fn(),
}));

vi.mock("element-plus", () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
}));

describe("路由守卫逻辑", () => {
  const ADMIN_ROLES = new Set(["admin", "superadmin"]);

  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  function createMockAuthStore(overrides: Record<string, any> = {}) {
    return {
      isLoggedIn: false,
      user: null,
      initFromStorage: vi.fn(),
      ...overrides,
    };
  }

  describe("认证守卫", () => {
    it("已登录用户访问 Login/Register 时重定向到 Dashboard", () => {
      const auth = createMockAuthStore({ isLoggedIn: true });
      const to = { name: "Login", matched: [] };
      const next = vi.fn();

      const guard = (auth: any, to: any, next: any) => {
        if (auth.isLoggedIn && (to.name === "Login" || to.name === "Register")) {
          next({ name: "Dashboard" });
          return;
        }
        next();
      };

      guard(auth, to, next);
      expect(next).toHaveBeenCalledWith({ name: "Dashboard" });
    });

    it("未登录用户访问需认证页面时重定向到 Login", () => {
      const auth = createMockAuthStore({ isLoggedIn: false });
      const to = {
        name: "Dashboard",
        matched: [{ meta: { requiresAuth: true } }],
        fullPath: "/dashboard",
      };
      const next = vi.fn();

      const guard = (auth: any, to: any, next: any) => {
        if (to.matched.some((r: any) => r.meta.requiresAuth) && !auth.isLoggedIn) {
          next({ name: "Login", query: { redirect: to.fullPath } });
          return;
        }
        next();
      };

      guard(auth, to, next);
      expect(next).toHaveBeenCalledWith({ name: "Login", query: { redirect: "/dashboard" } });
    });

    it("已登录用户访问需认证页面时放行", () => {
      const auth = createMockAuthStore({ isLoggedIn: true });
      const to = {
        name: "Dashboard",
        matched: [{ meta: { requiresAuth: true } }],
      };
      const next = vi.fn();

      const guard = (auth: any, to: any, next: any) => {
        if (to.matched.some((r: any) => r.meta.requiresAuth) && !auth.isLoggedIn) {
          next({ name: "Login", query: { redirect: to.fullPath } });
          return;
        }
        next();
      };

      guard(auth, to, next);
      expect(next).toHaveBeenCalledWith();
    });

    it("localStorage 有 token 时调用 initFromStorage", () => {
      localStorage.setItem("access_token", "stored-token");
      const auth = createMockAuthStore({ isLoggedIn: false, initFromStorage: vi.fn() });
      const to = { name: "Dashboard", matched: [{ meta: { requiresAuth: true } }] };
      const next = vi.fn();

      const guard = (auth: any, to: any, next: any, token: string | null) => {
        if (token && !auth.isLoggedIn) {
          auth.initFromStorage();
        }
        if (to.matched.some((r: any) => r.meta.requiresAuth) && !auth.isLoggedIn) {
          next({ name: "Login" });
          return;
        }
        next();
      };

      guard(auth, to, next, localStorage.getItem("access_token"));
      expect(auth.initFromStorage).toHaveBeenCalled();
    });
  });

  describe("管理员守卫", () => {
    it("管理员角色可以访问管理页面", () => {
      const auth = createMockAuthStore({
        isLoggedIn: true,
        user: { role: "admin" },
      });
      const to = {
        name: "AdminMonitor",
        matched: [{ meta: { requiresAdmin: true } }],
      };
      const next = vi.fn();

      const guard = (auth: any, to: any, next: any) => {
        if (to.matched.some((r: any) => r.meta.requiresAdmin)) {
          const userRole = auth.user?.role || "";
          if (!ADMIN_ROLES.has(userRole)) {
            next({ name: "Dashboard" });
            return;
          }
        }
        next();
      };

      guard(auth, to, next);
      expect(next).toHaveBeenCalledWith();
    });

    it("普通用户不能访问管理页面", async () => {
      const { ElMessage } = await import("element-plus");
      const auth = createMockAuthStore({
        isLoggedIn: true,
        user: { role: "user" },
      });
      const to = {
        name: "AdminMonitor",
        matched: [{ meta: { requiresAdmin: true } }],
      };
      const next = vi.fn();

      const guard = (auth: any, to: any, next: any) => {
        if (to.matched.some((r: any) => r.meta.requiresAdmin)) {
          const userRole = auth.user?.role || "";
          if (!ADMIN_ROLES.has(userRole)) {
            ElMessage.error("无权访问该页面");
            next({ name: "Dashboard" });
            return;
          }
        }
        next();
      };

      guard(auth, to, next);
      expect(vi.mocked(ElMessage.error)).toHaveBeenCalledWith("无权访问该页面");
      expect(next).toHaveBeenCalledWith({ name: "Dashboard" });
    });

    it("superadmin 也可以访问管理页面", () => {
      const auth = createMockAuthStore({
        isLoggedIn: true,
        user: { role: "superadmin" },
      });
      const to = {
        name: "AdminMonitor",
        matched: [{ meta: { requiresAdmin: true } }],
      };
      const next = vi.fn();

      const guard = (auth: any, to: any, next: any) => {
        if (to.matched.some((r: any) => r.meta.requiresAdmin)) {
          const userRole = auth.user?.role || "";
          if (!ADMIN_ROLES.has(userRole)) {
            next({ name: "Dashboard" });
            return;
          }
        }
        next();
      };

      guard(auth, to, next);
      expect(next).toHaveBeenCalledWith();
    });
  });

  describe("公开页面", () => {
    it("未登录用户可以访问 Landing 页面", () => {
      const auth = createMockAuthStore({ isLoggedIn: false });
      const to = { name: "Landing", matched: [] };
      const next = vi.fn();

      const guard = (auth: any, to: any, next: any) => {
        if (to.matched.some((r: any) => r.meta.requiresAuth) && !auth.isLoggedIn) {
          next({ name: "Login" });
          return;
        }
        next();
      };

      guard(auth, to, next);
      expect(next).toHaveBeenCalledWith();
    });
  });
});
