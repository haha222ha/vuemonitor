<template>
  <div class="signals-page">
    <div class="page-header">
      <h2>平台信号</h2>
      <div class="header-actions">
        <el-select v-model="platformFilter" placeholder="平台筛选" clearable size="small" style="width: 140px">
          <el-option label="全部平台" value="" />
          <el-option v-for="p in platforms" :key="p" :label="p" :value="p" />
        </el-select>
        <el-input v-model="searchText" placeholder="搜索信号..." size="small" clearable style="width: 220px" />
        <el-button size="small" @click="doExportCSV">导出CSV</el-button>
        <el-button size="small" @click="doExportJSON">导出JSON</el-button>
      </div>
    </div>

    <div v-if="loading" class="loading-placeholder">
      <el-skeleton :rows="6" animated />
    </div>
    <el-empty v-else-if="!items.length" description="暂无平台信号数据" />
    <div v-else>
      <div v-for="group in groupedItems" :key="group.platform" class="platform-group">
        <div class="group-header" :style="{ borderLeftColor: platformColor(group.platform) }">
          <div class="group-icon" :style="{ background: platformIconBg(group.platform), color: platformTextColor(group.platform) }">
            {{ platformEmoji(group.platform) }}
          </div>
          <span class="group-name">{{ group.platform }}</span>
          <el-tag size="small" type="info">{{ group.items.length }} 条信号</el-tag>
        </div>
        <div class="signal-list">
          <div
            v-for="item in group.items"
            :key="item.id || item.platform + item.title"
            class="signal-card"
            @click="openDetail(item)"
          >
            <div class="signal-body">
              <div class="signal-left">
                <div class="signal-strength" :class="'strength-' + (item.impact_level || 'low').toLowerCase()">
                  <span class="strength-dots">
                    <span v-for="n in 3" :key="n" class="dot" :class="{ active: n <= strengthLevel(item.impact_level) }"></span>
                  </span>
                </div>
              </div>
              <div class="signal-right">
                <div class="signal-title">{{ item.title || item.platform }}</div>
                <div class="signal-desc" v-if="item.description">{{ truncate(item.description, 80) }}</div>
                <div class="signal-meta">
                  <el-tag size="small" v-if="item.type" :type="signalTagType(item.type)" effect="plain">{{ item.type }}</el-tag>
                  <el-tag size="small" v-if="item.impact_level" :type="impactTagType(item.impact_level)" effect="dark">
                    影响: {{ item.impact_level }}
                  </el-tag>
                  <el-tag size="small" v-if="item.change_direction" :type="directionTagType(item.change_direction)" effect="plain">
                    {{ item.change_direction }}
                  </el-tag>
                  <span class="signal-time" v-if="item.detected_at">{{ item.detected_at?.slice(0, 10) }}</span>
                </div>
              </div>
              <el-button v-if="isAdmin()" type="danger" text size="small" @click.stop="handleDelete(item)" class="delete-btn">删除</el-button>
            </div>
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

    <el-dialog v-model="detailVisible" :title="detailItem?.title || detailItem?.platform" width="640px" destroy-on-close>
      <div v-if="detailItem" class="signal-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="平台">{{ detailItem.platform }}</el-descriptions-item>
          <el-descriptions-item label="变化方向" v-if="detailItem.change_direction">{{ detailItem.change_direction }}</el-descriptions-item>
          <el-descriptions-item label="影响程度" v-if="detailItem.magnitude">
            <el-tag :type="impactTagType(detailItem.magnitude)" size="small">{{ detailItem.magnitude }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="信号类型" v-if="detailItem.type">{{ detailItem.type }}</el-descriptions-item>
          <el-descriptions-item label="当前焦点" :span="2" v-if="detailItem.current_focus">{{ detailItem.current_focus }}</el-descriptions-item>
          <el-descriptions-item label="流量信号" :span="2" v-if="detailItem.traffic_signal">{{ detailItem.traffic_signal }}</el-descriptions-item>
          <el-descriptions-item label="政策风险" :span="2" v-if="detailItem.policy_risk">{{ detailItem.policy_risk }}</el-descriptions-item>
          <el-descriptions-item label="对副业影响" :span="2" v-if="detailItem.impact_on_side_hustle">{{ detailItem.impact_on_side_hustle }}</el-descriptions-item>
        </el-descriptions>
        <div class="detail-section" v-if="detailItem.signal_history?.length">
          <h4>信号历史</h4>
          <el-timeline>
            <el-timeline-item v-for="(h, idx) in detailItem.signal_history" :key="idx">
              {{ typeof h === 'string' ? h : JSON.stringify(h) }}
            </el-timeline-item>
          </el-timeline>
        </div>
      </div>
      <template #footer>
        <el-button v-if="isAdmin()" @click="handleDelete(detailItem)" type="danger" size="small">删除</el-button>
        <el-button @click="exportJSON([detailItem], detailItem?.platform || '信号')" size="small">导出</el-button>
        <el-button @click="detailVisible = false" size="small">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import api from "@/utils/api"
import { exportJSON, exportCSV, deleteItem, truncate, isAdmin, fetchWithCache, clearCache } from "@/utils/intel"

interface SignalItem {
  id?: string
  title?: string
  description?: string
  platform: string
  type?: string
  impact_level?: string
  detected_at?: string
  current_focus?: string
  traffic_signal?: string
  policy_risk?: string
  change_direction?: string
  magnitude?: string
  impact_on_side_hustle?: string
  signal_history?: unknown[]
  [key: string]: unknown
}

const items = ref<SignalItem[]>([])
const loading = ref(false)
const searchText = ref("")
const platformFilter = ref("")
const currentPage = ref(1)
const pageSize = 30
const detailItem = ref<SignalItem | null>(null)
const detailVisible = ref(false)

const platforms = computed(() => {
  const s = new Set(items.value.map((i) => i.platform).filter(Boolean))
  return Array.from(s).sort()
})

const filteredItems = computed(() => {
  let result = items.value
  if (platformFilter.value) result = result.filter((i) => i.platform === platformFilter.value)
  if (searchText.value) {
    const s = searchText.value.toLowerCase()
    result = result.filter((i) => (i.title || i.platform).toLowerCase().includes(s) || i.description?.toLowerCase().includes(s))
  }
  const start = (currentPage.value - 1) * pageSize
  return result.slice(start, start + pageSize)
})

const filteredTotal = computed(() => {
  let result = items.value
  if (platformFilter.value) result = result.filter((i) => i.platform === platformFilter.value)
  if (searchText.value) {
    const s = searchText.value.toLowerCase()
    result = result.filter((i) => (i.title || i.platform).toLowerCase().includes(s) || i.description?.toLowerCase().includes(s))
  }
  return result.length
})

const groupedItems = computed(() => {
  const groups: Record<string, SignalItem[]> = {}
  for (const item of filteredItems.value) {
    const p = item.platform || "未知"
    if (!groups[p]) groups[p] = []
    groups[p].push(item)
  }
  return Object.entries(groups).map(([platform, items]) => ({ platform, items }))
})

function platformColor(p: string): string {
  const map: Record<string, string> = {
    xiaohongshu: "#e3f2fd",
    douyin: "#fce4ec",
    weixin: "#e8f5e9",
    bilibili: "#fff3e0",
  }
  return map[p?.toLowerCase()] || "#f5f5f5"
}

function platformIconBg(p: string): string {
  const map: Record<string, string> = {
    xiaohongshu: "#ff2442",
    douyin: "#161823",
    weixin: "#07c160",
    bilibili: "#fb7299",
  }
  return map[p?.toLowerCase()] || "#909399"
}

function platformTextColor(p: string): string {
  return "#fff"
}

function platformEmoji(p: string): string {
  const map: Record<string, string> = {
    xiaohongshu: "📕",
    douyin: "🎵",
    weixin: "💬",
    bilibili: "📺",
  }
  return map[p?.toLowerCase()] || "📡"
}

function strengthLevel(level?: string): number {
  const map: Record<string, number> = { high: 3, medium: 2, low: 1 }
  return map[level?.toLowerCase() || ""] || 1
}

function signalTagType(type?: string): string {
  const map: Record<string, string> = {
    policy: "danger",
    market: "success",
    tech: "warning",
    social: "info",
    rising: "success",
    falling: "danger",
    stable: "info",
  }
  return map[type?.toLowerCase() || ""] || "info"
}

function impactTagType(level?: string): string {
  const map: Record<string, string> = { high: "danger", medium: "warning", low: "success" }
  return map[level?.toLowerCase() || ""] || "info"
}

function directionTagType(dir?: string): string {
  const map: Record<string, string> = { rising: "success", falling: "danger", stable: "info" }
  return map[dir?.toLowerCase() || ""] || "info"
}

function openDetail(item: SignalItem) {
  detailItem.value = item
  detailVisible.value = true
}

async function handleDelete(item: SignalItem | null) {
  if (!item?.id) return
  const ok = await deleteItem("signals", item.id, item.platform)
  if (ok) {
    items.value = items.value.filter((i) => i.id !== item.id)
    clearCache("signals")
    detailVisible.value = false
  }
}

function doExportCSV() { exportCSV(filteredItems.value as Record<string, unknown>[], "平台信号") }
function doExportJSON() { exportJSON(filteredItems.value, "平台信号") }

function handlePageChange() {
  scrollTo({ top: 0, behavior: "smooth" })
}

onMounted(async () => {
  loading.value = true
  try {
    items.value = await fetchWithCache<SignalItem>("signals", "/intel/signals")
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
  flex-wrap: wrap;
  gap: 10px;
}
.page-header h2 { margin: 0; font-size: 20px; }
.header-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.loading-placeholder { padding: 16px; }

.platform-group {
  margin-bottom: 24px;
}
.group-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  padding: 10px 14px;
  background: #f8f9fa;
  border-radius: 8px;
  border-left: 4px solid;
}
.group-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}
.group-name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  flex: 1;
}

.signal-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.signal-card {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 1px 6px rgba(0, 0, 0, 0.04);
  cursor: pointer;
  transition: all 0.2s ease;
  padding: 12px 16px;
}
.signal-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  transform: translateX(4px);
}
.signal-body {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}
.signal-left {
  padding-top: 4px;
}
.signal-strength {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.strength-dots {
  display: flex;
  gap: 3px;
}
.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #e4e7ed;
  transition: background 0.2s;
}
.dot.active { background: #d97706; }
.strength-high .dot.active { background: #dc2626; }
.strength-medium .dot.active { background: #d97706; }
.strength-low .dot.active { background: #059669; }
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
.delete-btn { flex-shrink: 0; }
.pagination-wrap {
  margin-top: 24px;
  display: flex;
  justify-content: center;
}
.signal-detail { padding: 0; }
.detail-section { margin-top: 20px; }
.detail-section h4 {
  font-size: 14px;
  color: #303133;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid #f0f0f0;
}
</style>
