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
        <h1>下载 XHS365 客户端</h1>
        <p>安装桌面客户端，获得实时采集、离线使用、系统通知等完整功能体验</p>
      </div>
    </section>

    <section class="platforms">
      <div class="platforms-grid">
        <div class="platform-card" v-for="p in platforms" :key="p.name">
          <div class="card-header" :style="{ borderColor: p.color }">
            <span class="platform-icon">{{ p.icon }}</span>
            <div>
              <h3>{{ p.name }}</h3>
              <p class="platform-sub">{{ p.desc }}</p>
            </div>
          </div>
          <div class="card-body">
            <div class="card-tags">
              <span class="tag">{{ p.version }}</span>
              <span class="tag">{{ p.size }}</span>
              <span class="tag">{{ p.arch }}</span>
            </div>
            <a :href="p.url" class="btn-dl" :style="{ background: p.color }" target="_blank">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              免费下载
            </a>
            <div class="alt-downloads" v-if="p.also && p.also.length">
              <span class="alt-label">其他格式：</span>
              <a v-for="alt in p.also" :key="alt.label" :href="alt.url" class="alt-link" target="_blank">{{ alt.label }}</a>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="why-desktop">
      <h2>为什么使用桌面客户端？</h2>
      <div class="features-grid">
        <div class="feature" v-for="f in features" :key="f.title">
          <span class="feature-icon">{{ f.icon }}</span>
          <h4>{{ f.title }}</h4>
          <p>{{ f.desc }}</p>
        </div>
      </div>
    </section>

    <section class="guide">
      <h2>安装指南</h2>
      <div class="guide-tabs">
        <button v-for="g in guides" :key="g.name" class="guide-tab" :class="{ active: activeGuide === g.name }" @click="activeGuide = g.name">
          {{ g.icon }} {{ g.name }}
        </button>
      </div>
      <div class="guide-steps">
        <div v-for="g in guides" :key="g.name" v-show="activeGuide === g.name">
          <div class="step" v-for="(step, i) in g.steps" :key="i">
            <span class="step-num">{{ i + 1 }}</span>
            <span class="step-text">{{ step }}</span>
          </div>
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
const activeGuide = ref("Windows");
const baseUrl = window.location.origin;

const platforms = [
  {
    name: "Windows",
    icon: "🪟",
    desc: "Windows 10/11 64位",
    version: "v0.1.0",
    size: "~80MB",
    arch: "x64",
    color: "#0078d4",
    url: `${baseUrl}/downloads/windows/XHS365-Setup-0.1.0.exe`,
    also: [
      { label: "便携版（免安装）", url: `${baseUrl}/downloads/windows/XHS365-0.1.0-portable.exe` },
    ],
  },
  {
    name: "macOS",
    icon: "🍎",
    desc: "macOS 12+ Intel / Apple Silicon",
    version: "v0.1.0",
    size: "~100MB",
    arch: "Universal",
    color: "#555",
    url: `${baseUrl}/downloads/macos/XHS365-0.1.0.dmg`,
    also: [
      { label: "ZIP 压缩包", url: `${baseUrl}/downloads/macos/XHS365-0.1.0-mac.zip` },
    ],
  },
  {
    name: "Linux",
    icon: "🐧",
    desc: "Ubuntu 22.04+ / Debian 12+",
    version: "v0.1.0",
    size: "~90MB",
    arch: "x64",
    color: "#dd4814",
    url: `${baseUrl}/downloads/linux/XHS365-0.1.0.AppImage`,
    also: [
      { label: ".deb", url: `${baseUrl}/downloads/linux/XHS365-0.1.0-amd64.deb` },
      { label: ".rpm", url: `${baseUrl}/downloads/linux/XHS365-0.1.0-x86_64.rpm` },
    ],
  },
];

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
      "点击「免费下载」按钮，下载 XHS365-Setup 安装包",
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
      "点击「免费下载」按钮，下载 XHS365.dmg 安装包",
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
      "点击「免费下载」按钮，下载 .AppImage 文件",
      "打开终端，添加执行权限：chmod +x XHS365-*.AppImage",
      "运行：./XHS365-*.AppImage",
      "如使用 .deb 包：sudo dpkg -i xhs365-*.deb && sudo apt-get install -f",
      "如使用 .rpm 包：sudo rpm -i xhs365-*.rpm",
      "首次使用需注册账号并输入授权码激活",
    ],
  },
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
  background: rgba(10, 10, 15, 0.9);
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
.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}
.logo-mark {
  width: 30px;
  height: 30px;
  background: linear-gradient(135deg, #6366f1, #f472b6);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 16px;
  color: #fff;
}
.logo-text { font-size: 18px; font-weight: 700; color: #fff; }
.nav-links { display: flex; gap: 28px; }
.nav-links a { color: rgba(255,255,255,0.55); text-decoration: none; font-size: 14px; transition: color 0.2s; }
.nav-links a:hover { color: #fff; }
.nav-actions { display: flex; gap: 12px; align-items: center; }
.btn-ghost { color: rgba(255,255,255,0.7); text-decoration: none; padding: 7px 14px; border-radius: 8px; font-size: 14px; transition: all 0.2s; }
.btn-ghost:hover { color: #fff; background: rgba(255,255,255,0.06); }
.btn-primary { background: linear-gradient(135deg, #6366f1, #8b5cf6); color: #fff; text-decoration: none; padding: 7px 18px; border-radius: 8px; font-size: 14px; font-weight: 600; transition: all 0.2s; border: none; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; }
.btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(99, 102, 241, 0.35); }
.btn-lg { padding: 12px 28px; font-size: 15px; }

.hero {
  padding: 120px 24px 40px;
  text-align: center;
  position: relative;
}
.hero-glow {
  position: absolute;
  top: -60px;
  left: 50%;
  transform: translateX(-50%);
  width: 600px;
  height: 300px;
  background: radial-gradient(ellipse, rgba(99,102,241,0.12), transparent 70%);
  pointer-events: none;
}
.hero-content { position: relative; }
.hero h1 {
  font-size: 36px;
  font-weight: 800;
  color: #fff;
  margin-bottom: 12px;
}
.hero p {
  font-size: 16px;
  color: rgba(255,255,255,0.45);
  max-width: 520px;
  margin: 0 auto;
  line-height: 1.6;
}

.platforms {
  padding: 40px 24px 60px;
}
.platforms-grid {
  max-width: 900px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}
.platform-card {
  background: rgba(255,255,255,0.025);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 14px;
  overflow: hidden;
  transition: all 0.3s;
}
.platform-card:hover {
  background: rgba(255,255,255,0.04);
  border-color: rgba(255,255,255,0.1);
  transform: translateY(-2px);
}
.card-header {
  padding: 20px 20px 16px;
  display: flex;
  align-items: center;
  gap: 14px;
  border-bottom: 2px solid;
  border-left: none;
  border-right: none;
  border-top: none;
}
.platform-icon { font-size: 32px; }
.card-header h3 { font-size: 18px; font-weight: 700; color: #fff; margin: 0; }
.platform-sub { font-size: 12px; color: rgba(255,255,255,0.4); margin: 2px 0 0; }
.card-body { padding: 16px 20px 20px; }
.card-tags { display: flex; gap: 6px; margin-bottom: 16px; flex-wrap: wrap; }
.tag {
  background: rgba(255,255,255,0.05);
  padding: 3px 10px;
  border-radius: 5px;
  font-size: 12px;
  color: rgba(255,255,255,0.45);
}
.btn-dl {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 11px 20px;
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.2s;
}
.btn-dl:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(0,0,0,0.3);
  filter: brightness(1.1);
}
.alt-downloads {
  margin-top: 10px;
  font-size: 12px;
  color: rgba(255,255,255,0.3);
}
.alt-link {
  color: #818cf8;
  text-decoration: none;
  margin-left: 4px;
}
.alt-link:hover { text-decoration: underline; }

.why-desktop {
  padding: 60px 24px;
  max-width: 900px;
  margin: 0 auto;
}
.why-desktop h2 {
  text-align: center;
  font-size: 24px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 36px;
}
.features-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
.feature {
  background: rgba(255,255,255,0.02);
  border: 1px solid rgba(255,255,255,0.04);
  border-radius: 12px;
  padding: 20px;
}
.feature-icon { font-size: 24px; }
.feature h4 { font-size: 14px; font-weight: 600; color: #fff; margin: 8px 0 4px; }
.feature p { font-size: 12px; color: rgba(255,255,255,0.35); line-height: 1.5; margin: 0; }

.guide {
  padding: 60px 24px;
  max-width: 640px;
  margin: 0 auto;
}
.guide h2 {
  text-align: center;
  font-size: 24px;
  font-weight: 700;
  color: #fff;
  margin-bottom: 24px;
}
.guide-tabs { display: flex; gap: 8px; justify-content: center; margin-bottom: 20px; }
.guide-tab {
  padding: 7px 18px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.08);
  background: transparent;
  color: rgba(255,255,255,0.45);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.guide-tab.active { background: rgba(99,102,241,0.12); border-color: rgba(99,102,241,0.4); color: #fff; }
.step {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid rgba(255,255,255,0.03);
}
.step-num {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  background: rgba(99,102,241,0.12);
  color: #818cf8;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
}
.step-text { font-size: 13px; color: rgba(255,255,255,0.5); line-height: 1.5; padding-top: 2px; }

.web-alt {
  padding: 40px 24px 60px;
}
.web-alt-card {
  max-width: 480px;
  margin: 0 auto;
  text-align: center;
  background: rgba(99,102,241,0.04);
  border: 1px solid rgba(99,102,241,0.12);
  border-radius: 14px;
  padding: 32px 24px;
}
.web-alt-icon { font-size: 36px; }
.web-alt-card h3 { font-size: 18px; font-weight: 700; color: #fff; margin: 8px 0; }
.web-alt-card p { font-size: 13px; color: rgba(255,255,255,0.4); margin-bottom: 20px; }

.footer {
  padding: 20px;
  text-align: center;
  border-top: 1px solid rgba(255,255,255,0.04);
}
.footer p { font-size: 12px; color: rgba(255,255,255,0.2); margin: 0; }

@media (max-width: 768px) {
  .platforms-grid { grid-template-columns: 1fr; max-width: 400px; }
  .features-grid { grid-template-columns: 1fr 1fr; }
  .hero h1 { font-size: 26px; }
  .nav-links { display: none; }
}
</style>