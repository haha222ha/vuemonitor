<template>
  <el-container class="main-layout">
    <el-aside width="220px" class="sidebar">
      <div class="logo">
        <h2>XHS365</h2>
      </div>
      <el-menu :default-active="route.path" router class="sidebar-menu">
        <el-menu-item index="/dashboard">
          <el-icon><Monitor /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/products">
          <el-icon><Goods /></el-icon>
          <span>商品监控</span>
        </el-menu-item>
        <el-menu-item index="/monitor">
          <el-icon><Bell /></el-icon>
          <span>监控规则</span>
        </el-menu-item>
        <el-menu-item index="/ai">
          <el-icon><MagicStick /></el-icon>
          <span>AI分析</span>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <span>设置</span>
        </el-menu-item>
        <el-menu-item index="/license">
          <el-icon><Key /></el-icon>
          <span>授权管理</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <div class="header-right">
          <el-dropdown>
            <span class="user-info">{{ authStore.user?.nickname || "用户" }}</span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="authStore.logout()">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { useRoute } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { Monitor, Goods, Bell, MagicStick, Setting, Key } from "@element-plus/icons-vue";

const route = useRoute();
const authStore = useAuthStore();
authStore.fetchUser();
</script>

<style scoped>
.main-layout {
  height: 100vh;
}
.sidebar {
  background: #304156;
}
.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}
.logo h2 {
  margin: 0;
  font-size: 20px;
}
.sidebar-menu {
  border-right: none;
}
.header {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  border-bottom: 1px solid #e6e6e6;
}
.user-info {
  cursor: pointer;
  font-size: 14px;
}
</style>
