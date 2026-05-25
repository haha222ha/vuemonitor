<template>
  <div class="trends-page">
    <div class="page-header">
      <div class="header-title-area">
        <h2>趋势分析</h2>
        <p class="header-subtitle" v-if="items.length">追踪互联网商业趋势变化，发现增长机会</p>
      </div>
      <div class="header-actions">
        <el-select v-model="platformFilter" placeholder="平台筛选" clearable size="small" style="width: 140px">
          <el-option label="全部平台" value="" />
          <el-option label="小红书" value="xiaohongshu" />
          <el-option label="抖音" value="douyin" />
        </el-select>
        <el-input v-model="searchText" placeholder="搜索趋势..." size="small" clearable style="width: 220px" />
        <el-button size="small" @click="doExportCSV">导出CSV</el-button>
        <el-button size="small" @click="doExportJSON">导出JSON</el-button>
      </div>
    </div>

    <div class="trend-stats" v-if="items.length">
      <div class="trend-stat-item stat-rising">
        <span class="stat-icon">↑</span>
        <span class="stat-num">{{ directionCount('rising') }}</span>
        <span class="stat-text">上升趋势</span>
      </div>
      <div class="trend-stat-item stat-stable">
        <span class="stat-icon">→</span>
        <span class="stat-num">{{ directionCount('stable') }}</span>
        <span class="stat-text">稳定趋势</span>
      </div>
      <div class="trend-stat-item stat-falling">
        <span class="stat-icon">↓</span>
        <span class="stat-num">{{ directionCount('falling') }}</span>
        <span class="stat-text">下降趋势</span>
      </div>
      <div class="trend-stat-item stat-total">
        <span class="stat-icon">📊</span>
        <span class="stat-num">{{ items.length }}</span>
        <span class="stat-text">总趋势数</span>
      </div>
    </div>

    <div v-if="loading" class="loading-placeholder">
      <el-skeleton :rows="8" animated />
    </div>
    <div v-else-if="!items.length" class="intel-empty-state">
      <div class="intel-empty-state-icon">📈</div>
      <div class="intel-empty-state-text">暂无趋势数据</div>
      <div class="intel-empty-state-action">数据更新后将自动展示</div>
    </div>
    <div v-else class="trend-grid intel-card-stagger">
      <div
        v-for="item in filteredItems"
        :key="item.id"
        class="trend-card"
        :class="'dir-' + (item.direction || '').toLowerCase()"
        @click="openDetail(item)"
      >
        <div class="trend-dir-bar"></div>
        <div class="card-body">
          <div class="card-top-row">
            <div class="dir-indicator" :class="'dir-' + (item.direction || '').toLowerCase()">
              <span class="dir-icon">{{ getDirectionIcon(item.direction) }}</span>
              <span class="dir-text">{{ getDirectionLabel(item.direction) }}</span>
            </div>
            <div class="score-badge" :style="{ color: getScoreColor(item.opportunity_score), borderColor: getScoreColor(item.opportunity_score) + '30' }">
              {{ item.opportunity_score }}
            </div>
          </div>
          <div class="card-title">{{ item.title }}</div>
          <div class="card-meta">
            <el-tag size="small" effect="plain">{{ item.category }}</el-tag>
            <el-tag size="small" v-if="item.platform" effect="plain">{{ item.platform }}</el-tag>
            <el-tag size="small" v-if="item.lifecycle" type="success" effect="plain">{{ item.lifecycle }}</el-tag>
          </div>
          <div class="card-extra" v-if="item.user_emotion || item.competition">
            <span v-if="item.user_emotion">用户情绪：{{ item.user_emotion }}</span>
            <span v-if="item.competition">竞争度：{{ item.competition }}</span>
          </div>
          <div class="card-risk" v-if="item.risk_level">
            <el-tag :type="riskType(item.risk_level)" size="small" effect="dark">风险：{{ item.risk_level }}</el-tag>
          </div>
          <div class="card-insight" v-if="item.actionable_insight">
            <span class="insight-icon">💡</span>
            {{ truncate(item.actionable_insight, 60) }}
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

    <el-dialog v-model="detailVisible" :title="detailItem?.title" width="720px" destroy-on-close class="trend-dialog">
      <div v-if="detailItem" class="trend-detail">
        <div class="detail-header-bar" :class="'dir-' + (detailItem.direction || '').toLowerCase()">
          <div class="detail-dir-badge">
            <span>{{ getDirectionIcon(detailItem.direction) }}</span>
            <span>{{ getDirectionLabel(detailItem.direction) }}</span>
          </div>
          <div class="detail-score-big" :style="{ color: getScoreColor(detailItem.opportunity_score) }">
            {{ detailItem.opportunity_score }}<span class="score-unit">分</span>
          </div>
        </div>

        <el-descriptions :column="2" border>
          <el-descriptions-item label="分类">{{ detailItem.category }}</el-descriptions-item>
          <el-descriptions-item label="平台">{{ detailItem.platform }}</el-descriptions-item>
          <el-descriptions-item label="生命周期">{{ detailItem.lifecycle }}</el-descriptions-item>
          <el-descriptions-item label="竞争度">{{ detailItem.competition }}</el-descriptions-item>
          <el-descriptions-item label="风险等级">
            <el-tag :type="riskType(detailItem.risk_level)">{{ detailItem.risk_level }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="用户情绪">{{ detailItem.user_emotion || "-" }}</el-descriptions-item>
          <el-descriptions-item label="变现潜力" v-if="detailItem.monetization_potential">{{ detailItem.monetization_potential }}</el-descriptions-item>
          <el-descriptions-item label="新鲜度" v-if="detailItem.freshness_days">{{ detailItem.freshness_days }}天</el-descriptions-item>
        </el-descriptions>

        <div class="detail-section" v-if="detailItem.evidence">
          <h4>📋 证据</h4>
          <div class="text-block">{{ detailItem.evidence }}</div>
        </div>

        <div class="detail-section" v-if="detailItem.actionable_insight">
          <h4>💡 行动建议</h4>
          <div class="text-block highlight">{{ detailItem.actionable_insight }}</div>
        </div>

        <div class="detail-section" v-if="detailItem.risk_note">
          <h4>⚠️ 风险备注</h4>
          <el-alert :title="detailItem.risk_note" type="warning" :closable="false" show-icon />
        </div>

        <div class="detail-section" v-if="detailItem.affected_opportunities?.length">
          <h4>🔗 关联机会</h4>
          <div class="tag-list">
            <el-tag v-for="(opp, idx) in detailItem.affected_opportunities" :key="idx" size="small" type="success">
              {{ typeof opp === 'string' ? opp : (opp as Record<string, unknown>).name || JSON.stringify(opp) }}
            </el-tag>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button v-if="isAdmin()" @click="handleDelete(detailItem)" type="danger" size="small">删除</el-button>
        <el-button @click="doExportJSON" size="small">导出</el-button>
        <el-button @click="detailVisible = false" size="small">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import api from "@/utils/api"
import { exportJSON, exportCSV, deleteItem, truncate, isAdmin, fetchWithCache, clearCache } from "@/utils/intel"
import { getScoreColor, getDirectionIcon, getDirectionLabel } from "@/utils/theme"

interface TrendItem {
  id: string
  title: string
  category: string
  platform: string
  opportunity_score: number
  lifecycle: string
  direction: string
  competition: string
  risk_level: string
  user_emotion: string
  monetization_potential?: string
  freshness_days?: number
  evidence?: string
  actionable_insight?: string
  risk_note?: string
  affected_opportunities?: unknown[]
  [key: string]: unknown
}

const items = ref<TrendItem[]>([])
const loading = ref(false)
const searchText = ref("")
const platformFilter = ref("")
const currentPage = ref(1)
const pageSize = 12
const detailItem = ref<TrendItem | null>(null)
const detailVisible = ref(false)

function directionCount(dir: string): number {
  return items.value.filter(i => (i.direction || '').toLowerCase() === dir).length
}

const filteredItems = computed(() => {
  let result = items.value
  if (searchText.value) {
    const s = searchText.value.toLowerCase()
    result = result.filter((i) => i.title.toLowerCase().includes(s) || i.category?.toLowerCase().includes(s))
  }
  if (platformFilter.value) {
    result = result.filter((i) => i.platform === platformFilter.value)
  }
  const start = (currentPage.value - 1) * pageSize
  return result.slice(start, start + pageSize)
})

const filteredTotal = computed(() => {
  let result = items.value
  if (searchText.value) {
    const s = searchText.value.toLowerCase()
    result = result.filter((i) => i.title.toLowerCase().includes(s) || i.category?.toLowerCase().includes(s))
  }
  if (platformFilter.value) {
    result = result.filter((i) => i.platform === platformFilter.value)
  }
  return result.length
})

function scoreType(score: number): string {
  if (score >= 80) return "success"
  if (score >= 60) return "warning"
  return "info"
}

function riskType(level: string): string {
  const map: Record<string, string> = { high: "danger", medium: "warning", low: "info" }
  return map[level?.toLowerCase()] || "info"
}

function directionType(d: string): string {
  const map: Record<string, string> = { rising: "success", stable: "info", falling: "danger" }
  return map[d?.toLowerCase()] || "info"
}

function openDetail(item: TrendItem) {
  detailItem.value = item
  detailVisible.value = true
}

async function handleDelete(item: TrendItem | null) {
  if (!item) return
  const ok = await deleteItem("trends", item.id, item.title)
  if (ok) {
    items.value = items.value.filter((i) => i.id !== item.id)
    clearCache("trends")
    detailVisible.value = false
  }
}

function doExportCSV() { exportCSV(filteredItems.value as Record<string, unknown>[], "趋势分析") }
function doExportJSON() { exportJSON(filteredItems.value, "趋势分析") }

function handlePageChange() {
  scrollTo({ top: 0, behavior: "smooth" })
}

onMounted(async () => {
  loading.value = true
  try {
    items.value = await fetchWithCache<TrendItem>("trends", "/intel/trends")
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.trends-page { max-width: 1400px; }
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

.trend-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}
.trend-stat-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md) var(--spacing-lg);
  border-radius: var(--intel-radius-lg);
  background: var(--intel-surface);
  box-shadow: var(--intel-shadow);
  transition: all var(--transition-base);
}
.trend-stat-item:hover {
  box-shadow: var(--intel-shadow-hover);
  transform: translateY(-2px);
}
.stat-icon { font-size: var(--font-size-xl); }
.stat-num { font-size: var(--font-size-2xl); font-weight: 800; }
.stat-text { font-size: var(--font-size-sm); color: var(--intel-text-secondary); }
.stat-rising .stat-num { color: var(--intel-success); }
.stat-rising .stat-icon { color: var(--intel-success); }
.stat-stable .stat-num { color: var(--intel-info); }
.stat-stable .stat-icon { color: var(--intel-info); }
.stat-falling .stat-num { color: var(--intel-danger); }
.stat-falling .stat-icon { color: var(--intel-danger); }
.stat-total .stat-num { color: var(--intel-primary); }
.stat-total .stat-icon { color: var(--intel-primary); }

.loading-placeholder { padding: var(--spacing-md); }

.trend-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: var(--spacing-md);
}
.trend-card {
  background: var(--intel-surface);
  border-radius: var(--intel-radius-lg);
  box-shadow: var(--intel-shadow);
  cursor: pointer;
  transition: all var(--transition-base);
  overflow: hidden;
}
.trend-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--intel-shadow-hover);
}
.trend-card:hover .card-footer .card-action {
  transform: translateX(4px);
}
.trend-dir-bar { height: 3px; width: 100%; }
.trend-card.dir-rising .trend-dir-bar { background: var(--intel-success); }
.trend-card.dir-stable .trend-dir-bar { background: var(--intel-info); }
.trend-card.dir-falling .trend-dir-bar { background: var(--intel-danger); }
.trend-card.dir-rising { border-left: 4px solid var(--intel-success); }
.trend-card.dir-stable { border-left: 4px solid var(--intel-info); }
.trend-card.dir-falling { border-left: 4px solid var(--intel-danger); }
.card-body { padding: var(--spacing-md) var(--spacing-lg); }
.card-top-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.dir-indicator {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: var(--font-size-sm);
  font-weight: 600;
}
.dir-indicator.dir-rising { background: #ecfdf5; color: var(--intel-success); }
.dir-indicator.dir-stable { background: #eff6ff; color: var(--intel-info); }
.dir-indicator.dir-falling { background: #fef2f2; color: var(--intel-danger); }
.dir-icon { font-size: var(--font-size-md); }
.score-badge {
  font-size: var(--font-size-2xl);
  font-weight: 800;
  padding: 2px 10px;
  border-radius: var(--intel-radius);
  border: 2px solid;
}
.card-title {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--intel-text);
  margin-bottom: 10px;
  line-height: 1.5;
}
.card-meta {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: var(--spacing-sm);
}
.card-extra {
  font-size: var(--font-size-sm);
  color: var(--intel-text-secondary);
  display: flex;
  gap: var(--spacing-md);
  margin-bottom: 6px;
}
.card-risk { margin-top: 4px; }
.card-insight {
  font-size: var(--font-size-sm);
  color: var(--intel-info);
  margin-top: 6px;
  line-height: 1.5;
  background: #eff6ff;
  padding: var(--spacing-sm) 10px;
  border-radius: var(--intel-radius);
  display: flex;
  align-items: flex-start;
  gap: 6px;
}
.insight-icon { flex-shrink: 0; }
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

.trend-detail { padding: 0; }
.detail-header-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md) var(--spacing-lg);
  border-radius: var(--intel-radius-lg);
  margin-bottom: var(--spacing-lg);
}
.detail-header-bar.dir-rising { background: linear-gradient(135deg, #ecfdf5 0%, #f0f9eb 100%); }
.detail-header-bar.dir-stable { background: linear-gradient(135deg, #eff6ff 0%, #f0f5ff 100%); }
.detail-header-bar.dir-falling { background: linear-gradient(135deg, #fef2f2 0%, #fff5f5 100%); }
.detail-dir-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  font-size: var(--font-size-lg);
}
.detail-header-bar.dir-rising .detail-dir-badge { color: var(--intel-success); }
.detail-header-bar.dir-stable .detail-dir-badge { color: var(--intel-info); }
.detail-header-bar.dir-falling .detail-dir-badge { color: var(--intel-danger); }
.detail-score-big {
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
.text-block {
  font-size: var(--font-size-sm);
  color: #606266;
  line-height: 1.8;
  background: #f8f9fa;
  padding: var(--spacing-md);
  border-radius: var(--intel-radius);
}
.text-block.highlight {
  background: #ecfdf5;
  color: var(--intel-text);
  font-weight: 500;
  border-left: 3px solid var(--intel-success);
}
.tag-list {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

@media (max-width: 768px) {
  .trend-stats {
    grid-template-columns: repeat(2, 1fr);
  }
  .trend-grid {
    grid-template-columns: 1fr;
  }
}
</style>
