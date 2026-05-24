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
      <div class="plans-section">
        <h3 class="plans-title">套餐方案</h3>
        <div class="plans-grid">
          <div class="plan-card">
            <div class="plan-name">7天趋势精选</div>
            <div class="plan-duration">7天</div>
            <div class="plan-desc">热门趋势速览</div>
          </div>
          <div class="plan-card plan-card--popular">
            <div class="plan-badge">推荐</div>
            <div class="plan-name">月度会员</div>
            <div class="plan-duration">30天</div>
            <div class="plan-desc">深度情报分析</div>
          </div>
          <div class="plan-card">
            <div class="plan-name">年费会员</div>
            <div class="plan-duration">365天</div>
            <div class="plan-desc">全年无间断追踪</div>
          </div>
        </div>
      </div>
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
.plans-section {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #f0f0f0;
}
.plans-title {
  text-align: center;
  font-size: 14px;
  color: #909399;
  margin-bottom: 12px;
}
.plans-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.plan-card {
  text-align: center;
  padding: 12px 8px;
  border-radius: 8px;
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  position: relative;
}
.plan-card--popular {
  background: #ecf5ff;
  border-color: #409eff;
}
.plan-badge {
  position: absolute;
  top: -8px;
  left: 50%;
  transform: translateX(-50%);
  background: #409eff;
  color: #fff;
  font-size: 10px;
  padding: 1px 8px;
  border-radius: 8px;
}
.plan-name {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}
.plan-duration {
  font-size: 18px;
  font-weight: 700;
  color: #409eff;
}
.plan-desc {
  font-size: 11px;
  color: #909399;
  margin-top: 4px;
}
</style>
