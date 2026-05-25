<template>
  <div class="reports-page">
    <UpgradeBanner />
    <div class="page-header">
      <div class="header-title-area">
        <h2>决策报告</h2>
        <p class="header-subtitle">周度/月度副业决策报告（HTML 完整版，非仪表盘摘要）</p>
      </div>
      <el-tag v-if="planName" effect="plain">{{ planLabel(planName) }}</el-tag>
    </div>

    <div v-if="loading" class="loading-wrap">
      <el-skeleton :rows="6" animated />
    </div>
    <div v-else-if="blockedMessage" class="intel-empty-state">
      <div class="intel-empty-state-icon">🔒</div>
      <div class="intel-empty-state-text">{{ blockedMessage }}</div>
    </div>
    <div v-else-if="!items.length" class="intel-empty-state">
      <div class="intel-empty-state-icon">📄</div>
      <div class="intel-empty-state-text">暂无已上传报告</div>
      <div class="intel-empty-state-action">本地执行同步并上传 html 报告后会出现在此</div>
    </div>
    <template v-else>
      <el-tabs v-model="typeTab" class="report-tabs">
        <el-tab-pane label="全部" name="all" />
        <el-tab-pane label="周度报告" name="weekly" />
        <el-tab-pane label="月度报告" name="monthly" />
      </el-tabs>
      <el-row :gutter="16" class="report-list">
        <el-col v-for="item in filteredByType" :key="item.id" :xs="24" :sm="12" :md="8">
          <el-card shadow="hover" class="report-card">
            <div class="report-type">{{ reportTypeLabel(item.report_type) }}</div>
            <h3 class="report-title">{{ item.title }}</h3>
            <p class="report-meta">
              <span v-if="item.week_number">{{ item.week_number }}</span>
              <span v-if="item.report_date">{{ formatDate(item.report_date) }}</span>
            </p>
            <div class="report-actions">
              <el-button type="primary" size="small" @click="openReport(item)">查看报告</el-button>
              <el-button size="small" link @click="openReportNewTab(item)">新窗口打开</el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </template>

    <el-drawer
      v-model="drawerOpen"
      :title="activeReport?.title || '报告预览'"
      size="92%"
      direction="rtl"
      destroy-on-close
    >
      <div v-if="!reportFrameUrl" class="drawer-empty">无法加载报告地址</div>
      <iframe v-else :src="reportFrameUrl" class="report-iframe" title="报告内容" />
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
// AIGC START
import { ref, computed, onMounted } from "vue"
import { useIntelAuthStore } from "@/stores/auth"
import api from "@/utils/api"
import { planLabel, REPORT_TYPE_LABELS } from "@/utils/plan"
import UpgradeBanner from "@/components/UpgradeBanner.vue"

const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api/v1"

interface ReportItem {
  id: string
  report_type: string
  title: string
  week_number?: string
  report_date?: string
  content_html?: string
  file_path?: string
}

const auth = useIntelAuthStore()
const loading = ref(true)
const items = ref<ReportItem[]>([])
const blockedMessage = ref("")
const drawerOpen = ref(false)
const activeReport = ref<ReportItem | null>(null)
const typeTab = ref("all")

const planName = computed(() => auth.planName)

function resolveReportUrl(item: ReportItem): string {
  const path = item.content_html || item.file_path || ""
  if (!path) return ""
  if (path.startsWith("http")) return path
  const filename = path.split("/").pop()?.split("?")[0] || ""
  if (!filename) return ""
  return `${API_BASE}/intel/reports/files/${encodeURIComponent(filename)}`
}

const reportFrameUrl = computed(() => {
  if (!activeReport.value) return ""
  return resolveReportUrl(activeReport.value)
})

const filteredByType = computed(() => {
  if (typeTab.value === "all") return items.value
  return items.value.filter((i) => i.report_type === typeTab.value)
})

function reportTypeLabel(t: string) {
  return REPORT_TYPE_LABELS[t] || t
}

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString("zh-CN")
  } catch {
    return iso
  }
}

function openReport(item: ReportItem) {
  const url = resolveReportUrl(item)
  if (!url) return
  activeReport.value = item
  drawerOpen.value = true
}

function openReportNewTab(item: ReportItem) {
  const url = resolveReportUrl(item)
  if (url) window.open(url, "_blank", "noopener,noreferrer")
}

onMounted(async () => {
  loading.value = true
  blockedMessage.value = ""
  try {
    const { data } = await api.get("/intel/reports")
    if (data?.message && !data?.items?.length) {
      blockedMessage.value = data.message
      items.value = []
    } else {
      items.value = (data?.items || []).filter(
        (r: ReportItem) => r.title && !/测试|test|demo/i.test(r.title),
      )
    }
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string; message?: string } } })?.response?.data
    blockedMessage.value = msg?.detail || msg?.message || "加载报告失败"
  } finally {
    loading.value = false
  }
})
// AIGC END
</script>

<style scoped>
.reports-page {
  max-width: 1400px;
}
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
}
.header-title-area h2 {
  margin: 0;
  font-size: var(--font-size-xl, 22px);
}
.header-subtitle {
  margin: 4px 0 0;
  color: var(--intel-text-muted, #909399);
  font-size: 13px;
}
.report-tabs {
  margin-bottom: 16px;
}
.report-card {
  margin-bottom: 16px;
}
.report-type {
  font-size: 12px;
  color: #409eff;
  margin-bottom: 6px;
}
.report-title {
  margin: 0 0 8px;
  font-size: 16px;
  line-height: 1.4;
}
.report-meta {
  font-size: 12px;
  color: #909399;
  margin: 0 0 12px;
  display: flex;
  gap: 8px;
}
.report-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.report-iframe {
  width: 100%;
  height: calc(100vh - 100px);
  border: none;
  border-radius: 8px;
  background: #fff;
}
.drawer-empty {
  padding: 40px;
  text-align: center;
  color: #909399;
}
.loading-wrap {
  padding: 24px;
}
</style>
