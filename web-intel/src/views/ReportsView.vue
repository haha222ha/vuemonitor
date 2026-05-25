<template>
  <div class="reports-page">
    <UpgradeBanner />
    <div class="page-header">
      <div class="header-title-area">
        <h2>决策报告</h2>
        <p class="header-subtitle">按类型分区展示：周度 / 月度 / 选题深度，不再混排</p>
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
    </div>
    <template v-else>
      <div class="report-summary">
        共 {{ items.length }} 份，分 {{ sections.length }} 类展示
      </div>
      <section v-for="sec in sections" :key="sec.key" class="report-section">
        <div class="section-head">
          <h3 class="section-title">{{ sec.title }}</h3>
          <span class="section-hint">{{ sec.hint }}</span>
          <el-tag size="small" type="info" effect="plain">{{ sec.items.length }} 份</el-tag>
        </div>
        <el-row :gutter="16" class="report-list">
          <el-col v-for="item in sec.items" :key="item.id" :xs="24" :sm="12" :md="8">
            <el-card shadow="hover" class="report-card">
              <div class="report-type-row">
                <el-tag size="small" :type="sectionTagType(sec.key)">{{ reportTypeLabel(sec.key) }}</el-tag>
                <span v-if="item.topic_id" class="topic-id">{{ item.topic_id }}</span>
              </div>
              <h3 class="report-title">{{ displayTitle(item) }}</h3>
              <p class="report-meta">
                <span v-if="item.week_number && sec.key === 'weekly'">{{ item.week_number }}</span>
                <span v-if="item.report_date">{{ formatDate(item.report_date) }}</span>
              </p>
              <div class="report-actions">
                <el-button type="primary" size="small" :loading="openingId === item.id" @click="openReport(item)">
                  查看报告
                </el-button>
                <el-button size="small" link @click="openReportNewTab(item)">新窗口打开</el-button>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </section>
    </template>

    <el-drawer
      v-model="drawerOpen"
      :title="activeReport ? displayTitle(activeReport) : '报告预览'"
      size="92%"
      direction="rtl"
      destroy-on-close
      @closed="onDrawerClosed"
    >
      <div v-if="reportLoading" class="drawer-loading">
        <el-skeleton :rows="10" animated />
      </div>
      <div v-else-if="reportError" class="drawer-empty">
        <p>{{ reportError }}</p>
        <el-button type="primary" @click="retryLoadReport">重试</el-button>
      </div>
      <iframe
        v-else-if="reportFrameUrl && !reportHtmlInline"
        :src="reportFrameUrl"
        class="report-iframe"
        title="报告内容"
        @error="onIframeError"
      />
      <iframe
        v-else-if="reportHtmlInline"
        :srcdoc="reportHtmlInline"
        class="report-iframe"
        title="报告内容"
        sandbox="allow-scripts allow-same-origin"
      />
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
// AIGC START
import { ref, computed, onMounted } from "vue"
import { ElMessage } from "element-plus"
import axios from "axios"
import { useIntelAuthStore } from "@/stores/auth"
import api from "@/utils/api"
import { planLabel, REPORT_TYPE_LABELS } from "@/utils/plan"
import {
  groupReportsBySection,
  type ReportListItem,
  type ReportDisplayType,
} from "@/utils/reports"
import UpgradeBanner from "@/components/UpgradeBanner.vue"

const auth = useIntelAuthStore()
const loading = ref(true)
const items = ref<ReportListItem[]>([])
const blockedMessage = ref("")
const drawerOpen = ref(false)
const activeReport = ref<ReportListItem | null>(null)
const openingId = ref("")
const reportLoading = ref(false)
const reportError = ref("")
const reportHtmlInline = ref("")
const reportFrameUrl = ref("")

const planName = computed(() => auth.planName)
const sections = computed(() => groupReportsBySection(items.value))

function sectionTagType(key: ReportDisplayType): string {
  const map: Record<string, string> = {
    weekly: "primary",
    monthly: "success",
    topic: "warning",
    quarterly: "",
    daily: "info",
    other: "info",
  }
  return map[key] || "info"
}

function displayTitle(item: ReportListItem): string {
  const t = item.title || ""
  if (item.topic_id && t.startsWith(item.topic_id)) {
    return t.replace(new RegExp(`^${item.topic_id}\\s*[·\\-]?\\s*`), "").trim() || t
  }
  return t
}

function extractFilename(path: string): string {
  const clean = path.split("?")[0]
  return clean.split("/").pop() || ""
}

function resolveReportUrl(item: ReportListItem): string {
  const path = item.content_html || item.file_path || ""
  if (!path) return ""

  const origin = window.location.origin

  if (path.startsWith("http")) {
    if (/localhost|127\.0\.0\.1/i.test(path)) {
      const filename = extractFilename(path)
      return filename ? `${origin}/static/reports/${encodeURIComponent(filename)}` : ""
    }
    return path
  }

  const filename = extractFilename(path)
  if (!filename) return ""

  if (path.startsWith("/static/reports/")) {
    return `${origin}/static/reports/${encodeURIComponent(filename)}`
  }

  return `${origin}/static/reports/${encodeURIComponent(filename)}`
}

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

async function loadReportContent(item: ReportListItem) {
  const url = resolveReportUrl(item)
  if (!url) {
    reportError.value = "报告文件地址无效"
    return
  }

  reportLoading.value = true
  reportError.value = ""
  reportHtmlInline.value = ""
  reportFrameUrl.value = url

  try {
    const { data } = await axios.get(url, {
      responseType: "text",
      timeout: 60000,
      headers: { Accept: "text/html" },
    })
    if (typeof data === "string" && data.includes("<html")) {
      reportHtmlInline.value = data
      reportFrameUrl.value = ""
    }
  } catch {
    reportFrameUrl.value = url
  } finally {
    reportLoading.value = false
  }
}

async function openReport(item: ReportListItem) {
  openingId.value = item.id
  activeReport.value = item
  drawerOpen.value = true
  await loadReportContent(item)
  openingId.value = ""
}

function openReportNewTab(item: ReportListItem) {
  const url = resolveReportUrl(item)
  if (url) window.open(url, "_blank", "noopener,noreferrer")
  else ElMessage.warning("无法解析报告地址")
}

function retryLoadReport() {
  if (activeReport.value) loadReportContent(activeReport.value)
}

function onIframeError() {
  reportError.value = "iframe 加载失败，请点击「新窗口打开」查看"
}

function onDrawerClosed() {
  reportHtmlInline.value = ""
  reportFrameUrl.value = ""
  reportError.value = ""
  activeReport.value = null
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
        (r: ReportListItem) => r.title && !/测试|test|demo/i.test(r.title),
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
.report-summary {
  font-size: 13px;
  color: #909399;
  margin-bottom: 20px;
}
.report-section {
  margin-bottom: 32px;
}
.section-head {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 14px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--el-border-color-lighter, #ebeef5);
}
.section-title {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
}
.section-hint {
  font-size: 12px;
  color: #909399;
  flex: 1;
  min-width: 200px;
}
.report-card {
  margin-bottom: 16px;
}
.report-type-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.topic-id {
  font-size: 11px;
  color: #909399;
  font-family: ui-monospace, monospace;
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
.drawer-empty,
.drawer-loading {
  padding: 40px;
  text-align: center;
  color: #909399;
}
.loading-wrap {
  padding: 24px;
}
</style>
