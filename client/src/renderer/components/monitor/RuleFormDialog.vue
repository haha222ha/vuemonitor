<template>
  <el-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)" :title="editingRule ? '编辑规则' : '新建规则'" width="600px" @close="handleClose" class="modern-dialog">
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
          <el-radio-button value="price_drop"><el-icon><PriceTag /></el-icon> 价格下跌</el-radio-button>
          <el-radio-button value="sales_surge"><el-icon><TrendCharts /></el-icon> 销量飙升</el-radio-button>
          <el-radio-button value="stock_change"><el-icon><ShoppingCart /></el-icon> 库存变化</el-radio-button>
          <el-radio-button value="rating_drop"><el-icon><Star /></el-icon> 评分下降</el-radio-button>
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
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from "vue";
import { ElMessage } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";
import { PriceTag, TrendCharts, ShoppingCart, Star, InfoFilled } from "@element-plus/icons-vue";
import type { AlertRule } from "../../composables/useAlertData";

const props = defineProps<{
  products: any[];
  editingRule: AlertRule | null;
  template: any | null;
  modelValue: boolean;
  submitRule: (form: any, editing: AlertRule | null) => Promise<void>;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void;
  (e: "close"): void;
}>();

const submitting = ref(false);
const formRef = ref<FormInstance>();

const conditionToggles = reactive({
  price_threshold: true, price_below: false,
  sales_threshold: true, sales_absolute: false,
  stock_out: true, stock_restock: true, stock_drop: false,
  rating_below: true, rating_decrease: false, review_count: false,
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
  if (conditionToggles.price_threshold && c.threshold) parts.push(`价格跌幅超过${c.threshold}%`);
  if (conditionToggles.price_below && c.below_price) parts.push(`价格低于¥${c.below_price}`);
  return parts.length > 0 ? `当${parts.join("或")}时触发通知` : "";
});

function resetForm() {
  ruleForm.rule_name = "";
  ruleForm.product_id = "";
  ruleForm.rule_type = "price_drop";
  ruleForm.conditions = {};
  ruleForm.notify_channels = ["app", "desktop"];
  ruleForm.is_active = true;
  Object.assign(conditionToggles, {
    price_threshold: true, price_below: false, sales_threshold: true, sales_absolute: false,
    stock_out: true, stock_restock: true, stock_drop: false, rating_below: true, rating_decrease: false, review_count: false,
  });
}

watch(() => props.editingRule, (rule) => {
  if (rule) {
    ruleForm.rule_name = rule.rule_name;
    ruleForm.product_id = rule.product_id || "";
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
  } else {
    resetForm();
  }
}, { immediate: true });

watch(() => props.template, (tpl) => {
  if (tpl) {
    ruleForm.rule_name = tpl.name;
    ruleForm.rule_type = tpl.rule_type;
    ruleForm.conditions = { ...tpl.conditions };
    if (tpl.rule_type === "price_drop") {
      conditionToggles.price_threshold = !!tpl.conditions.threshold;
      conditionToggles.price_below = !!tpl.conditions.below_price;
    } else if (tpl.rule_type === "sales_surge") {
      conditionToggles.sales_threshold = !!tpl.conditions.threshold;
    } else if (tpl.rule_type === "stock_change") {
      conditionToggles.stock_out = tpl.conditions.stock_events?.includes("out_of_stock") ?? false;
      conditionToggles.stock_restock = tpl.conditions.stock_events?.includes("restocked") ?? false;
    } else if (tpl.rule_type === "rating_drop") {
      conditionToggles.rating_below = !!tpl.conditions.below_rating;
      conditionToggles.rating_decrease = !!tpl.conditions.rating_decrease;
    }
  }
});

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
    const evts: string[] = [];
    if (conditionToggles.stock_out) evts.push("out_of_stock");
    if (conditionToggles.stock_restock) evts.push("restocked");
    if (evts.length > 0) c.stock_events = evts;
    if (conditionToggles.stock_drop && ruleForm.conditions.stock_drop_percent) c.stock_drop_percent = ruleForm.conditions.stock_drop_percent;
  } else if (t === "rating_drop") {
    if (conditionToggles.rating_below && ruleForm.conditions.below_rating) c.below_rating = ruleForm.conditions.below_rating;
    if (conditionToggles.rating_decrease && ruleForm.conditions.rating_decrease) c.rating_decrease = ruleForm.conditions.rating_decrease;
    if (conditionToggles.review_count && ruleForm.conditions.review_count_above) c.review_count_above = ruleForm.conditions.review_count_above;
  }
  return c;
}

async function handleSubmit() {
  if (!formRef.value) return;
  await formRef.value.validate();
  submitting.value = true;
  try {
    const conditions = buildConditions();
    await props.submitRule({ ...ruleForm, conditions }, props.editingRule);
    emit("update:modelValue", false);
  } catch { ElMessage.error(props.editingRule ? "更新失败" : "创建失败"); }
  finally { submitting.value = false; }
}

function handleClose() {
  resetForm();
  emit("close");
}
</script>

<style scoped>
.condition-builder { width: 100%; display: flex; flex-direction: column; gap: 10px; }
.condition-row { display: flex; align-items: center; gap: 8px; }
.condition-label { font-size: var(--text-xs); color: var(--color-text-secondary); min-width: 70px; }
.condition-unit { font-size: var(--text-xs); color: var(--color-text-tertiary); }
.condition-desc { font-size: var(--text-xs); color: var(--color-text-tertiary); margin-left: 4px; }
.condition-preview { display: flex; align-items: center; gap: 6px; padding: 8px 12px; background: var(--color-warning-bg); border-radius: var(--radius-base); font-size: var(--text-xs); color: var(--color-warning); }
.modern-dialog :deep(.el-dialog__header) { padding: 20px 24px; border-bottom: 1px solid var(--color-border-light); margin-right: 0; }
.modern-dialog :deep(.el-dialog__title) { font-size: var(--text-lg); font-weight: 600; color: var(--color-text-primary); }
.modern-dialog :deep(.el-dialog__body) { padding: 24px; }
.modern-dialog :deep(.el-dialog__footer) { padding: 16px 24px; border-top: 1px solid var(--color-border-light); }
</style>
