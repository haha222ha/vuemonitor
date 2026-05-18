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
        <div class="login__particles">
          <div v-for="i in 6" :key="i" :class="['login__particle', `login__particle--${i}`]" />
        </div>
        <div class="login__glow login__glow--1" />
        <div class="login__glow login__glow--2" />
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
            <el-button type="primary" :loading="loading" @click="handleLogin" size="large" class="login__submit">登录</el-button>
          </el-form-item>
        </el-form>

        <div class="login__register-link">
          <span>没有账号？</span>
          <a class="login__register-btn" @click="showRegister = true">立即注册</a>
        </div>
      </div>
    </div>

    <RegisterDialog
      v-model="showRegister"
      :reg-form="regForm"
      :reg-rules="regRules"
      :reg-form-ref="regFormRef"
      :reg-loading="regLoading"
      @register="handleRegister"
    />
  </div>
</template>

<script setup lang="ts">
import RegisterDialog from "../components/auth/RegisterDialog.vue";
import { useLoginData } from "../composables/useLoginData";

const {
  loading, regLoading, showRegister,
  loginFormRef, regFormRef,
  form, regForm, loginRules, regRules,
  handleLogin, handleRegister,
} = useLoginData();
</script>

<style scoped>
.login { display: flex; min-height: 100vh; }
.login__brand { flex: 1; background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%); display: flex; align-items: center; justify-content: center; position: relative; overflow: hidden; padding: 48px; }
.login__brand-content { position: relative; z-index: 1; color: #fff; max-width: 420px; }
.login__logo { display: flex; align-items: center; gap: 12px; margin-bottom: 32px; }
.login__logo-text { font-size: 24px; font-weight: 700; letter-spacing: 1px; }
.login__headline { font-size: 32px; font-weight: 700; line-height: 1.3; margin: 0 0 12px; }
.login__tagline { font-size: 16px; opacity: 0.8; margin: 0 0 40px; }
.login__features { display: flex; flex-direction: column; gap: 20px; }
.login__feature { display: flex; align-items: flex-start; gap: 14px; }
.login__feature-icon { flex-shrink: 0; width: 40px; height: 40px; border-radius: 10px; background: rgba(129, 140, 248, 0.2); display: flex; align-items: center; justify-content: center; }
.login__feature-title { font-size: 14px; font-weight: 600; color: #fff; }
.login__feature-desc { font-size: 12px; opacity: 0.7; margin-top: 2px; }
.login__brand-decoration { position: absolute; inset: 0; pointer-events: none; }
.login__circle { position: absolute; border-radius: 50%; background: rgba(255, 255, 255, 0.05); }
.login__circle--1 { width: 300px; height: 300px; top: -80px; right: -60px; animation: circleDrift1 12s ease-in-out infinite; }
.login__circle--2 { width: 200px; height: 200px; bottom: -40px; left: -40px; animation: circleDrift2 15s ease-in-out infinite; }
.login__circle--3 { width: 150px; height: 150px; top: 50%; left: 60%; animation: circleDrift3 10s ease-in-out infinite; }
.login__particles { position: absolute; inset: 0; }
.login__particle { position: absolute; width: 6px; height: 6px; border-radius: 50%; background: rgba(255, 255, 255, 0.3); animation: particleFloat 8s ease-in-out infinite; }
.login__particle--1 { top: 15%; left: 20%; animation-delay: 0s; animation-duration: 7s; }
.login__particle--2 { top: 60%; left: 75%; animation-delay: 1.2s; animation-duration: 9s; width: 4px; height: 4px; }
.login__particle--3 { top: 80%; left: 30%; animation-delay: 2.5s; animation-duration: 6s; width: 8px; height: 8px; background: rgba(255, 255, 255, 0.2); }
.login__particle--4 { top: 25%; left: 65%; animation-delay: 3.8s; animation-duration: 10s; width: 5px; height: 5px; }
.login__particle--5 { top: 70%; left: 50%; animation-delay: 0.8s; animation-duration: 8s; width: 3px; height: 3px; background: rgba(129, 140, 248, 0.5); }
.login__particle--6 { top: 40%; left: 85%; animation-delay: 4.5s; animation-duration: 7.5s; width: 7px; height: 7px; background: rgba(255, 255, 255, 0.15); }
.login__glow { position: absolute; border-radius: 50%; filter: blur(60px); pointer-events: none; }
.login__glow--1 { width: 200px; height: 200px; background: rgba(129, 140, 248, 0.15); top: 20%; right: 10%; animation: glowPulse 6s ease-in-out infinite; }
.login__glow--2 { width: 160px; height: 160px; background: rgba(167, 139, 250, 0.12); bottom: 15%; left: 15%; animation: glowPulse 8s ease-in-out infinite 2s; }
@keyframes particleFloat {
  0%, 100% { transform: translateY(0) translateX(0); opacity: 0.3; }
  25% { transform: translateY(-20px) translateX(10px); opacity: 0.6; }
  50% { transform: translateY(-10px) translateX(-8px); opacity: 0.4; }
  75% { transform: translateY(-25px) translateX(5px); opacity: 0.7; }
}
@keyframes glowPulse {
  0%, 100% { opacity: 0.4; transform: scale(1); }
  50% { opacity: 0.8; transform: scale(1.15); }
}
@keyframes circleDrift1 {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(-15px, 20px); }
}
@keyframes circleDrift2 {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(20px, -15px); }
}
@keyframes circleDrift3 {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(-10px, -18px); }
}
.login__form-side { flex: 1; display: flex; align-items: center; justify-content: center; padding: 48px; background: var(--color-bg-page); }
.login__form-wrapper { width: 100%; max-width: 400px; }
.login__form-header { margin-bottom: 32px; }
.login__form-title { font-size: 24px; font-weight: 700; color: var(--color-text-primary); margin: 0 0 8px; }
.login__form-subtitle { font-size: 14px; color: var(--color-text-secondary); margin: 0; }
.login__form .el-form-item { margin-bottom: 20px; }
.login__submit { width: 100%; }
.login__register-link { text-align: center; margin-top: 24px; font-size: 14px; color: var(--color-text-secondary); display: flex; align-items: center; justify-content: center; gap: 4px; }
.login__register-btn { color: var(--color-primary); font-weight: 600; cursor: pointer; text-decoration: none; font-size: 14px; transition: color 0.2s, text-decoration 0.2s; }
.login__register-btn:hover { color: var(--color-primary-dark); text-decoration: underline; }
@media (max-width: 768px) { .login { flex-direction: column; } .login__brand { padding: 32px; min-height: auto; } .login__form-side { padding: 32px; } }
</style>
