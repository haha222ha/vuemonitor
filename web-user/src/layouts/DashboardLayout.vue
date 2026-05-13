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
          <span>{{ t('nav.dashboard') }}</span>
        </el-menu-item>
        <el-menu-item index="/dashboard/monitor">
          <el-icon><View /></el-icon>
          <span>{{ t('nav.products') }}</span>
        </el-menu-item>
        <el-menu-item index="/dashboard/collect">
          <el-icon><Upload /></el-icon>
          <span>{{ t('nav.monitor') }}</span>
        </el-menu-item>
        <el-sub-menu index="/dashboard/ai-group">
          <template #title>
            <el-icon><MagicStick /></el-icon>
            <span>{{ t('nav.ai') }}</span>
          </template>
          <el-menu-item index="/dashboard/ai">AI分析</el-menu-item>
          <el-menu-item index="/dashboard/ai/reports">分析报告</el-menu-item>
        </el-sub-menu>
        <el-menu-item index="/dashboard/team">
          <el-icon><User /></el-icon>
          <span>{{ t('nav.team') }}</span>
        </el-menu-item>
        <el-menu-item index="/dashboard/notifications">
          <el-icon><Bell /></el-icon>
          <span>{{ t('nav.notifications') }}</span>
          <el-badge v-if="unreadCount > 0" :value="unreadCount" :max="99" class="nav-badge" />
        </el-menu-item>
        <el-menu-item index="/dashboard/settings">
          <el-icon><Setting /></el-icon>
          <span>{{ t('nav.settings') }}</span>
        </el-menu-item>
        <el-menu-item v-if="isAdmin" index="/dashboard/admin/monitor">
          <el-icon><DataAnalysis /></el-icon>
          <span>系统监控</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="topbar">
        <div class="topbar-left">
          <h3>{{ pageTitle }}</h3>
        </div>
        <div class="topbar-right">
          <el-badge :value="unreadCount" :hidden="unreadCount === 0" :max="99" class="notification-badge">
            <el-button :icon="Bell" circle size="small" @click="showNotifications = true" />
          </el-badge>
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

    <el-drawer v-model="showNotifications" title="通知中心" direction="rtl" size="380px" :append-to-body="true">
      <div class="notification-drawer">
        <div class="notification-toolbar">
          <el-button v-if="unreadCount > 0" link type="primary" size="small" @click="markAllRead">全部已读</el-button>
        </div>
        <div v-if="notifications.length === 0" class="notification-empty">
          <p>暂无通知</p>
        </div>
        <div v-else class="notification-list">
          <div
            v-for="n in notifications"
            :key="n.id"
            :class="['notification-item', { 'is-unread': !n.is_read }]"
            @click="handleNotificationClick(n)"
          >
            <div class="notification-dot" v-if="!n.is_read"></div>
            <div class="notification-body">
              <div class="notification-title">{{ n.title }}</div>
              <div class="notification-content">{{ n.content }}</div>
              <div class="notification-time">{{ timeAgo(n.created_at) }}</div>
            </div>
          </div>
        </div>
        <div v-if="notificationTotal > notifications.length" class="notification-more">
          <el-button link type="primary" @click="loadMoreNotifications">加载更多</el-button>
        </div>
      </div>
    </el-drawer>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { useWebSocket } from "../composables/useWebSocket";
import { Monitor, View, Upload, MagicStick, Setting, Bell, User, DataAnalysis } from "@element-plus/icons-vue";
import api from "../utils/api";
import { useI18n } from "../i18n";

const { t } = useI18n();

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();

const showNotifications = ref(false);
const notifications = ref<any[]>([]);
const notificationTotal = ref(0);
const unreadCount = ref(0);
let pollTimer: ReturnType<typeof setInterval> | null = null;

const { on: wsOn, off: wsOff, connect: wsConnect } = useWebSocket();

const activeMenu = computed(() => route.path);
const pageTitle = computed(() => {
  const map: Record<string, string> = {
    "/dashboard": "数据总览",
    "/dashboard/monitor": "商品监控",
    "/dashboard/collect": "采集中心",
    "/dashboard/ai": "AI分析",
    "/dashboard/team": "团队协作",
    "/dashboard/notifications": "通知中心",
    "/dashboard/settings": "设置",
    "/dashboard/admin/monitor": "系统监控",
  };
  return map[route.path] || "Dashboard";
});

const planTagType = computed(() => {
  const map: Record<string, string> = { pro: "primary", premium: "warning", enterprise: "danger" };
  return (map[auth.userPlan] || "info") as any;
});

const isAdmin = computed(() => auth.user?.role === "admin");

function handleCommand(cmd: string) {
  if (cmd === "logout") {
    auth.logout();
    router.push("/login");
  } else if (cmd === "settings") {
    router.push("/dashboard/settings");
  }
}

async function fetchUnreadCount() {
  try {
    const { data } = await api.get("/notifications/unread-count");
    unreadCount.value = data?.data?.unread_count || 0;
  } catch {}
}

async function fetchNotifications() {
  try {
    const { data } = await api.get("/notifications", { params: { page_size: 20 } });
    notifications.value = data?.data?.items || [];
    notificationTotal.value = data?.data?.total || 0;
  } catch {}
}

async function loadMoreNotifications() {
  try {
    const page = Math.floor(notifications.value.length / 20) + 1;
    const { data } = await api.get("/notifications", { params: { page, page_size: 20 } });
    const newItems = data?.data?.items || [];
    notifications.value = [...notifications.value, ...newItems];
  } catch {}
}

async function markAllRead() {
  try {
    await api.put("/notifications/read-all");
    unreadCount.value = 0;
    notifications.value.forEach((n) => (n.is_read = true));
  } catch {}
}

async function handleNotificationClick(n: any) {
  if (!n.is_read) {
    try {
      await api.put(`/notifications/${n.id}/read`);
      n.is_read = true;
      unreadCount.value = Math.max(0, unreadCount.value - 1);
    } catch {}
  }
  if (n.related_type === "product" && n.related_id) {
    showNotifications.value = false;
    router.push("/dashboard/monitor");
  }
}

function timeAgo(dateStr: string) {
  if (!dateStr) return "";
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = Math.max(0, now - then);
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes}分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}小时前`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}天前`;
  return new Date(dateStr).toLocaleDateString();
}

function onWsNotification(data: any) {
  fetchUnreadCount();
  if (showNotifications.value) {
    fetchNotifications();
  }
}

onMounted(() => {
  if (!auth.user) {
    auth.fetchUser();
  }
  fetchUnreadCount();
  wsConnect();
  wsOn("monitor:triggered", onWsNotification);
  wsOn("notification:new", onWsNotification);
  pollTimer = setInterval(fetchUnreadCount, 60000);
});

onUnmounted(() => {
  wsOff("monitor:triggered", onWsNotification);
  wsOff("notification:new", onWsNotification);
  if (pollTimer) clearInterval(pollTimer);
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
  gap: 16px;
}

.notification-badge {
  line-height: 1;
}

.notification-badge :deep(.el-badge__content) {
  background: #ef4444;
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

.notification-drawer {
  padding: 0;
}

.notification-toolbar {
  display: flex;
  justify-content: flex-end;
  padding: 0 0 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  margin-bottom: 12px;
}

.notification-empty {
  text-align: center;
  padding: 40px 0;
  color: #6a6a7a;
}

.notification-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.notification-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
}

.notification-item:hover {
  background: rgba(255, 255, 255, 0.04);
}

.notification-item.is-unread {
  background: rgba(99, 102, 241, 0.06);
}

.notification-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #6366f1;
  flex-shrink: 0;
  margin-top: 6px;
}

.notification-body {
  flex: 1;
  min-width: 0;
}

.notification-title {
  font-size: 14px;
  font-weight: 500;
  color: #e0e0e6;
  margin-bottom: 4px;
}

.notification-content {
  font-size: 13px;
  color: #8a8a9a;
  line-height: 1.5;
  word-break: break-all;
}

.notification-time {
  font-size: 12px;
  color: #5a5a6a;
  margin-top: 4px;
}

.notification-more {
  text-align: center;
  padding: 12px 0;
}

.nav-badge {
  margin-left: 6px;
}

.nav-badge :deep(.el-badge__content) {
  background: #ef4444;
}
</style>
