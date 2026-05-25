<template>
  <div class="emotions-page">
    <div class="page-header">
      <div class="header-title-area">
        <h2>用户情绪分析</h2>
        <p class="header-subtitle" v-if="items.length">洞察用户情绪变化，把握内容方向</p>
      </div>
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

    <div class="emotion-stats" v-if="items.length">
      <div class="emotion-stat-item stat-total">
        <span class="stat-icon">💭</span>
        <span class="stat-num">{{ items.length }}</span>
        <span class="stat-text">情绪关键词</span>
      </div>
      <div class="emotion-stat-item stat-positive">
        <span class="stat-icon">😊</span>
        <span class="stat-num">{{ sentimentCount('positive') }}</span>
        <span class="stat-text">正面情绪</span>
      </div>
      <div class="emotion-stat-item stat-negative">
        <span class="stat-icon">😟</span>
        <span class="stat-num">{{ sentimentCount('negative') }}</span>
        <span class="stat-text">负面情绪</span>
      </div>
      <div class="emotion-stat-item stat-avg">
        <span class="stat-icon">📊</span>
        <span class="stat-num">{{ avgIntensity }}%</span>
        <span class="stat-text">平均强度</span>
      </div>
    </div>

    <div v-if="loading" class="loading-placeholder">
      <el-skeleton :rows="8" animated />
    </div>
    <div v-else-if="!items.length" class="intel-empty-state">
      <div class="intel-empty-state-icon">💭</div>
      <div class="intel-empty-state-text">暂无用户情绪数据</div>
      <div class="intel-empty-state-action">数据更新后将自动展示</div>
    </div>
    <div v-else class="emotion-grid intel-card-stagger">
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
          <div class="card-footer">
            <el-tag v-if="item.trend_direction" size="small" :type="item.trend_direction === 'rising' ? 'success' : item.trend_direction === 'falling' ? 'danger' : 'info'" effect="plain">
              {{ item.trend_direction === 'rising' ? '↑ 上升' : item.trend_direction === 'falling' ? '↓ 下降' : '→ 稳定' }}
            </el-tag>
            <span class="card-action">查看详情 →</span>
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
        <div class="detail-sentiment-bar" :class="'sentiment-' + (detailItem.sentiment || '').toLowerCase()">
          <span class="sentiment-emoji">{{ sentimentEmoji(detailItem.sentiment) }}</span>
          <span class="sentiment-text">{{ sentimentLabel(detailItem.sentiment) }}情绪</span>
          <el-tag v-if="detailItem.trend_direction" :type="detailItem.trend_direction === 'rising' ? 'success' : detailItem.trend_direction === 'falling' ? 'danger' : 'info'" effect="dark" size="large">
            {{ detailItem.trend_direction === 'rising' ? '上升趋势' : detailItem.trend_direction === 'falling' ? '下降趋势' : '稳定' }}
          </el-tag>
        </div>
        <el-descriptions :column="2" border style="margin-top: var(--spacing-md);">
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
          <el-descriptions-item label="情绪类型" v-if="detailItem.emotion_type">{{ detailItem.emotion_type }}</el-descriptions-item>
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

function sentimentCount(s: string): number {
  return items.value.filter(i => i.sentiment?.toLowerCase() === s).length
}

const avgIntensity = computed(() => {
  const withIntensity = items.value.filter(i => i.intensity !== undefined)
  if (!withIntensity.length) return 0
  const sum = withIntensity.reduce((acc, i) => acc + (i.intensity || 0), 0)
  return (sum / withIntensity.length * 100).toFixed(0)
})

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

function sentimentEmoji(s?: string): string {
  const map: Record<string, string> = { positive: "😊", neutral: "😐", negative: "😟" }
  return map[s?.toLowerCase() || ""] || "💭"
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

.emotion-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}
.emotion-stat-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md) var(--spacing-lg);
  border-radius: var(--intel-radius-lg);
  background: var(--intel-surface);
  box-shadow: var(--intel-shadow);
  transition: all var(--transition-base);
}
.emotion-stat-item:hover {
  box-shadow: var(--intel-shadow-hover);
  transform: translateY(-2px);
}
.stat-icon { font-size: var(--font-size-xl); }
.stat-num { font-size: var(--font-size-2xl); font-weight: 800; }
.stat-text { font-size: var(--font-size-sm); color: var(--intel-text-secondary); }
.stat-total .stat-num { color: var(--intel-primary); }
.stat-positive .stat-num { color: var(--intel-success); }
.stat-negative .stat-num { color: var(--intel-danger); }
.stat-avg .stat-num { color: var(--intel-info); }

.loading-placeholder { padding: var(--spacing-md); }

.emotion-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: var(--spacing-md);
}
.emotion-card {
  background: var(--intel-surface);
  border-radius: var(--intel-radius-lg);
  box-shadow: var(--intel-shadow);
  cursor: pointer;
  transition: all var(--transition-base);
  overflow: hidden;
}
.emotion-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--intel-shadow-hover);
}
.emotion-card:hover .card-footer .card-action {
  transform: translateX(4px);
}
.sentiment-bar { height: 3px; width: 100%; }
.emotion-card.sentiment-positive .sentiment-bar { background: var(--intel-success); }
.emotion-card.sentiment-neutral .sentiment-bar { background: var(--intel-info); }
.emotion-card.sentiment-negative .sentiment-bar { background: var(--intel-danger); }
.emotion-card.sentiment-positive { border-left: 4px solid var(--intel-success); }
.emotion-card.sentiment-neutral { border-left: 4px solid var(--intel-info); }
.emotion-card.sentiment-negative { border-left: 4px solid var(--intel-danger); }
.card-body { padding: var(--spacing-md) var(--spacing-lg); }
.card-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-md);
}
.keyword {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--intel-text);
}
.intensity-section { margin-bottom: var(--spacing-md); }
.intensity-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.intensity-label { font-size: var(--font-size-xs); color: var(--intel-text-secondary); }
.intensity-val { font-size: var(--font-size-sm); font-weight: 700; }
.intensity-track {
  height: 8px;
  background: var(--intel-border);
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
  color: var(--intel-text-secondary);
}
.card-stats {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
}
.stat-label { font-size: var(--font-size-xs); color: var(--intel-text-secondary); }
.stat-value { font-size: var(--font-size-lg); font-weight: 600; color: var(--intel-text); }
.card-keywords {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin-bottom: 6px;
  align-items: center;
}
.kw-label { font-size: var(--font-size-xs); color: var(--intel-text-secondary); }
.card-note {
  font-size: var(--font-size-sm);
  color: var(--intel-text-secondary);
  line-height: 1.5;
  margin-top: 6px;
}
.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: var(--spacing-sm);
}
.card-action {
  font-size: var(--font-size-sm);
  color: var(--intel-accent);
  font-weight: 500;
  transition: transform var(--transition-fast);
}
.card-actions {
  margin-top: var(--spacing-sm);
  text-align: right;
}
.pagination-wrap {
  margin-top: var(--spacing-xl);
  display: flex;
  justify-content: center;
}

.emotion-detail { padding: 0; }
.detail-sentiment-bar {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md) var(--spacing-lg);
  border-radius: var(--intel-radius-lg);
}
.detail-sentiment-bar.sentiment-positive { background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%); }
.detail-sentiment-bar.sentiment-neutral { background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); }
.detail-sentiment-bar.sentiment-negative { background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%); }
.sentiment-emoji { font-size: 24px; }
.sentiment-text { font-size: var(--font-size-md); font-weight: 600; color: var(--intel-text); flex: 1; }
.detail-intensity {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}
.detail-intensity .intensity-track {
  flex: 1;
  height: 10px;
}
.detail-section { margin-top: var(--spacing-lg); }
.detail-section h4 {
  font-size: var(--font-size-md);
  color: var(--intel-text);
  margin-bottom: var(--spacing-sm);
  padding-bottom: 6px;
  border-bottom: 2px solid var(--intel-border-light);
  font-weight: 600;
}
.tag-list {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.text-block {
  font-size: var(--font-size-sm);
  color: var(--intel-text-secondary);
  line-height: 1.8;
  background: var(--intel-bg);
  padding: var(--spacing-md);
  border-radius: var(--intel-radius);
}
.text-block.highlight {
  background: #ecfdf5;
  color: var(--intel-text);
  font-weight: 500;
  border-left: 3px solid var(--intel-success);
}

@media (max-width: 768px) {
  .emotion-stats { grid-template-columns: repeat(2, 1fr); }
  .emotion-grid { grid-template-columns: 1fr; }
}
</style>
