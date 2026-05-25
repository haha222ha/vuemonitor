<template>
  <div class="reports-page">
    <UpgradeBanner />
    <div class="page-header">
      <div class="header-title-area">
        <h2>决策报告</h2>
        <p class="header-subtitle">周度/月度副业决策报告，与本地 HTML 报告同源</p>
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
      <div class="intel-empty-state-action">内容同步后会自动出现在此</div>
    </div>
    <template v-else>
      <el-row :gutter="16" class="report-list">
        <el-col v-for="item in items" :key="item.id" :xs="24" :sm="12" :md="8">
          <el-card shadow="hover" class="report-card" @click="openReport(item)">
            <div class="report-type">{{ reportTypeLabel(item.report_type) }}</div>
            <h3 class="report-title">{{ item.title }}</h3>
            <p class="report-meta">
              <span v-if="item.week_number">{{ item.week_number }}</span>
              <span v-if="item.report_date">{{ formatDate(item.report_date) }}</span>
            </p>
            <el-button type="primary" link>查看报告 →</el-button>
          </el-card>
        </el-col>
      </el-row>
    </template>

    <el-drawer v-model="drawerOpen" :title="activeReport?.title || '报告预览'" size="92%" direction="rtl" destroy-on-close>
      <iframe v-if="reportFrameUrl" :src="reportFrameUrl" class="report-iframe" title="报告内容" />
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

const planName = computed(() => auth.planName)

const reportFrameUrl = computed(() => {
  const path = activeReport.value?.content_html || activeReport.value?.file_path
  if (!path) return ""
  if (path.startsWith("http")) return path
  const origin = window.location.origin
  return `${origin}${path.startsWith("/") ? path : `/${path}`}`
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
  activeReport.value = item
  drawerOpen.value = true
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
      items.value = data?.items || []
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
.report-card {
  cursor: pointer;
  margin-bottom: 16px;
  transition: transform 0.15s;
}
.report-card:hover {
  transform: translateY(-2px);
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
  margin: 0 0 8px;
  display: flex;
  gap: 8px;
}
.report-iframe {
  width: 100%;
  height: calc(100vh - 100px);
  border: none;
  border-radius: 8px;
  background: #fff;
}
.loading-wrap {
  padding: 24px;
}
</style>
