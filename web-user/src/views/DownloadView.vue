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
        <div class="hero-badge" v-observe>Windows 桌面客户端</div>
        <h1 v-observe>下载 XHS365</h1>
        <p v-observe>安装桌面客户端，获得实时采集、系统通知、本地存储等完整功能体验</p>
      </div>
    </section>

    <section class="download-section" v-observe>
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
          <a :href="installerUrl" class="btn-dl-primary" download>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            免费下载 Windows 版
          </a>
        </div>

        <p class="dl-hint">安装如遇 Windows 安全提示，点击「更多信息」→「仍要运行」即可</p>
      </div>
    </section>

    <section class="features-section">
      <div class="section-header" v-observe>
        <div class="section-tag">客户端优势</div>
        <h2>桌面客户端优势</h2>
        <p>安装桌面客户端，解锁更强大的监控能力</p>
      </div>
      <div class="waterfall">
        <div class="waterfall-col">
          <div class="wf-card wf-card-tall" v-observe>
            <div class="wf-card-glow glow-indigo"></div>
            <div class="wf-card-content">
              <div class="wf-icon-wrap icon-indigo">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
              </div>
              <h3>实时数据采集</h3>
              <p>Chromium 内核实时加载页面，DOM 数据精准提取，比 Web 版采集更快更准，支持定时自动采集。</p>
              <div class="wf-mock-monitor">
                <div class="mock-row" v-for="i in 4" :key="i">
                  <div class="mock-dot" :class="{ up: i % 3 !== 0, down: i % 3 === 0 }"></div>
                  <div class="mock-bar" :style="{width: (35 + Math.random()*55).toFixed(0) + '%'}"></div>
                  <div class="mock-val">{{ i % 3 !== 0 ? '↑' : '↓' }} {{ (Math.random()*30).toFixed(1) }}%</div>
                </div>
              </div>
            </div>
          </div>
          <div class="wf-card" v-observe>
            <div class="wf-card-glow glow-green"></div>
            <div class="wf-card-content">
              <div class="wf-icon-wrap icon-green">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
              </div>
              <h3>本地加密存储</h3>
              <p>数据本地加密存储，隐私安全有保障，无需担心云端泄露风险。</p>
            </div>
          </div>
        </div>
        <div class="waterfall-col">
          <div class="wf-card" v-observe>
            <div class="wf-card-glow glow-pink"></div>
            <div class="wf-card-content">
              <div class="wf-icon-wrap icon-pink">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
              </div>
              <h3>系统通知推送</h3>
              <p>价格异动、销量激增等关键事件桌面实时提醒，不错过任何商机。</p>
            </div>
          </div>
          <div class="wf-card wf-card-tall" v-observe>
            <div class="wf-card-glow glow-amber"></div>
            <div class="wf-card-content">
              <div class="wf-icon-wrap icon-amber">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 0 1-9 9m9-9a9 9 0 0 0-9-9m9 9H3m9 9a9 9 0 0 1-9-9m9 9c1.66 0 3-4.03 3-9s-1.34-9-3-9m0 18c-1.66 0-3-4.03-3-9s1.34-9 3-9m-9 9a9 9 0 0 1 9-9"/></svg>
              </div>
              <h3>自动更新</h3>
              <p>新版本自动检测和安装，始终保持最新，享受最新功能和性能优化。</p>
              <div class="wf-update-timeline">
                <div class="timeline-item" v-for="i in 3" :key="i">
                  <div class="timeline-dot"></div>
                  <div class="timeline-bar" :style="{width: (50 + Math.random()*40).toFixed(0) + '%'}"></div>
                  <div class="timeline-label">v0.{{ 3 - i }}.0</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="guide-section" v-observe>
      <h2>安装指南</h2>
      <div class="guide-steps">
        <div class="step" v-for="(step, i) in installSteps" :key="i">
          <span class="step-num">{{ i + 1 }}</span>
          <span class="step-text">{{ step }}</span>
        </div>
      </div>
    </section>

    <section class="web-alt" v-observe>
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

const vObserve = {
  mounted(el: HTMLElement) {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.classList.add("visible");
          observer.unobserve(el);
        }
      },
      { threshold: 0.06, rootMargin: "0px 0px -40px 0px" }
    );
    observer.observe(el);
  },
};

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

onMounted(() => window.addEventListener("scroll", onScroll, { passive: true }));
onUnmounted(() => window.removeEventListener("scroll", onScroll));
</script>

<style scoped>
.download-page {
  min-height: 100vh;
  background: #06060f;
  color: #e0e0e0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  overflow-x: hidden;
}

.nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  padding: 0 24px;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  background: transparent;
  border-bottom: 1px solid transparent;
}
.nav.scrolled {
  background: rgba(6, 6, 15, 0.85);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-bottom-color: rgba(255,255,255,0.06);
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
  opacity: 0; transform: translateY(20px);
  transition: all 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}
.hero-badge.visible { opacity: 1; transform: translateY(0); }
.hero h1 {
  font-size: 40px;
  font-weight: 800;
  color: #fff;
  margin-bottom: 12px;
  letter-spacing: -0.5px;
  opacity: 0; transform: translateY(20px);
  transition: all 0.8s cubic-bezier(0.16, 1, 0.3, 1) 0.1s;
}
.hero h1.visible { opacity: 1; transform: translateY(0); }
.hero p {
  font-size: 16px;
  color: rgba(255,255,255,0.45);
  max-width: 460px;
  margin: 0 auto;
  line-height: 1.6;
  opacity: 0; transform: translateY(20px);
  transition: all 0.8s cubic-bezier(0.16, 1, 0.3, 1) 0.2s;
}
.hero p.visible { opacity: 1; transform: translateY(0); }

.download-section {
  padding: 24px 24px 48px;
  opacity: 0; transform: translateY(30px);
  transition: all 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}
.download-section.visible { opacity: 1; transform: translateY(0); }
.download-card {
  max-width: 520px;
  margin: 0 auto;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  padding: 28px;
  overflow: hidden;
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
  flex-wrap: wrap;
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
  box-sizing: border-box;
  white-space: nowrap;
}
.btn-dl-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4);
}

.dl-hint {
  font-size: 12px;
  color: rgba(255,255,255,0.25);
  text-align: center;
  margin: 0;
  line-height: 1.5;
}

.features-section {
  padding: 80px 24px;
  max-width: 900px;
  margin: 0 auto;
}
.section-header {
  text-align: center;
  margin-bottom: 48px;
  opacity: 0; transform: translateY(30px);
  transition: all 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}
.section-header.visible { opacity: 1; transform: translateY(0); }
.section-tag {
  display: inline-block;
  padding: 6px 16px;
  background: rgba(99,102,241,0.1);
  border: 1px solid rgba(99,102,241,0.2);
  border-radius: 100px;
  font-size: 12px;
  font-weight: 600;
  color: #818cf8;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 16px;
}
.section-header h2 {
  font-size: 28px;
  font-weight: 800;
  color: #fff;
  margin-bottom: 12px;
  letter-spacing: -0.02em;
}
.section-header p {
  font-size: 16px;
  color: rgba(255,255,255,0.45);
}

.waterfall { display: flex; gap: 24px; align-items: flex-start; }
.waterfall-col { flex: 1; display: flex; flex-direction: column; gap: 24px; }
.wf-card {
  position: relative;
  border-radius: 20px;
  overflow: hidden;
  border: 1px solid rgba(255,255,255,0.06);
  background: rgba(15, 15, 35, 0.7);
  backdrop-filter: blur(20px);
  transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
  opacity: 0; transform: translateY(40px);
}
.wf-card.visible { opacity: 1; transform: translateY(0); }
.wf-card:hover {
  border-color: rgba(255,255,255,0.12);
  background: rgba(20, 20, 50, 0.85);
  transform: translateY(-4px);
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
}
.wf-card-tall { }
.wf-card-glow { position: absolute; top: -1px; left: -1px; right: -1px; height: 2px; }
.glow-indigo { background: linear-gradient(90deg, transparent, #6366f1, transparent); }
.glow-pink { background: linear-gradient(90deg, transparent, #f472b6, transparent); }
.glow-green { background: linear-gradient(90deg, transparent, #22c55e, transparent); }
.glow-amber { background: linear-gradient(90deg, transparent, #f59e0b, transparent); }
.wf-card-content { position: relative; padding: 32px; z-index: 1; }
.wf-icon-wrap {
  width: 52px; height: 52px;
  border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 20px;
}
.icon-indigo { background: rgba(99,102,241,0.12); color: #6366f1; }
.icon-pink { background: rgba(244,114,182,0.12); color: #f472b6; }
.icon-green { background: rgba(34,197,94,0.12); color: #22c55e; }
.icon-amber { background: rgba(251,191,36,0.12); color: #f59e0b; }
.wf-card-content h3 { font-size: 22px; font-weight: 700; margin-bottom: 12px; letter-spacing: -0.01em; color: #fff; }
.wf-card-content p { font-size: 14px; line-height: 1.7; color: rgba(240,240,248,0.6); margin-bottom: 20px; }

.wf-mock-monitor { display: flex; flex-direction: column; gap: 10px; }
.mock-row {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 14px; border-radius: 8px;
  background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06);
}
.mock-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.mock-dot.up { background: #22c55e; box-shadow: 0 0 8px rgba(34,197,94,0.4); }
.mock-dot.down { background: #ef4444; box-shadow: 0 0 8px rgba(239,68,68,0.4); }
.mock-bar { height: 6px; border-radius: 3px; background: rgba(99,102,241,0.2); flex: 1; }
.mock-val { font-size: 12px; font-family: 'JetBrains Mono', monospace, monospace; color: rgba(240,240,248,0.6); white-space: nowrap; }

.wf-update-timeline { display: flex; flex-direction: column; gap: 12px; }
.timeline-item {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 14px; border-radius: 8px;
  background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06);
}
.timeline-dot { width: 8px; height: 8px; border-radius: 50%; background: #f59e0b; box-shadow: 0 0 8px rgba(251,191,36,0.4); flex-shrink: 0; }
.timeline-bar { height: 6px; border-radius: 3px; background: rgba(251,191,36,0.2); flex: 1; }
.timeline-label { font-size: 12px; font-family: monospace; color: rgba(240,240,248,0.6); white-space: nowrap; }

.guide-section {
  padding: 80px 24px;
  max-width: 560px;
  margin: 0 auto;
  opacity: 0; transform: translateY(30px);
  transition: all 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}
.guide-section.visible { opacity: 1; transform: translateY(0); }
.guide-section h2 {
  text-align: center;
  font-size: 28px;
  font-weight: 800;
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
  opacity: 0; transform: translateY(30px);
  transition: all 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}
.web-alt.visible { opacity: 1; transform: translateY(0); }
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
  .waterfall { flex-direction: column; }
  .nav-links { display: none; }
  .download-card { padding: 20px; }
  .btn-dl-primary { font-size: 14px; padding: 12px 16px; }
  .section-header h2 { font-size: 22px; }
  .guide-section h2 { font-size: 22px; }
  .wf-card-content { padding: 24px; }
  .wf-card-content h3 { font-size: 18px; }
}
</style>
