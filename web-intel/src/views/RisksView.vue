<template>
  <div class="risks-page">
    <div class="page-header">
      <h2>风险预警</h2>
      <div class="header-actions">
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

    <div v-if="loading" class="loading-placeholder">
      <el-skeleton :rows="6" animated />
    </div>
    <el-empty v-else-if="!items.length" description="暂无风险数据" />
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
        <el-table-column prop="alternative" label="替代方案" min-width="200" show-overflow-tooltip />
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

      <div class="pagination-wrap">
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
    </el-card>

    <el-dialog v-model="detailVisible" :title="detailItem?.name" width="640px" destroy-on-close>
      <div v-if="detailItem" class="risk-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="严重程度">
            <el-tag :type="severityTagType(detailItem.severity)" size="small">{{ severityLabel(detailItem.severity) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="detailItem.status === 'active' ? 'danger' : 'info'" size="small">{{ detailItem.status }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="风险类型" v-if="detailItem.risk_type">{{ detailItem.risk_type }}</el-descriptions-item>
          <el-descriptions-item label="分类" v-if="detailItem.category">{{ detailItem.category }}</el-descriptions-item>
          <el-descriptions-item label="原因" :span="2">{{ detailItem.reason }}</el-descriptions-item>
          <el-descriptions-item label="替代方案" :span="2">{{ detailItem.alternative }}</el-descriptions-item>
          <el-descriptions-item label="风险描述" :span="2" v-if="detailItem.risk_description">{{ detailItem.risk_description }}</el-descriptions-item>
          <el-descriptions-item label="建议行动" :span="2" v-if="detailItem.recommended_action">{{ detailItem.recommended_action }}</el-descriptions-item>
          <el-descriptions-item label="早期信号" :span="2" v-if="detailItem.early_signal">{{ detailItem.early_signal }}</el-descriptions-item>
          <el-descriptions-item label="影响赛道" v-if="detailItem.affected_track">{{ detailItem.affected_track }}</el-descriptions-item>
          <el-descriptions-item label="平台" v-if="detailItem.platform">{{ detailItem.platform }}</el-descriptions-item>
        </el-descriptions>
        <div class="detail-section" v-if="detailItem.early_signals?.length">
          <h4>早期信号列表</h4>
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
import { exportJSON, exportCSV, deleteItem, isAdmin } from "@/utils/intel"

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
const currentPage = ref(1)
const pageSize = 15
const detailItem = ref<RiskItem | null>(null)
const detailVisible = ref(false)

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
    const { data } = await api.get("/intel/risks")
    items.value = data?.items || data || []
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
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 10px;
}
.page-header h2 { margin: 0; font-size: 20px; }
.header-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.loading-placeholder { padding: 16px; }
.risk-table-card { margin-top: 0; }
.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}
.risk-detail { padding: 0; }
.detail-section { margin-top: 20px; }
.detail-section h4 {
  font-size: 14px;
  color: #303133;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid #f0f0f0;
}
.tag-list {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
</style>
