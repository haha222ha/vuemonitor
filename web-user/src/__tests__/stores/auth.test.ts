import { describe, it, expect, vi, beforeEach } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useAuthStore } from "../../stores/auth";

vi.mock("../../utils/api", () => ({
  default: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

import api from "../../utils/api";

describe("useAuthStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
    vi.clearAllMocks();
  });

  describe("初始状态", () => {
    it("token 为空时 isLoggedIn 为 false", () => {
      const store = useAuthStore();
      expect(store.isLoggedIn).toBe(false);
    });

    it("user 初始为 null", () => {
      const store = useAuthStore();
      expect(store.user).toBeNull();
    });

    it("localStorage 有 token 时 isLoggedIn 为 true", () => {
      localStorage.setItem("access_token", "test-token");
      const store = useAuthStore();
      expect(store.isLoggedIn).toBe(true);
    });
  });

  describe("login", () => {
    it("登录成功后存储 token 并获取用户信息", async () => {
      const mockPost = vi.mocked(api.post);
      const mockGet = vi.mocked(api.get);

      mockPost.mockResolvedValueOnce({
        data: { access_token: "new-token", refresh_token: "new-refresh" },
      });
      mockGet.mockResolvedValueOnce({
        data: { data: { email: "test@example.com", nickname: "Test", role: "user", plan: "free" } },
      });

      const store = useAuthStore();
      await store.login("test@example.com", "password123");

      expect(mockPost).toHaveBeenCalledWith("/auth/login", {
        account: "test@example.com",
        password: "password123",
      });
      expect(localStorage.getItem("access_token")).toBe("new-token");
      expect(localStorage.getItem("refresh_token")).toBe("new-refresh");
      expect(store.user).toEqual({ email: "test@example.com", nickname: "Test", role: "user", plan: "free" });
    });

    it("登录失败时抛出异常", async () => {
      const mockPost = vi.mocked(api.post);
      mockPost.mockRejectedValueOnce(new Error("Invalid credentials"));

      const store = useAuthStore();
      await expect(store.login("bad@example.com", "wrong")).rejects.toThrow("Invalid credentials");
    });
  });

  describe("register", () => {
    it("注册成功后自动登录", async () => {
      const mockPost = vi.mocked(api.post);
      const mockGet = vi.mocked(api.get);

      mockPost.mockResolvedValueOnce({ data: { message: "ok" } });
      mockPost.mockResolvedValueOnce({
        data: { access_token: "reg-token", refresh_token: "reg-refresh" },
      });
      mockGet.mockResolvedValueOnce({
        data: { data: { email: "new@example.com", nickname: "NewUser" } },
      });

      const store = useAuthStore();
      await store.register("new@example.com", "password123", "NewUser");

      expect(mockPost).toHaveBeenCalledWith("/auth/register", {
        password: "password123",
        nickname: "NewUser",
        email: "new@example.com",
      });
      expect(localStorage.getItem("access_token")).toBe("reg-token");
    });
  });

  describe("fetchUser", () => {
    it("有 token 时获取用户信息", async () => {
      localStorage.setItem("access_token", "valid-token");
      const mockGet = vi.mocked(api.get);
      mockGet.mockResolvedValueOnce({
        data: { data: { email: "user@test.com", plan: "pro" } },
      });

      const store = useAuthStore();
      await store.fetchUser();

      expect(mockGet).toHaveBeenCalledWith("/auth/me");
      expect(store.user).toEqual({ email: "user@test.com", plan: "pro" });
    });

    it("无 token 时不请求", async () => {
      const mockGet = vi.mocked(api.get);
      const store = useAuthStore();
      await store.fetchUser();

      expect(mockGet).not.toHaveBeenCalled();
    });

    it("请求失败时 user 为 null", async () => {
      localStorage.setItem("access_token", "bad-token");
      const mockGet = vi.mocked(api.get);
      mockGet.mockRejectedValueOnce(new Error("Unauthorized"));

      const store = useAuthStore();
      await store.fetchUser();

      expect(store.user).toBeNull();
    });
  });

  describe("logout", () => {
    it("清除所有认证状态", () => {
      localStorage.setItem("access_token", "token");
      localStorage.setItem("refresh_token", "refresh");
      localStorage.setItem("user_info", JSON.stringify({ email: "test@test.com" }));

      const store = useAuthStore();
      store.logout();

      expect(localStorage.getItem("access_token")).toBeNull();
      expect(localStorage.getItem("refresh_token")).toBeNull();
      expect(localStorage.getItem("user_info")).toBeNull();
      expect(store.token).toBe("");
      expect(store.user).toBeNull();
      expect(store.isLoggedIn).toBe(false);
    });
  });

  describe("initFromStorage", () => {
    it("从 localStorage 恢复用户信息", () => {
      localStorage.setItem("user_info", JSON.stringify({ email: "cached@test.com", plan: "premium" }));

      const store = useAuthStore();
      store.initFromStorage();

      expect(store.user).toEqual({ email: "cached@test.com", plan: "premium" });
    });

    it("无效 JSON 时不崩溃", () => {
      localStorage.setItem("user_info", "invalid-json{{{");

      const store = useAuthStore();
      store.initFromStorage();

      expect(store.user).toBeNull();
    });
  });

  describe("userPlan", () => {
    it("默认为 free", () => {
      const store = useAuthStore();
      expect(store.userPlan).toBe("free");
    });

    it("返回用户实际 plan", () => {
      localStorage.setItem("user_info", JSON.stringify({ plan: "pro" }));
      const store = useAuthStore();
      store.initFromStorage();
      expect(store.userPlan).toBe("pro");
    });
  });
});
