<template>
  <div class="login-page">
    <div class="login-card">
      <h2 class="login-title">AI Intelligence OS</h2>
      <p class="login-subtitle">登录以访问商业情报系统</p>
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="handleLogin">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" size="large" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" size="large" show-password @keyup.enter="handleLogin" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" :loading="auth.loading" class="login-btn" @click="handleLogin">
            登 录
          </el-button>
        </el-form-item>
        <div class="login-links">
          <span>没有账号？</span>
          <a href="https://www.xhs365.cn" target="_blank">前往 XHS365 注册</a>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue"
import { useRouter, useRoute } from "vue-router"
import { ElMessage } from "element-plus"
import type { FormInstance, FormRules } from "element-plus"
import { useIntelAuthStore } from "@/stores/auth"

const router = useRouter()
const route = useRoute()
const auth = useIntelAuthStore()
const formRef = ref<FormInstance>()

const form = reactive({ username: "", password: "" })
const rules: FormRules = {
  username: [{ required: true, message: "请输入用户名", trigger: "blur" }],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }],
}

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  const success = await auth.login(form.username, form.password)
  if (success) {
    ElMessage.success("登录成功")
    const redirect = (route.query.redirect as string) || "/dashboard"
    router.push(redirect)
  } else {
    ElMessage.error(auth.error || "登录失败")
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}
.login-card {
  width: 400px;
  padding: 40px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}
.login-title {
  text-align: center;
  font-size: 24px;
  color: #1a1a2e;
  margin-bottom: 4px;
}
.login-subtitle {
  text-align: center;
  color: #909399;
  font-size: 14px;
  margin-bottom: 32px;
}
.login-btn {
  width: 100%;
}
.login-links {
  text-align: center;
  font-size: 13px;
  color: #909399;
}
.login-links a {
  color: #4fc3f7;
  text-decoration: none;
  margin-left: 4px;
}
</style>