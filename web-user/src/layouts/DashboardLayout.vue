<template>
  <el-container class="dashboard-layout">
    <el-aside width="240px" class="sidebar">
      <div class="sidebar-logo">
        <span class="logo-icon">◆</span>
        <span class="logo-text">XHS365</span>
        <el-tag v-if="auth.userPlan !== 'free'" size="small" :type="planTagType" class="plan-tag">{{ auth.userPlan.toUpperCase() }}</el-tag>
      </div>
      <el-menu :default-active="activeMenu" router class="sidebar-menu">
        <el-menu-item index="/dashboard">
          <el-icon><Monitor /></el-icon>
          <span>数据总览</span>
        </el-menu-item>
        <el-menu-item index="/dashboard/monitor">
          <el-icon><View /></el-icon>
          <span>商品监控</span>
        </el-menu-item>
        <el-menu-item index="/dashboard/collect">
          <el-icon><Upload /></el-icon>
          <span>采集中心</span>
        </el-menu-item>
        <el-menu-item index="/dashboard/ai">
          <el-icon><MagicStick /></el-icon>
          <span>AI分析</span>
        </el-menu-item>
        <el-menu-item index="/dashboard/settings">
          <el-icon><Setting /></el-icon>
          <span>设置</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="topbar">
        <div class="topbar-left">
          <h3>{{ pageTitle }}</h3>
        </div>
        <div class="topbar-right">
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="32">{{ auth.user?.nickname?.[0] || "U" }}</el-avatar>
              <span class="user-name">{{ auth.user?.nickname || auth.user?.email || "用户" }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="settings">设置</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { Monitor, View, Upload, MagicStick, Setting } from "@element-plus/icons-vue";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const activeMenu = computed(() => route.path);
const pageTitle = computed(() => {
  const map: Record<string, string> = {
    "/dashboard": "数据总览",
    "/dashboard/monitor": "商品监控",
    "/dashboard/collect": "采集中心",
    "/dashboard/ai": "AI分析",
    "/dashboard/settings": "设置",
  };
  return map[route.path] || "Dashboard";
});

const planTagType = computed(() => {
  const map: Record<string, string> = { pro: "primary", premium: "warning", enterprise: "danger" };
  return (map[auth.userPlan] || "info") as any;
});

function handleCommand(cmd: string) {
  if (cmd === "logout") {
    auth.logout();
    router.push("/login");
  } else if (cmd === "settings") {
    router.push("/dashboard/settings");
  }
}

onMounted(() => {
  if (!auth.user) {
    auth.fetchUser();
  }
});
</script>

<style scoped>
.dashboard-layout {
  height: 100vh;
  background: #0f0f14;
}

.sidebar {
  background: #13131a;
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  overflow-y: auto;
}

.sidebar-logo {
  height: 64px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  gap: 8px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.logo-icon {
  color: #6366f1;
  font-size: 22px;
}

.logo-text {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
}

.plan-tag {
  margin-left: auto;
}

.sidebar-menu {
  border-right: none;
  background: transparent;
}

.sidebar-menu .el-menu-item {
  color: #8a8a9a;
  height: 48px;
  line-height: 48px;
}

.sidebar-menu .el-menu-item:hover {
  background: rgba(255, 255, 255, 0.04);
  color: #e0e0e6;
}

.sidebar-menu .el-menu-item.is-active {
  background: rgba(99, 102, 241, 0.12);
  color: #a5b4fc;
}

.topbar {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  background: #13131a;
  padding: 0 24px;
}

.topbar-left h3 {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  margin: 0;
}

.topbar-right {
  display: flex;
  align-items: center;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.user-name {
  color: #e0e0e6;
  font-size: 14px;
}

.main-content {
  background: #0f0f14;
  color: #e0e0e6;
  overflow-y: auto;
}
</style>
