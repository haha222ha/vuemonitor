<template>
  <div class="risks-page">
    <div class="page-header">
      <div class="header-title-area">
        <h2>风险预警</h2>
        <p class="header-subtitle" v-if="items.length">实时监控商业风险，提前预警规避陷阱</p>
      </div>
      <div class="header-actions">
        <el-radio-group v-model="viewMode" size="small">
          <el-radio-button value="card">卡片</el-radio-button>
          <el-radio-button value="table">表格</el-radio-button>
        </el-radio-group>
        <el-select v-model="severityFilter" placeholder="严重程度" clearable size="small" style="width: 120px">
          <el-option label="全部" value="" />
          <el-option label="高" value="high" />
          <el-option label="中" value="medium" />
          <el-option label="低" value="low" />
        </el-select>
        <el-input v-model="searchText" placeholder="搜索风险项..." size="small" clearable style="width: 220px" />
        <el-button size="small" @click="doExportCSV">导出CSV</el-button>
        <el-button size="small" @click="doExportJSON">导出JSON</el-button>
      </div>
    </div>

    <div class="risk-stats" v-if="items.length">
      <div class="risk-stat-item stat-high">
        <span class="stat-icon">🔴</span>
        <span class="stat-num">{{ severityCount('high') }}</span>
        <span class="stat-text">高风险</span>
      </div>
      <div class="risk-stat-item stat-medium">
        <span class="stat-icon">🟡</span>
        <span class="stat-num">{{ severityCount('medium') }}</span>
        <span class="stat-text">中风险</span>
      </div>
      <div class="risk-stat-item stat-low">
        <span class="stat-icon">🟢</span>
        <span class="stat-num">{{ severityCount('low') }}</span>
        <span class="stat-text">低风险</span>
      </div>
      <div class="risk-stat-item stat-active">
        <span class="stat-icon">⚡</span>
        <span class="stat-num">{{ activeCount }}</span>
        <span class="stat-text">活跃预警</span>
      </div>
    </div>

    <div v-if="loading" class="loading-placeholder">
      <el-skeleton :rows="6" animated />
    </div>
    <div v-else-if="!items.length" class="intel-empty-state">
      <div class="intel-empty-state-icon">🛡️</div>
      <div class="intel-empty-state-text">暂无风险数据</div>
      <div class="intel-empty-state-action">数据更新后将自动展示</div>
    </div>

    <div v-else-if="viewMode === 'card'" class="risk-grid intel-card-stagger">
      <div
        v-for="item in filteredItems"
        :key="item.id"
        class="risk-card"
        :class="'severity-' + (item.severity || '').toLowerCase()"
        @click="openDetail(item)"
      >
        <div class="risk-severity-bar"></div>
        <div class="card-body">
          <div class="card-top-row">
            <div class="severity-badge" :class="'sev-' + (item.severity || '').toLowerCase()">
              {{ severityLabel(item.severity) }}
            </div>
            <el-tag v-if="item.status === 'active'" type="danger" size="small" effect="dark">
              <span class="pulse-dot"></span> 活跃
            </el-tag>
            <el-tag v-else type="info" size="small">已解除</el-tag>
          </div>
          <div class="risk-name">{{ item.name }}</div>
          <div class="risk-reason">{{ item.reason }}</div>
          <div class="risk-alt" v-if="item.alternative">
            <div class="alt-label">✅ 替代方案</div>
            <div class="alt-text">{{ item.alternative }}</div>
          </div>
          <div class="card-meta">
            <el-tag v-if="item.risk_type" size="small" type="info" effect="plain">{{ item.risk_type }}</el-tag>
            <el-tag v-if="item.category" size="small" effect="plain">{{ item.category }}</el-tag>
          </div>
          <div class="card-footer">
            <span class="card-action">查看详情 →</span>
          </div>
        </div>
      </div>
    </div>

    <el-card v-else shadow="hover" class="risk-table-card">
      <el-table :data="filteredItems" style="width: 100%" @row-click="openDetail">
        <el-table-column prop="name" label="风险项" min-width="180" />
        <el-table-column prop="severity" label="严重程度" width="110">
          <template #default="{ row }">
            <el-tag :type="severityTagType(row.severity)" size="small">{{ severityLabel(row.severity) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'danger' : 'info'" size="small">
              {{ row.status === "active" ? "活跃" : "已解除" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="原因" min-width="240" show-overflow-tooltip />
        <el-table-column prop="alternative" label="替代方案" min-width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.alternative" class="alt-highlight">{{ row.alternative }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="risk_type" label="风险类型" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.risk_type" size="small" type="info">{{ row.risk_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button v-if="isAdmin()" type="danger" text size="small" @click.stop="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

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

    <el-dialog v-model="detailVisible" :title="detailItem?.name" width="640px" destroy-on-close>
      <div v-if="detailItem" class="risk-detail">
        <div class="detail-severity-bar" :class="'severity-' + (detailItem.severity || '').toLowerCase()">
          <div class="severity-badge-lg" :class="'sev-' + (detailItem.severity || '').toLowerCase()">
            {{ severityLabel(detailItem.severity) }}风险
          </div>
          <el-tag v-if="detailItem.status === 'active'" type="danger" effect="dark" size="large">
            <span class="pulse-dot"></span> 活跃预警
          </el-tag>
          <el-tag v-else type="info" effect="dark" size="large">已解除</el-tag>
        </div>

        <el-descriptions :column="2" border>
          <el-descriptions-item label="风险类型" v-if="detailItem.risk_type">{{ detailItem.risk_type }}</el-descriptions-item>
          <el-descriptions-item label="分类" v-if="detailItem.category">{{ detailItem.category }}</el-descriptions-item>
          <el-descriptions-item label="原因" :span="2">{{ detailItem.reason }}</el-descriptions-item>
          <el-descriptions-item label="替代方案" :span="2">
            <span v-if="detailItem.alternative" class="alt-highlight-detail">{{ detailItem.alternative }}</span>
            <span v-else>-</span>
          </el-descriptions-item>
          <el-descriptions-item label="风险描述" :span="2" v-if="detailItem.risk_description">{{ detailItem.risk_description }}</el-descriptions-item>
          <el-descriptions-item label="建议行动" :span="2" v-if="detailItem.recommended_action">{{ detailItem.recommended_action }}</el-descriptions-item>
          <el-descriptions-item label="早期信号" :span="2" v-if="detailItem.early_signal">{{ detailItem.early_signal }}</el-descriptions-item>
          <el-descriptions-item label="影响赛道" v-if="detailItem.affected_track">{{ detailItem.affected_track }}</el-descriptions-item>
          <el-descriptions-item label="平台" v-if="detailItem.platform">{{ detailItem.platform }}</el-descriptions-item>
        </el-descriptions>
        <div class="detail-section" v-if="detailItem.early_signals?.length">
          <h4>🔔 早期信号列表</h4>
          <div class="tag-list">
            <el-tag v-for="(s, idx) in detailItem.early_signals" :key="idx" size="small" type="warning">
              {{ typeof s === 'string' ? s : JSON.stringify(s) }}
            </el-tag>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button v-if="isAdmin()" @click="handleDelete(detailItem)" type="danger" size="small">删除</el-button>
        <el-button @click="exportJSON([detailItem], detailItem?.name || '风险')" size="small">导出</el-button>
        <el-button @click="detailVisible = false" size="small">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import api from "@/utils/api"
import { exportJSON, exportCSV, deleteItem, isAdmin, fetchWithCache, clearCache } from "@/utils/intel"

interface RiskItem {
  id: string
  name: string
  category?: string
  severity: string
  status: string
  reason?: string
  alternative?: string
  early_signal?: string
  early_signals?: unknown[]
  risk_type?: string
  risk_description?: string
  recommended_action?: string
  affected_track?: string
  platform?: string
  [key: string]: unknown
}

const items = ref<RiskItem[]>([])
const loading = ref(false)
const searchText = ref("")
const severityFilter = ref("")
const viewMode = ref<"card" | "table">("card")
const currentPage = ref(1)
const pageSize = 15
const detailItem = ref<RiskItem | null>(null)
const detailVisible = ref(false)

function severityCount(level: string): number {
  return items.value.filter(i => i.severity?.toLowerCase() === level).length
}

const activeCount = computed(() => items.value.filter(i => i.status === 'active').length)

const filteredItems = computed(() => {
  let result = items.value
  if (searchText.value) {
    const s = searchText.value.toLowerCase()
    result = result.filter((i) => i.name.toLowerCase().includes(s) || i.reason?.toLowerCase().includes(s))
  }
  if (severityFilter.value) {
    result = result.filter((i) => i.severity?.toLowerCase() === severityFilter.value)
  }
  const start = (currentPage.value - 1) * pageSize
  return result.slice(start, start + pageSize)
})

const filteredTotal = computed(() => {
  let result = items.value
  if (searchText.value) {
    const s = searchText.value.toLowerCase()
    result = result.filter((i) => i.name.toLowerCase().includes(s) || i.reason?.toLowerCase().includes(s))
  }
  if (severityFilter.value) {
    result = result.filter((i) => i.severity?.toLowerCase() === severityFilter.value)
  }
  return result.length
})

function severityTagType(s: string): string {
  const map: Record<string, string> = { high: "danger", medium: "warning", low: "info" }
  return map[s?.toLowerCase()] || "info"
}

function severityLabel(s: string): string {
  const map: Record<string, string> = { high: "高", medium: "中", low: "低" }
  return map[s?.toLowerCase()] || s
}

function openDetail(row: RiskItem) {
  detailItem.value = row
  detailVisible.value = true
}

async function handleDelete(item: RiskItem | null) {
  if (!item) return
  const ok = await deleteItem("risks", item.id, item.name)
  if (ok) {
    items.value = items.value.filter((i) => i.id !== item.id)
    clearCache("risks")
    detailVisible.value = false
  }
}

function doExportCSV() { exportCSV(filteredItems.value as Record<string, unknown>[], "风险预警") }
function doExportJSON() { exportJSON(filteredItems.value, "风险预警") }

function handlePageChange() {
  scrollTo({ top: 0, behavior: "smooth" })
}

onMounted(async () => {
  loading.value = true
  try {
    items.value = await fetchWithCache<RiskItem>("risks", "/intel/risks")
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.risks-page { max-width: 1400px; }
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

.risk-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}
.risk-stat-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md) var(--spacing-lg);
  border-radius: var(--intel-radius-lg);
  background: var(--intel-surface);
  box-shadow: var(--intel-shadow);
  transition: all var(--transition-base);
}
.risk-stat-item:hover {
  box-shadow: var(--intel-shadow-hover);
  transform: translateY(-2px);
}
.stat-icon { font-size: var(--font-size-xl); }
.stat-num { font-size: var(--font-size-2xl); font-weight: 800; }
.stat-text { font-size: var(--font-size-sm); color: var(--intel-text-secondary); }
.stat-high .stat-num { color: var(--intel-danger); }
.stat-medium .stat-num { color: var(--intel-warning); }
.stat-low .stat-num { color: var(--intel-success); }
.stat-active .stat-num { color: var(--intel-danger); }

.loading-placeholder { padding: var(--spacing-md); }

.risk-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: var(--spacing-md);
}
.risk-card {
  background: var(--intel-surface);
  border-radius: var(--intel-radius-lg);
  box-shadow: var(--intel-shadow);
  cursor: pointer;
  transition: all var(--transition-base);
  overflow: hidden;
}
.risk-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--intel-shadow-hover);
}
.risk-card:hover .card-footer .card-action {
  transform: translateX(4px);
}
.risk-severity-bar { height: 3px; width: 100%; }
.risk-card.severity-high .risk-severity-bar { background: var(--intel-danger); }
.risk-card.severity-medium .risk-severity-bar { background: var(--intel-warning); }
.risk-card.severity-low .risk-severity-bar { background: var(--intel-success); }
.risk-card.severity-high { border-left: 4px solid var(--intel-danger); }
.risk-card.severity-medium { border-left: 4px solid var(--intel-warning); }
.risk-card.severity-low { border-left: 4px solid var(--intel-success); }
.card-body { padding: var(--spacing-md) var(--spacing-lg); }
.card-top-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.severity-badge {
  padding: 3px 10px;
  border-radius: 10px;
  font-size: var(--font-size-sm);
  font-weight: 700;
}
.severity-badge.sev-high { background: #fef2f2; color: var(--intel-danger); }
.severity-badge.sev-medium { background: #fdf6ec; color: var(--intel-warning); }
.severity-badge.sev-low { background: #f0f9eb; color: var(--intel-success); }
.pulse-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  margin-right: 4px;
  animation: pulse-ring 2s ease-in-out infinite;
}
.risk-name {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--intel-text);
  margin-bottom: var(--spacing-sm);
}
.risk-reason {
  font-size: var(--font-size-sm);
  color: #606266;
  line-height: 1.6;
  margin-bottom: 10px;
}
.risk-alt {
  background: linear-gradient(135deg, #f0f9eb 0%, #ecfdf5 100%);
  border-radius: var(--intel-radius);
  padding: 10px 14px;
  margin-bottom: 10px;
  border: 1px solid #a7f3d0;
}
.alt-label {
  font-size: var(--font-size-sm);
  color: var(--intel-success);
  font-weight: 600;
  margin-bottom: 4px;
}
.alt-text {
  font-size: var(--font-size-sm);
  color: var(--intel-text);
  line-height: 1.6;
}
.card-meta {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
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

.risk-table-card { margin-top: 0; }
.alt-highlight {
  color: var(--intel-success);
  font-weight: 500;
}
.alt-highlight-detail {
  color: var(--intel-success);
  font-weight: 600;
  background: #f0f9eb;
  padding: 2px 8px;
  border-radius: var(--intel-radius);
}

.pagination-wrap {
  margin-top: var(--spacing-lg);
  display: flex;
  justify-content: center;
}

.risk-detail { padding: 0; }
.detail-severity-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-md) var(--spacing-lg);
  border-radius: var(--intel-radius-lg);
  margin-bottom: var(--spacing-lg);
}
.detail-severity-bar.severity-high { background: linear-gradient(135deg, #fef2f2 0%, #fff5f5 100%); }
.detail-severity-bar.severity-medium { background: linear-gradient(135deg, #fdf6ec 0%, #fffbeb 100%); }
.detail-severity-bar.severity-low { background: linear-gradient(135deg, #f0f9eb 0%, #ecfdf5 100%); }
.severity-badge-lg {
  font-size: var(--font-size-lg);
  font-weight: 700;
  padding: 4px 14px;
  border-radius: var(--intel-radius);
}
.severity-badge-lg.sev-high { background: #fef2f2; color: var(--intel-danger); }
.severity-badge-lg.sev-medium { background: #fdf6ec; color: var(--intel-warning); }
.severity-badge-lg.sev-low { background: #f0f9eb; color: var(--intel-success); }

.detail-section { margin-top: var(--spacing-lg); }
.detail-section h4 {
  font-size: var(--font-size-md);
  color: var(--intel-text);
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--intel-border-light);
  font-weight: 600;
}
.tag-list {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

@media (max-width: 768px) {
  .risk-stats {
    grid-template-columns: repeat(2, 1fr);
  }
  .risk-grid {
    grid-template-columns: 1fr;
  }
}
</style>
