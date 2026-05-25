<template>
  <div class="topics-page">
    <div class="page-header">
      <div class="header-title-area">
        <h2>选题库</h2>
        <p class="header-subtitle" v-if="items.length">AI驱动的选题推荐，精准匹配内容方向</p>
      </div>
      <div class="header-actions">
        <el-select v-model="categoryFilter" placeholder="分类筛选" clearable size="small" style="width: 140px">
          <el-option label="全部" value="" />
          <el-option v-for="cat in categories" :key="cat" :label="cat" :value="cat" />
        </el-select>
        <el-input v-model="searchText" placeholder="搜索选题..." size="small" clearable style="width: 260px" />
        <el-button size="small" @click="doExportCSV">导出CSV</el-button>
        <el-button size="small" @click="doExportJSON">导出JSON</el-button>
      </div>
    </div>

    <div class="topic-stats" v-if="items.length">
      <div class="topic-stat-item stat-total">
        <span class="stat-icon">📝</span>
        <span class="stat-num">{{ items.length }}</span>
        <span class="stat-text">总选题数</span>
      </div>
      <div class="topic-stat-item stat-high-ctr">
        <span class="stat-icon">🔥</span>
        <span class="stat-num">{{ highCtrCount }}</span>
        <span class="stat-text">高CTR选题</span>
      </div>
      <div class="topic-stat-item stat-avg-ctr">
        <span class="stat-icon">📊</span>
        <span class="stat-num">{{ avgCtr }}%</span>
        <span class="stat-text">平均CTR</span>
      </div>
      <div class="topic-stat-item stat-categories">
        <span class="stat-icon">🏷️</span>
        <span class="stat-num">{{ categories.length }}</span>
        <span class="stat-text">分类数</span>
      </div>
    </div>

    <div v-if="loading" class="loading-placeholder">
      <el-skeleton :rows="6" animated />
    </div>
    <div v-else-if="!items.length" class="intel-empty-state">
      <div class="intel-empty-state-icon">📝</div>
      <div class="intel-empty-state-text">暂无选题数据</div>
      <div class="intel-empty-state-action">数据更新后将自动展示</div>
    </div>
    <div v-else class="topic-grid intel-card-stagger">
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
const categoryFilter = ref("")
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

const categories = computed(() => {
  const cats = new Set<string>()
  items.value.forEach(i => {
    const td = i.topic_data as Record<string, any> | undefined
    const cat = td?.category || td?.decision_layer?.core_decision_type || ""
    if (cat) cats.add(cat)
  })
  return Array.from(cats).sort()
})

const highCtrCount = computed(() => {
  return items.value.filter(i => i.ctr_prediction && i.ctr_prediction >= 0.7).length
})

const avgCtr = computed(() => {
  const ctrItems = items.value.filter(i => i.ctr_prediction)
  if (!ctrItems.length) return 0
  const sum = ctrItems.reduce((acc, i) => acc + (i.ctr_prediction || 0), 0)
  return (sum / ctrItems.length * 100).toFixed(0)
})

const filteredItems = computed(() => {
  let result = items.value
  if (searchText.value) {
    const s = searchText.value.toLowerCase()
    result = result.filter((i) => i.title.toLowerCase().includes(s))
  }
  if (categoryFilter.value) {
    result = result.filter(i => {
      const td = i.topic_data as Record<string, any> | undefined
      const cat = td?.category || td?.decision_layer?.core_decision_type || ""
      return cat === categoryFilter.value
    })
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
  if (categoryFilter.value) {
    result = result.filter(i => {
      const td = i.topic_data as Record<string, any> | undefined
      const cat = td?.category || td?.decision_layer?.core_decision_type || ""
      return cat === categoryFilter.value
    })
  }
  return result.length
})

function ctrColor(val: number): string {
  if (val >= 0.7) return "var(--intel-success)"
  if (val >= 0.4) return "var(--intel-warning)"
  return "var(--intel-text-secondary)"
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

.topic-stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}
.topic-stat-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-md) var(--spacing-lg);
  border-radius: var(--intel-radius-lg);
  background: var(--intel-surface);
  box-shadow: var(--intel-shadow);
  transition: all var(--transition-base);
}
.topic-stat-item:hover {
  box-shadow: var(--intel-shadow-hover);
  transform: translateY(-2px);
}
.stat-icon { font-size: var(--font-size-xl); }
.stat-num { font-size: var(--font-size-2xl); font-weight: 800; }
.stat-text { font-size: var(--font-size-sm); color: var(--intel-text-secondary); }
.stat-total .stat-num { color: var(--intel-primary); }
.stat-high-ctr .stat-num { color: var(--intel-success); }
.stat-avg-ctr .stat-num { color: var(--intel-info); }
.stat-categories .stat-num { color: var(--intel-warning); }

.loading-placeholder { padding: var(--spacing-md); }

.topic-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: var(--spacing-md);
}
.topic-card {
  background: var(--intel-surface);
  border-radius: var(--intel-radius-lg);
  box-shadow: var(--intel-shadow);
  cursor: pointer;
  transition: all var(--transition-base);
  overflow: hidden;
  border-left: 4px solid var(--card-accent, var(--intel-accent));
  position: relative;
}
.topic-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--intel-shadow-hover);
}
.topic-card:hover .card-footer .card-action {
  transform: translateX(4px);
}
.card-accent-bar {
  height: 3px;
  width: 100%;
}
.card-body { padding: var(--spacing-md) var(--spacing-lg); }
.card-theme-badge {
  position: absolute;
  top: 12px;
  right: 14px;
  font-size: 20px;
}
.card-title {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--intel-text);
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
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
}
.ctr-label { font-size: var(--font-size-sm); color: var(--intel-text-secondary); }
.ctr-bar-track {
  flex: 1;
  height: 6px;
  background: var(--intel-border);
  border-radius: 3px;
  overflow: hidden;
}
.ctr-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.4s ease;
}
.ctr-val { font-size: var(--font-size-sm); font-weight: 600; color: var(--intel-text); min-width: 32px; }
.card-score {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
}
.score-label { font-size: var(--font-size-sm); color: var(--intel-text-secondary); }
.score-val { font-size: var(--font-size-2xl); font-weight: 800; }
.card-footer {
  display: flex;
  gap: var(--spacing-md);
  font-size: var(--font-size-sm);
  color: var(--intel-text-secondary);
  justify-content: space-between;
  align-items: center;
}
.card-action {
  color: var(--card-accent, var(--intel-accent));
  font-weight: 500;
  transition: transform var(--transition-fast);
}
.pagination-wrap {
  margin-top: var(--spacing-lg);
  display: flex;
  justify-content: center;
}

@media (max-width: 768px) {
  .topic-stats {
    grid-template-columns: repeat(2, 1fr);
  }
  .topic-grid {
    grid-template-columns: 1fr;
  }
}
</style>
