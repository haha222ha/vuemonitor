<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-header">
        <router-link to="/" class="auth-logo">
          <span class="logo-icon">◆</span> VueMonitor
        </router-link>
        <h2>登录</h2>
        <p>登录你的账户，继续使用监控服务</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="handleLogin">
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" size="large" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" size="large" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" :loading="loading" style="width: 100%" native-type="submit">
            登录
          </el-button>
        </el-form-item>
      </el-form>

      <div class="auth-footer">
        还没有账户？<router-link to="/register">免费注册</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { ElMessage } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();
const formRef = ref<FormInstance>();
const loading = ref(false);

const form = reactive({ email: "", password: "" });

const rules: FormRules = {
  email: [{ required: true, message: "请输入邮箱", trigger: "blur" }, { type: "email", message: "邮箱格式不正确", trigger: "blur" }],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }],
};

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;

  loading.value = true;
  try {
    await auth.login(form.email, form.password);
    ElMessage.success("登录成功");
    const redirect = (route.query.redirect as string) || "/dashboard";
    router.push(redirect);
  } catch (e: any) {
    const msg = e?.response?.data?.message || "登录失败，请检查邮箱和密码";
    ElMessage.error(msg);
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.auth-page {
  min-height: 100vh;
  background: #0a0a0f;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.auth-card {
  width: 100%;
  max-width: 420px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 16px;
  padding: 40px;
}

.auth-header {
  text-align: center;
  margin-bottom: 32px;
}

.auth-logo {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 20px;
  font-weight: 700;
  color: #fff;
  text-decoration: none;
  margin-bottom: 20px;
}

.logo-icon { color: #6366f1; font-size: 24px; }

.auth-header h2 {
  font-size: 24px;
  font-weight: 700;
  color: #fff;
  margin: 0 0 8px;
}

.auth-header p {
  font-size: 14px;
  color: #6a6a7a;
  margin: 0;
}

.auth-footer {
  text-align: center;
  font-size: 14px;
  color: #6a6a7a;
  margin-top: 20px;
}

.auth-footer a {
  color: #6366f1;
  text-decoration: none;
}

.auth-footer a:hover {
  text-decoration: underline;
}
</style>
