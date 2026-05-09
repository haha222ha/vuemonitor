<template>
  <el-container class="admin-layout">
    <el-aside width="220px" class="sidebar">
      <div class="logo"><h2>VM Admin</h2></div>
      <el-menu :default-active="route.path" router>
        <el-menu-item index="/admin/dashboard">仪表盘</el-menu-item>
        <el-menu-item index="/admin/users">用户管理</el-menu-item>
        <el-menu-item index="/admin/licenses">授权码管理</el-menu-item>
        <el-menu-item index="/admin/collect">采集管理</el-menu-item>
        <el-menu-item index="/admin/proxies">代理池管理</el-menu-item>
        <el-menu-item index="/admin/risk-events">风控事件</el-menu-item>
        <el-menu-item index="/admin/audit-logs">操作日志</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <el-button text @click="logout">退出</el-button>
      </el-header>
      <el-main><router-view /></el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { useRoute, useRouter } from "vue-router";
const route = useRoute();
const router = useRouter();
function logout() {
  localStorage.removeItem("admin_token");
  router.push("/admin/login");
}
</script>

<style scoped>
.admin-layout { height: 100vh; }
.sidebar { background: #1d1e1f; color: #fff; }
.logo { height: 60px; display: flex; align-items: center; justify-content: center; color: #fff; }
.logo h2 { margin: 0; }
.header { display: flex; align-items: center; justify-content: flex-end; border-bottom: 1px solid #e6e6e6; }
</style>
