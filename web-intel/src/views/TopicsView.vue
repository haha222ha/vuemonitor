<template>
  <div class="topics-page">
    <div class="page-header">
      <h2>选题库</h2>
      <el-input v-model="searchText" placeholder="搜索选题..." size="small" clearable style="width: 260px" />
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
            <el-tag v-if="item.tone" size="small" type="warning">{{ item.tone }}</el-tag>
          </div>
          <div class="card-desc" v-if="item.core_message">
            {{ truncate(item.core_message, 80) }}
          </div>
          <div class="card-footer">
            <span v-if="item.word_count">字数：{{ item.word_count }}</span>
            <span v-if="item.target_audience">受众：{{ item.target_audience }}</span>
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

    <el-dialog v-model="detailVisible" :title="detailItem?.title" width="700px">
      <div v-if="detailItem" class="topic-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="平台" v-if="detailItem.platform">{{ detailItem.platform }}</el-descriptions-item>
          <el-descriptions-item label="内容类型" v-if="detailItem.content_type">{{ detailItem.content_type }}</el-descriptions-item>
          <el-descriptions-item label="语气风格" v-if="detailItem.tone">{{ detailItem.tone }}</el-descriptions-item>
          <el-descriptions-item label="字数" v-if="detailItem.word_count">{{ detailItem.word_count }}</el-descriptions-item>
          <el-descriptions-item label="目标受众" :span="2" v-if="detailItem.target_audience">{{ detailItem.target_audience }}</el-descriptions-item>
          <el-descriptions-item label="核心信息" :span="2" v-if="detailItem.core_message">{{ detailItem.core_message }}</el-descriptions-item>
        </el-descriptions>
        <div class="detail-section" v-if="detailItem.structure?.length">
          <h4>内容结构</h4>
          <el-timeline>
            <el-timeline-item
              v-for="(step, idx) in detailItem.structure"
              :key="idx"
              :timestamp="`第${idx + 1}步`"
            >
              {{ step }}
            </el-timeline-item>
          </el-timeline>
        </div>
        <div class="detail-section" v-if="detailItem.keywords?.length">
          <h4>关键词</h4>
          <div class="keyword-list">
            <el-tag v-for="kw in detailItem.keywords" :key="kw" size="small" type="info">{{ kw }}</el-tag>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import api from "@/utils/api"

interface TopicItem {
  id?: string
  title: string
  platform?: string
  content_type?: string
  tone?: string
  word_count?: number
  target_audience?: string
  core_message?: string
  structure?: string[]
  keywords?: string[]
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
    result = result.filter(
      (i) => i.title.toLowerCase().includes(s) || i.core_message?.toLowerCase().includes(s)
    )
  }
  const start = (currentPage.value - 1) * pageSize
  return result.slice(start, start + pageSize)
})

const filteredTotal = computed(() => {
  let result = items.value
  if (searchText.value) {
    const s = searchText.value.toLowerCase()
    result = result.filter(
      (i) => i.title.toLowerCase().includes(s) || i.core_message?.toLowerCase().includes(s)
    )
  }
  return result.length
})

function truncate(text: string, max: number): string {
  if (!text) return ""
  return text.length > max ? text.slice(0, max) + "..." : text
}

function openDetail(item: TopicItem) {
  detailItem.value = item
  detailVisible.value = true
}

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
}
.page-header h2 { margin: 0; font-size: 20px; }
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
.card-desc {
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
  margin-bottom: 8px;
}
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
}
.keyword-list {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
</style>