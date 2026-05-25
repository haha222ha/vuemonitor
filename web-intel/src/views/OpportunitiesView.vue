<template>
  <div class="opportunities-page">
    <div class="page-header">
      <h2>商业机会</h2>
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

    <div v-if="loading" class="loading-placeholder">
      <el-skeleton :rows="8" animated />
    </div>
    <el-empty v-else-if="!items.length" description="暂无商业机会数据" />
    <div v-else class="opp-grid">
      <el-card v-for="item in filteredItems" :key="item.id" shadow="hover" class="opp-card" @click="openDetail(item)">
        <div class="card-body">
          <div class="card-title">{{ item.name }}</div>
          <div class="card-meta">
            <el-tag size="small">{{ item.category }}</el-tag>
            <el-tag size="small" :type="scoreType(item.verdict_score)">
              评分 {{ item.verdict_score }}
            </el-tag>
            <el-tag size="small" v-if="item.verdict" :type="verdictType(item.verdict)">{{ item.verdict }}</el-tag>
            <el-tag size="small" v-if="item.difficulty">难度 {{ item.difficulty }}</el-tag>
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
        </div>
      </el-card>
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
        <el-descriptions :column="2" border>
          <el-descriptions-item label="分类">{{ detailItem.category }}</el-descriptions-item>
          <el-descriptions-item label="子分类" v-if="detailItem.sub_category">{{ detailItem.sub_category }}</el-descriptions-item>
          <el-descriptions-item label="评分">
            <el-tag :type="scoreType(detailItem.verdict_score)">{{ detailItem.verdict_score }}分</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="判定">
            <el-tag :type="verdictType(detailItem.verdict)">{{ detailItem.verdict }}</el-tag>
          </el-descriptions-item>
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
          <h4>判定详情</h4>
          <div class="json-block">
            <div v-for="(val, key) in detailItem.verdict_detail" :key="key" class="json-row">
              <span class="json-key">{{ key }}</span>
              <span class="json-val">{{ formatValue(val) }}</span>
            </div>
          </div>
        </div>

        <div class="detail-section" v-if="detailItem.commercial_paths?.length">
          <h4>商业化路径</h4>
          <div class="paths-list">
            <div v-for="(path, idx) in detailItem.commercial_paths" :key="idx" class="path-item">
              <el-tag type="success" size="small">{{ idx + 1 }}</el-tag>
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
          <h4>关键指标</h4>
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
        <el-button @click="handleDelete(detailItem)" type="danger" size="small">删除</el-button>
        <el-button @click="exportJSON([detailItem!], detailItem!.name)" size="small">导出</el-button>
        <el-button @click="detailVisible = false" size="small">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import api from "@/utils/api"
import { exportJSON, exportCSV, deleteItem, formatValue } from "@/utils/intel"

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
  [key: string]: unknown
}

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

function openDetail(item: OpportunityItem) {
  detailItem.value = item
  detailVisible.value = true
}

async function handleDelete(item: OpportunityItem | null) {
  if (!item) return
  const ok = await deleteItem("opportunities", item.id, item.name)
  if (ok) {
    items.value = items.value.filter((i) => i.id !== item.id)
    detailVisible.value = false
  }
}

function handlePageChange() {
  scrollTo({ top: 0, behavior: "smooth" })
}

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await api.get("/intel/opportunities")
    items.value = data?.items || data || []
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
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 10px;
}
.page-header h2 { margin: 0; font-size: 20px; }
.header-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.loading-placeholder { padding: 16px; }
.opp-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}
.opp-card { cursor: pointer; transition: transform 0.2s; }
.opp-card:hover { transform: translateY(-2px); }
.card-body { padding: 0; }
.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 10px;
  line-height: 1.5;
}
.card-meta {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.card-details {
  background: #f5f7fa;
  border-radius: 6px;
  padding: 8px 12px;
  margin-bottom: 8px;
}
.detail-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  padding: 2px 0;
}
.detail-label { color: #909399; }
.detail-value { color: #303133; font-weight: 500; }
.card-paths {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin-bottom: 6px;
}
.card-fit {
  font-size: 12px;
  color: #909399;
}
.fit-label { color: #606266; }
.pagination-wrap {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}
.opp-detail { padding: 0; }
.detail-section { margin-top: 20px; }
.detail-section h4 {
  font-size: 14px;
  color: #303133;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid #f0f0f0;
}
.json-block {
  background: #f8f9fa;
  border-radius: 6px;
  padding: 12px;
}
.json-row {
  display: flex;
  gap: 12px;
  padding: 4px 0;
  font-size: 13px;
  border-bottom: 1px solid #f0f0f0;
}
.json-row:last-child { border-bottom: none; }
.json-key { color: #909399; min-width: 100px; flex-shrink: 0; }
.json-val { color: #303133; word-break: break-all; }
.paths-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.path-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
  color: #303133;
}
.path-detail {
  flex: 1;
  background: #f0f9eb;
  border-radius: 6px;
  padding: 8px 12px;
}
.path-main {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.path-type {
  font-weight: 600;
  color: #67c23a;
}
.path-desc {
  color: #303133;
}
.path-name {
  color: #303133;
  font-weight: 500;
}
.path-price {
  font-size: 12px;
  color: #e6a23c;
  margin-top: 4px;
  display: block;
}
</style>
