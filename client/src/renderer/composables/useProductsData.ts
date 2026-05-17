import { ref, computed } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";
import { parseXHSUrl } from "@shared/constants/platforms";
import { useProductStore } from "../stores/product";
import { useCollectStore } from "../stores/collect";
import { useSchedulerStore } from "../stores/scheduler";
import { usePermissionStore } from "../stores/permission";
import api from "../utils/api";

export interface ProductRanking {
  rank: number;
  total: number;
  trend: string;
  lifecycle: string;
}

export function useProductsData() {
  const productStore = useProductStore();
  const collectStore = useCollectStore();
  const schedulerStore = useSchedulerStore();
  const permissionStore = usePermissionStore();

  const productRankings = ref<Record<string, ProductRanking>>({});
  const rankingsLoading = ref(false);

  const showAdd = ref(false);
  const showCollect = ref(false);
  const showSchedule = ref(false);
  const addFormRef = ref<FormInstance>();
  const addForm = ref({ noteInput: "", product_name: "" });
  const concurrency = ref(3);
  const collectScope = ref("all");
  const scheduleFrequency = ref(60);
  const scheduleProduct = ref<Record<string, unknown> | null>(null);
  const viewMode = ref<"card" | "table">("card");
  const searchQuery = ref("");

  const addRules: FormRules = {
    noteInput: [{ required: true, message: "请输入小红书商品链接或ID", trigger: "blur" }],
  };

  const filteredProducts = computed(() => {
    if (!searchQuery.value) return productStore.products;
    const q = searchQuery.value.toLowerCase();
    return productStore.products.filter(
      (p) =>
        p.product_name?.toLowerCase().includes(q) ||
        p.platform_product_id?.toLowerCase().includes(q) ||
        p.shop_name?.toLowerCase().includes(q)
    );
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
      await window.electronAPI.invoke("storage:insert-product", {
        platform: "xhs", platform_product_id: productId,
        product_name: addForm.value.product_name || `XHS商品 ${productId}`, target_url: targetUrl,
      });
      ElMessage.success("添加成功");
      showAdd.value = false;
      addForm.value = { noteInput: "", product_name: "" };
      await productStore.fetchProducts();
      collectSingle({ platform: "xhs", platform_product_id: productId, target_url: targetUrl, targetType });
    } catch { ElMessage.error("添加失败"); }
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
    const targets = productStore.products.map((p) => ({
      targetId: p.platform_product_id,
      targetType: ((p as Record<string, unknown>).targetType as "goods" | "note") || "goods",
      targetUrl: (p as Record<string, unknown>).target_url as string | undefined,
    }));
    await collectStore.startCollect(targets);
    showCollect.value = false;
    ElMessage.success(`已提交 ${targets.length} 个采集任务`);
  }

  function addSchedule(product: Record<string, unknown>) {
    if (!permissionStore.canAutoRefresh) { ElMessage.warning("定时采集需要Pro及以上版本"); return; }
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
      await window.electronAPI.invoke("storage:run", "UPDATE products SET is_active = 0 WHERE id = ?", [id]);
      ElMessage.success("删除成功");
      await productStore.fetchProducts();
    } catch {}
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
    showAdd, showCollect, showSchedule,
    addFormRef, addForm, addRules,
    concurrency, collectScope, scheduleFrequency, scheduleProduct,
    viewMode, searchQuery, filteredProducts,
    formatDate, formatNumber, resolveProductInput,
    addProduct, collectSingle, startBatchCollect,
    addSchedule, confirmSchedule, confirmDelete,
    fetchRankings, getRankingInfo,
    trendIcon, lifecycleTagType, lifecycleLabel,
    percentileText, percentileWidth,
    quickAIAnalysis, init,
  };
}
