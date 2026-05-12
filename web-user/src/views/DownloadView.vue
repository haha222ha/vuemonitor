<template>
  <div class="download-page">
    <header class="nav" :class="{ scrolled: navScrolled }">
      <div class="nav-inner">
        <div class="logo" @click="$router.push('/')">
          <span class="logo-mark">X</span>
          <span class="logo-text">XHS365</span>
        </div>
        <nav class="nav-links">
          <router-link to="/">首页</router-link>
          <a href="/#features">功能</a>
          <a href="/#pricing">价格</a>
        </nav>
        <div class="nav-actions">
          <router-link to="/login" class="btn-ghost">登录</router-link>
          <router-link to="/register" class="btn-primary">免费开始</router-link>
        </div>
      </div>
    </header>

    <section class="hero">
      <div class="hero-glow"></div>
      <div class="hero-content">
        <div class="hero-badge">Windows 桌面客户端</div>
        <h1>下载 XHS365</h1>
        <p>安装桌面客户端，获得实时采集、系统通知、本地存储等完整功能体验</p>
      </div>
    </section>

    <section class="download-section">
      <div class="download-card">
        <div class="dl-platform">
          <div class="dl-icon-wrap">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#0078d4" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
              <line x1="8" y1="21" x2="16" y2="21"/>
              <line x1="12" y1="17" x2="12" y2="21"/>
            </svg>
          </div>
          <div class="dl-info">
            <h3>Windows 版</h3>
            <p class="dl-sub">适用于 Windows 10/11 64位系统</p>
          </div>
        </div>

        <div class="dl-meta">
          <span class="meta-item">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
            v{{ version }}
          </span>
          <span class="meta-divider">|</span>
          <span class="meta-item">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            ~80MB
          </span>
          <span class="meta-divider">|</span>
          <span class="meta-item">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="4" width="16" height="16" rx="2"/><path d="M9 9h6v6H9z"/></svg>
            x64
          </span>
        </div>

        <div class="dl-buttons">
          <a :href="installerUrl" class="btn-dl-primary" target="_blank">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            免费下载 Windows 版
          </a>
        </div>

        <p class="dl-hint">安装如遇 Windows 安全提示，点击「更多信息」→「仍要运行」即可</p>
      </div>
    </section>

    <section class="features-section">
      <h2>桌面客户端优势</h2>
      <div class="features-grid">
        <div class="feature-item" v-for="f in features" :key="f.title">
          <div class="feature-icon-wrap" :style="{ background: f.bg }">
            <span class="feature-icon">{{ f.icon }}</span>
          </div>
          <div class="feature-text">
            <h4>{{ f.title }}</h4>
            <p>{{ f.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <section class="guide-section">
      <h2>安装指南</h2>
      <div class="guide-steps">
        <div class="step" v-for="(step, i) in installSteps" :key="i">
          <span class="step-num">{{ i + 1 }}</span>
          <span class="step-text">{{ step }}</span>
        </div>
      </div>
    </section>

    <section class="web-alt">
      <div class="web-alt-card">
        <span class="web-alt-icon">🌐</span>
        <h3>不想安装？直接使用 Web 版</h3>
        <p>无需下载，浏览器打开即可使用核心监控功能</p>
        <router-link to="/login" class="btn-primary btn-lg">打开 Web 版</router-link>
      </div>
    </section>

    <footer class="footer">
      <p>&copy; 2026 XHS365. All rights reserved.</p>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";

const navScrolled = ref(false);
const version = "0.1.0";
const installerUrl = `/downloads/XHS365-Setup-${version}.exe`;

const features = [
  { icon: "⚡", title: "实时数据采集", desc: "Chromium 内核实时加载，数据采集更快更准", bg: "rgba(99,102,241,0.12)" },
  { icon: "🔔", title: "系统通知推送", desc: "价格异动、销量激增等关键事件桌面实时提醒", bg: "rgba(244,114,182,0.12)" },
  { icon: "🔒", title: "本地加密存储", desc: "数据本地加密存储，隐私安全有保障", bg: "rgba(34,197,94,0.12)" },
  { icon: "🔄", title: "自动更新", desc: "新版本自动检测和安装，始终保持最新", bg: "rgba(251,191,36,0.12)" },
];

const installSteps = [
  "点击上方「下载安装包」按钮，下载 XHS365-Setup 安装程序",
  "双击运行下载的 .exe 文件",
  "如出现 Windows 安全提示，点击「更多信息」→「仍要运行」",
  "选择安装目录，点击「安装」",
  "安装完成后，勾选「启动 XHS365」并点击「完成」",
  "首次使用需注册账号并输入授权码激活",
];

function onScroll() {
  navScrolled.value = window.scrollY > 20;
}

onMounted(() => window.addEventListener("scroll", onScroll));
onUnmounted(() => window.removeEventListener("scroll", onScroll));
</script>

<style scoped>
.download-page {
  min-height: 100vh;
  background: #0a0a0f;
  color: #e0e0e0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

.nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  padding: 0 24px;
  transition: all 0.3s;
  background: transparent;
}
.nav.scrolled {
  background: rgba(10, 10, 15, 0.92);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.nav-inner {
  max-width: 1100px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
}
.logo { display: flex; align-items: center; gap: 8px; cursor: pointer; }
.logo-mark {
  width: 30px; height: 30px;
  background: linear-gradient(135deg, #6366f1, #f472b6);
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 16px; color: #fff;
}
.logo-text { font-size: 18px; font-weight: 700; color: #fff; }
.nav-links { display: flex; gap: 28px; }
.nav-links a { color: rgba(255,255,255,0.55); text-decoration: none; font-size: 14px; transition: color 0.2s; }
.nav-links a:hover { color: #fff; }
.nav-actions { display: flex; gap: 12px; align-items: center; }
.btn-ghost { color: rgba(255,255,255,0.7); text-decoration: none; padding: 7px 14px; border-radius: 8px; font-size: 14px; transition: all 0.2s; }
.btn-ghost:hover { color: #fff; background: rgba(255,255,255,0.06); }
.btn-primary {
  background: linear-gradient(135deg, #6366f1, #8b5cf6); color: #fff;
  text-decoration: none; padding: 7px 18px; border-radius: 8px;
  font-size: 14px; font-weight: 600; transition: all 0.2s;
  border: none; cursor: pointer; display: inline-flex; align-items: center; gap: 6px;
}
.btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(99, 102, 241, 0.35); }
.btn-lg { padding: 12px 28px; font-size: 15px; }

.hero {
  padding: 120px 24px 32px;
  text-align: center;
  position: relative;
}
.hero-glow {
  position: absolute;
  top: -60px; left: 50%; transform: translateX(-50%);
  width: 500px; height: 260px;
  background: radial-gradient(ellipse, rgba(99,102,241,0.1), transparent 70%);
  pointer-events: none;
}
.hero-content { position: relative; }
.hero-badge {
  display: inline-block;
  padding: 4px 14px;
  border-radius: 20px;
  background: rgba(99,102,241,0.1);
  border: 1px solid rgba(99,102,241,0.2);
  color: #818cf8;
  font-size: 13px;
  font-weight: 500;
  margin-bottom: 16px;
}
.hero h1 {
  font-size: 40px;
  font-weight: 800;
  color: #fff;
  margin-bottom: 12px;
  letter-spacing: -0.5px;
}
.hero p {
  font-size: 16px;
  color: rgba(255,255,255,0.45);
  max-width: 460px;
  margin: 0 auto;
  line-height: 1.6;
}

.download-section {
  padding: 24px 24px 48px;
}
.download-card {
  max-width: 520px;
  margin: 0 auto;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  padding: 28px;
}
.dl-platform {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}
.dl-icon-wrap {
  width: 56px; height: 56px;
  background: rgba(0,120,212,0.08);
  border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.dl-info h3 { font-size: 20px; font-weight: 700; color: #fff; margin: 0; }
.dl-sub { font-size: 13px; color: rgba(255,255,255,0.4); margin: 2px 0 0; }

.dl-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 20px;
  font-size: 13px;
  color: rgba(255,255,255,0.4);
}
.meta-item { display: flex; align-items: center; gap: 4px; }
.meta-divider { color: rgba(255,255,255,0.15); }

.dl-buttons {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 12px;
}
.btn-dl-primary {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 13px 20px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.2s;
}
.btn-dl-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4);
}
.btn-dl-secondary {
  display: block;
  text-align: center;
  padding: 10px 20px;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.1);
  color: rgba(255,255,255,0.6);
  border-radius: 10px;
  font-size: 13px;
  text-decoration: none;
  transition: all 0.2s;
}
.btn-dl-secondary:hover {
  background: rgba(255,255,255,0.07);
  color: #fff;
  border-color: rgba(255,255,255,0.18);
}

.dl-hint {
  font-size: 12px;
  color: rgba(255,255,255,0.25);
  text-align: center;
  margin: 0;
  line-height: 1.5;
}

.features-section {
  padding: 48px 24px;
  max-width: 700px;
  margin: 0 auto;
}
.features-section h2 {
  text-align: center;
  font-size: 22px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 28px;
}
.features-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.feature-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.04);
  border-radius: 10px;
  padding: 16px;
}
.feature-icon-wrap {
  width: 36px; height: 36px;
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.feature-icon { font-size: 18px; }
.feature-text h4 { font-size: 14px; font-weight: 600; color: #fff; margin: 0 0 3px; }
.feature-text p { font-size: 12px; color: rgba(255,255,255,0.35); line-height: 1.5; margin: 0; }

.guide-section {
  padding: 48px 24px;
  max-width: 560px;
  margin: 0 auto;
}
.guide-section h2 {
  text-align: center;
  font-size: 22px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 24px;
}
.guide-steps {
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 12px;
  padding: 8px 20px;
}
.step {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid rgba(255,255,255,0.03);
}
.step:last-child { border-bottom: none; }
.step-num {
  flex-shrink: 0;
  width: 24px; height: 24px;
  background: rgba(99,102,241,0.12);
  color: #818cf8;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 600;
}
.step-text { font-size: 13px; color: rgba(255,255,255,0.5); line-height: 1.6; padding-top: 2px; }

.web-alt {
  padding: 32px 24px 56px;
}
.web-alt-card {
  max-width: 440px;
  margin: 0 auto;
  text-align: center;
  background: rgba(99,102,241,0.04);
  border: 1px solid rgba(99,102,241,0.12);
  border-radius: 14px;
  padding: 28px 24px;
}
.web-alt-icon { font-size: 32px; }
.web-alt-card h3 { font-size: 17px; font-weight: 700; color: #fff; margin: 8px 0; }
.web-alt-card p { font-size: 13px; color: rgba(255,255,255,0.4); margin-bottom: 18px; }

.footer {
  padding: 20px;
  text-align: center;
  border-top: 1px solid rgba(255,255,255,0.04);
}
.footer p { font-size: 12px; color: rgba(255,255,255,0.2); margin: 0; }

@media (max-width: 768px) {
  .hero h1 { font-size: 28px; }
  .features-grid { grid-template-columns: 1fr; }
  .nav-links { display: none; }
  .download-card { padding: 20px; }
}
</style>
