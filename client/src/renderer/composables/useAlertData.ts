import { ref, reactive } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import api from "../utils/api";

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
  conditions: Record<string, any>;
  notify_channels: string[];
  is_active: boolean;
  trigger_count: number;
  last_triggered_at?: string;
  severity?: string;
  window_minutes?: number;
  cooldown_minutes?: number;
  [key: string]: any;
}

export function useAlertData() {
  const rules = ref<AlertRule[]>([]);
  const products = ref<any[]>([]);
  const loading = ref(false);
  const cloudAvailable = ref(true);

  const events = ref<any[]>([]);
  const eventsLoading = ref(false);
  const eventSeverityFilter = ref("");

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

  function buildConditionsFromServer(r: any): Record<string, any> {
    const c: Record<string, any> = {};
    const metric = r.metric || "";
    const op = r.operator || "";
    const threshold = r.threshold;
    if (metric === "price" && op === "decrease_by_percent" && threshold) c.threshold = threshold;
    else if (metric === "price" && op === "less_than" && threshold) c.below_price = threshold;
    else if (metric === "sales_count" && op === "increase_by_percent" && threshold) c.threshold = threshold;
    else if (metric === "sales_count" && op === "increase_by" && threshold) c.absolute_increase = threshold;
    else if (metric === "stock" && op === "equals" && threshold === 0) c.stock_events = ["out_of_stock"];
    else if (metric === "rating" && op === "less_than" && threshold) c.below_rating = threshold;
    else if (metric === "rating" && op === "decrease_by" && threshold) c.rating_decrease = threshold;
    if (r.window_minutes) c.window_hours = Math.round(r.window_minutes / 60) || 1;
    return c;
  }

  function adaptServerRule(r: any): AlertRule {
    const ruleType = metricToRuleType(r.metric, r.rule_type);
    return {
      id: r.id,
      rule_name: r.name,
      rule_type: ruleType,
      product_id: r.filters?.product_id || null,
      conditions: buildConditionsFromServer(r),
      notify_channels: r.channels?.notify || ["app"],
      is_active: r.is_active,
      trigger_count: r.trigger_count || 0,
      last_triggered_at: r.last_triggered_at,
      severity: r.severity,
      window_minutes: r.window_minutes,
      cooldown_minutes: r.cooldown_minutes,
    };
  }

  async function fetchRules() {
    loading.value = true;
    try {
      const productsRes = await window.electronAPI.invoke("storage:get-products");
      products.value = productsRes || [];
    } catch {}

    try {
      const { data: rulesRes } = await api.get("/alert-rules");
      if (rulesRes?.code === 0 && Array.isArray(rulesRes.data)) {
        rules.value = rulesRes.data.map((r: any) => adaptServerRule(r));
        cloudAvailable.value = true;
      } else {
        throw new Error("invalid response");
      }
    } catch {
      cloudAvailable.value = false;
      try {
        const localRules = await window.electronAPI.invoke("monitor:get-rules");
        rules.value = localRules || [];
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
      } else {
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
      } else {
        await window.electronAPI.invoke("monitor:delete-rule", id);
      }
      ElMessage.success("删除成功");
      fetchRules();
    } catch {}
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
    } catch {}
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
    } else {
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
  };
}
