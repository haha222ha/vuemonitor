<template>
  <div class="login">
    <div class="login__brand">
      <div class="login__brand-content">
        <div class="login__logo">
          <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
            <rect width="48" height="48" rx="14" fill="rgba(255,255,255,0.15)"/>
            <path d="M14 17h20M14 24h14M14 31h16" stroke="#fff" stroke-width="3" stroke-linecap="round"/>
          </svg>
          <span class="login__logo-text">XHS365</span>
        </div>
        <h1 class="login__headline">AI 驱动的<br/>选品决策系统</h1>
        <p class="login__tagline">实时监控 · 智能分析 · 趋势预警</p>
        <div class="login__features">
          <div class="login__feature">
            <div class="login__feature-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="9" stroke="#818CF8" stroke-width="2"/><path d="M12 8v4l3 3" stroke="#818CF8" stroke-width="2" stroke-linecap="round"/></svg>
            </div>
            <div>
              <div class="login__feature-title">实时监控</div>
              <div class="login__feature-desc">7×24 小时商品数据追踪</div>
            </div>
          </div>
          <div class="login__feature">
            <div class="login__feature-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M12 2L2 7l10 5 10-5-10-5z" stroke="#818CF8" stroke-width="2" stroke-linejoin="round"/><path d="M2 17l10 5 10-5M2 12l10 5 10-5" stroke="#818CF8" stroke-width="2" stroke-linejoin="round"/></svg>
            </div>
            <div>
              <div class="login__feature-title">AI 智能分析</div>
              <div class="login__feature-desc">DeepSeek 驱动深度洞察</div>
            </div>
          </div>
          <div class="login__feature">
            <div class="login__feature-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" stroke="#818CF8" stroke-width="2" stroke-linejoin="round"/></svg>
            </div>
            <div>
              <div class="login__feature-title">趋势预警</div>
              <div class="login__feature-desc">价格/销量/评分异动即时通知</div>
            </div>
          </div>
        </div>
      </div>
      <div class="login__brand-decoration">
        <div class="login__circle login__circle--1" />
        <div class="login__circle login__circle--2" />
        <div class="login__circle login__circle--3" />
      </div>
    </div>

    <div class="login__form-side">
      <div class="login__form-wrapper">
        <div class="login__form-header">
          <h2 class="login__form-title">欢迎回来</h2>
          <p class="login__form-subtitle">登录您的 XHS365 账户</p>
        </div>

        <el-form :model="form" :rules="loginRules" ref="loginFormRef" @submit.prevent="handleLogin" class="login__form">
          <el-form-item prop="account">
            <el-input v-model="form.account" placeholder="昵称或邮箱" size="large" />
          </el-form-item>
          <el-form-item prop="password">
            <el-input v-model="form.password" placeholder="密码" type="password" show-password size="large" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="loading" @click="handleLogin" size="large" class="login__submit">
              登录
            </el-button>
          </el-form-item>
        </el-form>

        <div class="login__register-link">
          <span>没有账号？</span>
          <el-button type="primary" plain @click="showRegister = true" class="login__register-btn">立即注册</el-button>
        </div>
      </div>
    </div>

    <el-dialog v-model="showRegister" title="创建账户" width="420px" class="login__register-dialog">
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
        <el-button @click="showRegister = false">取消</el-button>
        <el-button type="primary" :loading="regLoading" @click="handleRegister">注册</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { ElMessage } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";

const router = useRouter();
const authStore = useAuthStore();
const loading = ref(false);
const regLoading = ref(false);
const showRegister = ref(false);
const loginFormRef = ref<FormInstance>();
const regFormRef = ref<FormInstance>();

const form = reactive({ account: "", password: "" });
const regForm = reactive({ email: "", nickname: "", password: "" });

const loginRules: FormRules = {
  account: [{ required: true, message: "请输入昵称或邮箱", trigger: "blur" }],
  password: [{ required: true, message: "请输入密码", trigger: "blur" }],
};

const emailPattern = /^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/;

const regRules: FormRules = {
  nickname: [
    { required: true, message: "请输入昵称", trigger: "blur" },
    { min: 2, max: 20, message: "昵称长度2-20个字符", trigger: "blur" },
  ],
  email: [
    {
      validator: (_rule, value, callback) => {
        if (!value || value.trim() === "") {
          callback();
        } else if (!emailPattern.test(value.trim())) {
          callback(new Error("邮箱格式不正确"));
        } else {
          callback();
        }
      },
      trigger: "blur",
    },
  ],
  password: [
    { required: true, message: "请输入密码", trigger: "blur" },
    { min: 8, message: "密码至少8位", trigger: "blur" },
    {
      validator: (_rule, value, callback) => {
        if (value && !/[A-Z]/.test(value)) {
          callback(new Error("密码需包含大写字母"));
        } else if (value && !/[a-z]/.test(value)) {
          callback(new Error("密码需包含小写字母"));
        } else if (value && !/[0-9]/.test(value)) {
          callback(new Error("密码需包含数字"));
        } else {
          callback();
        }
      },
      trigger: "blur",
    },
  ],
};

async function handleLogin() {
  const valid = await loginFormRef.value?.validate().catch(() => false);
  if (!valid) return;

  loading.value = true;
  try {
    await authStore.login(form.account, form.password);
    router.push("/dashboard");
    ElMessage.success("登录成功");
  } catch {
    ElMessage.error("登录失败，请检查账号和密码");
  } finally {
    loading.value = false;
  }
}

async function handleRegister() {
  const valid = await regFormRef.value?.validate().catch(() => false);
  if (!valid) return;

  regLoading.value = true;
  try {
    await authStore.register(regForm.email || undefined, regForm.nickname, regForm.password);
    ElMessage.success("注册成功，请登录");
    showRegister.value = false;
    form.account = regForm.nickname;
    regForm.email = "";
    regForm.nickname = "";
    regForm.password = "";
  } catch (e: any) {
    const msg = e?.response?.data?.message || e?.message || "注册失败，请稍后重试";
    ElMessage.error(msg);
  } finally {
    regLoading.value = false;
  }
}
</script>

<style scoped>
.login {
  height: 100vh;
  display: flex;
  overflow: hidden;
}

.login__brand {
  flex: 1;
  background: var(--gradient-hero);
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 64px;
  position: relative;
  overflow: hidden;
}

.login__brand-content {
  position: relative;
  z-index: 1;
}

.login__logo {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 48px;
}

.login__logo-text {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text-inverse);
  letter-spacing: -0.5px;
}

.login__headline {
  font-size: 40px;
  font-weight: 700;
  color: var(--color-text-inverse);
  line-height: 1.2;
  margin-bottom: 16px;
  letter-spacing: -1px;
}

.login__tagline {
  font-size: var(--text-lg);
  color: rgba(255, 255, 255, 0.7);
  margin-bottom: 48px;
  letter-spacing: 2px;
}

.login__features {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.login__feature {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.login__feature-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.login__feature-title {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--color-text-inverse);
  margin-bottom: 4px;
}

.login__feature-desc {
  font-size: var(--text-sm);
  color: rgba(255, 255, 255, 0.6);
}

.login__brand-decoration {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.login__circle {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.login__circle--1 {
  width: 400px;
  height: 400px;
  right: -100px;
  top: -100px;
}

.login__circle--2 {
  width: 300px;
  height: 300px;
  right: -50px;
  bottom: -80px;
}

.login__circle--3 {
  width: 200px;
  height: 200px;
  left: 20%;
  bottom: 10%;
}

.login__form-side {
  width: 480px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 64px;
  background: var(--color-bg-card);
}

.login__form-wrapper {
  width: 100%;
  max-width: 360px;
}

.login__form-header {
  margin-bottom: 36px;
}

.login__form-title {
  font-size: var(--text-2xl);
  font-weight: 700;
  color: var(--color-text-primary);
  margin-bottom: 8px;
}

.login__form-subtitle {
  font-size: var(--text-base);
  color: var(--color-text-secondary);
}

.login__form :deep(.el-form-item) {
  margin-bottom: 20px;
}

.login__submit {
  width: 100%;
  height: 44px;
  font-size: var(--text-base);
  font-weight: 600;
  border-radius: var(--radius-base);
}

.login__register-link {
  text-align: center;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.login__register-btn {
  font-weight: 600;
}

.login__register-dialog :deep(.el-dialog) {
  border-radius: var(--radius-xl);
}

@media (max-width: 900px) {
  .login {
    flex-direction: column;
  }

  .login__brand {
    padding: 40px 32px;
    min-height: auto;
  }

  .login__headline {
    font-size: 28px;
  }

  .login__features {
    display: none;
  }

  .login__form-side {
    width: 100%;
    padding: 32px;
  }
}
</style>
