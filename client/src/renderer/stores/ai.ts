import { defineStore } from "pinia";
import { ref, computed } from "vue";

export interface AIAnalysisRecord {
  id: string;
  product_id: string;
  analysis_type: string;
  result: Record<string, unknown>;
  created_at: string;
}

export const useAIStore = defineStore("ai", () => {
  const analyses = ref<AIAnalysisRecord[]>([]);
  const currentAnalysis = ref<Record<string, unknown> | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  const analysisCount = computed(() => analyses.value.length);
  const isAnalyzing = computed(() => loading.value);

  async function analyzeProduct(productId: string, analysisType: string) {
    loading.value = true;
    error.value = null;
    currentAnalysis.value = null;
    try {
      const result = await window.electronAPI.invoke("sync:ai-analyze", productId, analysisType) as Record<string, unknown> | null;
      if (result) {
        currentAnalysis.value = result;
        return result;
      }
      error.value = "AI分析请求失败";
      return null;
    } catch (err) {
      error.value = String(err);
      return null;
    } finally {
      loading.value = false;
    }
  }

  async function fetchAnalyses(productId?: string) {
    loading.value = true;
    try {
      const sql = productId
        ? "SELECT * FROM ai_analysis WHERE product_id = ? ORDER BY analyzed_at DESC LIMIT 50"
        : "SELECT * FROM ai_analysis ORDER BY analyzed_at DESC LIMIT 100";
      const params = productId ? [productId] : [];
      const rows = await window.electronAPI.invoke("storage:query", sql, params);
      analyses.value = (rows as AIAnalysisRecord[]) || [];
    } catch (err) {
      error.value = String(err);
    } finally {
      loading.value = false;
    }
  }

  return {
    analyses,
    currentAnalysis,
    loading,
    error,
    analysisCount,
    isAnalyzing,
    analyzeProduct,
    fetchAnalyses,
  };
});
