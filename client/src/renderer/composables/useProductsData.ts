import { ref, computed, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";
import { parseXHSUrl } from "@shared/constants/platforms";
import { useProductStore } from "../stores/product";
import { useCollectStore } from "../stores/collect";
import { useSchedulerStore } from "../stores/scheduler";
import { usePermissionStore } from "../stores/permission";
import api from "../utils/api";
import type { Product } from "@shared/types";

export interface ProductRanking {
  rank: number;
  total: number;
  trend: string;
  lifecycle: string;
}

export interface DiscoveryQuotaState {
  plan?: string;
  daily_limit: number;
  used_today: number;
  remaining: number;
  quota_hint: string;
}

const DISCOVERY_QUOTA_HINT_FALLBACK =
  "「搜索添加」使用云端商品发现库，按账号与当前 IP 合计计次，每日 0 点重置。免费版每日 20 次，Pro 每日 200 次。「粘贴链接」不占用发现库额度。";

export function useProductsData() {
  const productStore = useProductStore();
  const collectStore = useCollectStore();
  const schedulerStore = useSchedulerStore();
  const permissionStore = usePermissionStore();

  const productRankings = ref<Record<string, ProductRanking>>({});
  const rankingsLoading = ref(false);

  const showAdd = ref(false);
  const addTab = ref<"link" | "search">("link");
  const discoveryKeyword = ref("");
  const discoveryResults = ref<Product[]>([]);
  const discoveryLoading = ref(false);
  const discoveryHasSearched = ref(false);
  const discoveryQuota = ref<DiscoveryQuotaState | null>(null);
  const showCollect = ref(false);
  const showSchedule = ref(false);
  const addFormRef = ref<FormInstance>();
  const addForm = ref({ noteInput: "", product_name: "" });
  const concurrency = ref(3);
  const collectScope = ref("all");
  const collectCategory = ref("");
  const scheduleFrequency = ref(60);
  const scheduleProduct = ref<Record<string, unknown> | null>(null);
  const viewMode = ref<"card" | "table" | "waterfall">("card");
  const searchQuery = ref("");
  const categoryFilter = ref<string | null>(null);

  const addRules: FormRules = {
    noteInput: [{ required: true, message: "请输入小红书商品链接或ID", trigger: "blur" }],
  };

  const filteredProducts = computed(() => {
    let result = productStore.products;
    if (categoryFilter.value) {
      result = result.filter((p) => p.category === categoryFilter.value);
    }
    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase();
      result = result.filter(
        (p) =>
          p.product_name?.toLowerCase().includes(q) ||
          p.platform_product_id?.toLowerCase().includes(q) ||
          p.shop_name?.toLowerCase().includes(q)
      );
    }
    return result;
  });

  const categoryList = computed(() => {
    const cats = new Set<string>();
    for (const p of productStore.products) {
      if (p.category) cats.add(p.category);
    }
    return Array.from(cats).sort();
  });

  const uncollectedCount = computed(() => {
    return productStore.products.filter((p) => !p.last_collected_at).length;
  });

  const staleCount = computed(() => {
    const oneDayAgo = Date.now() - 24 * 60 * 60 * 1000;
    return productStore.products.filter((p) => {
      if (!p.last_collected_at) return false;
      return new Date(p.last_collected_at).getTime() < oneDayAgo;
    }).length;
  });

  const failedCount = computed(() => {
    return productStore.products.filter((p) => p.last_collect_status === "failed").length;
  });

  const batchCollectTargets = computed(() => {
    const oneDayAgo = Date.now() - 24 * 60 * 60 * 1000;
    if (collectScope.value === "uncollected") {
      return productStore.products.filter((p) => !p.last_collected_at);
    }
    if (collectScope.value === "stale") {
      return productStore.products.filter((p) => {
        if (!p.last_collected_at) return false;
        return new Date(p.last_collected_at).getTime() < oneDayAgo;
      });
    }
    if (collectScope.value === "failed") {
      return productStore.products.filter((p) => p.last_collect_status === "failed");
    }
    if (collectScope.value === "category" && collectCategory.value) {
      return productStore.products.filter((p) => p.category === collectCategory.value);
    }
    return productStore.products;
  });

  const batchCollectCount = computed(() => batchCollectTargets.value.length);

  const estimatedTime = computed(() => {
    const count = batchCollectCount.value;
    if (count === 0) return "0分钟";
    const avgSeconds = 15;
    const totalSeconds = Math.ceil(count / concurrency.value) * avgSeconds;
    if (totalSeconds < 60) return `${totalSeconds}秒`;
    const minutes = Math.ceil(totalSeconds / 60);
    return `${minutes}分钟`;
  });

  function formatDate(dateStr: string): string {
    const d = new Date(dateStr);
    return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")}`;
  }

  function formatNumber(num: number): string {
    if (num >= 10000) return `${(num / 10000).toFixed(1)}万`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}k`;
    return String(num);
  }

  function resolveProductInput(input: string): { productId: string; targetType: string; targetUrl?: string } {
    const trimmed = input.trim();
    const parsed = parseXHSUrl(trimmed);
    if (parsed.type === "goods" && parsed.id) return { productId: parsed.id, targetType: "goods" };
    if (parsed.type === "note" && parsed.id && parsed.id !== "short_url") return { productId: parsed.id, targetType: "note" };
    if (parsed.type === "note" && parsed.id === "short_url") return { productId: "short_url", targetType: "note", targetUrl: trimmed };
    if (/^[a-f0-9]{8,}$/.test(trimmed)) return { productId: trimmed, targetType: "goods" };
    return { productId: trimmed, targetType: "goods", targetUrl: trimmed };
  }

  async function addProduct() {
    const valid = await addFormRef.value?.validate().catch(() => false);
    if (!valid) return;
    if (!permissionStore.canAddProduct) { ElMessage.warning("当前套餐商品数量已达上限，请升级"); return; }
    const { productId, targetType, targetUrl } = resolveProductInput(addForm.value.noteInput);
    try {
      if (window.electronAPI) {
        await window.electronAPI.invoke("storage:insert-product", {
          platform: "xhs", platform_product_id: productId,
          product_name: addForm.value.product_name || `XHS商品 ${productId}`, target_url: targetUrl,
        });
      } else {
        await api.post("/products", {
          platform: "xhs", platform_product_id: productId,
          product_name: addForm.value.product_name || `XHS商品 ${productId}`, target_url: targetUrl,
        });
      }
      ElMessage.success("添加成功");
      showAdd.value = false;
      addForm.value = { noteInput: "", product_name: "" };
      await productStore.fetchProducts();
      collectSingle({ platform: "xhs", platform_product_id: productId, target_url: targetUrl, targetType });
    } catch { ElMessage.error("添加失败"); }
  }

  function applyDiscoveryQuotaPayload(payload: Record<string, unknown> | undefined) {
    if (!payload) return;
    const q = (payload.quota as Record<string, unknown> | undefined) ?? payload;
    if (q.daily_limit === undefined && q.remaining === undefined) return;
    discoveryQuota.value = {
      plan: String(q.plan ?? discoveryQuota.value?.plan ?? ""),
      daily_limit: Number(q.daily_limit ?? -1),
      used_today: Number(q.used_today ?? 0),
      remaining: Number(q.remaining ?? 0),
      quota_hint: String(
        payload.quota_hint ?? q.quota_hint ?? payload.policy_hint ?? DISCOVERY_QUOTA_HINT_FALLBACK,
      ),
    };
  }

  async function fetchDiscoveryQuota() {
    try {
      const { data } = await api.get("/discovery/quota");
      if (data?.code === 0 && data.data) {
        applyDiscoveryQuotaPayload(data.data);
      }
    } catch {
      if (!discoveryQuota.value) {
        discoveryQuota.value = {
          daily_limit: 20,
          used_today: 0,
          remaining: 20,
          quota_hint: DISCOVERY_QUOTA_HINT_FALLBACK,
        };
      }
    }
  }

  watch(showAdd, (open) => {
    if (open) void fetchDiscoveryQuota();
  });

  watch(addTab, (tab) => {
    if (tab === "search" && showAdd.value) void fetchDiscoveryQuota();
  });

  async function searchDiscovery() {
    if (!discoveryKeyword.value.trim()) return;
    discoveryLoading.value = true;
    discoveryHasSearched.value = true;
    const payload = {
      keyword: discoveryKeyword.value.trim(),
      page: 1,
      page_size: 20,
    };
    try {
      try {
        const { data } = await api.post("/discovery/search", payload);
        if (data.code === 42021) {
          applyDiscoveryQuotaPayload(data.detail as Record<string, unknown> | undefined);
          ElMessage.warning(data.message || "今日「搜索添加」次数已用完，请明日再试或使用「粘贴链接」");
          discoveryResults.value = [];
          return;
        }
        if (data.code === 0) {
          discoveryResults.value = data.data?.items || [];
          applyDiscoveryQuotaPayload(data.data);
          if (discoveryResults.value.length === 0) {
            ElMessage.info("未找到匹配商品，请换关键词或检查云端发现库是否已部署");
          }
          return;
        }
        ElMessage.warning(data.message || "搜索失败");
        return;
      } catch (err: unknown) {
        const ax = err as { response?: { data?: { code?: number; message?: string; detail?: Record<string, unknown> } } };
        if (ax.response?.data?.code === 42021) {
          applyDiscoveryQuotaPayload(ax.response.data.detail);
          ElMessage.warning(ax.response.data.message || "今日「搜索添加」次数已用完");
          discoveryResults.value = [];
          return;
        }
        // 云端 API 不可用时走 Electron IPC 兜底
      }

      if (window.electronAPI?.invoke) {
        const result = await window.electronAPI.invoke("discovery:search", payload) as { code?: number; data?: { items?: unknown[] } };
        discoveryResults.value = (result?.data?.items || []) as typeof discoveryResults.value;
        if (discoveryResults.value.length === 0) {
          ElMessage.info("未找到匹配商品。请确认服务器已配置 DISCOVERY_DB_PATH 并导入发现库。");
        }
      } else {
        discoveryResults.value = [];
        ElMessage.warning("当前环境无法搜索商品发现库");
      }
    } catch (err) {
      discoveryResults.value = [];
      ElMessage.error(`搜索失败: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      discoveryLoading.value = false;
    }
  }

  let discoveryDebounceTimer: ReturnType<typeof setTimeout> | null = null;
  const DISCOVERY_DEBOUNCE_MS = 400;

  function debouncedSearchDiscovery() {
    if (discoveryDebounceTimer) clearTimeout(discoveryDebounceTimer);
    discoveryDebounceTimer = setTimeout(() => {
      searchDiscovery();
    }, DISCOVERY_DEBOUNCE_MS);
  }

  function cancelDebouncedSearchDiscovery() {
    if (discoveryDebounceTimer) {
      clearTimeout(discoveryDebounceTimer);
      discoveryDebounceTimer = null;
    }
  }

  async function addFromDiscovery(item: { ref?: string; title?: string; store_name?: string }) {
    const refId = String(item.ref || "").trim();
    if (!refId) {
      ElMessage.warning("该条目缺少引用ID，无法加入监控，请重新搜索");
      return;
    }
    try {
      try {
        const { data } = await api.post("/discovery/add-to-monitor", {
          ref_id: refId,
          product_name: item.title,
          mode: "goods",
        });
        if (data?.code === 42021) {
          applyDiscoveryQuotaPayload(data.detail as Record<string, unknown> | undefined);
          ElMessage.warning(data.message || "今日「搜索添加」次数已用完");
          return;
        }
        if (data?.code === 0) {
          applyDiscoveryQuotaPayload(data.data);
          ElMessage.success("已加入监控");
          await productStore.fetchProducts();
          return;
        }
        ElMessage.warning(data?.message || "加入监控失败");
        return;
      } catch (err: unknown) {
        const ax = err as { response?: { data?: { code?: number; message?: string; detail?: Record<string, unknown> } } };
        if (ax.response?.data?.code === 42021) {
          applyDiscoveryQuotaPayload(ax.response.data.detail);
          ElMessage.warning(ax.response.data.message || "今日「搜索添加」次数已用完");
          return;
        }
        // network/api 失败时走 IPC 兜底
      }

      if (window.electronAPI?.invoke) {
        const result = await window.electronAPI.invoke("discovery:add-to-monitor", {
          ref_id: refId,
          product_name: item.title,
          mode: "goods",
        }) as { code?: number; message?: string };
        if ((result?.code ?? 1) === 0) {
          ElMessage.success("已加入监控");
          await productStore.fetchProducts();
          return;
        }
        ElMessage.warning(result?.message || "加入监控失败，请稍后重试");
        return;
      }

      ElMessage.error("添加失败：当前环境无法访问发现库服务");
    } catch (err) {
      ElMessage.error(`添加失败: ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  function resetAddDialog() {
    addTab.value = "link";
    discoveryKeyword.value = "";
    discoveryResults.value = [];
    discoveryHasSearched.value = false;
    addForm.value = { noteInput: "", product_name: "" };
  }

  async function collectSingle(product: Record<string, unknown>) {
    const targetType = (product.targetType as string) || "goods";
    await collectStore.startCollect([{
      targetId: product.platform_product_id as string,
      targetType: targetType as "goods" | "note",
      targetUrl: product.target_url as string | undefined,
    }]);
    ElMessage.success("采集任务已提交");
  }

  async function startBatchCollect() {
    await collectStore.setConcurrency(concurrency.value);
    const targets = batchCollectTargets.value.map((p) => ({
      targetId: p.platform_product_id,
      targetType: ((p as Record<string, unknown>).targetType as "goods" | "note") || "goods",
      targetUrl: (p as Record<string, unknown>).target_url as string | undefined,
    }));
    if (targets.length === 0) {
      ElMessage.warning("没有可采集的商品");
      return;
    }
    await collectStore.startCollect(targets);
    showCollect.value = false;
    ElMessage.success(`已提交 ${targets.length} 个采集任务`);
  }

  function addSchedule(product: Record<string, unknown>) {
    scheduleProduct.value = product;
    showSchedule.value = true;
  }

  async function confirmSchedule() {
    if (!scheduleProduct.value) return;
    try {
      await schedulerStore.addTask({
        product_id: scheduleProduct.value.id as string,
        platform: "xhs",
        platform_product_id: scheduleProduct.value.platform_product_id as string,
        product_name: scheduleProduct.value.product_name as string,
        frequency_minutes: scheduleFrequency.value,
        is_active: true,
      });
      ElMessage.success("定时任务已创建");
      showSchedule.value = false;
    } catch { ElMessage.error("创建定时任务失败"); }
  }

  async function confirmDelete(id: string) {
    try {
      await ElMessageBox.confirm("确定要删除该商品监控吗？", "确认删除", {
        confirmButtonText: "删除", cancelButtonText: "取消", type: "warning",
      });
      if (window.electronAPI) {
        await window.electronAPI.invoke("storage:deactivate-product", id);
      } else {
        await api.delete(`/products/${id}`);
      }
      ElMessage.success("删除成功");
      await productStore.fetchProducts();
    } catch (err) { console.warn("[Composable] operation failed:", err); }
  }

  async function fetchRankings() {
    if (productStore.products.length === 0) return;
    rankingsLoading.value = true;
    try {
      const { data } = await api.get("/feature/product-rankings", { params: { limit: 50 } });
      if (data?.rankings) {
        const map: Record<string, ProductRanking> = {};
        for (const r of data.rankings) {
          if (r.product_id) {
            map[r.product_id] = {
              rank: r.overall_rank || r.category_rank || 0,
              total: r.total_in_category || r.category_total || 0,
              trend: r.trend_direction || "",
              lifecycle: r.lifecycle_stage || "",
            };
          }
        }
        productRankings.value = map;
      }
    } catch {
      productRankings.value = {};
    } finally {
      rankingsLoading.value = false;
    }
  }

  function getRankingInfo(productId: string): ProductRanking | null {
    return productRankings.value[productId] || null;
  }

  function trendIcon(trend: string) {
    if (trend === "上升") return "📈";
    if (trend === "下降") return "📉";
    return "➡️";
  }

  function lifecycleTagType(stage: string): "" | "success" | "warning" | "danger" | "info" {
    const map: Record<string, "" | "success" | "warning" | "danger" | "info"> = {
      new: "warning", growth: "success", rising: "success", stable: "info", declining: "danger", decline: "danger", mature: "info",
    };
    return map[stage] || "info";
  }

  function lifecycleLabel(stage: string): string {
    const map: Record<string, string> = { new: "新品期", growth: "成长期", rising: "上升期", stable: "稳定期", declining: "衰退期", decline: "衰退期", mature: "成熟期" };
    return map[stage] || stage;
  }

  function percentileText(productId: string): string {
    const info = getRankingInfo(productId);
    if (!info || info.total === 0) return "-";
    const pct = Math.round(((info.total - info.rank) / info.total) * 100);
    return `${pct}%`;
  }

  function percentileWidth(productId: string): string {
    const info = getRankingInfo(productId);
    if (!info || info.total === 0) return "0%";
    return `${Math.round(((info.total - info.rank) / info.total) * 100)}%`;
  }

  async function quickAIAnalysis(product: Record<string, unknown>, type: string) {
    const gateMap: Record<string, boolean> = {
      trend_score: permissionStore.canAITrend,
      prediction: permissionStore.canAIPrediction,
      risk_warning: permissionStore.canAIRisk,
    };
    if (!gateMap[type]) {
      ElMessage.warning("当前套餐不支持此AI分析，请升级");
      return;
    }
    try {
      const productId = product.id as string;
      await api.post("/ai/analyze", { product_id: productId, analysis_type: type });
      ElMessage.success("AI分析已提交，请稍后在AI决策页查看结果");
    } catch {
      ElMessage.error("AI分析提交失败");
    }
  }

  function init() {
    productStore.fetchProducts();
    collectStore.setupListeners();
    collectStore.fetchStatus();
    permissionStore.fetchPermissions();
    fetchRankings();
  }

  return {
    productStore, collectStore, schedulerStore, permissionStore,
    productRankings, rankingsLoading,
    showAdd, addTab, discoveryKeyword, discoveryResults, discoveryLoading, discoveryHasSearched, discoveryQuota,
    fetchDiscoveryQuota,
    showCollect, showSchedule,
    addFormRef, addForm, addRules,
    concurrency, collectScope, collectCategory, scheduleFrequency, scheduleProduct,
    viewMode, searchQuery, categoryFilter, filteredProducts,
    categoryList, uncollectedCount, staleCount, failedCount, batchCollectTargets, batchCollectCount, estimatedTime,
    formatDate, formatNumber, resolveProductInput,
    addProduct, searchDiscovery, debouncedSearchDiscovery, cancelDebouncedSearchDiscovery, addFromDiscovery, resetAddDialog,
    collectSingle, startBatchCollect,
    addSchedule, confirmSchedule, confirmDelete,
    fetchRankings, getRankingInfo,
    trendIcon, lifecycleTagType, lifecycleLabel,
    percentileText, percentileWidth,
    quickAIAnalysis, init,
  };
}
