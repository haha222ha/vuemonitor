﻿﻿﻿﻿﻿import { ref, reactive } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import api from "../utils/api";
import type { Product, AlertEvent } from "@shared/types";

export interface AlertStats {
  total_rules: number;
  active_rules: number;
  total_events: number;
  unacknowledged_events: number;
}

export interface AlertRule {
  id: string;
  rule_name: string;
  rule_type: string;
  product_id: string | null;
  conditions: Record<string, unknown>;
  notify_channels: string[];
  is_active: boolean;
  trigger_count: number;
  last_triggered_at?: string;
  severity?: string;
  window_minutes?: number;
  cooldown_minutes?: number;
  [key: string]: unknown;
}

export interface AnomalyItem {
  id: string;
  product_id: string;
  product_name: string;
  platform: string;
  metric: string;
  direction: "up" | "down";
  z_score: number;
  latest_value: number;
  mean: number;
  severity: "info" | "warning" | "critical";
  title: string;
  detail: string;
  created_at: string | null;
}

export interface AutoDetectResult {
  total_scanned: number;
  anomaly_count: number;
  metric: string;
  z_threshold: number;
  days: number;
  anomalies: AnomalyItem[];
}

export function useAlertData() {
  const rules = ref<AlertRule[]>([]);
  const products = ref<Product[]>([]);
  const loading = ref(false);
  const cloudAvailable = ref(true);

  const events = ref<AlertEvent[]>([]);
  const eventsLoading = ref(false);
  const eventSeverityFilter = ref("");

  const anomalies = ref<AnomalyItem[]>([]);
  const anomaliesLoading = ref(false);
  const autoDetectResult = ref<AutoDetectResult | null>(null);

  const alertStats = reactive<AlertStats>({
    total_rules: 0,
    active_rules: 0,
    total_events: 0,
    unacknowledged_events: 0,
  });

  function metricToRuleType(metric: string, ruleType?: string): string {
    if (ruleType && ["price_drop", "sales_surge", "stock_change", "rating_drop"].includes(ruleType)) return ruleType;
    const map: Record<string, string> = {
      price: "price_drop", sales_count: "sales_surge", stock: "stock_change",
      rating: "rating_drop", review_count: "rating_drop", favorite_count: "sales_surge",
    };
    return map[metric] || "custom";
  }

  function buildConditionsFromServer(r: Record<string, unknown>): Record<string, unknown> {
    const c: Record<string, unknown> = {};
    const metric = String(r.metric || "");
    const op = String(r.operator || "");
    const threshold = r.threshold;
    if (metric === "price" && op === "decrease_by_percent" && threshold) c.threshold = threshold;
    else if (metric === "price" && op === "less_than" && threshold) c.below_price = threshold;
    else if (metric === "sales_count" && op === "increase_by_percent" && threshold) c.threshold = threshold;
    else if (metric === "sales_count" && op === "increase_by" && threshold) c.absolute_increase = threshold;
    else if (metric === "stock" && op === "equals" && threshold === 0) c.stock_events = ["out_of_stock"];
    else if (metric === "rating" && op === "less_than" && threshold) c.below_rating = threshold;
    else if (metric === "rating" && op === "decrease_by" && threshold) c.rating_decrease = threshold;
    if (r.window_minutes) c.window_hours = Math.round(Number(r.window_minutes) / 60) || 1;
    return c;
  }

  function adaptServerRule(r: Record<string, unknown>): AlertRule {
    const ruleType = metricToRuleType(String(r.metric || ""), String(r.rule_type || ""));
    return {
      id: String(r.id || ""),
      rule_name: String(r.name || ""),
      rule_type: ruleType,
      product_id: (r.filters as Record<string, unknown> | undefined)?.product_id as string || null,
      conditions: buildConditionsFromServer(r),
      notify_channels: ((r.channels as Record<string, unknown> | undefined)?.notify as string[]) || ["app"],
      is_active: !!r.is_active,
      trigger_count: Number(r.trigger_count || 0),
      last_triggered_at: r.last_triggered_at as string | undefined,
      severity: r.severity as string | undefined,
      window_minutes: r.window_minutes as number | undefined,
      cooldown_minutes: r.cooldown_minutes as number | undefined,
    };
  }

  async function fetchRules() {
    loading.value = true;
    try {
      if (window.electronAPI) {
        const productsRes = await window.electronAPI.invoke("storage:get-products") as Product[] | null;
        products.value = productsRes || [];
      } else {
        const { data } = await api.get("/products", { params: { page: 1, page_size: 200 } });
        if (data?.code === 0 && data.data) {
          products.value = data.data.items || data.data || [];
        }
      }
    } catch (err) { console.warn("[Composable] operation failed:", err); }

    try {
      const { data: rulesRes } = await api.get("/alert-rules");
      if (rulesRes?.code === 0 && Array.isArray(rulesRes.data)) {
        rules.value = rulesRes.data.map((r: Record<string, unknown>) => adaptServerRule(r));
        cloudAvailable.value = true;
      } else {
        throw new Error("invalid response");
      }
    } catch {
      cloudAvailable.value = false;
      try {
        if (window.electronAPI) {
          const localRules = await window.electronAPI.invoke("monitor:get-rules") as AlertRule[] | null;
          rules.value = localRules || [];
        }
      } catch {
        rules.value = [];
      }
    } finally {
      loading.value = false;
    }
  }

  async function fetchAlertStats() {
    try {
      const { data } = await api.get("/alert-rules/stats/summary");
      if (data?.code === 0 && data.data) {
        Object.assign(alertStats, data.data);
      }
    } catch {
      alertStats.total_rules = rules.value.length;
      alertStats.active_rules = rules.value.filter((r) => r.is_active).length;
    }
  }

  async function fetchEvents() {
    eventsLoading.value = true;
    try {
      const params: Record<string, any> = { limit: 50 };
      if (eventSeverityFilter.value) params.severity = eventSeverityFilter.value;
      const { data } = await api.get("/alert-rules/events/all", { params });
      if (data?.code === 0 && Array.isArray(data.data)) {
        events.value = data.data;
      }
    } catch {
      events.value = [];
    } finally {
      eventsLoading.value = false;
    }
  }

  async function toggleRule(rule: AlertRule) {
    try {
      if (cloudAvailable.value) {
        await api.put(`/alert-rules/${rule.id}`, { is_active: !rule.is_active });
      } else if (window.electronAPI) {
        await window.electronAPI.invoke("monitor:toggle-rule", rule.id, !rule.is_active);
      }
      rule.is_active = !rule.is_active;
      ElMessage.success(rule.is_active ? "已启用" : "已停用");
    } catch { ElMessage.error("操作失败"); }
  }

  async function deleteRule(id: string) {
    try {
      await ElMessageBox.confirm("确定要删除该规则吗？", "确认删除", { confirmButtonText: "删除", cancelButtonText: "取消", type: "warning" });
      if (cloudAvailable.value) {
        await api.delete(`/alert-rules/${id}`);
      } else if (window.electronAPI) {
        await window.electronAPI.invoke("monitor:delete-rule", id);
      }
      ElMessage.success("删除成功");
      fetchRules();
    } catch (err) { console.warn("[Composable] operation failed:", err); }
  }

  async function acknowledgeEvent(eventId: string) {
    try {
      await api.post(`/alert-rules/events/${eventId}/acknowledge`);
      ElMessage.success("已确认");
      await fetchEvents();
      await fetchAlertStats();
    } catch { ElMessage.error("确认失败"); }
  }

  async function batchAcknowledge(ids: string[]) {
    try {
      await ElMessageBox.confirm(`确认 ${ids.length} 条告警事件？`, "批量确认", { type: "warning" });
      for (const id of ids) {
        await api.post(`/alert-rules/events/${id}/acknowledge`);
      }
      ElMessage.success(`已确认 ${ids.length} 条事件`);
      await fetchEvents();
      await fetchAlertStats();
    } catch (err) { console.warn("[Composable] operation failed:", err); }
  }

  function buildServerPayload(name: string, ruleType: string, conditions: Record<string, any>, channels: string[], isActive: boolean, productId?: string) {
    const metricMap: Record<string, string> = {
      price_drop: "price", sales_surge: "sales_count", stock_change: "stock", rating_drop: "rating",
    };
    const metric = metricMap[ruleType] || "price";
    let operator = "decrease_by_percent";
    let threshold = 10;
    const windowMinutes = (conditions.window_hours || 1) * 60;

    if (ruleType === "price_drop") {
      if (conditions.threshold) { operator = "decrease_by_percent"; threshold = conditions.threshold; }
      else if (conditions.below_price) { operator = "less_than"; threshold = conditions.below_price; }
    } else if (ruleType === "sales_surge") {
      if (conditions.threshold) { operator = "increase_by_percent"; threshold = conditions.threshold; }
      else if (conditions.absolute_increase) { operator = "increase_by"; threshold = conditions.absolute_increase; }
    } else if (ruleType === "stock_change") {
      if (conditions.stock_events?.includes("out_of_stock")) { operator = "equals"; threshold = 0; }
      else if (conditions.stock_drop_percent) { operator = "decrease_by_percent"; threshold = conditions.stock_drop_percent; }
    } else if (ruleType === "rating_drop") {
      if (conditions.below_rating) { operator = "less_than"; threshold = conditions.below_rating; }
      else if (conditions.rating_decrease) { operator = "decrease_by"; threshold = conditions.rating_decrease; }
    }

    const params: Record<string, any> = {
      name, rule_type: ruleType, metric, operator, threshold,
      window_minutes: windowMinutes, cooldown_minutes: 30,
      severity: "warning", is_active: isActive,
    };
    if (channels.length > 0) params.channels = { notify: channels };
    if (productId) params.filters = { product_id: productId };
    return params;
  }

  async function submitRule(form: { rule_name: string; product_id: string; rule_type: string; conditions: Record<string, any>; notify_channels: string[]; is_active: boolean }, editingRule: AlertRule | null) {
    if (cloudAvailable.value) {
      const serverPayload = buildServerPayload(form.rule_name, form.rule_type, form.conditions, form.notify_channels, form.is_active, form.product_id);
      if (editingRule) {
        await api.put(`/alert-rules/${editingRule.id}`, serverPayload);
        ElMessage.success("规则已更新");
      } else {
        await api.post("/alert-rules", serverPayload);
        ElMessage.success("规则已创建");
      }
    } else if (window.electronAPI) {
      if (editingRule) {
        await window.electronAPI.invoke("monitor:update-rule", editingRule.id, { rule_name: form.rule_name, conditions: form.conditions, notify_channels: form.notify_channels, is_active: form.is_active });
        ElMessage.success("规则已更新");
      } else {
        await window.electronAPI.invoke("monitor:create-rule", { product_id: form.product_id, rule_name: form.rule_name, rule_type: form.rule_type, conditions: form.conditions, notify_channels: form.notify_channels, is_active: form.is_active });
        ElMessage.success("规则已创建");
      }
    }
    fetchRules();
  }

  async function runAutoDetect(metric: string = "sales_count", zThreshold: number = 2.0, days: number = 7) {
    anomaliesLoading.value = true;
    try {
      const { data } = await api.post("/alert-rules/auto-detect", null, {
        params: { metric, z_threshold: zThreshold, days },
      });
      if (data?.code === 0 && data.data) {
        anomalies.value = data.data.anomalies || [];
        autoDetectResult.value = data.data;
        if (anomalies.value.length > 0) {
          ElMessage.warning(`检测到 ${anomalies.value.length} 个异常商品`);
        } else {
          ElMessage.success("未检测到异常商品");
        }
      }
    } catch {
      anomalies.value = [];
      autoDetectResult.value = null;
      ElMessage.error("异常检测失败");
    } finally {
      anomaliesLoading.value = false;
    }
  }

  return {
    rules,
    products,
    loading,
    cloudAvailable,
    events,
    eventsLoading,
    eventSeverityFilter,
    alertStats,
    fetchRules,
    fetchAlertStats,
    fetchEvents,
    toggleRule,
    deleteRule,
    acknowledgeEvent,
    batchAcknowledge,
    buildServerPayload,
    submitRule,
    anomalies,
    anomaliesLoading,
    autoDetectResult,
    runAutoDetect,
  };
}
