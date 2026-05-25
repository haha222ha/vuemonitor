<template>
  <div class="report-page" ref="reportRoot">
    <div v-if="loading" class="loading-wrap">
      <el-skeleton :rows="12" animated />
    </div>
    <div v-else-if="!topicData" class="intel-empty-state">
      <div class="intel-empty-state-icon">📄</div>
      <div class="intel-empty-state-text">未找到选题数据</div>
      <div class="intel-empty-state-action">请返回选题库重新选择</div>
    </div>
    <div v-else class="report-content" :style="cssVars">

      <div class="report-toolbar">
        <el-button text @click="$router.back()" class="back-btn">
          <el-icon><ArrowLeft /></el-icon> 返回选题库
        </el-button>
        <div class="toolbar-actions">
          <el-button size="small" @click="doExportJSON">导出JSON</el-button>
          <el-button size="small" @click="viewHTML" v-if="htmlUrl">
            <el-icon><View /></el-icon> 查看HTML报告
          </el-button>
          <el-button size="small" type="primary" @click="downloadPDF" v-if="pdfUrl">
            <el-icon><Download /></el-icon> 下载PDF
          </el-button>
        </div>
      </div>

      <div class="intel-report-cover" :class="coverGradientClass">
        <div class="cover-inner">
          <div class="cover-badge">
            <el-tag effect="dark" round>{{ theme.emoji }} {{ theme.name }}</el-tag>
          </div>
          <h1 class="cover-title">{{ topicData.title || item?.title }}</h1>
          <div class="cover-meta">
            <span v-if="topicData.platform" class="meta-chip">{{ topicData.platform }}</span>
            <span v-if="topicData.content_type" class="meta-chip">{{ topicData.content_type }}</span>
            <span v-if="topicData.hook_type" class="meta-chip">{{ topicData.hook_type }}</span>
            <span v-if="topicData.lifecycle_stage" class="meta-chip">{{ topicData.lifecycle_stage }}</span>
          </div>
        </div>
        <div class="cover-score" v-if="topicData.opportunity_score">
          <div class="score-ring">
            <span class="score-num">{{ topicData.opportunity_score }}</span>
            <span class="score-unit">分</span>
          </div>
        </div>
      </div>

      <div class="intel-report-section" v-if="topicData.topic_description">
        <div class="intel-report-section-title">📋 核心摘要</div>
        <div class="summary-text">{{ topicData.topic_description }}</div>
      </div>

      <div class="intel-report-section" v-if="topicData.score_breakdown && Object.keys(topicData.score_breakdown).length">
        <div class="intel-report-section-title">📊 机会评分细项</div>
        <div class="score-overview">
          <div class="score-big" :style="{ color: getScoreColor(topicData.opportunity_score || 0) }">
            {{ topicData.opportunity_score || 0 }}
          </div>
          <div class="score-label">综合评分</div>
        </div>
        <div class="score-bars-grid">
          <div v-for="(val, key) in topicData.score_breakdown" :key="key" class="score-bar-item">
            <div class="score-bar-header">
              <span class="score-bar-key">{{ scoreLabel(String(key)) }}</span>
              <span class="score-bar-val" :style="{ color: getScoreColor(Number(val) * 10) }">{{ val }}/10</span>
            </div>
            <div class="score-bar-track">
              <div class="score-bar-fill" :style="{ width: Number(val) * 10 + '%', background: getScoreColor(Number(val) * 10) }"></div>
            </div>
          </div>
        </div>
      </div>

      <div class="intel-report-section" v-if="topicData.decision_layer">
        <div class="intel-report-section-title">🧠 决策分析</div>
        <div class="decision-meta" v-if="topicData.decision_layer.core_decision_type">
          <el-tag type="warning" size="large">{{ topicData.decision_layer.core_decision_type }}</el-tag>
          <span class="decision-sub" v-if="topicData.decision_layer.sub_scenario">{{ topicData.decision_layer.sub_scenario }}</span>
        </div>
        <div class="persona-grid" v-if="topicData.decision_layer.persona_decision_map?.length">
          <div v-for="(pm, idx) in topicData.decision_layer.persona_decision_map" :key="idx" class="intel-persona-card">
            <div class="persona-tag">
              <el-tag size="small" type="info">{{ pm.persona }}</el-tag>
            </div>
            <div class="persona-field" v-if="pm.current_state">
              <span class="pf-label">现状</span>
              <span class="pf-value">{{ pm.current_state }}</span>
            </div>
            <div class="persona-field" v-if="pm.decision_pressure">
              <span class="pf-label">决策压力</span>
              <span class="pf-value">{{ pm.decision_pressure }}</span>
            </div>
            <div class="persona-field highlight" v-if="pm.recommended_direction">
              <span class="pf-label">推荐方向</span>
              <span class="pf-value">{{ pm.recommended_direction }}</span>
            </div>
            <div class="persona-field" v-if="pm.why_now">
              <span class="pf-label">为什么现在</span>
              <span class="pf-value">{{ pm.why_now }}</span>
            </div>
            <div class="persona-field warn" v-if="pm.avoid_mistake">
              <span class="pf-label">避坑</span>
              <span class="pf-value">{{ pm.avoid_mistake }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="intel-report-section" v-if="topicData.user_psychology">
        <div class="intel-report-section-title">💭 用户心理分析</div>
        <div class="psychology-grid">
          <div class="psy-card anxiety" v-if="topicData.user_psychology.anxiety">
            <div class="psy-icon">😰</div>
            <div class="psy-label">焦虑</div>
            <div class="psy-value">{{ topicData.user_psychology.anxiety }}</div>
          </div>
          <div class="psy-card desire" v-if="topicData.user_psychology.desire">
            <div class="psy-icon">✨</div>
            <div class="psy-label">渴望</div>
            <div class="psy-value">{{ topicData.user_psychology.desire }}</div>
          </div>
          <div class="psy-card fear" v-if="topicData.user_psychology.fear">
            <div class="psy-icon">😨</div>
            <div class="psy-label">恐惧</div>
            <div class="psy-value">{{ topicData.user_psychology.fear }}</div>
          </div>
          <div class="psy-card driver" v-if="topicData.user_psychology.paying_driver">
            <div class="psy-icon">💳</div>
            <div class="psy-label">付费驱动</div>
            <div class="psy-value">{{ topicData.user_psychology.paying_driver }}</div>
          </div>
        </div>
      </div>

      <div class="intel-report-section" v-if="topicData.commercial_paths?.length">
        <div class="intel-report-section-title">💰 商业化路径</div>
        <div class="paths-grid">
          <div v-for="(cp, idx) in topicData.commercial_paths" :key="idx" class="intel-path-card">
            <div class="path-index">{{ idx + 1 }}</div>
            <div class="path-content" v-if="typeof cp === 'object'">
              <div class="path-type" v-if="(cp as Record<string, unknown>).type">{{ (cp as Record<string, unknown>).type }}</div>
              <div class="path-desc" v-if="(cp as Record<string, unknown>).description">{{ (cp as Record<string, unknown>).description }}</div>
              <div class="path-price" v-if="(cp as Record<string, unknown>).price_range">💰 {{ (cp as Record<string, unknown>).price_range }}</div>
            </div>
            <div class="path-content" v-else>{{ cp }}</div>
          </div>
        </div>
      </div>

      <div class="intel-report-section" v-if="topicData.content_angles?.length">
        <div class="intel-report-section-title">📝 内容角度</div>
        <div class="angles-list">
          <div v-for="(angle, idx) in topicData.content_angles" :key="idx" class="angle-item">
            <span class="angle-num">{{ idx + 1 }}</span>
            <span class="angle-text">{{ angle }}</span>
          </div>
        </div>
      </div>

      <div class="intel-report-section" v-if="topicData.risk_warnings?.length || topicData.risk_matrix">
        <div class="intel-report-section-title">⚠️ 风险评估</div>
        <div class="risk-warnings" v-if="topicData.risk_warnings?.length">
          <div v-for="(rw, idx) in topicData.risk_warnings" :key="idx" class="intel-risk-card">
            <el-icon style="color: var(--intel-danger); margin-right: 8px"><WarningFilled /></el-icon>
            {{ rw }}
          </div>
        </div>
        <div class="risk-matrix" v-if="topicData.risk_matrix">
          <div v-for="(val, key) in topicData.risk_matrix" :key="key" class="rm-item">
            <span class="rm-label">{{ riskLabel(String(key)) }}</span>
            <div class="rm-stars">
              <span v-for="n in 10" :key="n" class="rm-star" :class="{ active: n <= Number(val) }">★</span>
            </div>
            <span class="rm-val">{{ val }}/10</span>
          </div>
        </div>
      </div>

      <div class="intel-report-section" v-if="topicData.lifecycle_stage || topicData.lifecycle_prediction">
        <div class="intel-report-section-title">📅 生命周期预测</div>
        <div class="lifecycle-status" v-if="topicData.lifecycle_stage">
          <el-tag type="success" size="large" effect="dark">{{ topicData.lifecycle_stage }}</el-tag>
        </div>
        <div class="lifecycle-timeline" v-if="topicData.lifecycle_prediction">
          <div v-for="(pred, key) in topicData.lifecycle_prediction" :key="key" class="intel-timeline-item">
            <div class="tl-key">{{ key }}</div>
            <div class="tl-val">{{ pred }}</div>
          </div>
        </div>
      </div>

      <div class="intel-report-section" v-if="topicData.keywords?.length">
        <div class="intel-report-section-title">🏷️ 关键词标签</div>
        <div class="tags-wrap">
          <el-tag v-for="kw in topicData.keywords" :key="kw" effect="plain" round>{{ kw }}</el-tag>
        </div>
      </div>

      <div class="intel-report-section" v-if="topicData.target_audience">
        <div class="intel-report-section-title">👥 目标受众</div>
        <div class="audience-text">{{ topicData.target_audience }}</div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import { useRoute } from "vue-router"
import { ArrowLeft, Download, View, WarningFilled } from "@element-plus/icons-vue"
import api from "@/utils/api"
import { exportJSON, fetchWithCache } from "@/utils/intel"
import { getThemeByCategory, getThemeKeyByCategory, getScoreColor } from "@/utils/theme"

interface TopicItem {
  id?: string
  title: string
  platform?: string
  content_type?: string
  hook_type?: string
  emotion?: string
  ctr_prediction?: number
  competition?: string
  topic_data?: Record<string, unknown>
  [key: string]: unknown
}

const SCORE_LABELS: Record<string, string> = {
  traffic_growth: "流量增长",
  willingness_to_pay: "付费意愿",
  competition_level: "竞争水平",
  platform_support: "平台支持",
  ai_scalability: "AI可扩展性",
  virtual_product_fit: "虚拟产品适配",
  anxiety_intensity: "焦虑强度",
  lifecycle: "生命周期",
  low_cost_entry: "低成本进入",
  ordinary_person_fit: "普通人适配",
}

const RISK_LABELS: Record<string, string> = {
  time_cost: "时间成本",
  money_cost: "资金成本",
  execution_difficulty: "执行难度",
  platform_risk: "平台风险",
}

function scoreLabel(key: string): string {
  return SCORE_LABELS[key] || key
}

function riskLabel(key: string): string {
  return RISK_LABELS[key] || key
}

const route = useRoute()
const reportRoot = ref<HTMLElement>()
const item = ref<TopicItem | null>(null)
const loading = ref(true)

const topicData = computed(() => {
  if (!item.value?.topic_data) return null
  return item.value.topic_data as Record<string, any>
})

const category = computed(() => {
  const td = topicData.value
  if (!td) return ""
  return td.category || td.decision_layer?.core_decision_type || ""
})

const theme = computed(() => getThemeByCategory(category.value))

const themeKey = computed(() => getThemeKeyByCategory(category.value))

const coverGradientClass = computed(() => `intel-gradient-${themeKey.value}`)

const cssVars = computed(() => ({
  "--domain-primary": theme.value.primary,
  "--domain-accent": theme.value.accent,
  "--domain-bg": theme.value.bg,
}))

const pdfUrl = ref("")
const htmlUrl = ref("")

async function loadReportFiles() {
  if (!item.value) return
  try {
    const { data } = await api.get("/intel/reports")
    const reports = data?.items || data || []
    const sourceId = (item.value as any)?.source_topic_id || ""
    for (const r of reports) {
      const rTitle = (r.title || "").toLowerCase()
      const iTitle = (item.value?.title || "").toLowerCase()
      const titleMatch = rTitle && iTitle && (rTitle.includes(iTitle.slice(0, 10)) || iTitle.includes(rTitle.slice(0, 10)))
      const idMatch = sourceId && r.file_path && r.file_path.includes(sourceId)
      if (titleMatch || idMatch) {
        const url = r.file_path || r.url || ""
        if (url.endsWith(".pdf")) pdfUrl.value = url
        else if (url.endsWith(".html") || url.endsWith(".htm")) htmlUrl.value = url
      }
    }
    if (sourceId && !pdfUrl.value) {
      const directPdf = `/static/reports/${sourceId}_report.pdf`
      try {
        const check = await fetch(directPdf, { method: "HEAD" })
        if (check.ok) pdfUrl.value = directPdf
      } catch {}
    }
  } catch {}
}

function doExportJSON() {
  if (!item.value) return
  exportJSON(item.value, item.value.title || "选题报告")
}

function downloadPDF() {
  if (!pdfUrl.value) return
  const a = document.createElement("a")
  a.href = pdfUrl.value
  a.download = `${item.value?.title || "报告"}.pdf`
  a.target = "_blank"
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

function viewHTML() {
  if (!htmlUrl.value) return
  window.open(htmlUrl.value, "_blank")
}

onMounted(async () => {
  loading.value = true
  try {
    const topicId = route.params.topicId as string
    const items = await fetchWithCache<TopicItem>("topics", "/intel/topics")
    item.value = items.find((t) => t.id === topicId) || null
    if (item.value) await loadReportFiles()
  } catch {
    item.value = null
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.report-page {
  max-width: 900px;
  margin: 0 auto;
  padding-bottom: 60px;
}
.loading-wrap { padding: 40px; }
.report-content { }

.report-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-lg);
}
.back-btn { font-weight: 500; }
.toolbar-actions { display: flex; gap: var(--spacing-sm); }

.intel-report-cover {
  position: relative;
  border-radius: var(--intel-radius-xl);
  padding: var(--spacing-2xl) var(--spacing-xl);
  color: #fff;
  margin-bottom: var(--spacing-2xl);
  overflow: hidden;
}
.cover-inner { position: relative; z-index: 1; }
.cover-badge { margin-bottom: var(--spacing-md); }
.cover-title {
  font-size: var(--font-size-3xl);
  font-weight: 800;
  line-height: 1.3;
  margin-bottom: var(--spacing-md);
  letter-spacing: -0.5px;
}
.cover-meta {
  display: flex;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}
.meta-chip {
  padding: 4px 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(4px);
  font-size: var(--font-size-sm);
}
.cover-score {
  position: absolute;
  right: 40px;
  top: 50%;
  transform: translateY(-50%);
}
.score-ring {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  border: 4px solid rgba(255, 255, 255, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(4px);
}
.score-num { font-size: var(--font-size-2xl); font-weight: 800; }
.score-unit { font-size: var(--font-size-xs); opacity: 0.7; }

.intel-report-section {
  margin-bottom: var(--spacing-xl);
  animation: fade-in 0.4s ease both;
}
.intel-report-section-title {
  font-size: var(--font-size-lg);
  font-weight: 700;
  color: var(--intel-text);
  margin-bottom: var(--spacing-md);
  padding-bottom: var(--spacing-sm);
  border-bottom: 2px solid var(--intel-border-light);
}

.summary-text {
  font-size: var(--font-size-md);
  line-height: 1.8;
  color: var(--intel-text);
  background: var(--intel-bg);
  padding: var(--spacing-md) var(--spacing-lg);
  border-radius: var(--intel-radius);
  border-left: 4px solid var(--domain-accent);
}

.score-overview {
  text-align: center;
  margin-bottom: var(--spacing-lg);
}
.score-big {
  font-size: 56px;
  font-weight: 800;
  line-height: 1;
}
.score-label {
  font-size: var(--font-size-sm);
  color: var(--intel-text-secondary);
  margin-top: 4px;
}
.score-bars-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-md);
}
.score-bar-item {
  background: var(--intel-bg);
  border-radius: var(--intel-radius);
  padding: 10px 14px;
}
.score-bar-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
}
.score-bar-key { font-size: var(--font-size-sm); color: var(--intel-text-secondary); }
.score-bar-val { font-size: var(--font-size-sm); font-weight: 700; }
.score-bar-track {
  height: 6px;
  background: var(--intel-border);
  border-radius: 3px;
  overflow: hidden;
}
.score-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.6s ease;
}

.decision-meta {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}
.decision-sub { font-size: var(--font-size-md); color: var(--intel-text-secondary); font-weight: 500; }
.persona-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--spacing-md);
}
.intel-persona-card {
  background: var(--intel-surface);
  border-radius: var(--intel-radius-lg);
  padding: var(--spacing-md) var(--spacing-lg);
  box-shadow: var(--intel-shadow);
  transition: all var(--transition-base);
}
.intel-persona-card:hover {
  box-shadow: var(--intel-shadow-hover);
}
.persona-tag { margin-bottom: var(--spacing-sm); }
.persona-field {
  font-size: var(--font-size-sm);
  color: var(--intel-text-secondary);
  line-height: 1.6;
  padding: 6px 0;
  border-bottom: 1px solid var(--intel-border-light);
}
.persona-field:last-child { border-bottom: none; }
.pf-label {
  color: var(--intel-text-secondary);
  font-weight: 500;
  margin-right: var(--spacing-sm);
  font-size: var(--font-size-xs);
}
.pf-value { color: var(--intel-text); }
.persona-field.highlight {
  background: #ecfdf5;
  border-radius: var(--intel-radius);
  padding: 8px 10px;
  color: var(--intel-success);
  font-weight: 500;
  border-bottom: none;
}
.persona-field.warn {
  background: #fef2f2;
  border-radius: var(--intel-radius);
  padding: 8px 10px;
  color: var(--intel-danger);
  border-bottom: none;
}

.psychology-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-md);
}
.psy-card {
  border-radius: var(--intel-radius-lg);
  padding: var(--spacing-lg);
  text-align: center;
  transition: all var(--transition-base);
}
.psy-card:hover { transform: translateY(-2px); }
.psy-card.anxiety { background: #fef2f2; border: 1px solid #fecaca; }
.psy-card.desire { background: #ecfdf5; border: 1px solid #a7f3d0; }
.psy-card.fear { background: #fdf6ec; border: 1px solid #fde68a; }
.psy-card.driver { background: #eff6ff; border: 1px solid #bfdbfe; }
.psy-icon { font-size: 28px; margin-bottom: 6px; }
.psy-label { font-size: var(--font-size-xs); color: var(--intel-text-secondary); margin-bottom: 6px; }
.psy-value { font-size: var(--font-size-sm); color: var(--intel-text); line-height: 1.6; }

.paths-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--spacing-sm);
}
.intel-path-card {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-md);
  padding: var(--spacing-sm) 0;
}
.path-index {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--intel-success);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-sm);
  font-weight: 700;
  flex-shrink: 0;
}
.path-content { flex: 1; }
.path-type { font-weight: 700; color: var(--intel-success); margin-bottom: 4px; }
.path-desc { font-size: var(--font-size-sm); color: var(--intel-text); line-height: 1.6; }
.path-price { font-size: var(--font-size-sm); color: var(--intel-warning); margin-top: 4px; }

.angles-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}
.angle-item {
  display: flex;
  gap: var(--spacing-md);
  align-items: flex-start;
  font-size: var(--font-size-sm);
  color: var(--intel-text);
  line-height: 1.6;
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--intel-bg);
  border-radius: var(--intel-radius);
}
.angle-num {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--domain-accent);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-xs);
  font-weight: 700;
  flex-shrink: 0;
}
.angle-text { flex: 1; }

.risk-warnings {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}
.intel-risk-card {
  display: flex;
  align-items: center;
  font-size: var(--font-size-sm);
  background: #fef2f2;
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--intel-radius);
}
.risk-matrix {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-md);
}
.rm-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  background: var(--intel-bg);
  border-radius: var(--intel-radius);
  padding: 10px 14px;
}
.rm-label { font-size: var(--font-size-sm); color: var(--intel-text-secondary); min-width: 70px; }
.rm-stars { display: flex; gap: 1px; }
.rm-star {
  font-size: var(--font-size-xs);
  color: var(--intel-border);
  transition: color 0.2s;
}
.rm-star.active { color: var(--intel-warning); }
.rm-val { font-size: var(--font-size-sm); font-weight: 700; color: var(--intel-text); }

.lifecycle-status { margin-bottom: var(--spacing-md); }
.lifecycle-timeline {
  display: flex;
  flex-direction: column;
  gap: 0;
}
.intel-timeline-item {
  padding: var(--spacing-sm) var(--spacing-md);
  border-left: 3px solid var(--domain-accent);
  margin-left: 8px;
  margin-bottom: var(--spacing-sm);
}
.tl-key {
  font-size: var(--font-size-xs);
  color: var(--intel-text-secondary);
  font-weight: 500;
}
.tl-val {
  font-size: var(--font-size-sm);
  color: var(--intel-text);
  line-height: 1.6;
}

.tags-wrap {
  display: flex;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}
.audience-text {
  font-size: var(--font-size-sm);
  color: var(--intel-text);
  line-height: 1.8;
  background: var(--intel-bg);
  padding: var(--spacing-md) var(--spacing-lg);
  border-radius: var(--intel-radius);
}

@media (max-width: 768px) {
  .cover-score { position: static; transform: none; margin-top: var(--spacing-md); }
  .score-bars-grid { grid-template-columns: 1fr; }
  .psychology-grid { grid-template-columns: 1fr; }
  .risk-matrix { grid-template-columns: 1fr; }
  .cover-title { font-size: var(--font-size-2xl); }
}
</style>
