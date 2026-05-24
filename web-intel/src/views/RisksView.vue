<template>
  <div class="risks-page">
    <div class="page-header">
      <h2>风险预警</h2>
      <div class="header-filters">
        <el-select v-model="severityFilter" placeholder="严重程度" clearable size="small" style="width: 120px">
          <el-option label="全部" value="" />
          <el-option label="高" value="high" />
          <el-option label="中" value="medium" />
          <el-option label="低" value="low" />
        </el-select>
        <el-input v-model="searchText" placeholder="搜索风险项..." size="small" clearable style="width: 220px" />
      </div>
    </div>

    <div v-if="loading" class="loading-placeholder">
      <el-skeleton :rows="6" animated />
    </div>
    <el-empty v-else-if="!items.length" description="暂无风险数据" />
    <el-card v-else shadow="hover" class="risk-table-card">
      <el-table :data="filteredItems" style="width: 100%" @row-click="showDetail = $event">
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

    <el-dialog v-model="detailVisible" :title="showDetail?.name" width="600px">
      <div v-if="showDetail" class="risk-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="严重程度">
            <el-tag :type="severityTagType(showDetail.severity)" size="small">{{ showDetail.severity }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="showDetail.status === 'active' ? 'danger' : 'info'" size="small">{{ showDetail.status }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="风险类型" v-if="showDetail.risk_type">{{ showDetail.risk_type }}</el-descriptions-item>
          <el-descriptions-item label="原因" :span="2">{{ showDetail.reason }}</el-descriptions-item>
          <el-descriptions-item label="替代方案" :span="2">{{ showDetail.alternative }}</el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import api from "@/utils/api"
import type { RiskItem } from "@/stores/intel"

const items = ref<RiskItem[]>([])
const loading = ref(false)
const searchText = ref("")
const severityFilter = ref("")
const currentPage = ref(1)
const pageSize = 15
const showDetail = ref<RiskItem | null>(null)
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
}
.page-header h2 { margin: 0; font-size: 20px; }
.header-filters { display: flex; gap: 10px; }
.loading-placeholder { padding: 16px; }
.risk-table-card { margin-top: 0; }
.pagination-wrap {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}
.risk-detail { padding: 0; }
</style>