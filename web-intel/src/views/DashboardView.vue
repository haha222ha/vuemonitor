<template>
  <div class="dashboard">
    <div class="page-header">
      <h2>商业情报仪表盘</h2>
      <el-tag v-if="intel.dashboard" type="success" size="small" effect="dark">
        {{ planLabel }} · 数据实时更新
      </el-tag>
    </div>

    <div class="stat-row" v-if="intel.dashboard">
      <div class="stat-card stat-trend">
        <div class="stat-bg"></div>
        <div class="stat-content">
          <div class="stat-icon-wrap">
            <el-icon :size="24"><TrendCharts /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ intel.dashboard.summary.active_trends }}</div>
            <div class="stat-label">活跃趋势</div>
          </div>
        </div>
      </div>
      <div class="stat-card stat-opp">
        <div class="stat-bg"></div>
        <div class="stat-content">
          <div class="stat-icon-wrap">
            <el-icon :size="24"><Opportunity /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ intel.dashboard.summary.recommended_opportunities }}</div>
            <div class="stat-label">推荐机会</div>
          </div>
        </div>
      </div>
      <div class="stat-card stat-risk">
        <div class="stat-bg"></div>
        <div class="stat-content">
          <div class="stat-icon-wrap">
            <el-icon :size="24"><Warning /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ intel.dashboard.summary.active_risks }}</div>
            <div class="stat-label">活跃风险</div>
          </div>
        </div>
      </div>
    </div>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card shadow="hover" class="section-card">
          <template #header>
            <div class="card-header">
              <span>🔥 热门趋势</span>
              <el-button text type="primary" @click="$router.push('/trends')">查看全部</el-button>
            </div>
          </template>
          <div v-if="intel.loading" class="loading-placeholder">
            <el-skeleton :rows="5" animated />
          </div>
          <el-empty v-else-if="!intel.dashboard?.top_trends?.length" description="暂无趋势数据" />
          <div v-else class="trend-list">
            <div v-for="item in intel.dashboard.top_trends" :key="item.id" class="trend-item">
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
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card shadow="hover" class="section-card">
          <template #header>
            <div class="card-header">
              <span>💡 推荐机会</span>
              <el-button text type="primary" @click="$router.push('/opportunities')">查看全部</el-button>
            </div>
          </template>
          <div v-if="intel.loading" class="loading-placeholder">
            <el-skeleton :rows="5" animated />
          </div>
          <el-empty v-else-if="!intel.dashboard?.top_opportunities?.length" description="暂无机会数据" />
          <div v-else class="opp-list">
            <div v-for="item in intel.dashboard.top_opportunities" :key="item.id" class="opp-item" :class="'verdict-' + (item.verdict || '').toLowerCase()">
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
                  <el-tag v-if="item.verdict" size="small" :type="verdictType(item.verdict)" effect="dark">{{ item.verdict }}</el-tag>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card shadow="hover" class="section-card">
          <template #header>
            <div class="card-header">
              <span>📊 趋势评分分布</span>
            </div>
          </template>
          <div class="chart-container">
            <Bar v-if="trendChartData" :data="trendChartData" :options="barChartOptions" />
            <el-empty v-else description="暂无图表数据" :image-size="60" />
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover" class="section-card">
          <template #header>
            <div class="card-header">
              <span>📊 风险等级分布</span>
            </div>
          </template>
          <div class="chart-container">
            <Doughnut v-if="riskChartData" :data="riskChartData" :options="doughnutOpts" />
            <el-empty v-else description="暂无图表数据" :image-size="60" />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="24">
        <el-card shadow="hover" class="section-card">
          <template #header>
            <div class="card-header">
              <span>⚠️ 风险预警</span>
              <el-button text type="primary" @click="$router.push('/risks')">查看全部</el-button>
            </div>
          </template>
          <div v-if="intel.loading" class="loading-placeholder">
            <el-skeleton :rows="3" animated />
          </div>
          <el-empty v-else-if="!intel.dashboard?.top_risks?.length" description="暂无风险数据" />
          <div v-else class="risk-list">
            <div v-for="item in intel.dashboard.top_risks" :key="item.id" class="risk-item" :class="'severity-' + (item.severity || '').toLowerCase()">
              <div class="risk-severity-dot"></div>
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
import { TrendCharts, Opportunity, Warning, Right } from "@element-plus/icons-vue"
import { getScoreColor, getDirectionIcon } from "@/utils/theme"
import { Bar, Doughnut } from "vue-chartjs"
import { defaultChartOptions, doughnutOptions, chartColors } from "@/utils/charts"
import type { ChartData } from "chart.js"

const intel = useIntelStore()
const auth = useIntelAuthStore()

const planLabel = computed(() => auth.planLabel)

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
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.page-header h2 { margin: 0; font-size: 20px; }

.stat-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}
.stat-card {
  border-radius: 14px;
  overflow: hidden;
  position: relative;
  color: #fff;
  min-height: 100px;
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
  width: 52px;
  height: 52px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(4px);
}
.stat-value {
  font-size: 36px;
  font-weight: 800;
  line-height: 1;
}
.stat-label {
  font-size: 14px;
  opacity: 0.85;
  margin-top: 4px;
}

.section-card { border-radius: 12px; }
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.loading-placeholder { padding: 16px; }

.trend-list { display: flex; flex-direction: column; gap: 2px; }
.trend-item {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 12px 8px;
  border-radius: 8px;
  transition: background 0.15s;
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
.trend-right { flex: 1; }
.trend-title {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 6px;
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

.opp-list { display: flex; flex-direction: column; gap: 2px; }
.opp-item {
  display: flex;
  gap: 14px;
  align-items: center;
  padding: 12px 8px;
  border-radius: 8px;
  border-left: 3px solid transparent;
  transition: background 0.15s;
}
.opp-item:hover { background: #f8f9fa; }
.opp-item.verdict-recommended { border-left-color: #059669; }
.opp-item.verdict-caution { border-left-color: #d97706; }
.opp-item.verdict-avoid { border-left-color: #dc2626; }
.opp-score-ring {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 3px solid;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.opp-score-ring span {
  font-size: 15px;
  font-weight: 800;
}
.opp-right { flex: 1; }
.opp-title {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 6px;
}
.opp-meta {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.risk-list { display: flex; flex-direction: column; gap: 8px; }
.risk-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  background: #f8f9fa;
  border-left: 4px solid transparent;
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
.risk-name { font-size: 14px; font-weight: 600; color: #303133; min-width: 140px; }
.risk-reason { font-size: 13px; color: #606266; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.risk-alt {
  font-size: 12px;
  color: #059669;
  font-weight: 500;
  white-space: nowrap;
}
.chart-container {
  height: 280px;
  padding: 8px;
}
</style>
