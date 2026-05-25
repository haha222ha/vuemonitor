<template>
  <div class="purchase-page">
    <header class="nav">
      <div class="nav-inner">
        <router-link to="/" class="logo">
          <span class="logo-icon">◆</span>
          <span class="logo-text">XHS365</span>
        </router-link>
        <div class="nav-actions">
          <router-link to="/pricing" class="btn-ghost">价格方案</router-link>
          <router-link to="/login" class="btn-ghost">登录</router-link>
        </div>
      </div>
    </header>

    <main class="main">
      <h1>购买与激活授权码</h1>
      <p class="lead">无需在线支付。联系 QQ 客服付款后，我们将发送授权码，您在设置页激活即可升级套餐。</p>

      <ol class="steps">
        <li>
          <strong>注册并登录</strong>
          <span>打开 <router-link to="/register">免费注册</router-link>，使用用户名 + 密码登录。</span>
        </li>
        <li>
          <strong>联系 QQ 客服下单</strong>
          <span>说明需要的套餐（Pro / Premium / Enterprise）与时长，完成付款。</span>
        </li>
        <li>
          <strong>收到授权码</strong>
          <span>客服通过 QQ 发送一串授权码（请妥善保存）。</span>
        </li>
        <li>
          <strong>在设置页激活</strong>
          <span>
            登录后进入
            <router-link to="/dashboard/settings">设置 → 授权码激活</router-link>
            ，粘贴授权码并点击激活。
          </span>
        </li>
        <li>
          <strong>立即生效</strong>
          <span>激活成功后套餐权益即时生效，可返回监控/AI 等功能使用。</span>
        </li>
      </ol>

      <section class="plans-ref">
        <h2>参考价格（以客服报价为准）</h2>
        <ul>
          <li><b>Pro</b> — ¥49/月 · 50 商品监控 · AI 趋势评分等</li>
          <li><b>Premium</b> — ¥149/月 · 500 商品 · 爆品预测 / 风险预警等</li>
          <li><b>Enterprise</b> — 定制 · 私有化 / API / 团队协作</li>
        </ul>
        <router-link to="/pricing" class="link-more">查看完整功能对比 →</router-link>
      </section>

      <section class="contact-box">
        <h2>联系客服</h2>
        <SupportQqPanel />
      </section>

      <div class="cta-row">
        <router-link to="/dashboard/settings" class="btn-primary">我已有机码，去激活</router-link>
        <router-link to="/register" class="btn-outline">先免费注册</router-link>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import SupportQqPanel from "../components/SupportQqPanel.vue";
</script>

<style scoped>
.purchase-page {
  min-height: 100vh;
  background: #0a0a0f;
  color: #e0e0e6;
}
.nav {
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.nav-inner {
  max-width: 960px;
  margin: 0 auto;
  padding: 16px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  color: #fff;
  font-weight: 700;
}
.logo-icon {
  color: #ff2442;
}
.nav-actions {
  display: flex;
  gap: 12px;
}
.btn-ghost {
  color: rgba(255, 255, 255, 0.75);
  text-decoration: none;
  font-size: 14px;
}
.main {
  max-width: 640px;
  margin: 0 auto;
  padding: 40px 24px 64px;
}
h1 {
  margin: 0 0 12px;
  font-size: 28px;
}
.lead {
  margin: 0 0 28px;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.7);
}
.steps {
  margin: 0 0 32px;
  padding-left: 20px;
  line-height: 1.7;
}
.steps li {
  margin-bottom: 16px;
}
.steps strong {
  display: block;
  color: #fff;
  margin-bottom: 4px;
}
.steps span {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.65);
}
.steps a {
  color: #818cf8;
}
.plans-ref {
  margin-bottom: 28px;
  padding: 16px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
}
.plans-ref h2 {
  margin: 0 0 12px;
  font-size: 16px;
}
.plans-ref ul {
  margin: 0;
  padding-left: 18px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.75);
}
.link-more {
  display: inline-block;
  margin-top: 12px;
  font-size: 13px;
  color: #818cf8;
  text-decoration: none;
}
.contact-box h2 {
  margin: 0 0 12px;
  font-size: 16px;
  text-align: center;
}
.cta-row {
  margin-top: 24px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  justify-content: center;
}
.btn-primary,
.btn-outline {
  padding: 10px 20px;
  border-radius: 8px;
  font-size: 14px;
  text-decoration: none;
}
.btn-primary {
  background: #ff2442;
  color: #fff;
}
.btn-outline {
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #fff;
}
</style>
