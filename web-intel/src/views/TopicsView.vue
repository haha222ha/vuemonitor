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
      <el-card v-for="item in filteredItems" :key="item.id || item.title" shadow="hover" class="topic-card" @click="openDetail(item)">
        <div class="card-body">
          <div class="card-title">{{ item.title }}</div>
          <div class="card-meta">
            <el-tag v-if="item.platform" size="small">{{ item.platform }}</el-tag>
            <el-tag v-if="item.content_type" size="small" type="success">{{ item.content_type }}</el-tag>
            <el-tag v-if="item.hook_type" size="small" type="warning">{{ item.hook_type }}</el-tag>
            <el-tag v-if="item.emotion" size="small" type="info">{{ item.emotion }}</el-tag>
          </div>
          <div class="card-ctr" v-if="item.ctr_prediction">
            <span class="ctr-label">CTR预测</span>
            <el-progress :percentage="Math.round(item.ctr_prediction * 100)" :stroke-width="8" :color="ctrColor(item.ctr_prediction)" style="flex:1" />
          </div>
          <div class="card-footer">
            <span v-if="item.competition">竞争度：{{ item.competition }}</span>
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

    <el-dialog v-model="detailVisible" :title="detailItem?.title" width="700px" destroy-on-close>
      <div v-if="detailItem" class="topic-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="平台" v-if="detailItem.platform">{{ detailItem.platform }}</el-descriptions-item>
          <el-descriptions-item label="内容类型" v-if="detailItem.content_type">{{ detailItem.content_type }}</el-descriptions-item>
          <el-descriptions-item label="钩子类型" v-if="detailItem.hook_type">{{ detailItem.hook_type }}</el-descriptions-item>
          <el-descriptions-item label="情绪" v-if="detailItem.emotion">{{ detailItem.emotion }}</el-descriptions-item>
          <el-descriptions-item label="CTR预测" v-if="detailItem.ctr_prediction">{{ (detailItem.ctr_prediction * 100).toFixed(1) }}%</el-descriptions-item>
          <el-descriptions-item label="竞争度" v-if="detailItem.competition">{{ detailItem.competition }}</el-descriptions-item>
        </el-descriptions>

        <div class="detail-section" v-if="detailItem.topic_data && Object.keys(detailItem.topic_data).length">
          <h4>选题详情</h4>
          <div class="json-block">
            <div v-for="(val, key) in detailItem.topic_data" :key="key" class="json-row">
              <span class="json-key">{{ key }}</span>
              <span class="json-val">{{ formatValue(val) }}</span>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="handleDelete(detailItem)" type="danger" size="small">删除</el-button>
        <el-button @click="exportJSON([detailItem], detailItem?.title || '选题')" size="small">导出</el-button>
        <el-button @click="detailVisible = false" size="small">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import api from "@/utils/api"
import { exportJSON, exportCSV, deleteItem, formatValue } from "@/utils/intel"

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

const items = ref<TopicItem[]>([])
const loading = ref(false)
const searchText = ref("")
const currentPage = ref(1)
const pageSize = 12
const detailItem = ref<TopicItem | null>(null)
const detailVisible = ref(false)

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
  if (val >= 0.7) return "#67c23a"
  if (val >= 0.4) return "#e6a23c"
  return "#909399"
}

function openDetail(item: TopicItem) {
  detailItem.value = item
  detailVisible.value = true
}

async function handleDelete(item: TopicItem | null) {
  if (!item?.id) return
  const ok = await deleteItem("topics", item.id, item.title)
  if (ok) {
    items.value = items.value.filter((i) => i.id !== item.id)
    detailVisible.value = false
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
    const { data } = await api.get("/intel/topics")
    items.value = data?.items || data || []
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
.topic-card { cursor: pointer; transition: transform 0.2s; }
.topic-card:hover { transform: translateY(-2px); }
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
.card-ctr {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.ctr-label { font-size: 12px; color: #909399; }
.card-footer {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #909399;
}
.pagination-wrap {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}
.topic-detail { padding: 0; }
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
</style>
