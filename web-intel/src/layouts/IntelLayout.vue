<template>
  <el-container class="intel-layout">
    <el-aside :width="collapsed ? '64px' : '220px'" class="intel-sidebar">
      <div class="sidebar-header">
        <span v-if="!collapsed" class="logo-text">AI Intelligence OS</span>
        <span v-else class="logo-icon">AI</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        :collapse="collapsed"
        router
        background-color="#1a1a2e"
        text-color="#a0a0b8"
        active-text-color="#4fc3f7"
      >
        <el-menu-item index="/dashboard">
          <el-icon><Monitor /></el-icon>
          <template #title>仪表盘</template>
        </el-menu-item>
        <el-menu-item index="/trends">
          <el-icon><TrendCharts /></el-icon>
          <template #title>趋势分析</template>
        </el-menu-item>
        <el-menu-item index="/opportunities">
          <el-icon><Opportunity /></el-icon>
          <template #title>商业机会</template>
        </el-menu-item>
        <el-menu-item index="/risks">
          <el-icon><Warning /></el-icon>
          <template #title>风险预警</template>
        </el-menu-item>
        <el-menu-item index="/topics">
          <el-icon><Document /></el-icon>
          <template #title>选题库</template>
        </el-menu-item>
        <el-menu-item index="/signals">
          <el-icon><Connection /></el-icon>
          <template #title>平台信号</template>
        </el-menu-item>
        <el-menu-item index="/emotions">
          <el-icon><ChatDotRound /></el-icon>
          <template #title>用户情绪</template>
        </el-menu-item>
      </el-menu>
      <div class="sidebar-footer">
        <el-button text class="collapse-btn" @click="collapsed = !collapsed">
          <el-icon><Fold v-if="!collapsed" /><Expand v-else /></el-icon>
        </el-button>
      </div>
    </el-aside>
    <el-container>
      <el-header class="intel-header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/dashboard' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item v-if="pageTitle">{{ pageTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-tag :type="planTagType" size="small" class="plan-tag">
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
              <el-icon><UserFilled /></el-icon>
              <el-icon><ArrowDown /></el-icon>
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
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed } from "vue"
import { useRoute, useRouter } from "vue-router"
import { useIntelAuthStore } from "@/stores/auth"
import {
  Monitor, TrendCharts, Opportunity, Warning, Document,
  Connection, ChatDotRound, Fold, Expand, ArrowDown, UserFilled,
} from "@element-plus/icons-vue"

const route = useRoute()
const router = useRouter()
const auth = useIntelAuthStore()
const collapsed = ref(false)

const pageTitle = computed(() => {
  const map: Record<string, string> = {
    dashboard: "仪表盘",
    trends: "趋势分析",
    opportunities: "商业机会",
    risks: "风险预警",
    topics: "选题库",
    signals: "平台信号",
    emotions: "用户情绪",
  }
  const name = (route.name as string) || route.path.split("/").pop() || ""
  return map[name] || ""
})

const activeMenu = computed(() => "/" + (route.path.split("/")[1] || "dashboard"))

const planTagType = computed(() => {
  const map: Record<string, string> = { free: "info", pro: "success", enterprise: "warning" }
  return map[auth.planName] || "info"
})

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
  background-color: #1a1a2e;
  display: flex;
  flex-direction: column;
  transition: width 0.3s;
  overflow: hidden;
}
.sidebar-header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid #16213e;
}
.logo-text {
  color: #4fc3f7;
  font-size: 18px;
  font-weight: 700;
  white-space: nowrap;
}
.logo-icon {
  color: #4fc3f7;
  font-size: 22px;
  font-weight: 700;
}
.sidebar-footer {
  margin-top: auto;
  padding: 12px;
  text-align: center;
}
.collapse-btn {
  color: #a0a0b8;
}
.intel-header {
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 60px;
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
}
.days-badge.days-warning {
  color: #e6a23c;
}
.days-badge.days-expired {
  color: #f56c6c;
}
.expire-date {
  font-size: 12px;
  color: #909399;
}
.user-info {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
  color: #303133;
}
.intel-main {
  background: #f5f7fa;
  padding: 24px;
  overflow-y: auto;
}
</style>