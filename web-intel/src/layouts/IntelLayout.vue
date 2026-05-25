<template>
  <el-container class="intel-layout">
    <el-aside :width="collapsed ? '64px' : '220px'" class="intel-sidebar">
      <div class="sidebar-header">
        <div class="logo-area" :class="{ 'logo-collapsed': collapsed }">
          <div class="logo-icon-wrap">
            <span class="logo-icon-text">AI</span>
          </div>
          <transition name="logo-fade">
            <span v-if="!collapsed" class="logo-text">AI副业情报</span>
          </transition>
        </div>
      </div>
      <nav class="sidebar-nav">
        <router-link
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ 'nav-active': activeMenu === item.path }"
        >
          <div class="nav-indicator"></div>
          <el-icon :size="18"><component :is="item.icon" /></el-icon>
          <transition name="label-fade">
            <span v-if="!collapsed" class="nav-label">{{ item.label }}</span>
          </transition>
          <transition name="label-fade">
            <span v-if="!collapsed && item.badge" class="nav-badge">{{ item.badge }}</span>
          </transition>
        </router-link>
      </nav>
      <div class="sidebar-footer">
        <button class="collapse-btn" @click="collapsed = !collapsed">
          <el-icon :size="16"><Fold v-if="!collapsed" /><Expand v-else /></el-icon>
          <transition name="label-fade">
            <span v-if="!collapsed" class="collapse-label">收起菜单</span>
          </transition>
        </button>
      </div>
    </el-aside>
    <el-container class="intel-main-container">
      <el-header class="intel-header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/dashboard' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="pageTitle">{{ pageTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-tag :type="planTagType" size="small" class="plan-tag" effect="plain">
            {{ auth.planLabel }}
          </el-tag>
          <span class="days-badge" :class="{ 'days-warning': auth.daysRemaining > 0 && auth.daysRemaining <= 7, 'days-expired': auth.daysRemaining <= 0 }">
            <el-icon v-if="auth.daysRemaining <= 7 && auth.daysRemaining > 0"><Warning /></el-icon>
            <template v-if="auth.daysRemaining > 0">剩余 {{ auth.daysRemaining }} 天</template>
            <template v-else>已过期</template>
          </span>
          <span class="expire-date" v-if="auth.expiresAt">到期：{{ formatDate(auth.expiresAt) }}</span>
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <div class="user-avatar">
                <el-icon :size="14"><UserFilled /></el-icon>
              </div>
              <el-icon :size="12"><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="activate">激活授权码</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="intel-main">
        <OnboardingGuide />
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import { useIntelAuthStore } from "@/stores/auth"
import { useIntelStore } from "@/stores/intel"
import OnboardingGuide from "@/components/OnboardingGuide.vue"
import { visibleMenuItems } from "@/utils/plan"
import {
  Monitor, TrendCharts, Opportunity, Warning, Document,
  Connection, ChatDotRound, Fold, Expand, ArrowDown, UserFilled,
  DataAnalysis,
} from "@element-plus/icons-vue"

const route = useRoute()
const router = useRouter()
const auth = useIntelAuthStore()
const intel = useIntelStore()
const collapsed = ref(false)

const MENU_ICONS: Record<string, typeof Monitor> = {
  "/dashboard": Monitor,
  "/trends": TrendCharts,
  "/opportunities": Opportunity,
  "/risks": Warning,
  "/reports": DataAnalysis,
  "/topics": Document,
  "/signals": Connection,
  "/emotions": ChatDotRound,
}

const menuItems = computed(() =>
  visibleMenuItems(auth.planName).map((m) => ({
    path: m.path,
    label: m.label,
    icon: MENU_ICONS[m.path] || Document,
    badge:
      m.path === "/trends" && intel.dashboard?.summary?.active_trends
        ? String(intel.dashboard.summary.active_trends)
        : m.path === "/risks" && intel.dashboard?.summary?.active_risks
          ? String(intel.dashboard.summary.active_risks)
          : "",
  })),
)

const pageTitle = computed(() => {
  const map: Record<string, string> = {
    dashboard: "仪表盘",
    trends: "趋势分析",
    opportunities: "商业机会",
    risks: "风险预警",
    reports: "决策报告",
    topics: "选题库",
    signals: "平台信号",
    emotions: "用户情绪",
  }
  const name = (route.name as string) || route.path.split("/").pop() || ""
  return map[name] || ""
})

const activeMenu = computed(() => "/" + (route.path.split("/")[1] || "dashboard"))

const planTagType = computed(() => auth.planTagType || "info")

function formatDate(isoStr: string): string {
  try {
    const d = new Date(isoStr)
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`
  } catch {
    return isoStr
  }
}

function handleCommand(command: string) {
  if (command === "logout") {
    auth.logout()
    router.push("/login")
  } else if (command === "activate") {
    router.push("/activate")
  }
}
</script>

<style scoped>
.intel-layout {
  height: 100vh;
}

.intel-sidebar {
  background: linear-gradient(180deg, var(--sidebar-bg-start) 0%, var(--sidebar-bg-end) 100%);
  display: flex;
  flex-direction: column;
  transition: width var(--transition-base);
  overflow: hidden;
  border-right: 1px solid rgba(255, 255, 255, 0.05);
}

.sidebar-header {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.logo-area {
  display: flex;
  align-items: center;
  gap: 10px;
  overflow: hidden;
}

.logo-collapsed {
  justify-content: center;
}

.logo-icon-wrap {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, #4fc3f7 0%, #0288d1 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(79, 195, 247, 0.3);
}

.logo-icon-text {
  color: #fff;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.5px;
}

.logo-text {
  color: #e2e8f0;
  font-size: 16px;
  font-weight: 700;
  white-space: nowrap;
  background: linear-gradient(90deg, #e2e8f0, #4fc3f7, #e2e8f0);
  background-size: 200% auto;
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  animation: shimmer 4s linear infinite;
}

.sidebar-nav {
  flex: 1;
  padding: 12px 8px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow-y: auto;
  overflow-x: hidden;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border-radius: 10px;
  color: var(--sidebar-text);
  text-decoration: none;
  transition: all var(--transition-fast);
  position: relative;
  overflow: hidden;
  cursor: pointer;
}

.nav-item:hover {
  background: var(--sidebar-hover);
  color: var(--sidebar-text-active);
}

.nav-item:hover .el-icon {
  transform: translateX(2px);
}

.nav-item .el-icon {
  transition: transform var(--transition-fast);
  flex-shrink: 0;
}

.nav-indicator {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 0;
  border-radius: 0 3px 3px 0;
  background: var(--sidebar-active);
  transition: height var(--transition-fast);
}

.nav-active {
  background: var(--sidebar-hover);
  color: var(--sidebar-active);
}

.nav-active .nav-indicator {
  height: 20px;
}

.nav-active .el-icon {
  color: var(--sidebar-active);
}

.nav-label {
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
}

.nav-badge {
  margin-left: auto;
  font-size: 11px;
  font-weight: 700;
  background: rgba(79, 195, 247, 0.15);
  color: var(--sidebar-active);
  padding: 1px 7px;
  border-radius: 10px;
  min-width: 20px;
  text-align: center;
}

.sidebar-footer {
  padding: 12px 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.collapse-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 14px;
  border-radius: 10px;
  background: transparent;
  border: none;
  color: var(--sidebar-text);
  cursor: pointer;
  transition: all var(--transition-fast);
  font-size: 14px;
}

.collapse-btn:hover {
  background: var(--sidebar-hover);
  color: var(--sidebar-text-active);
}

.collapse-label {
  font-weight: 500;
  white-space: nowrap;
}

.intel-main-container {
  display: flex;
  flex-direction: column;
}

.intel-header {
  background: var(--intel-surface);
  border-bottom: 1px solid var(--intel-border-light);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: var(--header-height);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.03);
}

.header-left {
  display: flex;
  align-items: center;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.plan-tag {
  font-weight: 500;
}

.days-badge {
  font-size: 12px;
  color: #67c23a;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 4px;
}

.days-badge.days-warning {
  color: #e6a23c;
}

.days-badge.days-expired {
  color: #f56c6c;
}

.expire-date {
  font-size: 12px;
  color: var(--intel-text-secondary);
}

.user-info {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--intel-text);
}

.user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: #f0f2f5;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--intel-text-secondary);
  transition: background var(--transition-fast);
}

.user-info:hover .user-avatar {
  background: #e4e7ed;
}

.intel-main {
  background: var(--intel-bg);
  padding: var(--spacing-lg);
  overflow-y: auto;
}

.logo-fade-enter-active,
.logo-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.logo-fade-enter-from {
  opacity: 0;
  transform: translateX(-8px);
}
.logo-fade-leave-to {
  opacity: 0;
  transform: translateX(-8px);
}

.label-fade-enter-active,
.label-fade-leave-active {
  transition: opacity 0.15s ease;
}
.label-fade-enter-from,
.label-fade-leave-to {
  opacity: 0;
}

.page-fade-enter-active {
  animation: fade-in 0.25s ease both;
}
.page-fade-leave-active {
  animation: fade-in 0.15s ease reverse both;
}

@media (max-width: 768px) {
  .intel-sidebar {
    width: 64px !important;
  }
  .nav-label,
  .nav-badge,
  .collapse-label,
  .logo-text {
    display: none !important;
  }
  .intel-header {
    padding: 0 12px;
  }
  .expire-date {
    display: none;
  }
}
</style>
