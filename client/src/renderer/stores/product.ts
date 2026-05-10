import { defineStore } from "pinia";
import { ref, computed } from "vue";

export interface Product {
  id: string;
  platform: string;
  platform_product_id: string;
  product_name: string;
  shop_name: string | null;
  category: string | null;
  image_url: string | null;
  product_url: string | null;
  last_collected_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProductFeature {
  id: string;
  product_id: string;
  price: number | null;
  original_price: number | null;
  sales_count: number | null;
  monthly_sales: number | null;
  rating: number | null;
  review_count: number | null;
  favorite_count: number | null;
  stock_status: string | null;
  collected_at: string;
  source: string;
}

export const useProductStore = defineStore("product", () => {
  const products = ref<Product[]>([]);
  const currentProduct = ref<Product | null>(null);
  const features = ref<ProductFeature[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const filter = ref<{ platform?: string; search?: string }>({});

  const productCount = computed(() => products.value.length);
  const activeProducts = computed(() => products.value.filter((p) => p.last_collected_at));

  async function fetchProducts() {
    loading.value = true;
    error.value = null;
    try {
      const result = await window.electronAPI.invoke("datamart:list-products", filter.value.platform, 100);
      products.value = result as Product[];
    } catch (err) {
      error.value = String(err);
    } finally {
      loading.value = false;
    }
  }

  async function fetchProductDetail(productId: string) {
    loading.value = true;
    try {
      const result = await window.electronAPI.invoke("datamart:get-product", productId);
      currentProduct.value = result as Product;
    } catch (err) {
      error.value = String(err);
    } finally {
      loading.value = false;
    }
  }

  async function fetchFeatures(productId: string) {
    try {
      const result = await window.electronAPI.invoke("storage:query", "SELECT * FROM product_features WHERE product_id = ? ORDER BY collected_at DESC LIMIT 30", [productId]);
      features.value = (result as ProductFeature[]).map((f: ProductFeature) => ({
        ...f,
        extra_features: typeof (f as Record<string, unknown>).extra_features === "string"
          ? JSON.parse((f as Record<string, unknown>).extra_features as string)
          : (f as Record<string, unknown>).extra_features,
      }));
    } catch (err) {
      error.value = String(err);
    }
  }

  function setFilter(newFilter: { platform?: string; search?: string }) {
    filter.value = { ...filter.value, ...newFilter };
  }

  return {
    products,
    currentProduct,
    features,
    loading,
    error,
    filter,
    productCount,
    activeProducts,
    fetchProducts,
    fetchProductDetail,
    fetchFeatures,
    setFilter,
  };
});
