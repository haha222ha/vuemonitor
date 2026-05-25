<template>
  <div class="opportunities-page">
    <div class="page-header">
      <div class="header-title-area">
        <h2>商业机会</h2>
        <p class="header-subtitle" v-if="items.length">发现高潜力商业机会，精准评估变现路径</p>
      </div>
      <div class="header-actions">
        <el-select v-model="categoryFilter" placeholder="分类筛选" clearable size="small" style="width: 140px">
          <el-option label="全部" value="" />
          <el-option v-for="cat in categories" :key="cat" :label="cat" :value="cat" />
        </el-select>
        <el-input v-model="searchText" placeholder="搜索机会..." size="small" clearable style="width: 220px" />
        <el-button size="small" @click="exportCSV(filteredItems, '商业机会')">导出CSV</el-button>
        <el-button size="small" @click="exportJSON(filteredItems, '商业机会')">导出JSON</el-button>
      </div>
    </div>

    <div class="opp-stats" v-if="items.length">
      <div class="opp-stat-item stat-recommended">
        <span class="stat-icon">✅</span>
        <span class="stat-num">{{ verdictCount('RECOMMENDED') }}</span>
        <span class="stat-text">推荐机会</span>
      </div>
      <div class="opp-stat-item stat-caution">
        <span class="stat-icon">⚠️</span>
        <span class="stat-num">{{ verdictCount('CAUTION') }}</span>
        <span class="stat-text">需谨慎</span>
      </div>
      <div class="opp-stat-item stat-avoid">
        <span class="stat-icon">🚫</span>
        <span class="stat-num">{{ verdictCount('AVOID') }}</span>
        <span class="stat-text">建议回避</span>
      </div>
      <div class="opp-stat-item stat-avg">
        <span class="stat-icon">📊</span>
        <span class="stat-num">{{ avgScore }}</span>
        <span class="stat-text">平均评分</span>
      </div>
    </div>

    <div v-if="loading" class="loading-placeholder">
      <el-skeleton :rows="8" animated />
    </div>
    <div v-else-if="!items.length" class="intel-empty-state">
      <div class="intel-empty-state-icon">💰</div>
      <div class="intel-empty-state-text">暂无商业机会数据</div>
      <div class="intel-empty-state-action">数据更新后将自动展示</div>
    </div>
    <div v-else class="opp-grid intel-card-stagger">
      <div
        v-for="item in filteredItems"
        :key="item.id"
        class="opp-card"
        :class="'verdict-' + (item.verdict || '').toLowerCase()"
        @click="openReport(item)"
      >
        <div class="opp-verdict-bar"></div>
        <div class="card-body">
          <div class="card-top-row">
            <div class="opp-score-ring" :style="{ borderColor: getScoreColor(item.verdict_score), boxShadow: '0 0 0 3px ' + getScoreColor(item.verdict_score) + '20' }">
              <span :style="{ color: getScoreColor(item.verdict_score) }">{{ item.verdict_score }}</span>
            </div>
            <div class="card-title-area">
              <div class="card-title">{{ item.name }}</div>
              <div class="card-meta">
                <el-tag size="small" effect="plain">{{ item.category }}</el-tag>
                <el-tag size="small" v-if="item.verdict" :type="verdictType(item.verdict)" effect="dark">{{ verdictLabel(item.verdict) }}</el-tag>
                <el-tag size="small" v-if="item.difficulty" effect="plain">{{ item.difficulty }}</el-tag>
              </div>
            </div>
          </div>
          <div class="card-details" v-if="item.startup_cost || item.monthly_ceiling">
            <div class="detail-row" v-if="item.startup_cost">
              <span class="detail-label">启动成本</span>
              <span class="detail-value">{{ item.startup_cost }}元</span>
            </div>
            <div class="detail-row" v-if="item.monthly_ceiling">
              <span class="detail-label">月收入上限</span>
              <span class="detail-value">{{ item.monthly_ceiling }}</span>
            </div>
            <div class="detail-row" v-if="item.time_to_first_revenue">
              <span class="detail-label">首次营收</span>
              <span class="detail-value">{{ item.time_to_first_revenue }}</span>
            </div>
          </div>
          <div class="card-paths" v-if="item.commercial_paths?.length">
            <el-tag v-for="(path, idx) in item.commercial_paths.slice(0, 3)" :key="idx" size="small" type="success" effect="plain">
              {{ formatPath(path) }}
            </el-tag>
            <el-tag v-if="item.commercial_paths.length > 3" size="small" type="info">+{{ item.commercial_paths.length - 3 }}</el-tag>
          </div>
          <div class="card-fit" v-if="item.persona_fit?.length">
            <span class="fit-label">适合：</span>
            <span>{{ formatArray(item.persona_fit) }}</span>
          </div>
          <div class="card-footer">
            <span class="card-action">查看详情 →</span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="items.length > 0" class="pagination-wrap">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="filteredTotal"
        layout="total, prev, pager, next"
        background
        small
        @current-change="handlePageChange"
      />
    </div>

    <el-dialog v-model="detailVisible" :title="detailItem?.name" width="720px" destroy-on-close>
      <div v-if="detailItem" class="opp-detail">
        <div class="detail-verdict-bar" :class="'verdict-' + (detailItem.verdict || '').toLowerCase()">
          <div class="verdict-badge">
            <span class="verdict-icon">{{ verdictIcon(detailItem.verdict) }}</span>
            <span class="verdict-text">{{ verdictLabel(detailItem.verdict) }}</span>
          </div>
          <div class="verdict-score-big" :style="{ color: getScoreColor(detailItem.verdict_score) }">
            {{ detailItem.verdict_score }}<span class="score-unit">分</span>
          </div>
        </div>

        <el-descriptions :column="2" border>
          <el-descriptions-item label="分类">{{ detailItem.category }}</el-descriptions-item>
          <el-descriptions-item label="子分类" v-if="detailItem.sub_category">{{ detailItem.sub_category }}</el-descriptions-item>
          <el-descriptions-item label="难度" v-if="detailItem.difficulty">{{ detailItem.difficulty }}</el-descriptions-item>
          <el-descriptions-item label="启动成本" v-if="detailItem.startup_cost">{{ detailItem.startup_cost }}元</el-descriptions-item>
          <el-descriptions-item label="月收入上限" v-if="detailItem.monthly_ceiling">{{ detailItem.monthly_ceiling }}</el-descriptions-item>
          <el-descriptions-item label="首次营收" v-if="detailItem.time_to_first_revenue">{{ detailItem.time_to_first_revenue }}</el-descriptions-item>
          <el-descriptions-item label="风险等级" v-if="detailItem.risk_level">
            <el-tag :type="detailItem.risk_level === 'high' ? 'danger' : detailItem.risk_level === 'medium' ? 'warning' : 'info'" size="small">{{ detailItem.risk_level }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="趋势方向" v-if="detailItem.trend_direction">{{ detailItem.trend_direction }}</el-descriptions-item>
          <el-descriptions-item label="生命周期" v-if="detailItem.lifecycle_stage">{{ detailItem.lifecycle_stage }}</el-descriptions-item>
          <el-descriptions-item label="适合人群" :span="2" v-if="detailItem.persona_fit?.length">{{ formatArray(detailItem.persona_fit) }}</el-descriptions-item>
          <el-descriptions-item label="平台" :span="2" v-if="detailItem.platform?.length">{{ formatArray(detailItem.platform) }}</el-descriptions-item>
        </el-descriptions>

        <div class="detail-section" v-if="detailItem.verdict_detail && Object.keys(detailItem.verdict_detail).length">
          <h4>📊 判定详情</h4>
          <div class="verdict-bars">
            <div v-for="(val, key) in detailItem.verdict_detail" :key="key" class="verdict-bar-item">
              <div class="verdict-bar-label">
                <span class="verdict-key">{{ verdictLabel(key as string) }}</span>
                <span class="verdict-score" :style="{ color: verdictBarColor(Number(val)) }">{{ val }}/10</span>
              </div>
              <div class="verdict-bar-track">
                <div class="verdict-bar-fill" :style="{ width: Number(val) * 10 + '%', background: verdictBarColor(Number(val)) }"></div>
              </div>
            </div>
          </div>
        </div>

        <div class="detail-section" v-if="detailItem.commercial_paths?.length">
          <h4>💰 商业化路径</h4>
          <div class="paths-list">
            <div v-for="(path, idx) in detailItem.commercial_paths" :key="idx" class="path-item">
              <div class="path-index">{{ idx + 1 }}</div>
              <div class="path-detail" v-if="typeof path === 'object'">
                <div class="path-main">
                  <span class="path-type" v-if="(path as Record<string, unknown>).type">{{ (path as Record<string, unknown>).type }}</span>
                  <span class="path-desc" v-if="(path as Record<string, unknown>).description">{{ (path as Record<string, unknown>).description }}</span>
                  <span class="path-name" v-else-if="(path as Record<string, unknown>).name">{{ (path as Record<string, unknown>).name }}</span>
                </div>
                <span class="path-price" v-if="(path as Record<string, unknown>).price_range">💰 {{ (path as Record<string, unknown>).price_range }}</span>
              </div>
              <span v-else>{{ path }}</span>
            </div>
          </div>
        </div>

        <div class="detail-section" v-if="detailItem.key_metrics && Object.keys(detailItem.key_metrics).length">
          <h4>📈 关键指标</h4>
          <div class="json-block">
            <div v-for="(val, key) in detailItem.key_metrics" :key="key" class="json-row">
              <span class="json-key">{{ key }}</span>
              <span class="json-val">{{ formatValue(val) }}</span>
            </div>
          </div>
        </div>

        <div class="detail-section" v-if="detailItem.risk_flag">
          <el-alert title="风险标记" type="warning" :closable="false" show-icon>
            该机会存在风险标记，请谨慎评估
          </el-alert>
        </div>
      </div>
      <template #footer>
        <el-button v-if="isAdmin()" @click="handleDelete(detailItem)" type="danger" size="small">删除</el-button>
        <el-button @click="exportJSON([detailItem!], detailItem!.name)" size="small">导出</el-button>
        <el-button @click="detailVisible = false" size="small">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import { useRouter } from "vue-router"
import api from "@/utils/api"
import { exportJSON, exportCSV, deleteItem, formatValue, isAdmin, fetchWithCache, clearCache } from "@/utils/intel"
import { getScoreColor, getVerdictColor } from "@/utils/theme"

interface OpportunityItem {
  id: string
  name: string
  category: string
  sub_category?: string
  verdict_score: number
  verdict: string
  verdict_detail: Record<string, unknown>
  difficulty?: string
  startup_cost: number
  monthly_ceiling?: string
  time_to_first_revenue?: string
  risk_level?: string
  risk_flag: boolean
  persona_fit: unknown[]
  platform: unknown[]
  lifecycle_stage?: string
  key_metrics: Record<string, unknown>
  commercial_paths: unknown[]
  trend_direction?: string
  topic_id?: string
  [key: string]: unknown
}

const router = useRouter()
const items = ref<OpportunityItem[]>([])
const loading = ref(false)
const searchText = ref("")
const categoryFilter = ref("")
const currentPage = ref(1)
const pageSize = 12
const detailItem = ref<OpportunityItem | null>(null)
const detailVisible = ref(false)

const categories = computed(() => {
  const cats = new Set(items.value.map((i) => i.category).filter(Boolean))
  return Array.from(cats).sort()
})

function verdictCount(verdict: string): number {
  return items.value.filter(i => i.verdict === verdict).length
}

const avgScore = computed(() => {
  if (!items.value.length) return 0
  const sum = items.value.reduce((acc, i) => acc + (i.verdict_score || 0), 0)
  return Math.round(sum / items.value.length)
})

const filteredItems = computed(() => {
  let result = items.value
  if (searchText.value) {
    const s = searchText.value.toLowerCase()
    result = result.filter((i) => i.name.toLowerCase().includes(s) || i.category?.toLowerCase().includes(s))
  }
  if (categoryFilter.value) {
    result = result.filter((i) => i.category === categoryFilter.value)
  }
  const start = (currentPage.value - 1) * pageSize
  return result.slice(start, start + pageSize)
})

const filteredTotal = computed(() => {
  let result = items.value
  if (searchText.value) {
    const s = searchText.value.toLowerCase()
    result = result.filter((i) => i.name.toLowerCase().includes(s) || i.category?.toLowerCase().includes(s))
  }
  if (categoryFilter.value) {
    result = result.filter((i) => i.category === categoryFilter.value)
  }
  return result.length
})

function scoreType(score: number): string {
  if (score >= 80) return "success"
  if (score >= 60) return "warning"
  return "info"
}

function verdictType(verdict: string): string {
  const map: Record<string, string> = { RECOMMENDED: "success", CAUTION: "warning", AVOID: "danger" }
  return map[verdict] || "info"
}

function verdictLabel(verdict: string): string {
  const map: Record<string, string> = { RECOMMENDED: "推荐", CAUTION: "谨慎", AVOID: "回避" }
  return map[verdict] || verdict
}

function verdictIcon(verdict: string): string {
  const map: Record<string, string> = { RECOMMENDED: "✅", CAUTION: "⚠️", AVOID: "🚫" }
  return map[verdict] || "📋"
}

function verdictBarColor(val: number): string {
  if (val >= 8) return "#059669"
  if (val >= 5) return "#d97706"
  return "#dc2626"
}

function formatArray(arr: unknown[]): string {
  if (!arr?.length) return "-"
  return arr.map((v) => (typeof v === "string" ? v : JSON.stringify(v))).join("、")
}

function formatPath(path: unknown): string {
  if (typeof path === "string") return path
  if (typeof path === "object" && path !== null) {
    const p = path as Record<string, unknown>
    if (p.type && p.description) return `${p.type}：${p.description}`
    if (p.name) return String(p.name)
    if (p.type) return String(p.type)
  }
  return JSON.stringify(path)
}

const VERDICT_LABELS: Record<string, string> = {
  monetization_path_authenticity: "变现路径真实性",
  competition_heat: "竞争热度",
  ordinary_person_fit: "普通人适配度",
  sustained_demand: "持续需求",
  copy_barrier: "抄袭壁垒",
}

function verdictDetailLabel(key: string): string {
  return VERDICT_LABELS[key] || key
}

function openReport(item: OpportunityItem) {
  if (item.topic_id) {
    router.push(`/report/${item.topic_id}`)
  } else {
    detailItem.value = item
    detailVisible.value = true
  }
}

async function handleDelete(item: OpportunityItem | null) {
  if (!item) return
  const ok = await deleteItem("opportunities", item.id, item.name)
  if (ok) {
    items.value = items.value.filter((i) => i.id !== item.id)
    clearCache("opportunities")
    detailVisible.value = false
  }
}

function handlePageChange() {
  scrollTo({ top: 0, behavior: "smooth" })
}

onMounted(async () => {
  loading.value = true
  try {
    items.value = await fetchWithCache<OpportunityItem>("opportunities", "/intel/opportunities")
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.opportunities-page { max-width: 1400px; }
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: var(--spacing-lg);
  flex-wrap: wrap;
  gap: var(--spacing-md);
}
.header-title-area h2 {
  margin: 0;
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--intel-text);
}
.header-subtitle {
  margin: var(--spacing-xs) 0 0;
  font-size: var(--font-size-sm);
  color: var(--intel-text-secondary);
}
.header-actions { display: flex; gap: var(--spacing-sm); flex-wrap: wrap; }

.opp-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}
.opp-stat-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md) var(--spacing-lg);
  border-radius: var(--intel-radius-lg);
  background: var(--intel-surface);
  box-shadow: var(--intel-shadow);
  transition: all var(--transition-base);
}
.opp-stat-item:hover {
  box-shadow: var(--intel-shadow-hover);
  transform: translateY(-2px);
}
.stat-icon { font-size: var(--font-size-xl); }
.stat-num { font-size: var(--font-size-2xl); font-weight: 800; }
.stat-text { font-size: var(--font-size-sm); color: var(--intel-text-secondary); }
.stat-recommended .stat-num { color: var(--intel-success); }
.stat-caution .stat-num { color: var(--intel-warning); }
.stat-avoid .stat-num { color: var(--intel-danger); }
.stat-avg .stat-num { color: var(--intel-primary); }

.loading-placeholder { padding: var(--spacing-md); }

.opp-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: var(--spacing-md);
}
.opp-card {
  background: var(--intel-surface);
  border-radius: var(--intel-radius-lg);
  box-shadow: var(--intel-shadow);
  cursor: pointer;
  transition: all var(--transition-base);
  overflow: hidden;
  position: relative;
}
.opp-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--intel-shadow-hover);
}
.opp-card:hover .card-footer .card-action {
  transform: translateX(4px);
}
.opp-verdict-bar { height: 3px; width: 100%; }
.opp-card.verdict-recommended .opp-verdict-bar { background: var(--intel-success); }
.opp-card.verdict-caution .opp-verdict-bar { background: var(--intel-warning); }
.opp-card.verdict-avoid .opp-verdict-bar { background: var(--intel-danger); }
.opp-card.verdict-recommended { border-left: 4px solid var(--intel-success); }
.opp-card.verdict-caution { border-left: 4px solid var(--intel-warning); }
.opp-card.verdict-avoid { border-left: 4px solid var(--intel-danger); }
.card-body { padding: var(--spacing-md) var(--spacing-lg); }
.card-top-row {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  margin-bottom: var(--spacing-md);
}
.opp-score-ring {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: 3px solid;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all var(--transition-base);
}
.opp-card:hover .opp-score-ring {
  transform: scale(1.05);
}
.opp-score-ring span {
  font-size: var(--font-size-lg);
  font-weight: 800;
}
.card-title-area { flex: 1; }
.card-title {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--intel-text);
  margin-bottom: var(--spacing-sm);
  line-height: 1.5;
}
.card-meta {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.card-details {
  background: var(--intel-bg);
  border-radius: var(--intel-radius);
  padding: var(--spacing-sm) var(--spacing-md);
  margin-bottom: var(--spacing-sm);
}
.detail-row {
  display: flex;
  justify-content: space-between;
  font-size: var(--font-size-sm);
  padding: 2px 0;
}
.detail-label { color: var(--intel-text-secondary); }
.detail-value { color: var(--intel-text); font-weight: 500; }
.card-paths {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin-bottom: var(--spacing-sm);
}
.card-fit {
  font-size: var(--font-size-sm);
  color: var(--intel-text-secondary);
}
.fit-label { color: #606266; }
.card-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--spacing-sm);
}
.card-action {
  font-size: var(--font-size-sm);
  color: var(--intel-accent);
  font-weight: 500;
  transition: transform var(--transition-fast);
}
.pagination-wrap {
  margin-top: var(--spacing-lg);
  display: flex;
  justify-content: center;
}

.opp-detail { padding: 0; }
.detail-verdict-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md) var(--spacing-lg);
  border-radius: var(--intel-radius-lg);
  margin-bottom: var(--spacing-lg);
}
.detail-verdict-bar.verdict-recommended { background: linear-gradient(135deg, #f0f9eb 0%, #ecfdf5 100%); }
.detail-verdict-bar.verdict-caution { background: linear-gradient(135deg, #fdf6ec 0%, #fffbeb 100%); }
.detail-verdict-bar.verdict-avoid { background: linear-gradient(135deg, #fef0f0 0%, #fef2f2 100%); }
.verdict-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  font-size: var(--font-size-lg);
}
.verdict-icon { font-size: var(--font-size-xl); }
.detail-verdict-bar.verdict-recommended .verdict-text { color: var(--intel-success); }
.detail-verdict-bar.verdict-caution .verdict-text { color: var(--intel-warning); }
.detail-verdict-bar.verdict-avoid .verdict-text { color: var(--intel-danger); }
.verdict-score-big {
  font-size: var(--font-size-3xl);
  font-weight: 800;
}
.score-unit { font-size: var(--font-size-base); font-weight: 400; opacity: 0.6; margin-left: 2px; }

.detail-section { margin-top: var(--spacing-lg); }
.detail-section h4 {
  font-size: var(--font-size-md);
  color: var(--intel-text);
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--intel-border-light);
  font-weight: 600;
}
.verdict-bars {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.verdict-bar-item {
  background: var(--intel-bg);
  border-radius: var(--intel-radius);
  padding: 10px var(--spacing-md);
}
.verdict-bar-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.verdict-key {
  font-size: var(--font-size-sm);
  color: #606266;
  font-weight: 500;
}
.verdict-score {
  font-size: var(--font-size-md);
  font-weight: 700;
}
.verdict-bar-track {
  height: 6px;
  background: var(--intel-border);
  border-radius: 3px;
  overflow: hidden;
}
.verdict-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.6s ease;
}
.json-block {
  background: var(--intel-bg);
  border-radius: var(--intel-radius);
  padding: var(--spacing-md);
}
.json-row {
  display: flex;
  gap: var(--spacing-md);
  padding: 4px 0;
  font-size: var(--font-size-sm);
  border-bottom: 1px solid var(--intel-border-light);
}
.json-row:last-child { border-bottom: none; }
.json-key { color: var(--intel-text-secondary); min-width: 100px; flex-shrink: 0; }
.json-val { color: var(--intel-text); word-break: break-all; }
.paths-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}
.path-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: var(--font-size-sm);
  color: var(--intel-text);
}
.path-index {
  width: 24px;
  height: 24px;
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
.path-detail {
  flex: 1;
  background: #f0f9eb;
  border-radius: var(--intel-radius);
  padding: var(--spacing-sm) var(--spacing-md);
}
.path-main {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.path-type { font-weight: 600; color: var(--intel-success); }
.path-desc { color: var(--intel-text); }
.path-name { color: var(--intel-text); font-weight: 500; }
.path-price {
  font-size: var(--font-size-sm);
  color: var(--intel-warning);
  margin-top: 4px;
  display: block;
}

@media (max-width: 768px) {
  .opp-stats {
    grid-template-columns: repeat(2, 1fr);
  }
  .opp-grid {
    grid-template-columns: 1fr;
  }
}
</style>
