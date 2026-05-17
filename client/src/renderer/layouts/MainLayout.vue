<template>
  <div class="app-layout">
    <aside :class="['sidebar', { 'sidebar--collapsed': collapsed }]">
      <div class="sidebar__logo" @click="collapsed = !collapsed">
        <div class="sidebar__logo-icon">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
            <rect width="28" height="28" rx="8" fill="url(#logo-gradient)"/>
            <path d="M8 10h12M8 14h8M8 18h10" stroke="#fff" stroke-width="2" stroke-linecap="round"/>
            <defs><linearGradient id="logo-gradient" x1="0" y1="0" x2="28" y2="28"><stop stop-color="#818CF8"/><stop offset="1" stop-color="#4F46E5"/></linearGradient></defs>
          </svg>
        </div>
        <transition name="fade">
          <span v-if="!collapsed" class="sidebar__logo-text">XHS365</span>
        </transition>
      </div>

      <nav class="sidebar__nav">
        <div class="sidebar__group">
          <div v-if="!collapsed" class="sidebar__group-label">洞察</div>
          <router-link
            v-for="item in insightItems"
            :key="item.path"
            :to="item.path"
            :class="['sidebar__item', { 'sidebar__item--active': route.path === item.path }]"
          >
            <el-icon :size="20"><component :is="item.icon" /></el-icon>
            <transition name="fade">
              <span v-if="!collapsed" class="sidebar__item-label">{{ item.label }}</span>
            </transition>
          </router-link>
        </div>

        <div class="sidebar__group">
          <div v-if="!collapsed" class="sidebar__group-label">决策</div>
          <router-link
            v-for="item in decisionItems"
            :key="item.path"
            :to="item.path"
            :class="['sidebar__item', { 'sidebar__item--active': route.path === item.path }]"
          >
            <el-icon :size="20"><component :is="item.icon" /></el-icon>
            <transition name="fade">
              <span v-if="!collapsed" class="sidebar__item-label">{{ item.label }}</span>
            </transition>
          </router-link>
        </div>

        <div class="sidebar__group">
          <div v-if="!collapsed" class="sidebar__group-label">系统</div>
          <router-link
            v-for="item in systemItems"
            :key="item.path"
            :to="item.path"
            :class="['sidebar__item', { 'sidebar__item--active': route.path === item.path }]"
          >
            <el-icon :size="20"><component :is="item.icon" /></el-icon>
            <transition name="fade">
              <span v-if="!collapsed" class="sidebar__item-label">{{ item.label }}</span>
            </transition>
            <transition name="fade">
              <el-badge
                v-if="!collapsed && item.badge"
                :value="item.badge"
                :max="99"
                class="sidebar__item-badge"
              />
            </transition>
          </router-link>
        </div>
      </nav>

      <div v-if="!collapsed" class="sidebar__footer">
        <PlanCard
          :plan="permissionStore.plan || 'free'"
          :expires-at="licenseStore.expiresAtFormatted"
          @click="$router.push('/license')"
        />
      </div>
    </aside>

    <div v-if="isMobile && !collapsed" class="sidebar-overlay" @click="collapsed = true" />

    <div class="app-layout__main">
      <header class="topbar">
        <div class="topbar__left">
          <el-button
            v-if="isMobile"
            :icon="Fold"
            circle
            size="small"
            @click="collapsed = !collapsed"
            class="topbar__menu-btn"
          />
          <el-button
            v-else
            :icon="collapsed ? Expand : Fold"
            circle
            size="small"
            @click="collapsed = !collapsed"
            class="topbar__menu-btn"
          />
          <div class="topbar__breadcrumb">
            <span class="topbar__page-name">{{ currentPageTitle }}</span>
          </div>
        </div>

        <div class="topbar__center">
          <SearchInput
            v-if="!isMobile"
            ref="searchRef"
            placeholder="搜索商品、规则、设置..."
            shortcut="⌘K"
            @search="handleSearch"
          />
        </div>

        <div class="topbar__right">
          <div class="topbar__collect-status">
            <StatusDot :status="collectStore.isCollecting ? 'busy' : 'idle'" />
            <span class="topbar__collect-label">{{ collectStore.isCollecting ? '采集中' : '空闲' }}</span>
          </div>
          <el-badge :value="notificationStore.unreadCount" :hidden="!notificationStore.hasUnread" :max="99">
            <el-button :icon="Bell" circle size="small" @click="$router.push('/notifications')" />
          </el-badge>
          <el-dropdown>
            <div class="topbar__user">
              <div class="topbar__avatar">
                {{ (authStore.user?.nickname || 'U')[0].toUpperCase() }}
              </div>
              <span v-if="!isMobile" class="topbar__username">{{ authStore.user?.nickname || '用户' }}</span>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="$router.push('/settings')">
                  <el-icon><Setting /></el-icon>
                  {{ t('nav.settings') }}
                </el-dropdown-item>
                <el-dropdown-item divided @click="authStore.logout()">
                  <el-icon><SwitchButton /></el-icon>
                  {{ t('auth.logout') }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <main class="app-layout__content">
        <router-view />
      </main>

      <div v-if="isMobile" class="mobile-nav">
        <router-link
          v-for="item in mobileNavItems"
          :key="item.path"
          :to="item.path"
          :class="['mobile-nav__item', { 'mobile-nav__item--active': route.path === item.path }]"
        >
          <el-icon :size="20"><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </router-link>
      </div>
    </div>

    <GlobalSearchDialog :visible="showGlobalSearch" @close="showGlobalSearch = false" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed } from "vue";
import { useRoute } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { useNotificationStore } from "../stores/notification";
import { usePermissionStore } from "../stores/permission";
import { useLicenseStore } from "../stores/license";
import { useCollectStore } from "../stores/collect";
import { useI18n } from "../i18n";
import {
  Monitor, Goods, MagicStick, Timer, Bell, Setting, Key,
  Fold, Expand, SwitchButton, DataAnalysis, ChatDotRound,
  Opportunity, Warning
} from "@element-plus/icons-vue";
import SearchInput from "../components/SearchInput.vue";
import GlobalSearchDialog from "../components/GlobalSearchDialog.vue";
import StatusDot from "../components/StatusDot.vue";
import PlanCard from "../components/PlanCard.vue";

const { t } = useI18n();
const route = useRoute();
const authStore = useAuthStore();
const notificationStore = useNotificationStore();
const permissionStore = usePermissionStore();
const licenseStore = useLicenseStore();
const collectStore = useCollectStore();

const windowWidth = ref(window.innerWidth);
const collapsed = ref(false);
const searchRef = ref<InstanceType<typeof SearchInput>>();
const showGlobalSearch = ref(false);

const isMobile = computed(() => windowWidth.value < 768);

const insightItems = computed(() => [
  { path: "/dashboard", icon: Opportunity, label: "机会雷达" },
  { path: "/products", icon: Goods, label: "我的商品" },
  { path: "/category-insight", icon: DataAnalysis, label: "品类洞察" },
  { path: "/compare", icon: DataAnalysis, label: "竞品对比" },
]);

const decisionItems = computed(() => [
  { path: "/ai", icon: MagicStick, label: "AI 决策" },
  { path: "/monitor", icon: Warning, label: "告警中心" },
]);

const systemItems = computed(() => [
  { path: "/scheduler", icon: Timer, label: "采集调度" },
  { path: "/notifications", icon: ChatDotRound, label: t('nav.notifications'), badge: notificationStore.unreadCount || undefined },
  { path: "/settings", icon: Setting, label: t('nav.settings') },
  { path: "/license", icon: Key, label: t('nav.license') },
]);

const mobileNavItems = computed(() => [
  { path: "/dashboard", icon: Opportunity, label: "机会雷达" },
  { path: "/products", icon: Goods, label: "我的商品" },
  { path: "/ai", icon: MagicStick, label: "AI 决策" },
  { path: "/monitor", icon: Warning, label: "告警中心" },
  { path: "/settings", icon: Setting, label: t('nav.settings') },
]);

const PAGE_TITLES: Record<string, string> = {
  "/dashboard": "机会雷达",
  "/products": "我的商品",
  "/category-insight": "品类洞察",
  "/ai": "AI 决策",
  "/scheduler": "采集调度",
  "/monitor": "告警中心",
  "/notifications": "通知中心",
  "/compare": "竞品对比",
  "/settings": "设置",
  "/license": "授权管理",
};

const currentPageTitle = computed(() => {
  const path = route.path;
  if (PAGE_TITLES[path]) return PAGE_TITLES[path];
  const base = "/" + path.split("/").filter(Boolean)[0];
  return PAGE_TITLES[base] || "";
});

function onResize() {
  windowWidth.value = window.innerWidth;
  if (isMobile.value) {
    collapsed.value = true;
  }
}

function handleSearch(query: string) {
  if (query) {
    showGlobalSearch.value = true;
  }
}

authStore.fetchUser();

let notifTimer: ReturnType<typeof setInterval> | null = null;
let unsubscribeLocal: (() => void) | null = null;
let unsubscribeWs: (() => void) | null = null;

onMounted(() => {
  notificationStore.fetchUnreadCount();
  permissionStore.fetchPermissions();
  licenseStore.fetchLicense();

  notifTimer = setInterval(() => {
    notificationStore.fetchUnreadCount();
  }, 60000);
  window.addEventListener("resize", onResize);
  onResize();

  window.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "k") {
      e.preventDefault();
      showGlobalSearch.value = !showGlobalSearch.value;
    }
  });

  try {
    unsubscribeLocal = window.electronAPI.on("notification:local", (data: unknown) => {
      notificationStore.handleNewNotification(data as import("../stores/notification").NotificationItem);
    });
  } catch {}

  try {
    unsubscribeWs = window.electronAPI.on("notification", (data: unknown) => {
      const msg = data as { type: string; data: import("../stores/notification").NotificationItem };
      if (msg.type === "notification:new" && msg.data) {
        notificationStore.handleNewNotification({ ...msg.data, source: "cloud" });
      } else if (msg.type === "monitor:triggered" && msg.data) {
        notificationStore.handleNewNotification({
          id: (msg.data as Record<string, unknown>).id as string || crypto.randomUUID(),
          type: "monitor",
          title: "监控规则触发",
          content: String((msg.data as Record<string, unknown>).message || "商品数据触发监控规则"),
          is_read: false,
          related_id: (msg.data as Record<string, unknown>).product_id as string || null,
          related_type: "product",
          created_at: new Date().toISOString(),
          source: "cloud",
        });
      } else if (msg.type === "ai:analysis_completed" && msg.data) {
        notificationStore.handleNewNotification({
          id: (msg.data as Record<string, unknown>).analysis_id as string || crypto.randomUUID(),
          type: "ai",
          title: "AI分析完成",
          content: "AI分析已完成，点击查看结果",
          is_read: false,
          related_id: (msg.data as Record<string, unknown>).product_id as string || null,
          related_type: "product",
          created_at: new Date().toISOString(),
          source: "cloud",
        });
      }
    });
  } catch {}
});

onUnmounted(() => {
  if (notifTimer) clearInterval(notifTimer);
  if (unsubscribeLocal) unsubscribeLocal();
  if (unsubscribeWs) unsubscribeWs();
  window.removeEventListener("resize", onResize);
});
</script>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  width: var(--sidebar-width);
  background: var(--gradient-sidebar);
  display: flex;
  flex-direction: column;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  flex-shrink: 0;
  z-index: 100;
}

.sidebar--collapsed {
  width: var(--sidebar-collapsed-width);
}

.sidebar__logo {
  height: var(--header-height);
  display: flex;
  align-items: center;
  padding: 0 18px;
  gap: 12px;
  cursor: pointer;
  flex-shrink: 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.sidebar--collapsed .sidebar__logo {
  justify-content: center;
  padding: 0;
}

.sidebar__logo-icon {
  flex-shrink: 0;
}

.sidebar__logo-text {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text-inverse);
  letter-spacing: -0.5px;
  white-space: nowrap;
}

.sidebar__nav {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 8px 0;
}

.sidebar__group {
  margin-bottom: 8px;
}

.sidebar__group-label {
  padding: 12px 24px 8px;
  font-size: 11px;
  font-weight: 600;
  color: #818CF8;
  text-transform: uppercase;
  letter-spacing: 1px;
  white-space: nowrap;
}

.sidebar--collapsed .sidebar__group-label {
  display: none;
}

.sidebar__item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 18px;
  margin: 2px 8px;
  border-radius: var(--radius-base);
  color: rgba(255, 255, 255, 0.7);
  text-decoration: none;
  transition: all 0.2s;
  white-space: nowrap;
  position: relative;
}

.sidebar--collapsed .sidebar__item {
  justify-content: center;
  padding: 10px;
  margin: 2px 6px;
}

.sidebar__item:hover {
  background: rgba(255, 255, 255, 0.06);
  color: #FFFFFF;
}

.sidebar__item--active {
  background: rgba(79, 70, 229, 0.2);
  color: #FFFFFF;
}

.sidebar__item--active::before {
  content: "";
  position: absolute;
  left: -8px;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 20px;
  background: #4F46E5;
  border-radius: 0 4px 4px 0;
}

.sidebar--collapsed .sidebar__item--active::before {
  left: -6px;
}

.sidebar__item-label {
  font-size: var(--text-base);
  font-weight: 500;
}

.sidebar__item-badge {
  margin-left: auto;
}

.sidebar__footer {
  flex-shrink: 0;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.sidebar-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 99;
}

.app-layout__main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

.topbar {
  height: var(--header-height);
  background: var(--color-bg-card);
  border-bottom: 1px solid var(--color-border-light);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  flex-shrink: 0;
  gap: 16px;
}

.topbar__left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.topbar__menu-btn {
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
}

.topbar__menu-btn:hover {
  background: var(--color-bg-hover);
  color: var(--color-text-primary);
}

.topbar__breadcrumb {
  display: flex;
  align-items: center;
}

.topbar__page-name {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-text-primary);
}

.topbar__center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.topbar__right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.topbar__collect-status {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: var(--text-xs);
  font-weight: 500;
  background: var(--color-bg-page);
  color: var(--color-text-tertiary);
  transition: all 0.3s;
}

.topbar__collect-status:has(.status-dot--busy) {
  background: var(--color-success-bg);
  color: var(--color-success);
}

.topbar__collect-label {
  font-size: var(--text-xs);
}

.topbar__user {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: var(--radius-base);
  transition: background 0.2s;
}

.topbar__user:hover {
  background: var(--color-bg-hover);
}

.topbar__avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--gradient-hero);
  color: var(--color-text-inverse);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-sm);
  font-weight: 600;
}

.topbar__username {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  font-weight: 500;
}

.app-layout__content {
  flex: 1;
  overflow-y: auto;
  background: var(--color-bg-page);
}

.mobile-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 56px;
  background: var(--color-bg-card);
  border-top: 1px solid var(--color-border-light);
  display: flex;
  align-items: center;
  justify-content: space-around;
  z-index: 998;
}

.mobile-nav__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  font-size: 10px;
  color: var(--color-text-tertiary);
  text-decoration: none;
  padding: 4px 0;
  gap: 2px;
  transition: color 0.2s;
}

.mobile-nav__item--active {
  color: var(--color-primary);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    height: 100vh;
    z-index: 1000;
  }

  .app-layout__content {
    padding-bottom: 56px;
  }

  .topbar {
    padding: 0 16px;
  }

  .topbar__center {
    display: none;
  }
}
</style>
