import { defineStore } from "pinia";
import { ref, computed } from "vue";
import api from "../utils/api";
import { ElMessage } from "element-plus";
import { PLAN_LIMITS } from "../../../shared/constants/feature-gates";
import { useAuthStore } from "./auth";

export interface Product {
  id: string;
  name: string;
  shop_name: string;
  platform: string;
  category: string;
  price: number;
  original_price?: number;
  sales: number;
  monthly_sales: number;
  rating: number;
  review_count: number;
  favorite_count: number;
  url: string;
  image_url?: string;
  last_collected_at: string;
  trend: "up" | "down" | "stable";
  is_monitoring: boolean;
}

export const useProductsStore = defineStore("products", () => {
  const items = ref<Product[]>([]);
  const current = ref<Product | null>(null);
  const loading = ref<boolean>(false);
  const total = ref<number>(0);

  const monitoringCount = computed(() => items.value.filter(item => item.is_monitoring).length);
  const canAddMore = computed(() => {
    const authStore = useAuthStore();
    const plan = authStore.userPlan;
    return monitoringCount.value < PLAN_LIMITS[plan].maxProducts;
  });

  async function fetchProducts(params?: { page?: number; page_size?: number; keyword?: string; platform?: string; category?: string }) {
    loading.value = true;
    try {
      const { data } = await api.get("/products", { params });
      items.value = data.items || [];
      total.value = data.total || 0;
    } catch (error) {
      ElMessage.error("Failed to fetch products");
    } finally {
      loading.value = false;
    }
  }

  async function fetchProductDetail(id: string) {
    loading.value = true;
    try {
      const { data } = await api.get(`/products/${id}`);
      current.value = data;
    } catch (error) {
      ElMessage.error("Failed to fetch product detail");
    } finally {
      loading.value = false;
    }
  }

  async function addProduct(data: { url: string; platform: string; name?: string }) {
    try {
      await api.post("/products", data);
    } catch (error) {
      ElMessage.error("Failed to add product");
    }
  }

  async function removeProduct(id: string) {
    try {
      await api.delete(`/products/${id}`);
    } catch (error) {
      ElMessage.error("Failed to remove product");
    }
  }

  async function toggleMonitoring(id: string, enabled: boolean) {
    try {
      await api.put(`/products/${id}/monitoring`, { enabled });
    } catch (error) {
      ElMessage.error("Failed to toggle monitoring");
    }
  }

  async function refreshProduct(id: string) {
    try {
      await api.post(`/products/${id}/refresh`);
    } catch (error) {
      ElMessage.error("Failed to refresh product");
    }
  }

  async function exportProducts(format: "csv" | "json") {
    try {
      const response = await api.get(`/products/export?format=${format}`, { responseType: "blob" });
      return response.data;
    } catch (error) {
      ElMessage.error("Failed to export products");
    }
  }

  return { items, current, loading, total, monitoringCount, canAddMore, fetchProducts, fetchProductDetail, addProduct, removeProduct, toggleMonitoring, refreshProduct, exportProducts };
});