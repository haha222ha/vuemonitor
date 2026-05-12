<template>
  <div class="auth-page">
    <div class="auth-card">
      <button class="auth-close" @click="goBack" title="关闭">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
      <div class="auth-header">
        <router-link to="/" class="auth-logo">
          <span class="logo-icon">◆</span> XHS365
        </router-link>
        <h2>登录</h2>
        <p>用户名或邮箱登录</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="handleLogin">
        <el-form-item label="用户名 / 邮箱" prop="account">
          <el-input v-model="form.account" placeholder="输入用户名或邮箱" size="large" />
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

const form = reactive({ account: "", password: "" });

const rules: FormRules = {
  account: [{ required: true, message: "请输入用户名或邮箱", trigger: "blur" }],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }],
};

function goBack() {
  router.push("/");
}

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;

  loading.value = true;
  try {
    await auth.login(form.account, form.password);
    ElMessage.success("登录成功");
    const redirect = (route.query.redirect as string) || "/dashboard";
    router.push(redirect);
  } catch (e: any) {
    const msg = e?.response?.data?.message || "登录失败，请检查账号和密码";
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
  position: relative;
}

.auth-close {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
  color: #6a6a7a;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.auth-close:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
  border-color: rgba(255, 255, 255, 0.15);
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