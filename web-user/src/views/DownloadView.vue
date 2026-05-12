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

    <section class="hero-section">
      <div class="hero-bg">
        <div class="hero-orb orb-1"></div>
        <div class="hero-orb orb-2"></div>
      </div>
      <div class="hero-inner">
        <h1>下载 XHS365 客户端</h1>
        <p class="hero-desc">安装桌面客户端，获得最佳使用体验。支持实时采集、离线使用、系统通知等完整功能。</p>
      </div>
    </section>

    <section class="platforms-section">
      <div class="platforms-inner">
        <div class="platform-card" v-for="p in platforms" :key="p.name">
          <div class="platform-icon-wrap" :style="{ background: p.gradient }">
            <span class="platform-emoji">{{ p.icon }}</span>
          </div>
          <h3>{{ p.name }}</h3>
          <p class="platform-desc">{{ p.desc }}</p>
          <div class="platform-meta">
            <span class="meta-tag">{{ p.version }}</span>
            <span class="meta-tag">{{ p.size }}</span>
            <span class="meta-tag">{{ p.arch }}</span>
          </div>
          <button class="btn-download" @click="handleDownload(p)" :disabled="downloading === p.name">
            <svg v-if="downloading !== p.name" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            <span v-if="downloading === p.name" class="spinner"></span>
            {{ downloading === p.name ? '下载中...' : '免费下载' }}
          </button>
          <div class="platform-also" v-if="p.also">
            <span>也可：</span>
            <a v-for="alt in p.also" :key="alt.label" :href="alt.url" class="alt-link">{{ alt.label }}</a>
          </div>
        </div>
      </div>
    </section>

    <section class="features-section">
      <div class="features-inner">
        <h2>为什么使用桌面客户端？</h2>
        <div class="features-grid">
          <div class="feature-card" v-for="f in features" :key="f.title">
            <div class="feature-icon">{{ f.icon }}</div>
            <h4>{{ f.title }}</h4>
            <p>{{ f.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <section class="guide-section">
      <div class="guide-inner">
        <h2>安装指南</h2>
        <div class="guide-tabs">
          <button v-for="g in guides" :key="g.name" class="guide-tab" :class="{ active: activeGuide === g.name }" @click="activeGuide = g.name">
            {{ g.icon }} {{ g.name }}
          </button>
        </div>
        <div class="guide-content">
          <div v-for="g in guides" :key="g.name" v-show="activeGuide === g.name">
            <ol class="guide-steps">
              <li v-for="(step, i) in g.steps" :key="i">
                <span class="step-num">{{ i + 1 }}</span>
                <span class="step-text">{{ step }}</span>
              </li>
            </ol>
          </div>
        </div>
      </div>
    </section>

    <section class="web-section">
      <div class="web-inner">
        <div class="web-icon">🌐</div>
        <h3>不想安装？直接使用 Web 版</h3>
        <p>无需下载，浏览器打开即可使用核心功能</p>
        <router-link to="/login" class="btn-primary btn-lg">打开 Web 版</router-link>
      </div>
    </section>

    <footer class="footer">
      <div class="footer-inner">
        <p>&copy; 2026 XHS365. All rights reserved.</p>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import "../assets/landing.css";

const navScrolled = ref(false);
const downloading = ref("");
const activeGuide = ref("Windows");

const baseUrl = window.location.origin;

const platforms = ref([
  {
    name: "Windows",
    icon: "🪟",
    desc: "适用于 Windows 10/11 64位系统",
    version: "v0.1.0",
    size: "~80MB",
    arch: "x64",
    gradient: "linear-gradient(135deg, #0078d4, #00bcf2)",
    url: `${baseUrl}/downloads/windows/XHS365-Setup-0.1.0.exe`,
    portableUrl: `${baseUrl}/downloads/windows/XHS365-0.1.0-portable.exe`,
    also: [
      { label: "便携版（免安装）", url: `${baseUrl}/downloads/windows/XHS365-0.1.0-portable.exe` },
    ],
  },
  {
    name: "macOS",
    icon: "🍎",
    desc: "适用于 macOS 12+ (Intel / Apple Silicon)",
    version: "v0.1.0",
    size: "~100MB",
    arch: "x64 / arm64",
    gradient: "linear-gradient(135deg, #333, #666)",
    url: `${baseUrl}/downloads/macos/XHS365-0.1.0.dmg`,
    also: [
      { label: "ZIP 压缩包", url: `${baseUrl}/downloads/macos/XHS365-0.1.0-mac.zip` },
    ],
  },
  {
    name: "Linux",
    icon: "🐧",
    desc: "适用于 Ubuntu 22.04+ / Debian 12+",
    version: "v0.1.0",
    size: "~90MB",
    arch: "x64",
    gradient: "linear-gradient(135deg, #dd4814, #f7a84b)",
    url: `${baseUrl}/downloads/linux/XHS365-0.1.0.AppImage`,
    also: [
      { label: ".deb 包", url: `${baseUrl}/downloads/linux/XHS365-0.1.0-amd64.deb` },
      { label: ".rpm 包", url: `${baseUrl}/downloads/linux/XHS365-0.1.0-x86_64.rpm` },
    ],
  },
]);

const features = [
  { icon: "⚡", title: "实时数据采集", desc: "Chromium 内核实时加载，数据采集更快更准" },
  { icon: "📴", title: "离线使用", desc: "断网也能查看历史数据和已生成的 AI 报告" },
  { icon: "🔔", title: "系统通知", desc: "价格异动、销量激增等关键事件桌面推送" },
  { icon: "🔄", title: "自动更新", desc: "新版本自动检测和安装，始终保持最新" },
  { icon: "🔒", title: "本地存储", desc: "数据本地加密存储，隐私安全有保障" },
  { icon: "📊", title: "性能监控", desc: "内置性能监控，采集任务状态一目了然" },
];

const guides = [
  {
    name: "Windows",
    icon: "🪟",
    steps: [
      "点击上方「免费下载」按钮，下载 XHS365-Setup 安装包",
      "双击运行下载的 .exe 文件",
      "如出现 Windows 安全提示，点击「更多信息」→「仍要运行」",
      "选择安装目录，点击「安装」",
      "安装完成后，勾选「启动 XHS365」并点击「完成」",
      "首次使用需注册账号并输入授权码激活",
    ],
  },
  {
    name: "macOS",
    icon: "🍎",
    steps: [
      "点击上方「免费下载」按钮，下载 XHS365.dmg 安装包",
      "双击打开 .dmg 文件",
      "将 XHS365 图标拖拽到 Applications 文件夹",
      "首次打开时，右键点击应用 → 选择「打开」",
      "如出现安全提示，前往「系统偏好设置 → 安全性与隐私」→ 点击「仍要打开」",
      "首次使用需注册账号并输入授权码激活",
    ],
  },
  {
    name: "Linux",
    icon: "🐧",
    steps: [
      "点击上方「免费下载」按钮，下载 .AppImage 文件",
      "打开终端，添加执行权限：chmod +x XHS365-*.AppImage",
      "运行：./XHS365-*.AppImage",
      "如使用 .deb 包：sudo dpkg -i xhs365-*.deb && sudo apt-get install -f",
      "如使用 .rpm 包：sudo rpm -i xhs365-*.rpm",
      "首次使用需注册账号并输入授权码激活",
    ],
  },
];

function handleDownload(p: any) {
  downloading.value = p.name;
  const a = document.createElement("a");
  a.href = p.url;
  a.download = "";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => {
    downloading.value = "";
  }, 3000);
}

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
  color: #e5e5e5;
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
  background: rgba(10, 10, 15, 0.85);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(255,255,255,0.06);
}
.nav-inner {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
}
.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
.logo-mark {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #6366f1, #f472b6);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 18px;
  color: #fff;
}
.logo-text {
  font-size: 20px;
  font-weight: 700;
  color: #fff;
}
.nav-links {
  display: flex;
  gap: 32px;
}
.nav-links a {
  color: rgba(255,255,255,0.6);
  text-decoration: none;
  font-size: 14px;
  transition: color 0.2s;
}
.nav-links a:hover {
  color: #fff;
}
.nav-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}
.btn-ghost {
  color: rgba(255,255,255,0.7);
  text-decoration: none;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  transition: all 0.2s;
}
.btn-ghost:hover {
  color: #fff;
  background: rgba(255,255,255,0.06);
}
.btn-primary {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  text-decoration: none;
  padding: 8px 20px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.2s;
  border: none;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 20px rgba(99, 102, 241, 0.4);
}
.btn-lg {
  padding: 12px 28px;
  font-size: 16px;
}

.hero-section {
  position: relative;
  padding: 140px 24px 60px;
  text-align: center;
  overflow: hidden;
}
.hero-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
.hero-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.3;
}
.orb-1 {
  width: 400px;
  height: 400px;
  background: #6366f1;
  top: -100px;
  left: 20%;
}
.orb-2 {
  width: 300px;
  height: 300px;
  background: #f472b6;
  bottom: -50px;
  right: 20%;
}
.hero-inner {
  position: relative;
  max-width: 700px;
  margin: 0 auto;
}
.hero-inner h1 {
  font-size: 42px;
  font-weight: 800;
  margin-bottom: 16px;
  background: linear-gradient(135deg, #fff, rgba(255,255,255,0.7));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.hero-desc {
  font-size: 17px;
  color: rgba(255,255,255,0.5);
  line-height: 1.7;
}

.platforms-section {
  padding: 40px 24px 80px;
}
.platforms-inner {
  max-width: 1000px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}
.platform-card {
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 16px;
  padding: 32px 24px;
  text-align: center;
  transition: all 0.3s;
}
.platform-card:hover {
  background: rgba(255,255,255,0.05);
  border-color: rgba(99, 102, 241, 0.3);
  transform: translateY(-4px);
}
.platform-icon-wrap {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
}
.platform-emoji {
  font-size: 28px;
}
.platform-card h3 {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 8px;
  color: #fff;
}
.platform-desc {
  font-size: 13px;
  color: rgba(255,255,255,0.4);
  margin-bottom: 16px;
}
.platform-meta {
  display: flex;
  gap: 8px;
  justify-content: center;
  margin-bottom: 20px;
}
.meta-tag {
  background: rgba(255,255,255,0.06);
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  color: rgba(255,255,255,0.5);
}
.btn-download {
  width: 100%;
  padding: 12px 24px;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: all 0.2s;
}
.btn-download:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 20px rgba(99, 102, 241, 0.4);
}
.btn-download:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}
.spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
.platform-also {
  margin-top: 12px;
  font-size: 12px;
  color: rgba(255,255,255,0.3);
}
.alt-link {
  color: #818cf8;
  text-decoration: none;
  margin-left: 4px;
}
.alt-link:hover {
  text-decoration: underline;
}

.features-section {
  padding: 80px 24px;
  background: rgba(255,255,255,0.01);
}
.features-inner {
  max-width: 1000px;
  margin: 0 auto;
  text-align: center;
}
.features-inner h2 {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 40px;
  color: #fff;
}
.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}
.feature-card {
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 12px;
  padding: 24px;
  text-align: left;
}
.feature-icon {
  font-size: 28px;
  margin-bottom: 12px;
}
.feature-card h4 {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #fff;
}
.feature-card p {
  font-size: 13px;
  color: rgba(255,255,255,0.4);
  line-height: 1.6;
}

.guide-section {
  padding: 80px 24px;
}
.guide-inner {
  max-width: 700px;
  margin: 0 auto;
}
.guide-inner h2 {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 32px;
  text-align: center;
  color: #fff;
}
.guide-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
  justify-content: center;
}
.guide-tab {
  padding: 8px 20px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.1);
  background: transparent;
  color: rgba(255,255,255,0.5);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}
.guide-tab.active {
  background: rgba(99, 102, 241, 0.15);
  border-color: #6366f1;
  color: #fff;
}
.guide-steps {
  list-style: none;
  padding: 0;
}
.guide-steps li {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 14px 0;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}
.step-num {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  background: rgba(99, 102, 241, 0.15);
  color: #818cf8;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
}
.step-text {
  font-size: 14px;
  color: rgba(255,255,255,0.6);
  line-height: 1.6;
  padding-top: 3px;
}

.web-section {
  padding: 80px 24px;
  text-align: center;
  background: rgba(255,255,255,0.01);
}
.web-inner {
  max-width: 500px;
  margin: 0 auto;
}
.web-icon {
  font-size: 48px;
  margin-bottom: 16px;
}
.web-inner h3 {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 8px;
  color: #fff;
}
.web-inner p {
  font-size: 14px;
  color: rgba(255,255,255,0.4);
  margin-bottom: 24px;
}

.footer {
  padding: 24px;
  text-align: center;
  border-top: 1px solid rgba(255,255,255,0.04);
}
.footer p {
  font-size: 13px;
  color: rgba(255,255,255,0.25);
}

@media (max-width: 768px) {
  .platforms-inner {
    grid-template-columns: 1fr;
  }
  .features-grid {
    grid-template-columns: 1fr;
  }
  .hero-inner h1 {
    font-size: 28px;
  }
}
</style>