import { defineStore } from "pinia";
import { ref } from "vue";
import api from "../utils/api";

interface BenchmarkItem {
  id: number;
  category: string;
  platform: string;
  sample_count: number;
  avg_price: number;
  median_price: number;
  avg_sales: number;
  avg_rating: number;
  p25_price: number;
  p75_price: number;
  updated_at: string;
  [key: string]: any;
}

interface DistributionItem {
  label: string;
  count: number;
  percentage: number;
}

interface BenchmarkSummary {
  avgPrice: number;
  avgSales: number;
  avgRating: number;
  sampleCount: number;
}

export const useBenchmarkStore = defineStore("benchmark", () => {
  const benchmarks = ref<BenchmarkItem[]>([]);
  const distribution = ref<DistributionItem[]>([]);
  const summary = ref<BenchmarkSummary>({
    avgPrice: 0,
    avgSales: 0,
    avgRating: 0,
    sampleCount: 0
  });
  const total = ref(0);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function fetchBenchmarks(page: number = 1, pageSize: number = 20, platform?: string, category?: string) {
    loading.value = true;
    error.value = null;
    try {
      const params: Record<string, any> = { page, pageSize };
      if (platform) params.platform = platform;
      if (category) params.category = category;
      const { data } = await api.get("/admin/benchmark", { params });
      benchmarks.value = data.items || data || [];
      total.value = data.total || benchmarks.value.length;
      if (data.summary) {
        summary.value = { ...summary.value, ...data.summary };
      }
    } catch (err: any) {
      error.value = err.message || "Failed to fetch benchmarks";
    } finally {
      loading.value = false;
    }
  }

  async function fetchDistribution(platform: string, category: string, metric: string = "price") {
    loading.value = true;
    error.value = null;
    try {
      const { data } = await api.get("/admin/benchmark/distribution", {
        params: { platform, category, metric }
      });
      distribution.value = data || [];
    } catch (err: any) {
      error.value = err.message || "Failed to fetch distribution";
    } finally {
      loading.value = false;
    }
  }

  async function exportBenchmarks(params: Record<string, unknown> = {}) {
    loading.value = true;
    error.value = null;
    try {
      const response = await api.get("/admin/benchmark/export", {
        params,
        responseType: "blob"
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", "benchmarks.csv");
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      error.value = err.message || "Failed to export benchmarks";
    } finally {
      loading.value = false;
    }
  }

  return {
    benchmarks,
    distribution,
    summary,
    total,
    loading,
    error,
    fetchBenchmarks,
    fetchDistribution,
    exportBenchmarks
  };
});
