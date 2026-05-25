<template>
  <div class="trends-page">
    <div class="page-header">
      <h2>趋势分析</h2>
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

    <div v-if="loading" class="loading-placeholder">
      <el-skeleton :rows="8" animated />
    </div>
    <el-empty v-else-if="!items.length" description="暂无趋势数据" />
    <div v-else class="trend-grid">
      <el-card v-for="item in filteredItems" :key="item.id" shadow="hover" class="trend-card" @click="openDetail(item)">
        <div class="card-body">
          <div class="card-title">{{ item.title }}</div>
          <div class="card-meta">
            <el-tag size="small">{{ item.category }}</el-tag>
            <el-tag size="small" :type="scoreType(item.opportunity_score)">
              {{ item.opportunity_score }}分
            </el-tag>
            <el-tag size="small" v-if="item.platform">{{ item.platform }}</el-tag>
            <el-tag size="small" v-if="item.lifecycle" type="success">{{ item.lifecycle }}</el-tag>
            <el-tag size="small" v-if="item.direction" :type="directionType(item.direction)">{{ directionLabel(item.direction) }}</el-tag>
          </div>
          <div class="card-extra" v-if="item.user_emotion || item.competition">
            <span v-if="item.user_emotion">用户情绪：{{ item.user_emotion }}</span>
            <span v-if="item.competition">竞争度：{{ item.competition }}</span>
          </div>
          <div class="card-risk" v-if="item.risk_level">
            <el-tag :type="riskType(item.risk_level)" size="small">风险：{{ item.risk_level }}</el-tag>
          </div>
          <div class="card-insight" v-if="item.actionable_insight">
            {{ truncate(item.actionable_insight, 60) }}
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

    <el-dialog v-model="detailVisible" :title="detailItem?.title" width="720px" destroy-on-close>
      <div v-if="detailItem" class="trend-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="分类">{{ detailItem.category }}</el-descriptions-item>
          <el-descriptions-item label="平台">{{ detailItem.platform }}</el-descriptions-item>
          <el-descriptions-item label="机会评分">
            <el-tag :type="scoreType(detailItem.opportunity_score)">{{ detailItem.opportunity_score }}分</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="生命周期">{{ detailItem.lifecycle }}</el-descriptions-item>
          <el-descriptions-item label="趋势方向">
            <el-tag :type="directionType(detailItem.direction)">{{ directionLabel(detailItem.direction) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="竞争度">{{ detailItem.competition }}</el-descriptions-item>
          <el-descriptions-item label="风险等级">
            <el-tag :type="riskType(detailItem.risk_level)">{{ detailItem.risk_level }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="用户情绪">{{ detailItem.user_emotion || "-" }}</el-descriptions-item>
          <el-descriptions-item label="变现潜力" v-if="detailItem.monetization_potential">{{ detailItem.monetization_potential }}</el-descriptions-item>
          <el-descriptions-item label="新鲜度" v-if="detailItem.freshness_days">{{ detailItem.freshness_days }}天</el-descriptions-item>
        </el-descriptions>

        <div class="detail-section" v-if="detailItem.evidence">
          <h4>证据</h4>
          <div class="text-block">{{ detailItem.evidence }}</div>
        </div>

        <div class="detail-section" v-if="detailItem.actionable_insight">
          <h4>行动建议</h4>
          <div class="text-block highlight">{{ detailItem.actionable_insight }}</div>
        </div>

        <div class="detail-section" v-if="detailItem.risk_note">
          <h4>风险备注</h4>
          <el-alert :title="detailItem.risk_note" type="warning" :closable="false" show-icon />
        </div>

        <div class="detail-section" v-if="detailItem.affected_opportunities?.length">
          <h4>关联机会</h4>
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
import { exportJSON, exportCSV, deleteItem, truncate, isAdmin } from "@/utils/intel"

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

function directionLabel(d: string): string {
  const map: Record<string, string> = { rising: "上升", stable: "稳定", falling: "下降" }
  return map[d?.toLowerCase()] || d
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
    const { data } = await api.get("/intel/trends")
    items.value = data?.items || data || []
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
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 10px;
}
.page-header h2 { margin: 0; font-size: 20px; }
.header-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.loading-placeholder { padding: 16px; }
.trend-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}
.trend-card { cursor: pointer; transition: transform 0.2s; }
.trend-card:hover { transform: translateY(-2px); }
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
.card-extra {
  font-size: 12px;
  color: #909399;
  display: flex;
  gap: 12px;
  margin-bottom: 6px;
}
.card-risk { margin-top: 4px; }
.card-insight {
  font-size: 12px;
  color: #409eff;
  margin-top: 6px;
  line-height: 1.5;
}
.pagination-wrap {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}
.trend-detail { padding: 0; }
.detail-section { margin-top: 20px; }
.detail-section h4 {
  font-size: 14px;
  color: #303133;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid #f0f0f0;
}
.text-block {
  font-size: 13px;
  color: #606266;
  line-height: 1.8;
  background: #f8f9fa;
  padding: 12px;
  border-radius: 6px;
}
.text-block.highlight {
  background: #ecf5ff;
  color: #303133;
  font-weight: 500;
}
.tag-list {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
</style>
