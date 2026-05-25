<template>
  <div class="emotions-page">
    <div class="page-header">
      <h2>用户情绪分析</h2>
      <div class="header-actions">
        <el-select v-model="sentimentFilter" placeholder="情绪倾向" clearable size="small" style="width: 140px">
          <el-option label="全部" value="" />
          <el-option label="正面" value="positive" />
          <el-option label="中性" value="neutral" />
          <el-option label="负面" value="negative" />
        </el-select>
        <el-input v-model="searchText" placeholder="搜索关键词..." size="small" clearable style="width: 220px" />
        <el-button size="small" @click="doExportCSV">导出CSV</el-button>
        <el-button size="small" @click="doExportJSON">导出JSON</el-button>
      </div>
    </div>

    <div v-if="loading" class="loading-placeholder">
      <el-skeleton :rows="8" animated />
    </div>
    <el-empty v-else-if="!items.length" description="暂无用户情绪数据" />
    <div v-else class="emotion-grid">
      <el-card v-for="item in filteredItems" :key="item.id || item.keyword" shadow="hover" class="emotion-card" @click="openDetail(item)">
        <div class="card-body">
          <div class="card-header-row">
            <span class="keyword">{{ item.keyword || item.keyword_cluster }}</span>
            <el-tag :type="sentimentTagType(item.sentiment)" size="small" effect="plain">
              {{ sentimentLabel(item.sentiment) }}
            </el-tag>
          </div>
          <div class="card-stats" v-if="item.intensity !== undefined || item.volume !== undefined">
            <div class="stat-item" v-if="item.intensity !== undefined">
              <span class="stat-label">情绪强度</span>
              <el-progress
                :percentage="Math.round((item.intensity || 0) * 100)"
                :color="intensityColor(item.intensity)"
                :stroke-width="8"
              />
            </div>
            <div class="stat-item" v-if="item.volume !== undefined">
              <span class="stat-label">讨论量</span>
              <span class="stat-value">{{ item.volume }}</span>
            </div>
          </div>
          <div class="card-keywords" v-if="item.related_keywords?.length">
            <span class="kw-label">关联词：</span>
            <el-tag v-for="kw in item.related_keywords.slice(0, 6)" :key="kw" size="small" type="info">{{ kw }}</el-tag>
            <el-tag v-if="item.related_keywords.length > 6" size="small" type="info">
              +{{ item.related_keywords.length - 6 }}
            </el-tag>
          </div>
          <div class="card-note" v-if="item.insight || item.note">
            {{ item.insight || item.note }}
          </div>
          <div class="card-actions" v-if="isAdmin()">
            <el-button type="danger" text size="small" @click.stop="handleDelete(item)">删除</el-button>
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

    <el-dialog v-model="detailVisible" :title="detailItem?.keyword || detailItem?.keyword_cluster || '情绪详情'" width="640px" destroy-on-close>
      <div v-if="detailItem" class="emotion-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="关键词">{{ detailItem.keyword || "-" }}</el-descriptions-item>
          <el-descriptions-item label="情绪倾向">
            <el-tag :type="sentimentTagType(detailItem.sentiment)" size="small">{{ sentimentLabel(detailItem.sentiment) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="情绪强度">
            <el-progress
              :percentage="Math.round((detailItem.intensity || 0) * 100)"
              :color="intensityColor(detailItem.intensity)"
              :stroke-width="10"
              style="width: 160px"
            />
          </el-descriptions-item>
          <el-descriptions-item label="讨论量">{{ detailItem.volume ?? "-" }}</el-descriptions-item>
          <el-descriptions-item label="平台来源" v-if="detailItem.platform_source">{{ detailItem.platform_source }}</el-descriptions-item>
          <el-descriptions-item label="趋势方向" v-if="detailItem.trend_direction">
            <el-tag :type="detailItem.trend_direction === 'rising' ? 'success' : detailItem.trend_direction === 'falling' ? 'danger' : 'info'" size="small">
              {{ detailItem.trend_direction === 'rising' ? '上升' : detailItem.trend_direction === 'falling' ? '下降' : '稳定' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="情绪类型" v-if="detailItem.emotion_type">{{ detailItem.emotion_type }}</el-descriptions-item>
          <el-descriptions-item label="原始强度" v-if="detailItem.intensity_raw">{{ detailItem.intensity_raw }}</el-descriptions-item>
        </el-descriptions>

        <div class="detail-section" v-if="detailItem.keyword_cluster?.length">
          <h4>关键词聚类</h4>
          <div class="tag-list">
            <el-tag v-for="kw in detailItem.keyword_cluster" :key="kw" size="small" type="info">{{ kw }}</el-tag>
          </div>
        </div>

        <div class="detail-section" v-if="detailItem.related_keywords?.length">
          <h4>关联关键词</h4>
          <div class="tag-list">
            <el-tag v-for="kw in detailItem.related_keywords" :key="kw" size="small">{{ kw }}</el-tag>
          </div>
        </div>

        <div class="detail-section" v-if="detailItem.insight || detailItem.note">
          <h4>洞察分析</h4>
          <div class="text-block highlight">{{ detailItem.insight || detailItem.note }}</div>
        </div>
      </div>
      <template #footer>
        <el-button v-if="isAdmin()" @click="handleDelete(detailItem)" type="danger" size="small">删除</el-button>
        <el-button @click="exportJSON([detailItem], detailItem?.keyword || '情绪')" size="small">导出</el-button>
        <el-button @click="detailVisible = false" size="small">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import api from "@/utils/api"
import { exportJSON, exportCSV, deleteItem, isAdmin } from "@/utils/intel"

interface EmotionItem {
  id?: string
  keyword?: string
  keyword_cluster?: string[]
  sentiment?: string
  intensity?: number
  volume?: number
  related_keywords?: string[]
  insight?: string
  note?: string
  platform_source?: string
  trend_direction?: string
  emotion_type?: string
  intensity_raw?: string
  [key: string]: unknown
}

const items = ref<EmotionItem[]>([])
const loading = ref(false)
const sentimentFilter = ref("")
const searchText = ref("")
const currentPage = ref(1)
const pageSize = 12
const detailItem = ref<EmotionItem | null>(null)
const detailVisible = ref(false)

const filteredItems = computed(() => {
  let result = items.value
  if (sentimentFilter.value) {
    result = result.filter((i) => i.sentiment?.toLowerCase() === sentimentFilter.value)
  }
  if (searchText.value) {
    const s = searchText.value.toLowerCase()
    result = result.filter((i) =>
      (i.keyword || "").toLowerCase().includes(s) ||
      (i.keyword_cluster || []).some((k) => k.toLowerCase().includes(s)) ||
      (i.related_keywords || []).some((k) => k.toLowerCase().includes(s))
    )
  }
  const start = (currentPage.value - 1) * pageSize
  return result.slice(start, start + pageSize)
})

const filteredTotal = computed(() => {
  let result = items.value
  if (sentimentFilter.value) {
    result = result.filter((i) => i.sentiment?.toLowerCase() === sentimentFilter.value)
  }
  if (searchText.value) {
    const s = searchText.value.toLowerCase()
    result = result.filter((i) =>
      (i.keyword || "").toLowerCase().includes(s) ||
      (i.keyword_cluster || []).some((k) => k.toLowerCase().includes(s)) ||
      (i.related_keywords || []).some((k) => k.toLowerCase().includes(s))
    )
  }
  return result.length
})

function sentimentTagType(s?: string): string {
  const map: Record<string, string> = { positive: "success", neutral: "info", negative: "danger" }
  return map[s?.toLowerCase() || ""] || "info"
}

function sentimentLabel(s?: string): string {
  const map: Record<string, string> = { positive: "正面", neutral: "中性", negative: "负面" }
  return map[s?.toLowerCase() || ""] || s || "未知"
}

function intensityColor(value?: number): string {
  if (!value) return "#909399"
  if (value >= 0.7) return "#f56c6c"
  if (value >= 0.4) return "#e6a23c"
  return "#67c23a"
}

function openDetail(item: EmotionItem) {
  detailItem.value = item
  detailVisible.value = true
}

async function handleDelete(item: EmotionItem | null) {
  if (!item?.id) return
  const ok = await deleteItem("emotions", item.id, item.keyword || "该情绪数据")
  if (ok) {
    items.value = items.value.filter((i) => i.id !== item.id)
    detailVisible.value = false
  }
}

function doExportCSV() { exportCSV(filteredItems.value as Record<string, unknown>[], "用户情绪分析") }
function doExportJSON() { exportJSON(filteredItems.value, "用户情绪分析") }

function handlePageChange() {
  scrollTo({ top: 0, behavior: "smooth" })
}

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await api.get("/intel/emotions")
    items.value = data?.items || data || []
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.emotions-page { max-width: 1400px; }
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
.emotion-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}
.emotion-card { cursor: pointer; transition: transform 0.2s; }
.emotion-card:hover { transform: translateY(-2px); }
.card-body { padding: 0; }
.card-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.keyword {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}
.card-stats {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 10px;
}
.stat-item { }
.stat-label {
  font-size: 12px;
  color: #909399;
  display: block;
  margin-bottom: 4px;
}
.stat-value {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}
.card-keywords {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin-bottom: 6px;
  align-items: center;
}
.kw-label {
  font-size: 12px;
  color: #909399;
}
.card-note {
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
  margin-top: 6px;
}
.card-actions {
  margin-top: 8px;
  text-align: right;
}
.pagination-wrap {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}
.emotion-detail { padding: 0; }
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
</style>
