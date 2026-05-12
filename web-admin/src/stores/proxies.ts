import { defineStore } from "pinia";
import { ref } from "vue";
import api from "../utils/api";

interface ProxyProvider {
  id: number;
  // Add other fields as needed
  [key: string]: any;
}

interface ProxyPool {
  id: number;
  // Add other fields as needed
  [key: string]: any;
}

export const useProxiesStore = defineStore("proxies", () => {
  const providers = ref<ProxyProvider[]>([]);
  const pools = ref<ProxyPool[]>([]);
  const loading = ref(false);

  async function fetchProviders() {
    loading.value = true;
    try {
      const { data } = await api.get("/admin/proxies/providers");
      providers.value = data;
    } catch (error) {
      // Error handling silent; views can handle UI feedback
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
      // Error handling silent; views can handle UI feedback
    } finally {
      loading.value = false;
    }
  }

  async function addProvider(data: Record<string, any>) {
    try {
      await api.post("/admin/proxies/providers", data);
      // Optionally refetch providers
      await fetchProviders();
    } catch (error) {
      // Error handling silent; views can handle UI feedback
    }
  }

  async function checkProxy(id: number) {
    try {
      await api.post(`/admin/proxies/pools/${id}/check`);
      // Optionally update the specific pool's status
      const pool = pools.value.find(p => p.id === id);
      if (pool) {
        // Assuming we want to update a status field; adjust as needed
        pool.lastChecked = new Date();
      }
    } catch (error) {
      // Error handling silent; views can handle UI feedback
    }
  });

  return { providers, pools, loading, fetchProviders, fetchPools, addProvider, checkProxy };
});