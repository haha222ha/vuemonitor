<template>
  <div class="opportunities-page">
    <div class="page-header">
      <h2>商业机会</h2>
      <div class="header-filters">
        <el-select v-model="categoryFilter" placeholder="分类筛选" clearable size="small" style="width: 140px">
          <el-option label="全部" value="" />
          <el-option v-for="cat in categories" :key="cat" :label="cat" :value="cat" />
        </el-select>
        <el-input v-model="searchText" placeholder="搜索机会..." size="small" clearable style="width: 220px" />
      </div>
    </div>

    <div v-if="loading" class="loading-placeholder">
      <el-skeleton :rows="8" animated />
    </div>
    <el-empty v-else-if="!items.length" description="暂无商业机会数据" />
    <div v-else class="opp-grid">
      <el-card v-for="item in filteredItems" :key="item.id" shadow="hover" class="opp-card">
        <div class="card-body">
          <div class="card-title">{{ item.name }}</div>
          <div class="card-meta">
            <el-tag size="small">{{ item.category }}</el-tag>
            <el-tag size="small" :type="scoreType(item.verdict_score)">
              评分 {{ item.verdict_score }}
            </el-tag>
            <el-tag size="small" v-if="item.difficulty">难度 {{ item.difficulty }}</el-tag>
          </div>
          <div class="card-details" v-if="item.startup_cost || item.monthly_ceiling">
            <div class="detail-row" v-if="item.startup_cost">
              <span class="detail-label">启动成本</span>
              <span class="detail-value">{{ item.startup_cost }}</span>
            </div>
            <div class="detail-row" v-if="item.monthly_ceiling">
              <span class="detail-label">月收入上限</span>
              <span class="detail-value">{{ item.monthly_ceiling }}</span>
            </div>
          </div>
          <div class="card-paths" v-if="item.commercial_paths?.length">
            <el-tag v-for="(path, idx) in item.commercial_paths" :key="idx" size="small" type="success" effect="plain">
              {{ path }}
            </el-tag>
          </div>
          <div class="card-fit" v-if="item.persona_fit">
            <span class="fit-label">适合人群：</span>{{ item.persona_fit }}
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
import type { OpportunityItem } from "@/stores/intel"

const items = ref<OpportunityItem[]>([])
const loading = ref(false)
const searchText = ref("")
const categoryFilter = ref("")
const currentPage = ref(1)
const pageSize = 12

const categories = computed(() => {
  const cats = new Set(items.value.map((i) => i.category).filter(Boolean))
  return Array.from(cats).sort()
})

const filteredItems = computed(() => {
  let result = items.value
  if (searchText.value) {
    const s = searchText.value.toLowerCase()
    result = result.filter((i) => i.name.toLowerCase().includes(s) || i.category?.toLowerCase().includes(s))
  }
  if (categoryFilter.value) {
    result = result.filter((i) => i.category === categoryFilter.value)
  }
  const start = (currentPage.value - 1) * pageSize
  return result.slice(start, start + pageSize)
})

const filteredTotal = computed(() => {
  let result = items.value
  if (searchText.value) {
    const s = searchText.value.toLowerCase()
    result = result.filter((i) => i.name.toLowerCase().includes(s) || i.category?.toLowerCase().includes(s))
  }
  if (categoryFilter.value) {
    result = result.filter((i) => i.category === categoryFilter.value)
  }
  return result.length
})

function scoreType(score: number): string {
  if (score >= 80) return "success"
  if (score >= 60) return "warning"
  return "info"
}

function handlePageChange() {
  scrollTo({ top: 0, behavior: "smooth" })
}

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await api.get("/intel/opportunities")
    items.value = data?.items || data || []
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.opportunities-page { max-width: 1400px; }
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.page-header h2 { margin: 0; font-size: 20px; }
.header-filters { display: flex; gap: 10px; }
.loading-placeholder { padding: 16px; }
.opp-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}
.opp-card { cursor: pointer; transition: transform 0.2s; }
.opp-card:hover { transform: translateY(-2px); }
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
.card-details {
  background: #f5f7fa;
  border-radius: 6px;
  padding: 8px 12px;
  margin-bottom: 8px;
}
.detail-row {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  padding: 2px 0;
}
.detail-label { color: #909399; }
.detail-value { color: #303133; font-weight: 500; }
.card-paths {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin-bottom: 6px;
}
.card-fit {
  font-size: 12px;
  color: #909399;
}
.fit-label { color: #606266; }
.pagination-wrap {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}
</style>