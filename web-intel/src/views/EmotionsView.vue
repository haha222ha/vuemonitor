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
      <div
        v-for="item in filteredItems"
        :key="item.id || item.keyword"
        class="emotion-card"
        :class="'sentiment-' + (item.sentiment || '').toLowerCase()"
        @click="openDetail(item)"
      >
        <div class="sentiment-bar"></div>
        <div class="card-body">
          <div class="card-header-row">
            <span class="keyword">{{ item.keyword || item.keyword_cluster }}</span>
            <el-tag :type="sentimentTagType(item.sentiment)" size="small" effect="dark">
              {{ sentimentLabel(item.sentiment) }}
            </el-tag>
          </div>
          <div class="intensity-section" v-if="item.intensity !== undefined">
            <div class="intensity-header">
              <span class="intensity-label">情绪强度</span>
              <span class="intensity-val" :style="{ color: getIntensityColor(item.intensity) }">
                {{ (item.intensity * 100).toFixed(0) }}%
              </span>
            </div>
            <div class="intensity-track">
              <div
                class="intensity-fill"
                :style="{
                  width: (item.intensity * 100) + '%',
                  background: getIntensityColor(item.intensity)
                }"
              ></div>
            </div>
            <div class="intensity-levels">
              <span class="level-low">低</span>
              <span class="level-mid">中</span>
              <span class="level-high">高</span>
            </div>
          </div>
          <div class="card-stats" v-if="item.volume !== undefined">
            <span class="stat-label">讨论量</span>
            <span class="stat-value">{{ item.volume }}</span>
          </div>
          <div class="card-keywords" v-if="item.related_keywords?.length">
            <span class="kw-label">关联词：</span>
            <el-tag v-for="kw in item.related_keywords.slice(0, 6)" :key="kw" size="small" type="info" effect="plain">{{ kw }}</el-tag>
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

    <el-dialog v-model="detailVisible" :title="detailItem?.keyword || detailItem?.keyword_cluster || '情绪详情'" width="640px" destroy-on-close>
      <div v-if="detailItem" class="emotion-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="关键词">{{ detailItem.keyword || "-" }}</el-descriptions-item>
          <el-descriptions-item label="情绪倾向">
            <el-tag :type="sentimentTagType(detailItem.sentiment)" size="small">{{ sentimentLabel(detailItem.sentiment) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="情绪强度">
            <div class="detail-intensity">
              <div class="intensity-track">
                <div
                  class="intensity-fill"
                  :style="{
                    width: ((detailItem.intensity || 0) * 100) + '%',
                    background: getIntensityColor(detailItem.intensity || 0)
                  }"
                ></div>
              </div>
              <span :style="{ color: getIntensityColor(detailItem.intensity || 0), fontWeight: 700 }">
                {{ ((detailItem.intensity || 0) * 100).toFixed(0) }}%
              </span>
            </div>
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
import { exportJSON, exportCSV, deleteItem, isAdmin, fetchWithCache, clearCache } from "@/utils/intel"
import { getIntensityColor } from "@/utils/theme"

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

function openDetail(item: EmotionItem) {
  detailItem.value = item
  detailVisible.value = true
}

async function handleDelete(item: EmotionItem | null) {
  if (!item?.id) return
  const ok = await deleteItem("emotions", item.id, item.keyword || "该情绪数据")
  if (ok) {
    items.value = items.value.filter((i) => i.id !== item.id)
    clearCache("emotions")
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
    items.value = await fetchWithCache<EmotionItem>("emotions", "/intel/emotions")
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
.emotion-card {
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  cursor: pointer;
  transition: all 0.25s ease;
  overflow: hidden;
}
.emotion-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.12);
}
.sentiment-bar {
  height: 3px;
  width: 100%;
}
.emotion-card.sentiment-positive .sentiment-bar { background: #059669; }
.emotion-card.sentiment-neutral .sentiment-bar { background: #2563eb; }
.emotion-card.sentiment-negative .sentiment-bar { background: #dc2626; }
.emotion-card.sentiment-positive { border-left: 4px solid #059669; }
.emotion-card.sentiment-neutral { border-left: 4px solid #2563eb; }
.emotion-card.sentiment-negative { border-left: 4px solid #dc2626; }
.card-body { padding: 16px 18px; }
.card-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.keyword {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}
.intensity-section {
  margin-bottom: 12px;
}
.intensity-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.intensity-label {
  font-size: 12px;
  color: #909399;
}
.intensity-val {
  font-size: 14px;
  font-weight: 700;
}
.intensity-track {
  height: 8px;
  background: #e4e7ed;
  border-radius: 4px;
  overflow: hidden;
}
.intensity-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.6s ease;
}
.intensity-levels {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
  font-size: 10px;
  color: #c0c4cc;
}
.card-stats {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.stat-label {
  font-size: 12px;
  color: #909399;
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
.detail-intensity {
  display: flex;
  align-items: center;
  gap: 10px;
}
.detail-intensity .intensity-track {
  flex: 1;
  height: 10px;
}
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
  background: #ecfdf5;
  color: #303133;
  font-weight: 500;
  border-left: 3px solid #059669;
}
</style>
