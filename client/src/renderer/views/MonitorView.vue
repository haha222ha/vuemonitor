<template>
  <div class="monitor fade-in">
    <PageHeader title="异动规则" subtitle="设置商品异动监控，价格/销量/评分变化自动预警">
      <el-tag v-if="!cloudAvailable" type="warning" effect="dark" size="small" style="margin-right: 8px">离线模式</el-tag>
      <el-button @click="showTemplateDialog = true">从模板创建</el-button>
      <el-button type="primary" @click="openCreateDialog">新建规则</el-button>
    </PageHeader>

    <div v-if="rules.length === 0 && !loading" class="monitor__empty">
      <EmptyState :icon="Bell" title="暂无异动规则" description="创建异动规则，当商品价格、销量、评分等发生变化时自动预警" />
    </div>

    <div v-else class="monitor__grid">
      <div v-for="rule in rules" :key="rule.id" class="rule-card">
        <div class="rule-card__header">
          <div class="rule-card__icon" :style="{ background: typeBg(rule.rule_type) }">
            <el-icon :size="18" :color="typeColor(rule.rule_type)">
              <component :is="typeIcon(rule.rule_type)" />
            </el-icon>
          </div>
          <div class="rule-card__info">
            <div class="rule-card__name">{{ rule.rule_name }}</div>
            <el-tag size="small" :type="typeTagType(rule.rule_type)">{{ typeLabel(rule.rule_type) }}</el-tag>
            <el-tag v-if="rule.severity && rule.severity !== 'warning'" size="small" :type="severityTagType(rule.severity)" effect="dark">{{ severityLabel(rule.severity) }}</el-tag>
          </div>
          <el-switch :model-value="rule.is_active" size="small" @change="toggleRule(rule)" />
        </div>

        <div class="rule-card__conditions">
          <span
            v-for="(cond, idx) in parseConditions(rule.conditions)"
            :key="idx"
            class="condition-chip"
            :style="{ background: cond.bg, color: cond.color }"
          >
            {{ cond.text }}
          </span>
        </div>

        <div class="rule-card__footer">
          <div class="rule-card__meta">
            <el-badge :value="rule.trigger_count" :type="rule.trigger_count > 0 ? 'danger' : 'info'" :hidden="rule.trigger_count === 0" />
            <span class="rule-card__time" v-if="rule.last_triggered_at">
              最近触发: {{ formatTime(rule.last_triggered_at) }}
            </span>
          </div>
          <div class="rule-card__actions">
            <el-button size="small" text type="primary" @click="openEditDialog(rule)">编辑</el-button>
            <el-button size="small" text type="danger" @click="confirmDeleteRule(rule.id)">删除</el-button>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="showCreateDialog" :title="editingRule ? '编辑规则' : '新建规则'" width="600px" @close="resetForm" class="modern-dialog">
      <el-form :model="ruleForm" label-width="100px" :rules="formRules" ref="formRef">
        <el-form-item label="规则名称" prop="rule_name">
          <el-input v-model="ruleForm.rule_name" placeholder="如：价格跌破50元" />
        </el-form-item>
        <el-form-item label="监控商品" prop="product_id">
          <el-select v-model="ruleForm.product_id" placeholder="选择商品" filterable style="width: 100%" :disabled="!!editingRule">
            <el-option v-for="p in products" :key="p.id" :label="p.product_name || p.platform_product_id" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="规则类型" prop="rule_type">
          <el-radio-group v-model="ruleForm.rule_type" :disabled="!!editingRule">
            <el-radio-button value="price_drop">
              <el-icon><PriceTag /></el-icon> 价格下跌
            </el-radio-button>
            <el-radio-button value="sales_surge">
              <el-icon><TrendCharts /></el-icon> 销量飙升
            </el-radio-button>
            <el-radio-button value="stock_change">
              <el-icon><ShoppingCart /></el-icon> 库存变化
            </el-radio-button>
            <el-radio-button value="rating_drop">
              <el-icon><Star /></el-icon> 评分下降
            </el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="触发条件">
          <div class="condition-builder">
            <template v-if="ruleForm.rule_type === 'price_drop'">
              <div class="condition-row">
                <el-checkbox v-model="conditionToggles.price_threshold">价格跌幅超过</el-checkbox>
                <el-input-number v-model="ruleForm.conditions.threshold" :min="1" :max="99" :step="5" :disabled="!conditionToggles.price_threshold" size="small" />
                <span class="condition-unit">%</span>
              </div>
              <div class="condition-row">
                <el-checkbox v-model="conditionToggles.price_below">或价格低于</el-checkbox>
                <el-input-number v-model="ruleForm.conditions.below_price" :min="0" :precision="2" :disabled="!conditionToggles.price_below" size="small" />
                <span class="condition-unit">元</span>
              </div>
              <div class="condition-preview" v-if="pricePreview">
                <el-icon color="#E6A23C"><InfoFilled /></el-icon>
                <span>{{ pricePreview }}</span>
              </div>
            </template>

            <template v-else-if="ruleForm.rule_type === 'sales_surge'">
              <div class="condition-row">
                <el-checkbox v-model="conditionToggles.sales_threshold">销量增幅超过</el-checkbox>
                <el-input-number v-model="ruleForm.conditions.threshold" :min="10" :max="10000" :step="10" :disabled="!conditionToggles.sales_threshold" size="small" />
                <span class="condition-unit">%</span>
              </div>
              <div class="condition-row">
                <span class="condition-label">时间窗口</span>
                <el-select v-model="ruleForm.conditions.window_hours" style="width: 120px" size="small">
                  <el-option :value="1" label="1小时" />
                  <el-option :value="6" label="6小时" />
                  <el-option :value="24" label="24小时" />
                  <el-option :value="72" label="3天" />
                </el-select>
              </div>
              <div class="condition-row">
                <el-checkbox v-model="conditionToggles.sales_absolute">或绝对增量超过</el-checkbox>
                <el-input-number v-model="ruleForm.conditions.absolute_increase" :min="1" :disabled="!conditionToggles.sales_absolute" size="small" />
                <span class="condition-unit">件</span>
              </div>
            </template>

            <template v-else-if="ruleForm.rule_type === 'stock_change'">
              <div class="condition-row">
                <el-checkbox v-model="conditionToggles.stock_out">缺货检测</el-checkbox>
                <span class="condition-desc">商品从有货变为无货时触发</span>
              </div>
              <div class="condition-row">
                <el-checkbox v-model="conditionToggles.stock_restock">补货检测</el-checkbox>
                <span class="condition-desc">商品从无货变为有货时触发</span>
              </div>
              <div class="condition-row">
                <el-checkbox v-model="conditionToggles.stock_drop">库存减少超过</el-checkbox>
                <el-input-number v-model="ruleForm.conditions.stock_drop_percent" :min="10" :max="100" :step="10" :disabled="!conditionToggles.stock_drop" size="small" />
                <span class="condition-unit">%</span>
              </div>
            </template>

            <template v-else-if="ruleForm.rule_type === 'rating_drop'">
              <div class="condition-row">
                <el-checkbox v-model="conditionToggles.rating_below">评分低于</el-checkbox>
                <el-input-number v-model="ruleForm.conditions.below_rating" :min="1" :max="5" :step="0.1" :precision="1" :disabled="!conditionToggles.rating_below" size="small" />
                <span class="condition-unit">分</span>
              </div>
              <div class="condition-row">
                <el-checkbox v-model="conditionToggles.rating_decrease">评分下降超过</el-checkbox>
                <el-input-number v-model="ruleForm.conditions.rating_decrease" :min="0.1" :max="2" :step="0.1" :precision="1" :disabled="!conditionToggles.rating_decrease" size="small" />
                <span class="condition-unit">分</span>
              </div>
              <div class="condition-row">
                <el-checkbox v-model="conditionToggles.review_count">评论数超过</el-checkbox>
                <el-input-number v-model="ruleForm.conditions.review_count_above" :min="0" :disabled="!conditionToggles.review_count" size="small" />
                <span class="condition-unit">条</span>
              </div>
            </template>
          </div>
        </el-form-item>

        <el-form-item label="通知方式">
          <el-checkbox-group v-model="ruleForm.notify_channels">
            <el-checkbox value="app">应用内通知</el-checkbox>
            <el-checkbox value="desktop">桌面通知</el-checkbox>
            <el-checkbox value="email">邮件通知</el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-form-item label="启用">
          <el-switch v-model="ruleForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmitRule">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showTemplateDialog" title="从模板创建规则" width="520px" class="modern-dialog">
      <div class="template-grid">
        <div
          v-for="tpl in ruleTemplates"
          :key="tpl.id"
          class="template-card"
          @click="applyTemplate(tpl)"
        >
          <div class="template-icon" :style="{ background: tpl.bg }">
            <el-icon :size="24" :color="tpl.color"><component :is="tpl.icon" /></el-icon>
          </div>
          <div class="template-info">
            <div class="template-name">{{ tpl.name }}</div>
            <div class="template-desc">{{ tpl.description }}</div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";
import PageHeader from "../components/PageHeader.vue";
import EmptyState from "../components/EmptyState.vue";
import {
  PriceTag,
  TrendCharts,
  ShoppingCart,
  Star,
  Setting,
  InfoFilled,
  Warning,
  Bell,
} from "@element-plus/icons-vue";
import api from "../utils/api";

const rules = ref<any[]>([]);
const products = ref<any[]>([]);
const loading = ref(false);
const submitting = ref(false);
const showCreateDialog = ref(false);
const showTemplateDialog = ref(false);
const editingRule = ref<any>(null);
const formRef = ref<FormInstance>();
const cloudAvailable = ref(true);

const conditionToggles = reactive({
  price_threshold: true,
  price_below: false,
  sales_threshold: true,
  sales_absolute: false,
  stock_out: true,
  stock_restock: true,
  stock_drop: false,
  rating_below: true,
  rating_decrease: false,
  review_count: false,
});

const ruleForm = reactive({
  rule_name: "",
  product_id: "",
  rule_type: "price_drop",
  conditions: {} as Record<string, any>,
  notify_channels: ["app", "desktop"] as string[],
  is_active: true,
});

const formRules: FormRules = {
  rule_name: [{ required: true, message: "请输入规则名称", trigger: "blur" }],
  product_id: [{ required: true, message: "请选择商品", trigger: "change" }],
  rule_type: [{ required: true, message: "请选择规则类型", trigger: "change" }],
};

const pricePreview = computed(() => {
  const c = ruleForm.conditions;
  const parts: string[] = [];
  if (conditionToggles.price_threshold && c.threshold) {
    parts.push(`价格跌幅超过${c.threshold}%`);
  }
  if (conditionToggles.price_below && c.below_price) {
    parts.push(`价格低于¥${c.below_price}`);
  }
  return parts.length > 0 ? `当${parts.join("或")}时触发通知` : "";
});

const TYPE_CONFIG: Record<string, { label: string; icon: typeof PriceTag; color: string; tagType: string; bg: string }> = {
  price_drop: { label: "价格下跌", icon: PriceTag, color: "#F56C6C", tagType: "danger", bg: "#FEF0F0" },
  sales_surge: { label: "销量飙升", icon: TrendCharts, color: "#67C23A", tagType: "success", bg: "#F0F9EB" },
  stock_change: { label: "库存变化", icon: ShoppingCart, color: "#E6A23C", tagType: "warning", bg: "#FDF6EC" },
  rating_drop: { label: "评分下降", icon: Star, color: "#F56C6C", tagType: "danger", bg: "#FEF0F0" },
  custom: { label: "自定义", icon: Setting, color: "#909399", tagType: "info", bg: "#F4F4F5" },
};

function typeIcon(type: string) { return TYPE_CONFIG[type]?.icon || Setting; }
function typeColor(type: string) { return TYPE_CONFIG[type]?.color || "#909399"; }
function typeBg(type: string) { return TYPE_CONFIG[type]?.bg || "#F5F7FA"; }
function typeLabel(type: string) { return TYPE_CONFIG[type]?.label || type; }
function typeTagType(type: string) { return TYPE_CONFIG[type]?.tagType || "info"; }

function severityTagType(severity: string): string {
  const map: Record<string, string> = { critical: "danger", high: "danger", warning: "warning", info: "info", low: "info" };
  return map[severity] || "info";
}

function severityLabel(severity: string): string {
  const map: Record<string, string> = { critical: "紧急", high: "高", warning: "中", info: "低", low: "低" };
  return map[severity] || severity;
}

const ruleTemplates = [
  { id: "price_alert_20", name: "价格下跌20%预警", description: "当商品价格跌幅超过20%时立即通知", rule_type: "price_drop", icon: PriceTag, color: "#F56C6C", bg: "#FEF0F0", conditions: { threshold: 20 } },
  { id: "price_below_50", name: "价格低于50元", description: "当商品价格跌破50元时通知", rule_type: "price_drop", icon: PriceTag, color: "#F56C6C", bg: "#FEF0F0", conditions: { threshold: 0, below_price: 50 } },
  { id: "sales_2x", name: "销量翻倍监控", description: "24小时内销量增长超过100%", rule_type: "sales_surge", icon: TrendCharts, color: "#67C23A", bg: "#F0F9EB", conditions: { threshold: 100, window_hours: 24 } },
  { id: "sales_surge_50", name: "销量激增50%", description: "6小时内销量增长超过50%", rule_type: "sales_surge", icon: TrendCharts, color: "#67C23A", bg: "#F0F9EB", conditions: { threshold: 50, window_hours: 6 } },
  { id: "stock_out", name: "缺货提醒", description: "商品变为缺货状态时通知", rule_type: "stock_change", icon: ShoppingCart, color: "#E6A23C", bg: "#FDF6EC", conditions: { stock_events: ["out_of_stock"] } },
  { id: "rating_below_4", name: "评分低于4.0", description: "商品评分降至4.0以下时预警", rule_type: "rating_drop", icon: Star, color: "#F56C6C", bg: "#FEF0F0", conditions: { below_rating: 4.0 } },
  { id: "rating_drop_05", name: "评分骤降0.5", description: "评分单次下降超过0.5分时通知", rule_type: "rating_drop", icon: Warning, color: "#E6A23C", bg: "#FDF6EC", conditions: { rating_decrease: 0.5 } },
  { id: "comprehensive", name: "综合监控", description: "价格跌10%+销量增50%+缺货+评分降", rule_type: "price_drop", icon: Bell, color: "#409EFF", bg: "#ECF5FF", conditions: { threshold: 10 } },
];

function parseConditions(conditions: Record<string, any>): Array<{ text: string; bg: string; color: string }> {
  if (!conditions) return [{ text: "-", bg: "#F5F7FA", color: "#909399" }];
  const chips: Array<{ text: string; bg: string; color: string }> = [];
  if (conditions.threshold) chips.push({ text: `阈值 ${conditions.threshold}%`, bg: "#FEF0F0", color: "#F56C6C" });
  if (conditions.below_price) chips.push({ text: `低于¥${conditions.below_price}`, bg: "#FEF0F0", color: "#F56C6C" });
  if (conditions.absolute_increase) chips.push({ text: `增量>${conditions.absolute_increase}件`, bg: "#F0F9EB", color: "#67C23A" });
  if (conditions.window_hours) chips.push({ text: `${conditions.window_hours}h窗口`, bg: "#ECF5FF", color: "#409EFF" });
  if (conditions.stock_events?.length) {
    const labels: Record<string, string> = { out_of_stock: "缺货", restocked: "补货" };
    for (const e of conditions.stock_events) chips.push({ text: labels[e] || e, bg: "#FDF6EC", color: "#E6A23C" });
  }
  if (conditions.stock_drop_percent) chips.push({ text: `库存降${conditions.stock_drop_percent}%`, bg: "#FDF6EC", color: "#E6A23C" });
  if (conditions.below_rating) chips.push({ text: `评分<${conditions.below_rating}`, bg: "#FEF0F0", color: "#F56C6C" });
  if (conditions.rating_decrease) chips.push({ text: `评分降${conditions.rating_decrease}`, bg: "#FDF6EC", color: "#E6A23C" });
  if (conditions.review_count_above) chips.push({ text: `评论>${conditions.review_count_above}`, bg: "#ECF5FF", color: "#409EFF" });
  return chips.length > 0 ? chips : [{ text: JSON.stringify(conditions), bg: "#F5F7FA", color: "#909399" }];
}

function formatTime(dateStr: string): string {
  const d = new Date(dateStr);
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function resetForm() {
  editingRule.value = null;
  ruleForm.rule_name = "";
  ruleForm.product_id = "";
  ruleForm.rule_type = "price_drop";
  ruleForm.conditions = {};
  ruleForm.notify_channels = ["app", "desktop"];
  ruleForm.is_active = true;
  Object.assign(conditionToggles, { price_threshold: true, price_below: false, sales_threshold: true, sales_absolute: false, stock_out: true, stock_restock: true, stock_drop: false, rating_below: true, rating_decrease: false, review_count: false });
}

function openCreateDialog() { resetForm(); showCreateDialog.value = true; }

function openEditDialog(rule: any) {
  editingRule.value = rule;
  ruleForm.rule_name = rule.rule_name;
  ruleForm.product_id = rule.product_id;
  ruleForm.rule_type = rule.rule_type;
  ruleForm.conditions = { ...rule.conditions };
  ruleForm.notify_channels = rule.notify_channels || ["app", "desktop"];
  ruleForm.is_active = rule.is_active;
  const c = rule.conditions || {};
  conditionToggles.price_threshold = !!c.threshold;
  conditionToggles.price_below = !!c.below_price;
  conditionToggles.sales_threshold = !!c.threshold;
  conditionToggles.sales_absolute = !!c.absolute_increase;
  conditionToggles.stock_out = c.stock_events?.includes("out_of_stock") ?? false;
  conditionToggles.stock_restock = c.stock_events?.includes("restocked") ?? false;
  conditionToggles.stock_drop = !!c.stock_drop_percent;
  conditionToggles.rating_below = !!c.below_rating;
  conditionToggles.rating_decrease = !!c.rating_decrease;
  conditionToggles.review_count = !!c.review_count_above;
  showCreateDialog.value = true;
}

function applyTemplate(tpl: any) {
  resetForm();
  ruleForm.rule_name = tpl.name;
  ruleForm.rule_type = tpl.rule_type;
  ruleForm.conditions = { ...tpl.conditions };
  if (tpl.rule_type === "price_drop") { conditionToggles.price_threshold = !!tpl.conditions.threshold; conditionToggles.price_below = !!tpl.conditions.below_price; }
  else if (tpl.rule_type === "sales_surge") { conditionToggles.sales_threshold = !!tpl.conditions.threshold; }
  else if (tpl.rule_type === "stock_change") { conditionToggles.stock_out = tpl.conditions.stock_events?.includes("out_of_stock") ?? false; conditionToggles.stock_restock = tpl.conditions.stock_events?.includes("restocked") ?? false; }
  else if (tpl.rule_type === "rating_drop") { conditionToggles.rating_below = !!tpl.conditions.below_rating; conditionToggles.rating_decrease = !!tpl.conditions.rating_decrease; }
  showTemplateDialog.value = false;
  showCreateDialog.value = true;
}

async function fetchData() {
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

function adaptServerRule(r: any) {
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

async function toggleRule(rule: any) {
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

async function confirmDeleteRule(id: string) {
  try {
    await ElMessageBox.confirm("确定要删除该规则吗？", "确认删除", { confirmButtonText: "删除", cancelButtonText: "取消", type: "warning" });
    if (cloudAvailable.value) {
      await api.delete(`/alert-rules/${id}`);
    } else {
      await window.electronAPI.invoke("monitor:delete-rule", id);
    }
    ElMessage.success("删除成功");
    fetchData();
  } catch {}
}

function buildConditions(): Record<string, any> {
  const c: Record<string, any> = {};
  const t = ruleForm.rule_type;
  if (t === "price_drop") {
    if (conditionToggles.price_threshold && ruleForm.conditions.threshold) c.threshold = ruleForm.conditions.threshold;
    if (conditionToggles.price_below && ruleForm.conditions.below_price) c.below_price = ruleForm.conditions.below_price;
  } else if (t === "sales_surge") {
    if (conditionToggles.sales_threshold && ruleForm.conditions.threshold) c.threshold = ruleForm.conditions.threshold;
    if (ruleForm.conditions.window_hours) c.window_hours = ruleForm.conditions.window_hours;
    if (conditionToggles.sales_absolute && ruleForm.conditions.absolute_increase) c.absolute_increase = ruleForm.conditions.absolute_increase;
  } else if (t === "stock_change") {
    const events: string[] = [];
    if (conditionToggles.stock_out) events.push("out_of_stock");
    if (conditionToggles.stock_restock) events.push("restocked");
    if (events.length > 0) c.stock_events = events;
    if (conditionToggles.stock_drop && ruleForm.conditions.stock_drop_percent) c.stock_drop_percent = ruleForm.conditions.stock_drop_percent;
  } else if (t === "rating_drop") {
    if (conditionToggles.rating_below && ruleForm.conditions.below_rating) c.below_rating = ruleForm.conditions.below_rating;
    if (conditionToggles.rating_decrease && ruleForm.conditions.rating_decrease) c.rating_decrease = ruleForm.conditions.rating_decrease;
    if (conditionToggles.review_count && ruleForm.conditions.review_count_above) c.review_count_above = ruleForm.conditions.review_count_above;
  }
  return c;
}

async function handleSubmitRule() {
  if (!formRef.value) return;
  await formRef.value.validate();
  submitting.value = true;
  try {
    const conditions = buildConditions();
    if (cloudAvailable.value) {
      const serverPayload = buildServerPayload(ruleForm.rule_name, ruleForm.rule_type, conditions, ruleForm.notify_channels, ruleForm.is_active, ruleForm.product_id);
      if (editingRule.value) {
        await api.put(`/alert-rules/${editingRule.value.id}`, serverPayload);
        ElMessage.success("规则已更新");
      } else {
        await api.post("/alert-rules", serverPayload);
        ElMessage.success("规则已创建");
      }
    } else {
      if (editingRule.value) {
        await window.electronAPI.invoke("monitor:update-rule", editingRule.value.id, { rule_name: ruleForm.rule_name, conditions, notify_channels: ruleForm.notify_channels, is_active: ruleForm.is_active });
        ElMessage.success("规则已更新");
      } else {
        await window.electronAPI.invoke("monitor:create-rule", { product_id: ruleForm.product_id, rule_name: ruleForm.rule_name, rule_type: ruleForm.rule_type, conditions, notify_channels: ruleForm.notify_channels, is_active: ruleForm.is_active });
        ElMessage.success("规则已创建");
      }
    }
    showCreateDialog.value = false;
    fetchData();
  } catch { ElMessage.error(editingRule.value ? "更新失败" : "创建失败"); } finally { submitting.value = false; }
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

onMounted(fetchData);
</script>

<style scoped>
.monitor {
  padding: 0;
}

.monitor__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}

.rule-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: 16px;
  transition: all 0.2s;
}

.rule-card:hover {
  border-color: var(--color-primary);
  box-shadow: 0 2px 12px rgba(79, 70, 229, 0.08);
}

.rule-card__header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.rule-card__icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-base);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.rule-card__info {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.rule-card__name {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rule-card__conditions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-bottom: 12px;
}

.condition-chip {
  display: inline-block;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  line-height: 1.5;
}

.rule-card__footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid var(--color-border-light);
}

.rule-card__meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rule-card__time {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.rule-card__actions {
  display: flex;
  gap: 4px;
}

.condition-builder {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.condition-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.condition-label {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  min-width: 70px;
}

.condition-unit {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.condition-desc {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-left: 4px;
}

.condition-preview {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  background: #FDF6EC;
  border-radius: var(--radius-base);
  font-size: var(--text-xs);
  color: #E6A23C;
}

.template-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.template-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all 0.2s;
}

.template-card:hover {
  border-color: var(--color-primary);
  box-shadow: 0 2px 8px rgba(79, 70, 229, 0.1);
}

.template-icon {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  border-radius: var(--radius-base);
  display: flex;
  align-items: center;
  justify-content: center;
}

.template-info {
  flex: 1;
  min-width: 0;
}

.template-name {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-text-primary);
}

.template-desc {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-top: 2px;
}

.modern-dialog :deep(.el-dialog__header) {
  padding: 20px 24px;
  border-bottom: 1px solid var(--color-border-light);
  margin-right: 0;
}

.modern-dialog :deep(.el-dialog__title) {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-text-primary);
}

.modern-dialog :deep(.el-dialog__body) {
  padding: 24px;
}

.modern-dialog :deep(.el-dialog__footer) {
  padding: 16px 24px;
  border-top: 1px solid var(--color-border-light);
}
</style>
