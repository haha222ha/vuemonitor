<template>
  <div class="signals-page">
    <div class="page-header">
      <h2>平台信号</h2>
      <div class="header-filters">
        <el-select v-model="platformFilter" placeholder="平台筛选" clearable size="small" style="width: 140px">
          <el-option label="全部平台" value="" />
          <el-option v-for="p in platforms" :key="p" :label="p" :value="p" />
        </el-select>
        <el-select v-model="typeFilter" placeholder="信号类型" clearable size="small" style="width: 140px">
          <el-option label="全部类型" value="" />
          <el-option v-for="t in signalTypes" :key="t" :label="t" :value="t" />
        </el-select>
      </div>
    </div>

    <div v-if="loading" class="loading-placeholder">
      <el-skeleton :rows="6" animated />
    </div>
    <el-empty v-else-if="!items.length" description="暂无平台信号数据" />
    <div v-else class="signal-list">
      <el-card v-for="item in filteredItems" :key="item.id || item.title" shadow="hover" class="signal-card">
        <div class="signal-body">
          <div class="signal-left">
            <div class="signal-icon" :style="{ background: iconColor(item.type) }">
              <el-icon :size="16"><Connection /></el-icon>
            </div>
          </div>
          <div class="signal-right">
            <div class="signal-title">{{ item.title }}</div>
            <div class="signal-desc" v-if="item.description">{{ item.description }}</div>
            <div class="signal-meta">
              <el-tag size="small" v-if="item.platform">{{ item.platform }}</el-tag>
              <el-tag size="small" v-if="item.type" :type="signalTagType(item.type)">{{ item.type }}</el-tag>
              <el-tag size="small" v-if="item.impact_level" :type="impactTagType(item.impact_level)">影响: {{ item.impact_level }}</el-tag>
              <span class="signal-time" v-if="item.detected_at">{{ item.detected_at }}</span>
            </div>
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
import { Connection } from "@element-plus/icons-vue"

interface SignalItem {
  id?: string
  title: string
  description?: string
  platform?: string
  type?: string
  impact_level?: string
  detected_at?: string
  [key: string]: unknown
}

const items = ref<SignalItem[]>([])
const loading = ref(false)
const platformFilter = ref("")
const typeFilter = ref("")
const currentPage = ref(1)
const pageSize = 15

const platforms = computed(() => {
  const s = new Set(items.value.map((i) => i.platform).filter(Boolean))
  return Array.from(s).sort()
})

const signalTypes = computed(() => {
  const s = new Set(items.value.map((i) => i.type).filter(Boolean))
  return Array.from(s).sort()
})

const filteredItems = computed(() => {
  let result = items.value
  if (platformFilter.value) result = result.filter((i) => i.platform === platformFilter.value)
  if (typeFilter.value) result = result.filter((i) => i.type === typeFilter.value)
  const start = (currentPage.value - 1) * pageSize
  return result.slice(start, start + pageSize)
})

const filteredTotal = computed(() => {
  let result = items.value
  if (platformFilter.value) result = result.filter((i) => i.platform === platformFilter.value)
  if (typeFilter.value) result = result.filter((i) => i.type === typeFilter.value)
  return result.length
})

function iconColor(type?: string): string {
  const map: Record<string, string> = {
    policy: "#e3f2fd",
    market: "#e8f5e9",
    tech: "#fff3e0",
    social: "#fce4ec",
  }
  return map[type?.toLowerCase() || ""] || "#f5f5f5"
}

function signalTagType(type?: string): string {
  const map: Record<string, string> = {
    policy: "danger",
    market: "success",
    tech: "warning",
    social: "info",
  }
  return map[type?.toLowerCase() || ""] || "info"
}

function impactTagType(level?: string): string {
  const map: Record<string, string> = { high: "danger", medium: "warning", low: "success" }
  return map[level?.toLowerCase() || ""] || "info"
}

function handlePageChange() {
  scrollTo({ top: 0, behavior: "smooth" })
}

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await api.get("/intel/signals")
    items.value = data?.items || data || []
  } catch {
    items.value = []
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.signals-page { max-width: 1400px; }
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.page-header h2 { margin: 0; font-size: 20px; }
.header-filters { display: flex; gap: 10px; }
.loading-placeholder { padding: 16px; }
.signal-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.signal-card { cursor: pointer; transition: transform 0.2s; }
.signal-card:hover { transform: translateY(-1px); }
.signal-body {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
.signal-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #606266;
}
.signal-right { flex: 1; }
.signal-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}
.signal-desc {
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
  margin-bottom: 6px;
}
.signal-meta {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
}
.signal-time {
  font-size: 12px;
  color: #c0c4cc;
  margin-left: auto;
}
.pagination-wrap {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}
</style>