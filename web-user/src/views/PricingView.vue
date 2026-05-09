<template>
  <div class="pricing-page">
    <header class="nav">
      <div class="nav-inner">
        <div class="logo">
          <span class="logo-icon">◆</span>
          <span class="logo-text">VueMonitor</span>
        </div>
        <div class="nav-actions">
          <router-link to="/login" class="btn-ghost">登录</router-link>
          <router-link to="/register" class="btn-primary">免费开始</router-link>
        </div>
      </div>
    </header>

    <section class="pricing-hero">
      <h1>选择适合你的方案</h1>
      <p>从免费监控到AI决策，按需升级</p>
    </section>

    <section class="pricing-grid">
      <div class="plan-card">
        <div class="plan-badge free">免费版</div>
        <div class="plan-price">
          <span class="price-amount">¥0</span>
          <span class="price-period">/月</span>
        </div>
        <p class="plan-desc">体验基础监控能力，感知产品价值</p>
        <ul class="plan-features">
          <li>✓ 监控 3 个商品</li>
          <li>✓ 基础趋势描述</li>
          <li>✓ 手动采集刷新</li>
          <li>✓ 数据看板</li>
          <li class="disabled">✗ 定时自动采集</li>
          <li class="disabled">✗ AI趋势评分</li>
          <li class="disabled">✗ 爆品预测</li>
          <li class="disabled">✗ 数据导出</li>
        </ul>
        <router-link to="/register" class="btn-outline btn-full">免费开始</router-link>
      </div>

      <div class="plan-card featured">
        <div class="plan-popular">最受欢迎</div>
        <div class="plan-badge pro">Pro</div>
        <div class="plan-price">
          <span class="price-amount">¥49</span>
          <span class="price-period">/月</span>
        </div>
        <p class="plan-desc">建立使用依赖，AI辅助决策</p>
        <ul class="plan-features">
          <li>✓ 监控 50 个商品</li>
          <li>✓ AI趋势评分 ★★★★☆</li>
          <li>✓ 定时自动采集</li>
          <li>✓ 历史数据对比</li>
          <li>✓ 数据导出</li>
          <li>✓ 云端备份</li>
          <li class="disabled">✗ 爆品预测</li>
          <li class="disabled">✗ 风险预警</li>
        </ul>
        <router-link to="/register" class="btn-primary btn-full">升级 Pro</router-link>
      </div>

      <div class="plan-card">
        <div class="plan-badge premium">Premium</div>
        <div class="plan-price">
          <span class="price-amount">¥149</span>
          <span class="price-period">/月</span>
        </div>
        <p class="plan-desc">完整AI决策能力，选品利器</p>
        <ul class="plan-features">
          <li>✓ 无限监控商品</li>
          <li>✓ 爆品概率预测</li>
          <li>✓ 多维评分模型</li>
          <li>✓ 风险预警</li>
          <li>✓ 批量AI分析</li>
          <li>✓ 完整决策看板</li>
          <li>✓ 7天/30天趋势预测</li>
          <li>✓ 优先客服支持</li>
        </ul>
        <router-link to="/register" class="btn-outline btn-full">升级 Premium</router-link>
      </div>

      <div class="plan-card">
        <div class="plan-badge enterprise">Enterprise</div>
        <div class="plan-price">
          <span class="price-amount">定制</span>
        </div>
        <p class="plan-desc">企业级私有部署与定制AI模型</p>
        <ul class="plan-features">
          <li>✓ Premium全部功能</li>
          <li>✓ API开放接口</li>
          <li>✓ 私有化部署</li>
          <li>✓ 自定义AI模型</li>
          <li>✓ 团队协作管理</li>
          <li>✓ 专属客户经理</li>
          <li>✓ SLA保障</li>
          <li>✓ 定制化开发</li>
        </ul>
        <a href="#" class="btn-outline btn-full">联系我们</a>
      </div>
    </section>

    <footer class="footer">
      <div class="footer-inner">
        <div class="footer-brand"><span class="logo-icon">◆</span> VueMonitor</div>
        <div class="footer-copy">© 2026 VueMonitor. All rights reserved.</div>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.pricing-page {
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

.logo-icon { color: #6366f1; font-size: 24px; }

.nav-actions { display: flex; gap: 12px; align-items: center; }

.btn-ghost {
  color: #a0a0b0;
  text-decoration: none;
  font-size: 14px;
  padding: 8px 16px;
  border-radius: 8px;
  transition: all 0.2s;
}

.btn-ghost:hover { color: #fff; background: rgba(255, 255, 255, 0.06); }

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

.btn-outline:hover { color: #fff; border-color: rgba(255, 255, 255, 0.3); background: rgba(255, 255, 255, 0.04); }

.btn-full { width: 100%; justify-content: center; padding: 12px; font-size: 15px; }

.pricing-hero {
  text-align: center;
  padding: 120px 24px 48px;
}

.pricing-hero h1 {
  font-size: 40px;
  font-weight: 700;
  color: #fff;
  margin: 0 0 12px;
}

.pricing-hero p {
  font-size: 16px;
  color: #6a6a7a;
  margin: 0;
}

.pricing-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px 80px;
}

.plan-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 16px;
  padding: 32px 24px;
  position: relative;
  transition: all 0.3s;
}

.plan-card:hover {
  background: rgba(255, 255, 255, 0.05);
  transform: translateY(-2px);
}

.plan-card.featured {
  background: rgba(99, 102, 241, 0.08);
  border-color: rgba(99, 102, 241, 0.3);
}

.plan-popular {
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
  padding: 4px 16px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.plan-badge {
  display: inline-block;
  padding: 2px 12px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 16px;
}

.plan-badge.free { background: rgba(255, 255, 255, 0.08); color: #a0a0b0; }
.plan-badge.pro { background: rgba(99, 102, 241, 0.15); color: #a5b4fc; }
.plan-badge.premium { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
.plan-badge.enterprise { background: rgba(168, 85, 247, 0.15); color: #c084fc; }

.plan-price {
  margin-bottom: 8px;
}

.price-amount {
  font-size: 36px;
  font-weight: 800;
  color: #fff;
}

.price-period {
  font-size: 14px;
  color: #6a6a7a;
}

.plan-desc {
  font-size: 13px;
  color: #6a6a7a;
  margin: 0 0 24px;
}

.plan-features {
  list-style: none;
  padding: 0;
  margin: 0 0 24px;
}

.plan-features li {
  font-size: 14px;
  padding: 6px 0;
  color: #c0c0cc;
}

.plan-features li.disabled {
  color: #4a4a5a;
}

.footer {
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  padding: 32px 24px;
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

.footer-copy { font-size: 12px; color: #4a4a5a; }

@media (max-width: 900px) {
  .pricing-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 560px) {
  .pricing-grid {
    grid-template-columns: 1fr;
  }
}
</style>
