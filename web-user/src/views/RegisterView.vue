<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-header">
        <router-link to="/" class="auth-logo">
          <span class="logo-icon">◆</span> VueMonitor
        </router-link>
        <h2>创建账户</h2>
        <p>免费注册，开始监控你的商品</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="handleRegister">
        <el-form-item label="昵称" prop="nickname">
          <el-input v-model="form.nickname" placeholder="请输入昵称" size="large" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" size="large" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="至少6位密码" size="large" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input v-model="form.confirmPassword" type="password" placeholder="再次输入密码" size="large" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" :loading="loading" style="width: 100%" native-type="submit">
            注册
          </el-button>
        </el-form-item>
      </el-form>

      <div class="auth-footer">
        已有账户？<router-link to="/login">登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { ElMessage } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";

const router = useRouter();
const auth = useAuthStore();
const formRef = ref<FormInstance>();
const loading = ref(false);

const form = reactive({ nickname: "", email: "", password: "", confirmPassword: "" });

const rules: FormRules = {
  nickname: [{ required: true, message: "请输入昵称", trigger: "blur" }],
  email: [{ required: true, message: "请输入邮箱", trigger: "blur" }, { type: "email", message: "邮箱格式不正确", trigger: "blur" }],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }, { min: 6, message: "密码至少6位", trigger: "blur" }],
  confirmPassword: [
    { required: true, message: "请确认密码", trigger: "blur" },
    {
      validator: (_rule, value, callback) => {
        if (value !== form.password) {
          callback(new Error("两次密码不一致"));
        } else {
          callback();
        }
      },
      trigger: "blur",
    },
  ],
};

async function handleRegister() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;

  loading.value = true;
  try {
    await auth.register(form.email, form.password, form.nickname);
    ElMessage.success("注册成功");
    router.push("/dashboard");
  } catch (e: any) {
    const msg = e?.response?.data?.message || "注册失败，请稍后重试";
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
