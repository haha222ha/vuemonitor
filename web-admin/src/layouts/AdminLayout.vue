<template>
  <el-container class="admin-layout">
    <el-aside width="220px" class="sidebar">
      <div class="logo"><h2>VM Admin</h2></div>
      <el-menu :default-active="route.path" router>
        <el-menu-item index="/dashboard">仪表盘</el-menu-item>
        <el-menu-item index="/users">用户管理</el-menu-item>
        <el-menu-item index="/licenses">授权码管理</el-menu-item>
        <el-menu-item index="/collect">采集管理</el-menu-item>
        <el-menu-item index="/proxies">代理池管理</el-menu-item>
        <el-menu-item index="/risk-events">风控事件</el-menu-item>
        <el-menu-item index="/audit-logs">操作日志</el-menu-item>
        <el-menu-item index="/system-monitor">系统监控</el-menu-item>
        <el-menu-item index="/alert-config">告警配置</el-menu-item>
        <el-menu-item index="/security-audit">安全审计</el-menu-item>
        <el-menu-item index="/gdpr">数据合规</el-menu-item>
        <el-menu-item index="/benchmarks">基准测试</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <span class="admin-info">
          <span class="username">{{ adminUsername }}</span>
          <span class="divider">|</span>
          <span class="current-time">{{ currentTime }}</span>
        </span>
        <el-button text @click="logout">退出</el-button>
      </el-header>
      <el-main><router-view /></el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from "vue-router";
import { ref, onUnmounted } from "vue";
const route = useRoute();
const router = useRouter();
const adminUsername = ref(localStorage.getItem("admin_username") || "管理员");
const currentTime = ref(new Date().toLocaleTimeString());
const timer = setInterval(() => {
  currentTime.value = new Date().toLocaleTimeString();
}, 60000);
onUnmounted(() => clearInterval(timer));
function logout() {
  localStorage.removeItem("admin_token");
  router.push("/login");
}
</script>

<style scoped>
.admin-layout { height: 100vh; }
.sidebar { background: #1d1e1f; color: #fff; }
.logo { height: 60px; display: flex; align-items: center; justify-content: center; color: #fff; }
.logo h2 { margin: 0; }
.header { display: flex; align-items: center; justify-content: flex-end; border-bottom: 1px solid #e6e6e6; }
.admin-info { display: flex; align-items: center; margin-right: 20px; font-size: 14px; }
.divider { margin: 0 8px; color: #999; }
</style>
