<template>
  <div class="topics-page">
    <div class="page-header">
      <h2>选题库</h2>
      <div class="header-actions">
        <el-input v-model="searchText" placeholder="搜索选题..." size="small" clearable style="width: 260px" />
        <el-button size="small" @click="doExportCSV">导出CSV</el-button>
        <el-button size="small" @click="doExportJSON">导出JSON</el-button>
      </div>
    </div>

    <div v-if="loading" class="loading-placeholder">
      <el-skeleton :rows="6" animated />
    </div>
    <el-empty v-else-if="!items.length" description="暂无选题数据" />
    <div v-else class="topic-grid">
      <div
        v-for="item in filteredItems"
        :key="item.id || item.title"
        class="topic-card"
        :style="cardStyle(item)"
        @click="openReport(item)"
      >
        <div class="card-accent-bar" :style="{ background: getTheme(item).accent }"></div>
        <div class="card-body">
          <div class="card-theme-badge" v-if="getTheme(item).emoji">
            {{ getTheme(item).emoji }}
          </div>
          <div class="card-title">{{ item.title }}</div>
          <div class="card-meta">
            <el-tag v-if="item.platform" size="small" effect="plain">{{ item.platform }}</el-tag>
            <el-tag v-if="item.content_type" size="small" type="success" effect="plain">{{ item.content_type }}</el-tag>
            <el-tag v-if="item.hook_type" size="small" type="warning" effect="plain">{{ item.hook_type }}</el-tag>
            <el-tag v-if="item.emotion" size="small" type="info" effect="plain">{{ item.emotion }}</el-tag>
          </div>
          <div class="card-ctr" v-if="item.ctr_prediction">
            <span class="ctr-label">CTR预测</span>
            <div class="ctr-bar-track">
              <div class="ctr-bar-fill" :style="{ width: Math.round(item.ctr_prediction * 100) + '%', background: ctrColor(item.ctr_prediction) }"></div>
            </div>
            <span class="ctr-val">{{ (item.ctr_prediction * 100).toFixed(0) }}%</span>
          </div>
          <div class="card-score" v-if="getTopicScore(item)">
            <span class="score-label">机会评分</span>
            <span class="score-val" :style="{ color: getScoreColor(getTopicScore(item) || 0) }">{{ getTopicScore(item) }}</span>
          </div>
          <div class="card-footer">
            <span v-if="item.competition">竞争度：{{ item.competition }}</span>
            <span class="card-action">查看报告 →</span>
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import { useRouter } from "vue-router"
import api from "@/utils/api"
import { exportJSON, exportCSV, fetchWithCache } from "@/utils/intel"
import { getThemeByCategory, getScoreColor } from "@/utils/theme"

interface TopicItem {
  id?: string
  title: string
  platform?: string
  content_type?: string
  hook_type?: string
  emotion?: string
  ctr_prediction?: number
  competition?: string
  topic_data?: Record<string, unknown>
  [key: string]: unknown
}

const router = useRouter()
const items = ref<TopicItem[]>([])
const loading = ref(false)
const searchText = ref("")
const currentPage = ref(1)
const pageSize = 12

function getTheme(item: TopicItem) {
  const td = item.topic_data as Record<string, any> | undefined
  const cat = td?.category || td?.decision_layer?.core_decision_type || ""
  return getThemeByCategory(cat)
}

function getTopicScore(item: TopicItem): number | null {
  const td = item.topic_data as Record<string, any> | undefined
  return td?.opportunity_score || null
}

function cardStyle(item: TopicItem) {
  const theme = getTheme(item)
  return {
    "--card-accent": theme.accent,
    "--card-primary": theme.primary,
    borderLeftColor: theme.accent,
  }
}

const filteredItems = computed(() => {
  let result = items.value
  if (searchText.value) {
    const s = searchText.value.toLowerCase()
    result = result.filter((i) => i.title.toLowerCase().includes(s))
  }
  const start = (currentPage.value - 1) * pageSize
  return result.slice(start, start + pageSize)
})

const filteredTotal = computed(() => {
  let result = items.value
  if (searchText.value) {
    const s = searchText.value.toLowerCase()
    result = result.filter((i) => i.title.toLowerCase().includes(s))
  }
  return result.length
})

function ctrColor(val: number): string {
  if (val >= 0.7) return "#059669"
  if (val >= 0.4) return "#d97706"
  return "#909399"
}

function openReport(item: TopicItem) {
  if (item.id) {
    router.push(`/report/${item.id}`)
  }
}

function doExportCSV() { exportCSV(filteredItems.value as Record<string, unknown>[], "选题库") }
function doExportJSON() { exportJSON(filteredItems.value, "选题库") }

function handlePageChange() {
  scrollTo({ top: 0, behavior: "smooth" })
}

onMounted(async () => {
  loading.value = true
  try {
    items.value = await fetchWithCache<TopicItem>("topics", "/intel/topics")
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.topics-page { max-width: 1400px; }
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
.topic-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}
.topic-card {
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  cursor: pointer;
  transition: all 0.25s ease;
  overflow: hidden;
  border-left: 4px solid var(--card-accent, #4fc3f7);
  position: relative;
}
.topic-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.12);
}
.card-accent-bar {
  height: 3px;
  width: 100%;
}
.card-body { padding: 16px 18px; }
.card-theme-badge {
  position: absolute;
  top: 12px;
  right: 14px;
  font-size: 20px;
}
.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 10px;
  line-height: 1.5;
  padding-right: 30px;
}
.card-meta {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
.card-ctr {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.ctr-label { font-size: 12px; color: #909399; }
.ctr-bar-track {
  flex: 1;
  height: 6px;
  background: #e4e7ed;
  border-radius: 3px;
  overflow: hidden;
}
.ctr-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.4s ease;
}
.ctr-val { font-size: 12px; font-weight: 600; color: #303133; min-width: 32px; }
.card-score {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.score-label { font-size: 12px; color: #909399; }
.score-val { font-size: 20px; font-weight: 800; }
.card-footer {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #909399;
  justify-content: space-between;
  align-items: center;
}
.card-action {
  color: var(--card-accent, #4fc3f7);
  font-weight: 500;
  transition: transform 0.2s;
}
.topic-card:hover .card-action {
  transform: translateX(4px);
}
.pagination-wrap {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}
</style>
