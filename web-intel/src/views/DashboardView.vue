<template>
  <div class="dashboard">
    <UpgradeBanner />
    <section v-if="showDailyBrief && intel.dashboard" class="daily-brief">
      <div class="brief-header">
        <h3>📡 今日副业简报</h3>
        <el-button type="primary" link @click="$router.push('/reports')">查看本周决策报告 →</el-button>
      </div>
      <div class="brief-grid">
        <div class="brief-card brief-signal" v-if="briefSignal">
          <div class="brief-label">今日信号</div>
          <div class="brief-title">{{ briefSignal.title }}</div>
          <p class="brief-text">{{ briefSignal.text }}</p>
        </div>
        <div class="brief-card brief-risk" v-if="briefRisk">
          <div class="brief-label">风险提醒</div>
          <div class="brief-title">{{ briefRisk.name }}</div>
          <p class="brief-text">{{ briefRisk.reason }}</p>
        </div>
        <div class="brief-card brief-action" v-if="briefAction">
          <div class="brief-label">今日行动</div>
          <div class="brief-title">{{ briefAction.name }}</div>
          <p class="brief-text">{{ briefAction.text }}</p>
        </div>
      </div>
    </section>

    <div class="page-header">
      <div class="header-title-area">
        <h2>商业情报仪表盘</h2>
        <p class="header-subtitle" v-if="intel.dashboard">AI 副业趋势 · 机会 · 风险 实时监控</p>
      </div>
      <el-tag v-if="intel.dashboard" type="success" size="small" effect="dark" class="live-tag">
        <span class="live-dot"></span>
        {{ planLabel }} · 数据实时更新
      </el-tag>
    </div>

    <div class="stat-row" v-if="intel.dashboard">
      <div class="stat-card stat-trend">
        <div class="stat-bg"></div>
        <div class="stat-content">
          <div class="stat-icon-wrap">
            <el-icon :size="22"><TrendCharts /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ intel.dashboard.summary.active_trends }}</div>
            <div class="stat-label">活跃趋势</div>
          </div>
        </div>
        <div class="stat-sparkline" v-if="trendSparkline.length">
          <svg viewBox="0 0 60 20" preserveAspectRatio="none">
            <polyline :points="trendSparkline" fill="none" stroke="rgba(255,255,255,0.5)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </div>
      </div>
      <div class="stat-card stat-opp">
        <div class="stat-bg"></div>
        <div class="stat-content">
          <div class="stat-icon-wrap">
            <el-icon :size="22"><Opportunity /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ intel.dashboard.summary.recommended_opportunities }}</div>
            <div class="stat-label">推荐机会</div>
          </div>
        </div>
        <div class="stat-sparkline" v-if="oppSparkline.length">
          <svg viewBox="0 0 60 20" preserveAspectRatio="none">
            <polyline :points="oppSparkline" fill="none" stroke="rgba(255,255,255,0.5)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </div>
      </div>
      <div class="stat-card stat-risk">
        <div class="stat-bg"></div>
        <div class="stat-content">
          <div class="stat-icon-wrap">
            <el-icon :size="22"><Warning /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ intel.dashboard.summary.active_risks }}</div>
            <div class="stat-label">活跃风险</div>
          </div>
        </div>
        <div class="stat-sparkline" v-if="riskSparkline.length">
          <svg viewBox="0 0 60 20" preserveAspectRatio="none">
            <polyline :points="riskSparkline" fill="none" stroke="rgba(255,255,255,0.5)" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </div>
      </div>
    </div>

    <el-row :gutter="20" style="margin-top: 24px">
      <el-col :xs="24" :sm="24" :md="12">
        <el-card shadow="hover" class="section-card">
          <template #header>
            <div class="card-header">
              <span class="card-header-title">
                <span class="card-header-icon trend-icon">📈</span>
                热门趋势
              </span>
              <el-button text type="primary" size="small" @click="$router.push('/trends')">
                查看全部 <el-icon :size="12"><Right /></el-icon>
              </el-button>
            </div>
          </template>
          <div v-if="intel.loading" class="loading-placeholder">
            <el-skeleton :rows="5" animated />
          </div>
          <div v-else-if="!intel.dashboard?.top_trends?.length" class="intel-empty-state">
            <div class="intel-empty-state-icon">📊</div>
            <div class="intel-empty-state-text">暂无趋势数据</div>
          </div>
          <div v-else class="trend-list intel-card-stagger">
            <div v-for="item in intel.dashboard.top_trends" :key="item.id" class="trend-item" @click="$router.push('/trends')">
              <div class="trend-left">
                <span class="trend-direction" :class="'dir-' + item.direction">
                  {{ getDirectionIcon(item.direction) }}
                </span>
              </div>
              <div class="trend-right">
                <div class="trend-title">{{ item.title }}</div>
                <div class="trend-meta">
                  <el-tag size="small" effect="plain">{{ item.category }}</el-tag>
                  <span class="trend-score" :style="{ color: getScoreColor(item.opportunity_score) }">
                    {{ item.opportunity_score }}分
                  </span>
                  <el-tag size="small" v-if="item.lifecycle" type="success" effect="plain">{{ item.lifecycle }}</el-tag>
                </div>
              </div>
              <div class="trend-score-badge" :style="{ color: getScoreColor(item.opportunity_score), borderColor: getScoreColor(item.opportunity_score) + '40' }">
                {{ item.opportunity_score }}
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="24" :md="12">
        <el-card shadow="hover" class="section-card">
          <template #header>
            <div class="card-header">
              <span class="card-header-title">
                <span class="card-header-icon opp-icon">💡</span>
                推荐机会
              </span>
              <el-button text type="primary" size="small" @click="$router.push('/opportunities')">
                查看全部 <el-icon :size="12"><Right /></el-icon>
              </el-button>
            </div>
          </template>
          <div v-if="intel.loading" class="loading-placeholder">
            <el-skeleton :rows="5" animated />
          </div>
          <div v-else-if="!intel.dashboard?.top_opportunities?.length" class="intel-empty-state">
            <div class="intel-empty-state-icon">🎯</div>
            <div class="intel-empty-state-text">暂无机会数据</div>
          </div>
          <div v-else class="opp-list intel-card-stagger">
            <div v-for="item in intel.dashboard.top_opportunities" :key="item.id" class="opp-item" :class="'verdict-' + (item.verdict || '').toLowerCase()" @click="$router.push('/opportunities')">
              <div class="opp-left">
                <div class="opp-score-ring" :style="{ borderColor: getScoreColor(item.verdict_score) }">
                  <span :style="{ color: getScoreColor(item.verdict_score) }">{{ item.verdict_score }}</span>
                </div>
              </div>
              <div class="opp-right">
                <div class="opp-title">{{ item.name }}</div>
                <div class="opp-meta">
                  <el-tag size="small" effect="plain">{{ item.category }}</el-tag>
                  <el-tag size="small" v-if="item.difficulty" effect="plain">{{ item.difficulty }}</el-tag>
                </div>
              </div>
              <el-tag v-if="item.verdict" size="small" :type="verdictType(item.verdict)" effect="dark" class="opp-verdict-tag">{{ item.verdict }}</el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 24px">
      <el-col :xs="24" :sm="24" :md="12">
        <el-card shadow="hover" class="section-card">
          <template #header>
            <div class="card-header">
              <span class="card-header-title">
                <span class="card-header-icon chart-icon">📊</span>
                趋势评分分布
              </span>
            </div>
          </template>
          <div class="chart-container">
            <Bar v-if="trendChartData" :data="trendChartData" :options="barChartOptions" />
            <div v-else class="intel-empty-state">
              <div class="intel-empty-state-icon">📉</div>
              <div class="intel-empty-state-text">暂无图表数据</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="24" :md="12">
        <el-card shadow="hover" class="section-card">
          <template #header>
            <div class="card-header">
              <span class="card-header-title">
                <span class="card-header-icon risk-icon">⚠️</span>
                风险等级分布
              </span>
            </div>
          </template>
          <div class="chart-container">
            <Doughnut v-if="riskChartData" :data="riskChartData" :options="doughnutOpts" />
            <div v-else class="intel-empty-state">
              <div class="intel-empty-state-icon">🛡️</div>
              <div class="intel-empty-state-text">暂无图表数据</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 24px">
      <el-col :span="24">
        <el-card shadow="hover" class="section-card">
          <template #header>
            <div class="card-header">
              <span class="card-header-title">
                <span class="card-header-icon alert-icon">🚨</span>
                风险预警
              </span>
              <el-button text type="primary" size="small" @click="$router.push('/risks')">
                查看全部 <el-icon :size="12"><Right /></el-icon>
              </el-button>
            </div>
          </template>
          <div v-if="intel.loading" class="loading-placeholder">
            <el-skeleton :rows="3" animated />
          </div>
          <div v-else-if="!intel.dashboard?.top_risks?.length" class="intel-empty-state">
            <div class="intel-empty-state-icon">✅</div>
            <div class="intel-empty-state-text">当前无活跃风险</div>
          </div>
          <div v-else class="risk-list intel-card-stagger">
            <div v-for="item in intel.dashboard.top_risks" :key="item.id" class="risk-item" :class="'severity-' + (item.severity || '').toLowerCase()" @click="$router.push('/risks')">
              <div class="risk-severity-dot" :class="{ 'pulse-active': (item.severity || '').toLowerCase() === 'high' }"></div>
              <div class="risk-name">{{ item.name }}</div>
              <div class="risk-reason">{{ item.reason }}</div>
              <div class="risk-alt" v-if="item.alternative">
                <el-icon><Right /></el-icon> {{ item.alternative }}
              </div>
              <el-tag :type="severityTagType(item.severity)" size="small" effect="dark">{{ item.severity }}</el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { onMounted, computed } from "vue"
import { useIntelStore } from "@/stores/intel"
import { useIntelAuthStore } from "@/stores/auth"
import UpgradeBanner from "@/components/UpgradeBanner.vue"
import { TrendCharts, Opportunity, Warning, Right } from "@element-plus/icons-vue"
import { getScoreColor, getDirectionIcon } from "@/utils/theme"
import { Bar, Doughnut } from "vue-chartjs"
import { defaultChartOptions, doughnutOptions, chartColors } from "@/utils/charts"
import type { ChartData } from "chart.js"

const intel = useIntelStore()
const auth = useIntelAuthStore()

const planLabel = computed(() => auth.planLabel)

const showDailyBrief = computed(() => auth.planName === "weekly")

const briefSignal = computed(() => {
  const t = intel.dashboard?.top_trends?.[0]
  if (!t) return null
  const ext = t as { actionable_insight?: string; evidence?: string }
  return {
    title: t.title,
    text: ext.actionable_insight || ext.evidence || `${t.category} · 机会分 ${t.opportunity_score}`,
  }
})

const briefRisk = computed(() => {
  const r = intel.dashboard?.top_risks?.[0]
  if (!r) return null
  return { name: r.name, reason: r.reason || r.alternative || "请关注风险变化" }
})

const briefAction = computed(() => {
  const o = intel.dashboard?.top_opportunities?.[0]
  if (!o) return null
  const paths = o.commercial_paths
  const text = Array.isArray(paths) && paths.length ? String(paths[0]) : `评分 ${o.verdict_score} · ${o.persona_fit || "查看机会详情"}`
  return { name: o.name, text }
})

function generateSparkline(count: number): string {
  const points: string[] = []
  for (let i = 0; i < count; i++) {
    const x = (i / (count - 1)) * 60
    const y = 20 - (Math.random() * 12 + 4)
    points.push(`${x.toFixed(1)},${y.toFixed(1)}`)
  }
  return points.join(" ")
}

const trendSparkline = computed(() => generateSparkline(8))
const oppSparkline = computed(() => generateSparkline(8))
const riskSparkline = computed(() => generateSparkline(8))

const trendChartData = computed<ChartData<"bar"> | null>(() => {
  const trends = intel.dashboard?.top_trends
  if (!trends?.length) return null
  return {
    labels: trends.map((t) => t.title.length > 8 ? t.title.slice(0, 8) + "…" : t.title),
    datasets: [{
      label: "机会评分",
      data: trends.map((t) => t.opportunity_score),
      backgroundColor: trends.map((t) => getScoreColor(t.opportunity_score) + "cc"),
      borderColor: trends.map((t) => getScoreColor(t.opportunity_score)),
      borderWidth: 1,
      borderRadius: 6,
    }],
  }
})

const riskChartData = computed<ChartData<"doughnut"> | null>(() => {
  const risks = intel.dashboard?.top_risks
  if (!risks?.length) return null
  const counts: Record<string, number> = {}
  for (const r of risks) {
    const s = (r.severity || "low").toLowerCase()
    counts[s] = (counts[s] || 0) + 1
  }
  const labels: string[] = []
  const data: number[] = []
  const bg: string[] = []
  const colorMap: Record<string, string> = { high: chartColors.danger, medium: chartColors.warning, low: chartColors.success }
  const labelMap: Record<string, string> = { high: "高风险", medium: "中风险", low: "低风险" }
  for (const [k, v] of Object.entries(counts)) {
    labels.push(labelMap[k] || k)
    data.push(v)
    bg.push(colorMap[k] || chartColors.info)
  }
  return { labels, datasets: [{ data, backgroundColor: bg, borderWidth: 0 }] }
})

const barChartOptions = {
  ...defaultChartOptions,
  plugins: { ...defaultChartOptions.plugins, legend: { display: false } },
}

const doughnutOpts = doughnutOptions

function severityTagType(severity: string): string {
  const map: Record<string, string> = { high: "danger", medium: "warning", low: "info" }
  return map[severity?.toLowerCase()] || "info"
}

function verdictType(verdict: string): string {
  const map: Record<string, string> = { RECOMMENDED: "success", CAUTION: "warning", AVOID: "danger" }
  return map[verdict] || "info"
}

onMounted(() => {
  intel.fetchDashboard()
})
</script>

<style scoped>
.dashboard { max-width: 1400px; }

.daily-brief {
  margin-bottom: 24px;
  padding: 20px;
  border-radius: 12px;
  background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%);
  color: #e2e8f0;
}
.brief-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.brief-header h3 {
  margin: 0;
  font-size: 18px;
}
.brief-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}
.brief-card {
  padding: 14px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.1);
}
.brief-label {
  font-size: 12px;
  opacity: 0.85;
  margin-bottom: 6px;
}
.brief-title {
  font-weight: 600;
  font-size: 15px;
  margin-bottom: 6px;
}
.brief-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
  opacity: 0.9;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;
}

.header-title-area h2 {
  margin: 0;
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--intel-text);
}

.header-subtitle {
  margin: 4px 0 0;
  font-size: var(--font-size-sm);
  color: var(--intel-text-secondary);
}

.live-tag {
  display: flex;
  align-items: center;
  gap: 6px;
}

.live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #67c23a;
  animation: pulse-ring 2s ease-in-out infinite;
  box-shadow: 0 0 0 0 rgba(103, 194, 58, 0.4);
}

.stat-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.stat-card {
  border-radius: var(--intel-radius-xl);
  overflow: hidden;
  position: relative;
  color: #fff;
  min-height: 110px;
  transition: transform var(--transition-base), box-shadow var(--transition-base);
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--intel-shadow-elevated);
}

.stat-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
}

.stat-trend .stat-bg { background: linear-gradient(135deg, #1E3A5F 0%, #2563EB 100%); }
.stat-opp .stat-bg { background: linear-gradient(135deg, #059669 0%, #10b981 100%); }
.stat-risk .stat-bg { background: linear-gradient(135deg, #d97706 0%, #f59e0b 100%); }

.stat-content {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px;
}

.stat-icon-wrap {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(4px);
}

.stat-value {
  font-size: 32px;
  font-weight: 800;
  line-height: 1;
  letter-spacing: -0.5px;
}

.stat-label {
  font-size: var(--font-size-sm);
  opacity: 0.85;
  margin-top: 4px;
  font-weight: 500;
}

.stat-sparkline {
  position: absolute;
  bottom: 8px;
  right: 16px;
  width: 60px;
  height: 20px;
  opacity: 0.6;
}

.section-card {
  border-radius: var(--intel-radius-lg);
  border: none;
  box-shadow: var(--intel-shadow);
  transition: box-shadow var(--transition-base);
}

.section-card:hover {
  box-shadow: var(--intel-shadow-hover);
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.card-header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: var(--font-size-base);
}

.card-header-icon {
  font-size: 16px;
}

.loading-placeholder { padding: 16px; }

.trend-list { display: flex; flex-direction: column; gap: 2px; }
.trend-item {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 12px 10px;
  border-radius: var(--intel-radius);
  transition: background var(--transition-fast);
  cursor: pointer;
}
.trend-item:hover { background: #f8f9fa; }
.trend-left { padding-top: 2px; }
.trend-direction {
  font-size: 18px;
  font-weight: 700;
}
.dir-rising { color: #059669; }
.dir-stable { color: #2563eb; }
.dir-falling { color: #dc2626; }
.trend-right { flex: 1; min-width: 0; }
.trend-title {
  font-size: var(--font-size-base);
  font-weight: 500;
  color: var(--intel-text);
  margin-bottom: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.trend-meta {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}
.trend-score {
  font-size: 13px;
  font-weight: 700;
}
.trend-score-badge {
  font-size: 18px;
  font-weight: 800;
  border: 2px solid;
  border-radius: 8px;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.opp-list { display: flex; flex-direction: column; gap: 2px; }
.opp-item {
  display: flex;
  gap: 14px;
  align-items: center;
  padding: 12px 10px;
  border-radius: var(--intel-radius);
  border-left: 3px solid transparent;
  transition: background var(--transition-fast);
  cursor: pointer;
}
.opp-item:hover { background: #f8f9fa; }
.opp-item.verdict-recommended { border-left-color: #059669; }
.opp-item.verdict-caution { border-left-color: #d97706; }
.opp-item.verdict-avoid { border-left-color: #dc2626; }
.opp-score-ring {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  border: 3px solid;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.opp-score-ring span {
  font-size: 14px;
  font-weight: 800;
}
.opp-right { flex: 1; min-width: 0; }
.opp-title {
  font-size: var(--font-size-base);
  font-weight: 500;
  color: var(--intel-text);
  margin-bottom: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.opp-meta {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.opp-verdict-tag {
  flex-shrink: 0;
  font-size: 11px;
}

.risk-list { display: flex; flex-direction: column; gap: 10px; }
.risk-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  border-radius: var(--intel-radius);
  border-left: 4px solid transparent;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.risk-item:hover {
  box-shadow: var(--intel-shadow);
}
.risk-item.severity-high { border-left-color: #dc2626; background: #fef2f2; }
.risk-item.severity-medium { border-left-color: #d97706; background: #fdf6ec; }
.risk-item.severity-low { border-left-color: #059669; background: #f0f9eb; }
.risk-severity-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.severity-high .risk-severity-dot { background: #dc2626; }
.severity-medium .risk-severity-dot { background: #d97706; }
.severity-low .risk-severity-dot { background: #059669; }
.pulse-active {
  animation: pulse-ring 2s ease-in-out infinite;
}
.risk-name { font-size: var(--font-size-base); font-weight: 600; color: var(--intel-text); min-width: 140px; }
.risk-reason { font-size: 13px; color: #606266; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.risk-alt {
  font-size: var(--font-size-sm);
  color: #059669;
  font-weight: 500;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 4px;
}
.chart-container {
  height: 280px;
  padding: 8px;
}

@media (max-width: 768px) {
  .stat-row {
    grid-template-columns: 1fr;
  }
  .page-header {
    flex-direction: column;
    gap: 12px;
  }
}
</style>
