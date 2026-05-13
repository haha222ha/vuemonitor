import { defineStore } from "pinia";
import { ref } from "vue";
import api from "../utils/api";

interface ProxyProvider {
  id: number;
  [key: string]: any;
}

interface ProxyPool {
  id: number;
  lastChecked?: string;
  [key: string]: any;
}

interface ProxyItem {
  id: number;
  [key: string]: any;
}

export const useProxiesStore = defineStore("proxies", () => {
  const providers = ref<ProxyProvider[]>([]);
  const pools = ref<ProxyPool[]>([]);
  const proxies = ref<ProxyItem[]>([]);
  const total = ref(0);
  const loading = ref(false);

  async function fetchProviders() {
    loading.value = true;
    try {
      const { data } = await api.get("/admin/proxies/providers");
      providers.value = data;
    } catch (error) {
      console.error("Failed to fetch proxy providers:", error);
    } finally {
      loading.value = false;
    }
  }

  async function fetchPools(providerId?: number) {
    loading.value = true;
    try {
      const params = providerId ? { providerId } : {};
      const { data } = await api.get("/admin/proxies/pools", { params });
      pools.value = data;
    } catch (error) {
      console.error("Failed to fetch proxy pools:", error);
    } finally {
      loading.value = false;
    }
  }

  async function fetchProxies(page: number = 1, pageSize: number = 20) {
    loading.value = true;
    try {
      const { data } = await api.get("/admin/proxies", { params: { page, pageSize } });
      proxies.value = data.items || data;
      total.value = data.total || proxies.value.length;
    } catch (error) {
      console.error("Failed to fetch proxies:", error);
    } finally {
      loading.value = false;
    }
  }

  async function addProvider(payload: Record<string, any>) {
    try {
      await api.post("/admin/proxies/providers", payload);
      await fetchProviders();
    } catch (error) {
      console.error("Failed to add proxy provider:", error);
    }
  }

  async function addProxy(payload: Record<string, any>) {
    try {
      await api.post("/admin/proxies", payload);
      await fetchProxies();
    } catch (error) {
      console.error("Failed to add proxy:", error);
    }
  }

  async function deleteProxy(id: number) {
    try {
      await api.delete(`/admin/proxies/${id}`);
      const index = proxies.value.findIndex(p => p.id === id);
      if (index !== -1) {
        proxies.value.splice(index, 1);
        total.value = Math.max(total.value - 1, 0);
      }
    } catch (error) {
      console.error("Failed to delete proxy:", error);
    }
  }

  async function checkProxy(id: number) {
    try {
      await api.post(`/admin/proxies/pools/${id}/check`);
      const pool = pools.value.find(p => p.id === id);
      if (pool) {
        pool.lastChecked = new Date().toISOString();
      }
    } catch (error) {
      console.error("Failed to check proxy:", error);
    }
  }

  return {
    providers,
    pools,
    proxies,
    total,
    loading,
    fetchProviders,
    fetchPools,
    fetchProxies,
    addProvider,
    addProxy,
    deleteProxy,
    checkProxy
  };
});
