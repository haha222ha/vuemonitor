<template>
  <div class="trends-page">
    <div class="page-header">
      <h2>趋势分析</h2>
      <div class="header-filters">
        <el-select v-model="platformFilter" placeholder="平台筛选" clearable size="small" style="width: 140px">
          <el-option label="全部平台" value="" />
          <el-option label="小红书" value="xiaohongshu" />
          <el-option label="抖音" value="douyin" />
        </el-select>
        <el-input v-model="searchText" placeholder="搜索趋势..." size="small" clearable style="width: 220px" />
      </div>
    </div>

    <div v-if="loading" class="loading-placeholder">
      <el-skeleton :rows="8" animated />
    </div>
    <el-empty v-else-if="!items.length" description="暂无趋势数据" />
    <div v-else class="trend-grid">
      <el-card v-for="item in filteredItems" :key="item.id" shadow="hover" class="trend-card">
        <div class="card-body">
          <div class="card-title">{{ item.title }}</div>
          <div class="card-meta">
            <el-tag size="small">{{ item.category }}</el-tag>
            <el-tag size="small" :type="scoreType(item.opportunity_score)">
              {{ item.opportunity_score }}分
            </el-tag>
            <el-tag size="small" v-if="item.platform">{{ item.platform }}</el-tag>
            <el-tag size="small" v-if="item.lifecycle" type="success">{{ item.lifecycle }}</el-tag>
          </div>
          <div class="card-extra" v-if="item.direction || item.user_emotion">
            <span v-if="item.direction">趋势方向：{{ item.direction }}</span>
            <span v-if="item.user_emotion">用户情绪：{{ item.user_emotion }}</span>
          </div>
          <div class="card-risk" v-if="item.risk_level">
            <el-tag :type="riskType(item.risk_level)" size="small">
              风险：{{ item.risk_level }}
            </el-tag>
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
import type { TrendItem } from "@/stores/intel"

const items = ref<TrendItem[]>([])
const loading = ref(false)
const searchText = ref("")
const platformFilter = ref("")
const currentPage = ref(1)
const pageSize = 12

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
}
.page-header h2 { margin: 0; font-size: 20px; }
.header-filters { display: flex; gap: 10px; }
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
.pagination-wrap {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}
</style>