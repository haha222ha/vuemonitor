import { defineStore } from "pinia";
import { ref, computed } from "vue";
import api from "../utils/api";

export interface AIAnalysisRecord {
  id: string;
  product_id: string;
  analysis_type: string;
  result: Record<string, unknown>;
  provider?: string;
  model?: string;
  confidence?: number;
  created_at: string;
}

export type AnalysisType = "basic_analysis" | "trend_score" | "prediction" | "risk_warning" | "report" | "product_optimization";

export type AIErrorType = "network" | "permission" | "quota" | "no_data" | "provider" | "unknown";

export interface AIError {
  type: AIErrorType;
  message: string;
  retryable: boolean;
}

const ANALYSIS_TYPE_LABELS: Record<string, string> = {
  basic_analysis: "基础分析",
  trend_score: "趋势评分",
  prediction: "爆品预测",
  risk_warning: "风险预警",
  report: "分析报告",
  product_optimization: "商品优化",
};

const CACHE_TTL_MS = 30 * 60 * 1000;

interface CachedAnalysis {
  result: Record<string, unknown>;
  cachedAt: number;
  productId: string;
  analysisType: string;
}

function getCacheKey(productId: string, analysisType: string): string {
  return `ai_cache:${productId}:${analysisType}`;
}

function classifyError(err: unknown): AIError {
  const msg = err instanceof Error ? err.message : String(err);
  if (msg.includes("permission") || msg.includes("gate") || msg.includes("权限")) {
    return { type: "permission", message: "当前套餐不支持此分析类型，请升级", retryable: false };
  }
  if (msg.includes("quota") || msg.includes("配额") || msg.includes("limit")) {
    return { type: "quota", message: "今日AI分析次数已用完，请明天再试或升级套餐", retryable: false };
  }
  if (msg.includes("network") || msg.includes("ECONNREFUSED") || msg.includes("timeout") || msg.includes("网络")) {
    return { type: "network", message: "网络连接失败，请检查网络后重试", retryable: true };
  }
  if (msg.includes("no data") || msg.includes("无数据") || msg.includes("暂无")) {
    return { type: "no_data", message: "暂无足够数据进行分析，请先采集商品数据", retryable: false };
  }
  if (msg.includes("provider") || msg.includes("AI") || msg.includes("api")) {
    return { type: "provider", message: "AI服务暂时不可用，请稍后重试", retryable: true };
  }
  return { type: "unknown", message: msg || "分析请求失败", retryable: true };
}

export const useAIStore = defineStore("ai", () => {
  const analyses = ref<AIAnalysisRecord[]>([]);
  const currentAnalysis = ref<Record<string, unknown> | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const aiError = ref<AIError | null>(null);
  const analysisCache = ref<Map<string, CachedAnalysis>>(new Map());

  const analysisCount = computed(() => analyses.value.length);
  const isAnalyzing = computed(() => loading.value);
  const hasError = computed(() => error.value !== null);
  const canRetry = computed(() => aiError.value?.retryable === true);

  function getAnalysisTypeLabel(type: string): string {
    return ANALYSIS_TYPE_LABELS[type] || type;
  }

  function getCachedResult(productId: string, analysisType: string): Record<string, unknown> | null {
    const key = getCacheKey(productId, analysisType);
    const cached = analysisCache.value.get(key);
    if (!cached) return null;
    if (Date.now() - cached.cachedAt > CACHE_TTL_MS) {
      analysisCache.value.delete(key);
      return null;
    }
    return cached.result;
  }

  function setCachedResult(productId: string, analysisType: string, result: Record<string, unknown>): void {
    const key = getCacheKey(productId, analysisType);
    analysisCache.value.set(key, { result, cachedAt: Date.now(), productId, analysisType });
  }

  function clearCache(productId?: string): void {
    if (!productId) {
      analysisCache.value.clear();
      return;
    }
    for (const [key] of analysisCache.value) {
      if (key.startsWith(`ai_cache:${productId}:`)) {
        analysisCache.value.delete(key);
      }
    }
  }

  async function analyzeProduct(productId: string, analysisType: string, forceRefresh = false) {
    loading.value = true;
    error.value = null;
    aiError.value = null;

    if (!forceRefresh) {
      const cached = getCachedResult(productId, analysisType);
      if (cached) {
        currentAnalysis.value = cached;
        loading.value = false;
        return cached;
      }
    }

    try {
      if (window.electronAPI) {
        const result = await window.electronAPI.invoke("sync:ai-analyze", productId, analysisType) as Record<string, unknown> | null;
        if (result) {
          currentAnalysis.value = result;
          setCachedResult(productId, analysisType, result);
          return result;
        }
        const fallbackErr: AIError = { type: "provider", message: "AI分析请求失败，请检查网络连接或稍后重试", retryable: true };
        aiError.value = fallbackErr;
        error.value = fallbackErr.message;
        return null;
      } else {
        const { data } = await api.post("/ai/analyze", { product_id: productId, analysis_type: analysisType });
        if (data.code === 0 && data.data) {
          const result = data.data.result || data.data;
          currentAnalysis.value = result;
          setCachedResult(productId, analysisType, result);
          return result;
        }
        aiError.value = { type: "unknown", message: "分析请求失败", retryable: true };
        error.value = "分析请求失败";
        return null;
      }
    } catch (err) {
      const classified = classifyError(err);
      aiError.value = classified;
      error.value = classified.message;
      return null;
    } finally {
      loading.value = false;
    }
  }

  async function fetchAnalyses(productId?: string) {
    loading.value = true;
    error.value = null;
    try {
      if (window.electronAPI) {
        const sql = productId
          ? "SELECT * FROM ai_analysis WHERE product_id = ? ORDER BY analyzed_at DESC LIMIT 50"
          : "SELECT * FROM ai_analysis ORDER BY analyzed_at DESC LIMIT 100";
        const params = productId ? [productId] : [];
        const rows = await window.electronAPI.invoke("storage:query", sql, params);
        analyses.value = (rows as AIAnalysisRecord[]) || [];
      } else {
        const { data } = await api.get("/ai/analyses", { params: { product_id: productId } });
        if (data.code === 0 && data.data) {
          analyses.value = data.data.items || data.data || [];
        }
      }
    } catch (err) {
      error.value = String(err);
    } finally {
      loading.value = false;
    }
  }

  function clearCurrentAnalysis(): void {
    currentAnalysis.value = null;
    error.value = null;
    aiError.value = null;
  }

  return {
    analyses,
    currentAnalysis,
    loading,
    error,
    aiError,
    analysisCount,
    isAnalyzing,
    hasError,
    canRetry,
    getAnalysisTypeLabel,
    getCachedResult,
    clearCache,
    analyzeProduct,
    fetchAnalyses,
    clearCurrentAnalysis,
  };
});
