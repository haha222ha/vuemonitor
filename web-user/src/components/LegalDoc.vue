<template>
  <div class="legal-page">
    <header class="top">
      <router-link to="/" class="logo">◆ XHS365</router-link>
      <div class="links">
        <router-link to="/terms">服务条款</router-link>
        <router-link to="/privacy">隐私政策</router-link>
        <router-link to="/faq">FAQ</router-link>
      </div>
    </header>
    <main>
      <h1>{{ title }}</h1>
      <p class="updated">最后更新：2026-05-25</p>
      <section v-for="s in sections" :key="s.title">
        <h2>{{ s.title }}</h2>
        <p>{{ s.body }}</p>
      </section>
    </main>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string;
  sections: { title: string; body: string }[];
}>();
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
  flex-wrap: wrap;
  gap: 12px;
}
.logo {
  color: #fff;
  text-decoration: none;
  font-weight: 700;
}
.links {
  display: flex;
  gap: 16px;
  font-size: 13px;
}
.links a {
  color: #818cf8;
  text-decoration: none;
}
main {
  max-width: 720px;
  margin: 0 auto 48px;
}
h1 {
  margin: 0 0 8px;
  font-size: 26px;
}
.updated {
  margin: 0 0 28px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.45);
}
section {
  margin-bottom: 20px;
}
h2 {
  margin: 0 0 8px;
  font-size: 16px;
  color: #fff;
}
p {
  margin: 0;
  font-size: 14px;
  line-height: 1.7;
  color: rgba(255, 255, 255, 0.7);
}
</style>
