<template>
  <el-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)" title="生成分析报告" width="540px" class="ai-dialog">
    <el-form :model="reportForm" label-width="100px" :rules="reportFormRules" ref="formRef">
      <el-form-item label="报告标题" prop="title">
        <el-input v-model="reportForm.title" placeholder="如：本周商品分析报告" />
      </el-form-item>
      <el-form-item label="报告类型" prop="report_type">
        <el-select v-model="reportForm.report_type" style="width: 100%">
          <el-option label="商品分析" value="product" />
          <el-option label="品类分析" value="category" />
          <el-option label="趋势分析" value="trend" />
          <el-option label="风险分析" value="risk" />
        </el-select>
      </el-form-item>
      <el-form-item label="选择商品" prop="product_ids">
        <el-select v-model="reportForm.product_ids" multiple filterable placeholder="选择商品" style="width: 100%">
          <el-option v-for="p in products" :key="p.id" :label="p.product_name || p.platform_product_id" :value="p.id" />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="generating" @click="handleSubmit">生成报告</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from "vue";
import type { FormInstance, FormRules } from "element-plus";

const props = defineProps<{
  modelValue: boolean;
  reportForm: { title: string; report_type: string; product_ids: string[] };
  products: any[];
  generating: boolean;
  onGenerate: () => Promise<boolean>;
}>();

const emit = defineEmits<{ (e: "update:modelValue", value: boolean): void }>();

const formRef = ref<FormInstance>();

const reportFormRules: FormRules = {
  title: [{ required: true, message: "请输入报告标题", trigger: "blur" }],
  report_type: [{ required: true, message: "请选择报告类型", trigger: "change" }],
  product_ids: [{ required: true, message: "请选择商品", trigger: "change", type: "array", min: 1 }],
};

async function handleSubmit() {
  if (!formRef.value) return;
  await formRef.value.validate();
  const ok = await props.onGenerate();
  if (ok) emit("update:modelValue", false);
}
</script>

<style scoped>
.ai-dialog :deep(.el-dialog__header) { padding: 20px 24px; border-bottom: 1px solid var(--color-border-light); margin-right: 0; }
.ai-dialog :deep(.el-dialog__title) { font-size: var(--text-lg); font-weight: 600; color: var(--color-text-primary); }
.ai-dialog :deep(.el-dialog__body) { padding: 24px; }
</style>
