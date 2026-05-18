<template>
  <el-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)" title="创建账户" width="420px" class="login__register-dialog">
    <el-form :model="regForm" :rules="regRules" ref="regFormRef" class="login__form">
      <el-form-item prop="nickname">
        <el-input v-model="regForm.nickname" placeholder="昵称（必填）" size="large" />
      </el-form-item>
      <el-form-item prop="email">
        <el-input v-model="regForm.email" placeholder="邮箱（选填）" size="large" />
      </el-form-item>
      <el-form-item prop="password">
        <el-input v-model="regForm.password" placeholder="密码（至少8位，含大小写和数字）" type="password" show-password size="large" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="regLoading" @click="$emit('register')">注册</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import type { FormRules } from "element-plus";

defineProps<{
  modelValue: boolean;
  regForm: { email: string; nickname: string; password: string };
  regRules: FormRules;
  regFormRef: any;
  regLoading: boolean;
}>();

defineEmits<{
  (e: "update:modelValue", value: boolean): void;
  (e: "register"): void;
}>();
</script>

<style scoped>
.login__register-dialog :deep(.el-dialog__header) { padding: 20px 24px; border-bottom: 1px solid var(--color-border-light); margin-right: 0; }
.login__register-dialog :deep(.el-dialog__title) { font-size: var(--text-lg); font-weight: 600; }
.login__register-dialog :deep(.el-dialog__body) { padding: 24px; }

[data-theme="dark"] .login__register-dialog :deep(.el-dialog) { background: var(--color-bg-card) !important; border: 1px solid var(--color-border) !important; }
[data-theme="dark"] .login__register-dialog :deep(.el-dialog__header) { border-bottom-color: var(--color-border) !important; }
[data-theme="dark"] .login__register-dialog :deep(.el-dialog__footer) { border-top-color: var(--color-border) !important; }
[data-theme="dark"] .login__register-dialog :deep(.el-button--primary) { background: linear-gradient(135deg, #6366F1, #8B5CF6) !important; border: none !important; box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4) !important; }
[data-theme="dark"] .login__register-dialog :deep(.el-button--primary:hover) { background: linear-gradient(135deg, #818CF8, #A78BFA) !important; }
</style>
