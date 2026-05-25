<template>
  <div class="legal-page">
    <header class="top">
      <router-link to="/" class="logo">◆ XHS365</router-link>
      <router-link to="/purchase" class="link">购买与激活</router-link>
    </header>
    <main>
      <h1>常见问题</h1>
      <section v-for="item in items" :key="item.q">
        <h3>{{ item.q }}</h3>
        <p v-html="item.a" />
      </section>
      <SupportQqPanel compact />
    </main>
  </div>
</template>

<script setup lang="ts">
import SupportQqPanel from "../components/SupportQqPanel.vue";

const items = [
  {
    q: "如何购买 Pro / Premium？",
    a: '无需在线支付。打开 <a href="/purchase">购买教程</a>，联系 QQ 客服付款后获取授权码。',
  },
  {
    q: "授权码在哪里激活？",
    a: "登录后进入 <strong>设置 → 授权码激活</strong>，粘贴客服提供的授权码即可。",
  },
  {
    q: "没有收到邮件验证码？",
    a: "当前不依赖邮箱验证。注册用用户名+密码；找回密码请联系 QQ 客服。",
  },
  {
    q: "免费版有什么限制？",
    a: "可免费监控 3 个商品，含基础 AI 次数。升级后监控数量与 AI 能力按套餐提升。",
  },
  {
    q: "Windows 客户端在哪里下载？",
    a: '访问 <a href="/download">下载页</a>。若安装包暂未上传，请联系 QQ 客服获取。',
  },
  {
    q: "授权码激活失败？",
    a: "请检查是否完整复制、是否已使用或过期。仍失败请联系客服并提供您的用户名。",
  },
];
</script>

<style scoped>
.legal-page {
  min-height: 100vh;
  background: #0a0a0f;
  color: #e0e0e6;
  padding: 24px;
}
.top {
  max-width: 720px;
  margin: 0 auto 32px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.logo {
  color: #fff;
  text-decoration: none;
  font-weight: 700;
}
.link {
  color: #818cf8;
  font-size: 14px;
  text-decoration: none;
}
main {
  max-width: 720px;
  margin: 0 auto 48px;
}
h1 {
  margin: 0 0 24px;
  font-size: 26px;
}
section {
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
h3 {
  margin: 0 0 8px;
  font-size: 15px;
  color: #fff;
}
p {
  margin: 0;
  font-size: 14px;
  line-height: 1.65;
  color: rgba(255, 255, 255, 0.7);
}
p :deep(a) {
  color: #818cf8;
}
</style>
