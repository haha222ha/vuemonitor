<template>
  <div>
    <div style="display:flex;justify-content:space-between;margin-bottom:16px">
      <h2>授权码管理</h2>
      <el-button type="primary" @click="showCreate = true">生成授权码</el-button>
    </div>
    <el-table :data="store.licenses" stripe v-loading="store.loading">
      <el-table-column prop="code" label="授权码" />
      <el-table-column prop="plan" label="套餐" width="100" />
      <el-table-column prop="duration_days" label="天数" width="80" />
      <el-table-column prop="status" label="状态" width="80">
        <template #default="{ row }"><el-tag :type="row.status === 'unused' ? 'success' : row.status === 'active' ? 'primary' : 'info'">{{ row.status }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180" />
    </el-table>

    <el-dialog v-model="showCreate" title="生成授权码" width="400px">
      <el-form :model="form" :rules="formRules" ref="formRef" label-width="80px">
        <el-form-item label="套餐" prop="plan"><el-select v-model="form.plan"><el-option label="体验版" value="free" /><el-option label="Pro" value="pro" /><el-option label="Premium" value="premium" /><el-option label="Enterprise" value="enterprise" /></el-select></el-form-item>
        <el-form-item label="天数" prop="duration_days"><el-input-number v-model="form.duration_days" :min="1" /></el-form-item>
        <el-form-item label="数量" prop="count"><el-input-number v-model="form.count" :min="1" :max="100" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="showCreate = false">取消</el-button><el-button type="primary" @click="generate">生成</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";
import { useLicensesStore } from "../stores/licenses";

const store = useLicensesStore();

const showCreate = ref(false);
const formRef = ref<FormInstance>();
const form = reactive({ plan: "pro", duration_days: 30, count: 1 });

const formRules: FormRules = {
  plan: [{ required: true, message: "请选择套餐", trigger: "change" }],
  duration_days: [{ required: true, message: "请输入天数", trigger: "blur" }],
  count: [{ required: true, message: "请输入数量", trigger: "blur" }],
};

async function fetchLicenses() {
  try {
    await store.fetchLicenses();
  } catch {
    ElMessage.error("获取授权码列表失败");
  }
}

async function generate() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;

  try {
    await store.generateLicense({ plan: form.plan, duration_days: form.duration_days, count: form.count });
    ElMessage.success("生成成功");
    showCreate.value = false;
    fetchLicenses();
  } catch {
    ElMessage.error("生成失败");
  }
}

onMounted(fetchLicenses);
</script>
