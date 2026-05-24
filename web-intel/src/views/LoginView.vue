<template>
  <div class="login-page">
    <div class="login-card">
      <h2 class="login-title">AI Intelligence OS</h2>
      <p class="login-subtitle">输入授权码即可登录，无需注册</p>
      <el-alert v-if="kickReason" :title="kickReason" type="warning" :closable="true" show-icon class="kick-alert" />
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent="handleLogin">
        <el-form-item label="授权码" prop="code">
          <el-input
            v-model="form.code"
            placeholder="请输入授权码"
            size="large"
            maxlength="64"
            @keyup.enter="handleLogin"
          >
            <template #prefix>
              <el-icon><Key /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" :loading="auth.loading" class="login-btn" @click="handleLogin">
            授权登录
          </el-button>
        </el-form-item>
        <div class="login-hint">
          <el-icon><InfoFilled /></el-icon>
          <span>授权码即账号，登录后信息保存在本地，无需重复输入</span>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed } from "vue"
import { useRouter, useRoute } from "vue-router"
import { ElMessage } from "element-plus"
import type { FormInstance, FormRules } from "element-plus"
import { Key, InfoFilled } from "@element-plus/icons-vue"
import { useIntelAuthStore } from "@/stores/auth"

const router = useRouter()
const route = useRoute()
const auth = useIntelAuthStore()
const formRef = ref<FormInstance>()

const kickReason = computed(() => (route.query.reason as string) || "")

const form = reactive({ code: "" })
const rules: FormRules = {
  code: [{ required: true, message: "请输入授权码", trigger: "blur" }],
}

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  const success = await auth.codeLogin(form.code)
  if (success) {
    ElMessage.success("登录成功")
    const redirect = (route.query.redirect as string) || "/dashboard"
    router.push(redirect)
  } else {
    ElMessage.error(auth.error || "授权码无效")
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
  width: 420px;
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
.kick-alert {
  margin-bottom: 16px;
}
.login-btn {
  width: 100%;
}
.login-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #c0c4cc;
  text-align: center;
  justify-content: center;
}
</style>
