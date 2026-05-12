﻿﻿﻿<template>
  <el-container class="main-layout">
    <el-aside :width="sidebarCollapsed ? '0px' : '220px'" class="sidebar" :class="{ 'sidebar-collapsed': sidebarCollapsed, 'sidebar-mobile': isMobile }">
      <div class="logo">
        <h2>XHS365</h2>
      </div>
      <el-menu :default-active="route.path" router class="sidebar-menu">
        <el-menu-item index="/dashboard">
          <el-icon><Monitor /></el-icon>
          <span>{{ t('nav.dashboard') }}</span>
        </el-menu-item>
        <el-menu-item index="/products">
          <el-icon><Goods /></el-icon>
          <span>{{ t('nav.products') }}</span>
        </el-menu-item>
        <el-menu-item index="/compare">
          <el-icon><DataAnalysis /></el-icon>
          <span>商品对比</span>
        </el-menu-item>
        <el-menu-item index="/scheduler">
          <el-icon><Timer /></el-icon>
          <span>采集调度</span>
        </el-menu-item>
        <el-menu-item index="/monitor">
          <el-icon><Bell /></el-icon>
          <span>{{ t('nav.monitor') }}</span>
        </el-menu-item>
        <el-menu-item index="/notifications">
          <el-icon><ChatDotRound /></el-icon>
          <span>{{ t('nav.notifications') }}</span>
          <el-badge
            v-if="notificationStore.hasUnread"
            :value="notificationStore.unreadCount"
            :max="99"
            class="nav-badge"
          />
        </el-menu-item>
        <el-menu-item index="/ai">
          <el-icon><MagicStick /></el-icon>
          <span>{{ t('nav.ai') }}</span>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <span>{{ t('nav.settings') }}</span>
        </el-menu-item>
        <el-menu-item index="/license">
          <el-icon><Key /></el-icon>
          <span>{{ t('nav.license') }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <div v-if="isMobile && !sidebarCollapsed" class="sidebar-overlay" @click="sidebarCollapsed = true" />
    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-button v-if="isMobile" :icon="Fold" circle size="small" @click="sidebarCollapsed = !sidebarCollapsed" />
        </div>
        <div class="header-right">
          <el-badge :value="notificationStore.unreadCount" :hidden="!notificationStore.hasUnread" :max="99" class="header-badge">
            <el-button :icon="Bell" circle size="small" @click="$router.push('/notifications')" />
          </el-badge>
          <el-dropdown>
            <span class="user-info">{{ authStore.user?.nickname || "用户" }}</span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="$router.push('/settings')">{{ t('nav.settings') }}</el-dropdown-item>
                <el-dropdown-item divided @click="authStore.logout()">{{ t('auth.logout') }}</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
      <div v-if="isMobile" class="mobile-nav">
        <div class="mobile-nav-item" :class="{ active: route.path === '/dashboard' }" @click="$router.push('/dashboard')">
          <el-icon><Monitor /></el-icon>
          <span>{{ t('nav.dashboard') }}</span>
        </div>
        <div class="mobile-nav-item" :class="{ active: route.path === '/products' }" @click="$router.push('/products')">
          <el-icon><Goods /></el-icon>
          <span>{{ t('nav.products') }}</span>
        </div>
        <div class="mobile-nav-item" :class="{ active: route.path === '/monitor' }" @click="$router.push('/monitor')">
          <el-icon><Bell /></el-icon>
          <span>{{ t('nav.monitor') }}</span>
        </div>
        <div class="mobile-nav-item" :class="{ active: route.path === '/ai' }" @click="$router.push('/ai')">
          <el-icon><MagicStick /></el-icon>
          <span>{{ t('nav.ai') }}</span>
        </div>
        <div class="mobile-nav-item" :class="{ active: route.path === '/settings' }" @click="$router.push('/settings')">
          <el-icon><Setting /></el-icon>
          <span>{{ t('nav.settings') }}</span>
        </div>
      </div>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed } from "vue";
import { useRoute } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { useNotificationStore } from "../stores/notification";
import { useI18n } from "../i18n";
import { Monitor, Goods, Bell, MagicStick, Setting, Key, ChatDotRound, Fold } from "@element-plus/icons-vue";

const { t } = useI18n();

const route = useRoute();
const authStore = useAuthStore();
const notificationStore = useNotificationStore();

const windowWidth = ref(window.innerWidth);
const sidebarCollapsed = ref(false);

const isMobile = computed(() => windowWidth.value < 768);

function onResize() {
  windowWidth.value = window.innerWidth;
  if (isMobile.value) {
    sidebarCollapsed.value = true;
  } else {
    sidebarCollapsed.value = false;
  }
}

authStore.fetchUser();

let notifTimer: ReturnType<typeof setInterval> | null = null;

onMounted(() => {
  notificationStore.fetchUnreadCount();
  notifTimer = setInterval(() => {
    notificationStore.fetchUnreadCount();
  }, 60000);
  window.addEventListener("resize", onResize);
  onResize();
});

onUnmounted(() => {
  if (notifTimer) {
    clearInterval(notifTimer);
  }
  window.removeEventListener("resize", onResize);
});
</script>

<style scoped>
.main-layout {
  height: 100vh;
}
.sidebar {
  background: #304156;
  transition: width 0.3s ease;
  overflow: hidden;
}
.sidebar-collapsed {
  overflow: hidden;
}
.sidebar-mobile {
  position: fixed;
  top: 0;
  left: 0;
  height: 100vh;
  z-index: 1000;
}
.sidebar-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 999;
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
  justify-content: space-between;
  border-bottom: 1px solid #e6e6e6;
}
.header-left {
  display: flex;
  align-items: center;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}
.user-info {
  cursor: pointer;
  font-size: 14px;
}
.header-badge {
  line-height: 1;
}
.nav-badge {
  margin-left: 8px;
}
.mobile-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 56px;
  background: #fff;
  border-top: 1px solid #e6e6e6;
  display: flex;
  align-items: center;
  justify-content: space-around;
  z-index: 998;
}
.mobile-nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  font-size: 10px;
  color: #999;
  cursor: pointer;
  padding: 4px 0;
}
.mobile-nav-item.active {
  color: #409eff;
}
.mobile-nav-item .el-icon {
  font-size: 20px;
  margin-bottom: 2px;
}
@media (max-width: 768px) {
  .el-main {
    padding-bottom: 72px !important;
  }
}
</style>
