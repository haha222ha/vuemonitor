import { describe, it, expect, vi, beforeEach } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useAdminStore } from "../../stores/admin";

vi.mock("../../utils/api", () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

import api from "../../utils/api";

describe("useAdminStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
    vi.clearAllMocks();
  });

  describe("初始状态", () => {
    it("无 token 时 isLoggedIn 为 false", () => {
      const store = useAdminStore();
      expect(store.isLoggedIn).toBe(false);
    });

    it("localStorage 有 admin_token 时 isLoggedIn 为 true", () => {
      localStorage.setItem("admin_token", "admin-jwt");
      const store = useAdminStore();
      expect(store.isLoggedIn).toBe(true);
    });

    it("默认 username 为 '管理员'", () => {
      const store = useAdminStore();
      expect(store.username).toBe("管理员");
    });

    it("localStorage 有 admin_username 时恢复", () => {
      localStorage.setItem("admin_username", "superadmin");
      const store = useAdminStore();
      expect(store.username).toBe("superadmin");
    });
  });

  describe("login", () => {
    it("登录成功后存储 token 和 username", async () => {
      const mockPost = vi.mocked(api.post);
      mockPost.mockResolvedValueOnce({
        data: { access_token: "admin-token-123" },
      });

      const store = useAdminStore();
      await store.login("admin", "securepassword");

      expect(mockPost).toHaveBeenCalledWith("/admin/login", {
        username: "admin",
        password: "securepassword",
      });
      expect(localStorage.getItem("admin_token")).toBe("admin-token-123");
      expect(localStorage.getItem("admin_username")).toBe("admin");
      expect(store.token).toBe("admin-token-123");
      expect(store.username).toBe("admin");
      expect(store.isLoggedIn).toBe(true);
    });

    it("登录失败时抛出异常", async () => {
      const mockPost = vi.mocked(api.post);
      mockPost.mockRejectedValueOnce(new Error("Unauthorized"));

      const store = useAdminStore();
      await expect(store.login("bad", "wrong")).rejects.toThrow("Unauthorized");
      expect(store.isLoggedIn).toBe(false);
    });
  });

  describe("logout", () => {
    it("清除所有认证状态", () => {
      localStorage.setItem("admin_token", "token");
      localStorage.setItem("admin_username", "admin");

      const store = useAdminStore();
      store.logout();

      expect(localStorage.getItem("admin_token")).toBeNull();
      expect(localStorage.getItem("admin_username")).toBeNull();
      expect(store.token).toBe("");
      expect(store.username).toBe("");
      expect(store.isLoggedIn).toBe(false);
    });
  });
});
