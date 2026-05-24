import { describe, it, expect, vi, beforeEach } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import { useUsersStore } from "../../stores/users";

vi.mock("../../utils/api", () => ({
  default: {
    get: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

import api from "../../utils/api";

describe("useUsersStore", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  describe("初始状态", () => {
    it("users 为空数组", () => {
      const store = useUsersStore();
      expect(store.users).toEqual([]);
    });

    it("total 为 0", () => {
      const store = useUsersStore();
      expect(store.total).toBe(0);
    });

    it("loading 为 false", () => {
      const store = useUsersStore();
      expect(store.loading).toBe(false);
    });
  });

  describe("fetchUsers", () => {
    it("成功获取用户列表", async () => {
      const mockGet = vi.mocked(api.get);
      mockGet.mockResolvedValueOnce({
        data: {
          users: [
            { id: 1, email: "a@test.com", nickname: "A", plan: "free", is_active: true, created_at: "2026-01-01" },
            { id: 2, email: "b@test.com", nickname: "B", plan: "pro", is_active: false, created_at: "2026-02-01" },
          ],
          total: 2,
        },
      });

      const store = useUsersStore();
      await store.fetchUsers(1, 20);

      expect(mockGet).toHaveBeenCalledWith("/admin/users", { params: { page: 1, pageSize: 20 } });
      expect(store.users).toHaveLength(2);
      expect(store.total).toBe(2);
      expect(store.loading).toBe(false);
    });

    it("带关键词搜索", async () => {
      const mockGet = vi.mocked(api.get);
      mockGet.mockResolvedValueOnce({ data: { users: [], total: 0 } });

      const store = useUsersStore();
      await store.fetchUsers(1, 20, "test");

      expect(mockGet).toHaveBeenCalledWith("/admin/users", {
        params: { page: 1, pageSize: 20, keyword: "test" },
      });
    });

    it("请求失败时 loading 恢复为 false", async () => {
      const mockGet = vi.mocked(api.get);
      mockGet.mockRejectedValueOnce(new Error("Network error"));

      const store = useUsersStore();
      await store.fetchUsers(1, 20);

      expect(store.loading).toBe(false);
    });

    it("请求期间 loading 为 true", async () => {
      const mockGet = vi.mocked(api.get);
      let resolvePromise: (value: any) => void;
      mockGet.mockReturnValueOnce(new Promise((resolve) => { resolvePromise = resolve; }));

      const store = useUsersStore();
      const fetchPromise = store.fetchUsers(1, 20);

      expect(store.loading).toBe(true);

      resolvePromise!({ data: { users: [], total: 0 } });
      await fetchPromise;

      expect(store.loading).toBe(false);
    });
  });

  describe("updateUser", () => {
    it("成功更新用户", async () => {
      const mockPut = vi.mocked(api.put);
      mockPut.mockResolvedValueOnce({ data: {} });

      const store = useUsersStore();
      await store.updateUser(1, { plan: "premium" });

      expect(mockPut).toHaveBeenCalledWith("/admin/users/1", { plan: "premium" });
    });

    it("更新失败时抛出异常", async () => {
      const mockPut = vi.mocked(api.put);
      mockPut.mockRejectedValueOnce(new Error("Forbidden"));

      const store = useUsersStore();
      await expect(store.updateUser(1, { plan: "enterprise" })).rejects.toThrow("Forbidden");
    });
  });

  describe("deleteUser", () => {
    it("成功删除用户", async () => {
      const mockDelete = vi.mocked(api.delete);
      mockDelete.mockResolvedValueOnce({ data: {} });

      const store = useUsersStore();
      await store.deleteUser(5);

      expect(mockDelete).toHaveBeenCalledWith("/admin/users/5");
    });

    it("删除失败时抛出异常", async () => {
      const mockDelete = vi.mocked(api.delete);
      mockDelete.mockRejectedValueOnce(new Error("Not Found"));

      const store = useUsersStore();
      await expect(store.deleteUser(999)).rejects.toThrow("Not Found");
    });
  });
});
