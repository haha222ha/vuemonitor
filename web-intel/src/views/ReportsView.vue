<template>
  <div class="reports-page">
    <UpgradeBanner />
    <div class="page-header">
      <div class="header-title-area">
        <h2>决策报告</h2>
        <p class="header-subtitle">按报告类型标签筛选，分区浏览周度 / 月度 / 选题深度报告</p>
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
      <IntelCategoryTabs v-model="reportTypeTab" :tabs="reportTypeTabs" />

      <div v-if="!visibleSections.length" class="intel-empty-state">
        <div class="intel-empty-state-text">该分类下暂无报告</div>
      </div>

      <section v-for="sec in visibleSections" :key="sec.key" class="report-section">
        <div class="section-head" :style="{ borderLeftColor: reportStyle(sec.key).accent }">
          <div class="section-head-main">
            <el-tag size="small" :type="reportStyle(sec.key).type" effect="dark">{{ reportTypeLabel(sec.key) }}</el-tag>
            <h3 class="section-title">{{ sec.title }}</h3>
          </div>
          <span class="section-hint">{{ sec.hint }}</span>
          <span class="section-count">{{ sec.items.length }} 份</span>
        </div>
        <el-row :gutter="16" class="report-list">
          <el-col v-for="item in sec.items" :key="item.id" :xs="24" :sm="12" :lg="8">
            <div
              class="report-card"
              :style="{ '--card-accent': reportStyle(sec.key).accent, '--card-bg': reportStyle(sec.key).bg }"
            >
              <div class="report-card-accent" />
              <div class="report-card-body">
                <div class="report-type-row">
                  <el-tag size="small" :type="reportStyle(sec.key).type" effect="light">
                    {{ reportTypeLabel(sec.key) }}
                  </el-tag>
                  <span v-if="item.topic_id" class="topic-id">{{ item.topic_id }}</span>
                  <span v-if="item.week_number && sec.key === 'weekly'" class="week-badge">{{ item.week_number }}</span>
                </div>
                <h3 class="report-title">{{ displayTitle(item) }}</h3>
                <p class="report-meta">
                  <span v-if="item.report_date">📅 {{ formatDate(item.report_date) }}</span>
                </p>
                <div class="report-actions">
                  <el-button type="primary" size="small" :loading="openingId === item.id" @click="openReport(item)">
                    查看报告
                  </el-button>
                  <el-button size="small" link @click="openReportNewTab(item)">新窗口打开</el-button>
                </div>
              </div>
            </div>
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
  REPORT_SECTION_META,
  type ReportListItem,
  type ReportDisplayType,
} from "@/utils/reports"
import UpgradeBanner from "@/components/UpgradeBanner.vue"
import IntelCategoryTabs, { type CategoryTabItem } from "@/components/IntelCategoryTabs.vue"
import { getReportTypeStyle } from "@/utils/categoryStyle"

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
const reportTypeTab = ref("all")
const sections = computed(() => groupReportsBySection(items.value))

const reportTypeTabs = computed((): CategoryTabItem[] => {
  const all = sections.value
  const total = items.value.length
  const tabs: CategoryTabItem[] = [{ value: "all", label: "全部报告", count: total, icon: "📑" }]
  for (const sec of all) {
    const st = getReportTypeStyle(sec.key)
    tabs.push({
      value: sec.key,
      label: REPORT_SECTION_META[sec.key as ReportDisplayType]?.title || sec.title,
      count: sec.items.length,
      accent: st.accent,
      icon: sec.key === "weekly" ? "📅" : sec.key === "topic" ? "🎯" : "📊",
    })
  }
  return tabs
})

const visibleSections = computed(() => {
  if (reportTypeTab.value === "all") return sections.value
  return sections.value.filter((s) => s.key === reportTypeTab.value)
})

function reportStyle(key: string) {
  return getReportTypeStyle(key)
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

/** 线上 /static/reports/ 若未配 Nginx 反代会落到 SPA index.html，故统一走 API 文件接口 */
function resolveReportUrl(item: ReportListItem): string {
  const path = item.content_html || item.file_path || ""
  if (!path) return ""

  const origin = window.location.origin
  let filename = extractFilename(path)
  if (!filename && path.startsWith("http")) {
    filename = extractFilename(path)
  }
  if (!filename) return ""

  const encoded = encodeURIComponent(filename)
  return `${origin}/api/v1/intel/reports/files/${encoded}`
}

function isSpaIndexHtml(html: string): boolean {
  if (!html || html.length < 80) return false
  return (
    (html.includes('id="app"') || html.includes("id='app'")) &&
    (html.includes("/assets/index-") || html.includes("vite") || html.includes("web-intel"))
  )
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
    if (typeof data !== "string" || !data.includes("<html")) {
      reportError.value = "报告内容为空或格式异常"
      return
    }
    if (isSpaIndexHtml(data)) {
      reportError.value = "服务器未正确暴露报告文件（返回了站点首页）。请联系管理员执行一键部署并检查 Nginx。"
      return
    }
    reportHtmlInline.value = data
    reportFrameUrl.value = ""
  } catch {
    reportError.value = "加载报告失败，请尝试「新窗口打开」或稍后重试"
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
.report-section {
  margin-bottom: 36px;
}
.section-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
  padding: 10px 12px 10px 14px;
  border-left: 4px solid #409eff;
  background: var(--el-fill-color-light, #f5f7fa);
  border-radius: 8px;
}
.section-head-main {
  display: flex;
  align-items: center;
  gap: 10px;
}
.section-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}
.section-hint {
  font-size: 12px;
  color: #909399;
  flex: 1;
  min-width: 160px;
}
.section-count {
  font-size: 12px;
  color: #606266;
  font-weight: 600;
}
.report-card {
  position: relative;
  margin-bottom: 16px;
  border-radius: 10px;
  border: 1px solid var(--el-border-color-lighter, #ebeef5);
  background: var(--card-bg, #fff);
  overflow: hidden;
  transition: box-shadow 0.2s, transform 0.2s;
}
.report-card:hover {
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}
.report-card-accent {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--card-accent, #409eff);
}
.report-card-body {
  padding: 16px 16px 16px 20px;
}
.report-type-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}
.topic-id {
  font-size: 11px;
  color: #909399;
  font-family: ui-monospace, monospace;
  padding: 2px 8px;
  background: rgba(0, 0, 0, 0.04);
  border-radius: 4px;
}
.week-badge {
  font-size: 11px;
  color: #606266;
}
.report-title {
  margin: 0 0 8px;
  font-size: 15px;
  line-height: 1.45;
  font-weight: 600;
  color: #303133;
}
.report-meta {
  font-size: 12px;
  color: #909399;
  margin: 0 0 14px;
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
