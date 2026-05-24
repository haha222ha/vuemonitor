<template>
  <div class="emotions-page">
    <div class="page-header">
      <h2>用户情绪分析</h2>
      <el-select v-model="sentimentFilter" placeholder="情绪倾向" clearable size="small" style="width: 140px">
        <el-option label="全部" value="" />
        <el-option label="正面" value="positive" />
        <el-option label="中性" value="neutral" />
        <el-option label="负面" value="negative" />
      </el-select>
    </div>

    <div v-if="loading" class="loading-placeholder">
      <el-skeleton :rows="8" animated />
    </div>
    <el-empty v-else-if="!items.length" description="暂无用户情绪数据" />
    <div v-else class="emotion-grid">
      <el-card v-for="item in filteredItems" :key="item.id || item.keyword" shadow="hover" class="emotion-card">
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import api from "@/utils/api"

interface EmotionItem {
  id?: string
  keyword?: string
  keyword_cluster?: string
  sentiment?: string
  intensity?: number
  volume?: number
  related_keywords?: string[]
  insight?: string
  note?: string
  [key: string]: unknown
}

const items = ref<EmotionItem[]>([])
const loading = ref(false)
const sentimentFilter = ref("")
const currentPage = ref(1)
const pageSize = 12

const filteredItems = computed(() => {
  let result = items.value
  if (sentimentFilter.value) {
    result = result.filter((i) => i.sentiment?.toLowerCase() === sentimentFilter.value)
  }
  const start = (currentPage.value - 1) * pageSize
  return result.slice(start, start + pageSize)
})

const filteredTotal = computed(() => {
  let result = items.value
  if (sentimentFilter.value) {
    result = result.filter((i) => i.sentiment?.toLowerCase() === sentimentFilter.value)
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
}
.page-header h2 { margin: 0; font-size: 20px; }
.loading-placeholder { padding: 16px; }
.emotion-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}
.emotion-card { transition: transform 0.2s; }
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
.pagination-wrap {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}
</style>