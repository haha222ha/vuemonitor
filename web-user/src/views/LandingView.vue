<template>
  <div class="landing">
    <header class="nav">
      <div class="nav-inner">
        <div class="logo">
          <span class="logo-icon">◆</span>
          <span class="logo-text">VueMonitor</span>
        </div>
        <nav class="nav-links">
          <a href="#features">功能</a>
          <a href="#ai-power">AI能力</a>
          <router-link to="/pricing">价格</router-link>
        </nav>
        <div class="nav-actions">
          <router-link to="/login" class="btn-ghost">登录</router-link>
          <router-link to="/register" class="btn-primary">免费开始使用</router-link>
        </div>
      </div>
    </header>

    <section class="hero">
      <div class="hero-inner">
        <div class="hero-badge">🚀 AI驱动的选品决策系统</div>
        <h1 class="hero-title">
          多源数据采集 + AI分析<br />
          <span class="gradient-text">爆品预测引擎</span>
        </h1>
        <p class="hero-desc">
          实时监控商品动态，AI智能分析趋势，提前7天发现潜力商品。<br />
          从数据采集到决策建议，一站式选品决策平台。
        </p>
        <div class="hero-actions">
          <router-link to="/register" class="btn-primary btn-lg">免费开始使用</router-link>
          <router-link to="/pricing" class="btn-outline btn-lg">查看价格方案</router-link>
        </div>
        <div class="hero-stats">
          <div class="stat-item">
            <div class="stat-num">10,000+</div>
            <div class="stat-label">监控商品</div>
          </div>
          <div class="stat-item">
            <div class="stat-num">85%</div>
            <div class="stat-label">爆品预测准确率</div>
          </div>
          <div class="stat-item">
            <div class="stat-num">7天</div>
            <div class="stat-label">提前发现潜力商品</div>
          </div>
        </div>
      </div>
    </section>

    <section id="ai-power" class="section ai-section">
      <div class="section-inner">
        <div class="section-header">
          <h2>🤖 AI核心能力</h2>
          <p>从数据到决策，AI帮你完成最关键的判断</p>
        </div>
        <div class="ai-grid">
          <div class="ai-card">
            <div class="ai-icon">🔮</div>
            <h3>爆品预测模型</h3>
            <p>提前7天发现潜力商品，基于多维数据建模预测商品爆发趋势</p>
            <div class="ai-tier">Premium</div>
          </div>
          <div class="ai-card">
            <div class="ai-icon">📊</div>
            <h3>多维评分系统</h3>
            <p>流量/增长/竞争三维评估，量化每个商品的潜力值</p>
            <div class="ai-tier">Pro</div>
          </div>
          <div class="ai-card">
            <div class="ai-icon">📈</div>
            <h3>趋势分析</h3>
            <p>实时追踪市场变化，7天/30天趋势对比分析</p>
            <div class="ai-tier">Pro</div>
          </div>
          <div class="ai-card">
            <div class="ai-icon">⚠️</div>
            <h3>风险预警</h3>
            <p>自动识别异常波动，价格/销量/评分风险实时预警</p>
            <div class="ai-tier">Premium</div>
          </div>
        </div>
      </div>
    </section>

    <section id="features" class="section features-section">
      <div class="section-inner">
        <div class="section-header">
          <h2>🧩 核心功能</h2>
          <p>从采集到分析，覆盖选品全链路</p>
        </div>
        <div class="features-list">
          <div class="feature-item">
            <div class="feature-num">01</div>
            <div class="feature-content">
              <h3>商品监控</h3>
              <p>添加关注的商品，实时追踪价格、销量、评价等关键指标变化。支持小红书、淘宝、京东等多平台。</p>
            </div>
          </div>
          <div class="feature-item">
            <div class="feature-num">02</div>
            <div class="feature-content">
              <h3>定时采集</h3>
              <p>自动定时获取最新数据，无需手动刷新。支持5分钟到自定义间隔的灵活配置。</p>
            </div>
          </div>
          <div class="feature-item">
            <div class="feature-num">03</div>
            <div class="feature-content">
              <h3>AI智能分析</h3>
              <p>基于采集数据，AI自动生成趋势评分、爆品预测、风险预警等决策建议。</p>
            </div>
          </div>
          <div class="feature-item">
            <div class="feature-num">04</div>
            <div class="feature-content">
              <h3>数据看板</h3>
              <p>可视化展示监控数据、趋势图表、AI评分，一目了然掌握商品动态。</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="section cta-section">
      <div class="section-inner">
        <div class="cta-content">
          <h2>开始你的智能选品之旅</h2>
          <p>免费监控3个商品，体验AI趋势分析能力</p>
          <div class="cta-actions">
            <router-link to="/register" class="btn-primary btn-lg">免费注册</router-link>
            <router-link to="/pricing" class="btn-outline btn-lg">对比方案</router-link>
          </div>
        </div>
      </div>
    </section>

    <footer class="footer">
      <div class="footer-inner">
        <div class="footer-brand">
          <span class="logo-icon">◆</span> VueMonitor
        </div>
        <div class="footer-links">
          <router-link to="/pricing">价格方案</router-link>
          <a href="#">服务条款</a>
          <a href="#">隐私政策</a>
          <a href="#">联系我们</a>
        </div>
        <div class="footer-copy">© 2026 VueMonitor. All rights reserved.</div>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import { useAuthStore } from "../stores/auth";

const auth = useAuthStore();

onMounted(() => {
  auth.initFromStorage();
});
</script>

<style scoped>
.landing {
  min-height: 100vh;
  background: #0a0a0f;
  color: #e0e0e6;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

.nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  background: rgba(10, 10, 15, 0.85);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.nav-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 20px;
  font-weight: 700;
  color: #fff;
}

.logo-icon {
  color: #6366f1;
  font-size: 24px;
}

.nav-links {
  display: flex;
  gap: 32px;
}

.nav-links a {
  color: #a0a0b0;
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
  color: #a0a0b0;
  text-decoration: none;
  font-size: 14px;
  padding: 8px 16px;
  border-radius: 8px;
  transition: all 0.2s;
}

.btn-ghost:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.06);
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  text-decoration: none;
  font-size: 14px;
  font-weight: 600;
  padding: 8px 20px;
  border-radius: 8px;
  transition: all 0.3s;
  border: none;
  cursor: pointer;
}

.btn-primary:hover {
  background: linear-gradient(135deg, #7c7ff7, #9d6ffa);
  transform: translateY(-1px);
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.3);
}

.btn-outline {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: #a0a0b0;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  padding: 8px 20px;
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  transition: all 0.3s;
  cursor: pointer;
}

.btn-outline:hover {
  color: #fff;
  border-color: rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.04);
}

.btn-lg {
  padding: 12px 28px;
  font-size: 16px;
  border-radius: 10px;
}

.hero {
  padding: 160px 24px 80px;
  text-align: center;
}

.hero-inner {
  max-width: 800px;
  margin: 0 auto;
}

.hero-badge {
  display: inline-block;
  background: rgba(99, 102, 241, 0.12);
  color: #a5b4fc;
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 24px;
  border: 1px solid rgba(99, 102, 241, 0.2);
}

.hero-title {
  font-size: 52px;
  font-weight: 800;
  line-height: 1.2;
  margin: 0 0 24px;
  color: #fff;
  letter-spacing: -1px;
}

.gradient-text {
  background: linear-gradient(135deg, #6366f1, #a78bfa, #f472b6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-desc {
  font-size: 18px;
  line-height: 1.7;
  color: #8a8a9a;
  margin: 0 0 40px;
}

.hero-actions {
  display: flex;
  gap: 16px;
  justify-content: center;
  margin-bottom: 60px;
}

.hero-stats {
  display: flex;
  gap: 48px;
  justify-content: center;
  padding-top: 40px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.stat-item {
  text-align: center;
}

.stat-num {
  font-size: 32px;
  font-weight: 800;
  color: #fff;
}

.stat-label {
  font-size: 13px;
  color: #6a6a7a;
  margin-top: 4px;
}

.section {
  padding: 80px 24px;
}

.section-inner {
  max-width: 1100px;
  margin: 0 auto;
}

.section-header {
  text-align: center;
  margin-bottom: 56px;
}

.section-header h2 {
  font-size: 36px;
  font-weight: 700;
  color: #fff;
  margin: 0 0 12px;
}

.section-header p {
  font-size: 16px;
  color: #6a6a7a;
  margin: 0;
}

.ai-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.ai-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 16px;
  padding: 32px;
  transition: all 0.3s;
  position: relative;
}

.ai-card:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(99, 102, 241, 0.3);
  transform: translateY(-2px);
}

.ai-icon {
  font-size: 36px;
  margin-bottom: 16px;
}

.ai-card h3 {
  font-size: 20px;
  font-weight: 600;
  color: #fff;
  margin: 0 0 8px;
}

.ai-card p {
  font-size: 14px;
  color: #8a8a9a;
  line-height: 1.6;
  margin: 0;
}

.ai-tier {
  position: absolute;
  top: 16px;
  right: 16px;
  background: rgba(99, 102, 241, 0.15);
  color: #a5b4fc;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
  font-weight: 600;
}

.features-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.feature-item {
  display: flex;
  gap: 24px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  padding: 32px;
  transition: all 0.3s;
}

.feature-item:hover {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 255, 255, 0.1);
}

.feature-num {
  font-size: 48px;
  font-weight: 800;
  color: rgba(99, 102, 241, 0.3);
  line-height: 1;
  min-width: 80px;
}

.feature-content h3 {
  font-size: 20px;
  font-weight: 600;
  color: #fff;
  margin: 0 0 8px;
}

.feature-content p {
  font-size: 14px;
  color: #8a8a9a;
  line-height: 1.7;
  margin: 0;
}

.cta-section {
  background: linear-gradient(180deg, transparent, rgba(99, 102, 241, 0.06));
}

.cta-content {
  text-align: center;
  padding: 60px 0;
}

.cta-content h2 {
  font-size: 36px;
  font-weight: 700;
  color: #fff;
  margin: 0 0 12px;
}

.cta-content p {
  font-size: 16px;
  color: #8a8a9a;
  margin: 0 0 32px;
}

.cta-actions {
  display: flex;
  gap: 16px;
  justify-content: center;
}

.footer {
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  padding: 40px 24px;
}

.footer-inner {
  max-width: 1100px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.footer-brand {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  display: flex;
  align-items: center;
  gap: 6px;
}

.footer-links {
  display: flex;
  gap: 24px;
}

.footer-links a {
  color: #6a6a7a;
  text-decoration: none;
  font-size: 13px;
  transition: color 0.2s;
}

.footer-links a:hover {
  color: #a0a0b0;
}

.footer-copy {
  font-size: 12px;
  color: #4a4a5a;
}

@media (max-width: 768px) {
  .hero-title {
    font-size: 32px;
  }
  .ai-grid {
    grid-template-columns: 1fr;
  }
  .hero-stats {
    flex-direction: column;
    gap: 24px;
  }
  .hero-actions {
    flex-direction: column;
    align-items: center;
  }
  .footer-inner {
    flex-direction: column;
    gap: 16px;
  }
  .feature-item {
    flex-direction: column;
    gap: 12px;
  }
}
</style>
