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

    <el-dialog v-model="detailVisible" :title="detailItem?.title" width="760px" destroy-on-close>
      <div v-if="detailItem" class="topic-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="平台" v-if="detailItem.platform">{{ detailItem.platform }}</el-descriptions-item>
          <el-descriptions-item label="内容类型" v-if="detailItem.content_type">{{ detailItem.content_type }}</el-descriptions-item>
          <el-descriptions-item label="钩子类型" v-if="detailItem.hook_type">{{ detailItem.hook_type }}</el-descriptions-item>
          <el-descriptions-item label="情绪" v-if="detailItem.emotion">{{ detailItem.emotion }}</el-descriptions-item>
          <el-descriptions-item label="CTR预测" v-if="detailItem.ctr_prediction">{{ (detailItem.ctr_prediction * 100).toFixed(1) }}%</el-descriptions-item>
          <el-descriptions-item label="竞争度" v-if="detailItem.competition">{{ detailItem.competition }}</el-descriptions-item>
        </el-descriptions>

        <template v-if="detailItem.topic_data">
          <div class="detail-section" v-if="topicData.topic_description">
            <h4>选题描述</h4>
            <div class="text-block">{{ topicData.topic_description }}</div>
          </div>

          <div class="detail-section" v-if="topicData.keywords?.length">
            <h4>关键词</h4>
            <div class="tag-list">
              <el-tag v-for="kw in topicData.keywords" :key="kw" size="small">{{ kw }}</el-tag>
            </div>
          </div>

          <div class="detail-section" v-if="topicData.target_audience">
            <h4>目标受众</h4>
            <div class="text-block">{{ topicData.target_audience }}</div>
          </div>

          <div class="detail-section" v-if="topicData.opportunity_score">
            <h4>机会评分</h4>
            <div class="score-display">
              <span class="score-number" :style="{ color: topicData.opportunity_score >= 80 ? '#67c23a' : topicData.opportunity_score >= 60 ? '#e6a23c' : '#909399' }">{{ topicData.opportunity_score }}</span>
              <el-progress
                :percentage="topicData.opportunity_score"
                :stroke-width="14"
                :color="topicData.opportunity_score >= 80 ? '#67c23a' : topicData.opportunity_score >= 60 ? '#e6a23c' : '#909399'"
                style="flex: 1"
              />
            </div>
          </div>

          <div class="detail-section" v-if="topicData.score_breakdown && Object.keys(topicData.score_breakdown).length">
            <h4>评分细项</h4>
            <div class="score-bars">
              <div v-for="(val, key) in topicData.score_breakdown" :key="key" class="score-bar-item">
                <div class="score-bar-label">
                  <span class="score-key">{{ scoreLabel(String(key)) }}</span>
                  <span class="score-val">{{ val }}/10</span>
                </div>
                <el-progress
                  :percentage="Number(val) * 10"
                  :stroke-width="10"
                  :color="Number(val) >= 8 ? '#67c23a' : Number(val) >= 5 ? '#e6a23c' : '#f56c6c'"
                  :show-text="false"
                />
              </div>
            </div>
          </div>

          <div class="detail-section" v-if="topicData.lifecycle_stage">
            <h4>生命周期</h4>
            <div class="lifecycle-row">
              <el-tag type="success" size="large">{{ topicData.lifecycle_stage }}</el-tag>
              <div class="lifecycle-pred" v-if="topicData.lifecycle_prediction">
                <div v-for="(pred, key) in topicData.lifecycle_prediction" :key="key" class="pred-item">
                  <span class="pred-key">{{ key }}</span>
                  <span class="pred-val">{{ pred }}</span>
                </div>
              </div>
            </div>
          </div>

          <div class="detail-section" v-if="topicData.decision_layer">
            <h4>决策分析</h4>
            <div class="decision-info">
              <div class="decision-meta" v-if="topicData.decision_layer.core_decision_type">
                <el-tag type="warning">{{ topicData.decision_layer.core_decision_type }}</el-tag>
                <span v-if="topicData.decision_layer.sub_scenario" class="decision-sub">{{ topicData.decision_layer.sub_scenario }}</span>
              </div>
              <div class="persona-maps" v-if="topicData.decision_layer.persona_decision_map?.length">
                <div v-for="(pm, idx) in topicData.decision_layer.persona_decision_map" :key="idx" class="persona-card">
                  <div class="persona-header">
                    <el-tag size="small" type="info">{{ pm.persona }}</el-tag>
                  </div>
                  <div class="persona-body">
                    <div class="persona-row" v-if="pm.current_state"><span class="plabel">现状</span>{{ pm.current_state }}</div>
                    <div class="persona-row" v-if="pm.decision_pressure"><span class="plabel">决策压力</span>{{ pm.decision_pressure }}</div>
                    <div class="persona-row highlight" v-if="pm.recommended_direction"><span class="plabel">推荐方向</span>{{ pm.recommended_direction }}</div>
                    <div class="persona-row" v-if="pm.why_now"><span class="plabel">为什么现在</span>{{ pm.why_now }}</div>
                    <div class="persona-row warn" v-if="pm.avoid_mistake"><span class="plabel">避坑</span>{{ pm.avoid_mistake }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="detail-section" v-if="topicData.user_psychology">
            <h4>用户心理</h4>
            <div class="psychology-grid">
              <div class="psy-item" v-if="topicData.user_psychology.anxiety">
                <span class="psy-label">焦虑</span>
                <span class="psy-val">{{ topicData.user_psychology.anxiety }}</span>
              </div>
              <div class="psy-item" v-if="topicData.user_psychology.desire">
                <span class="psy-label">渴望</span>
                <span class="psy-val">{{ topicData.user_psychology.desire }}</span>
              </div>
              <div class="psy-item" v-if="topicData.user_psychology.fear">
                <span class="psy-label">恐惧</span>
                <span class="psy-val">{{ topicData.user_psychology.fear }}</span>
              </div>
              <div class="psy-item" v-if="topicData.user_psychology.paying_driver">
                <span class="psy-label">付费驱动</span>
                <span class="psy-val">{{ topicData.user_psychology.paying_driver }}</span>
              </div>
            </div>
          </div>

          <div class="detail-section" v-if="topicData.commercial_paths?.length">
            <h4>商业化路径</h4>
            <div class="paths-list">
              <div v-for="(cp, idx) in topicData.commercial_paths" :key="idx" class="path-item">
                <el-tag type="success" size="small">{{ idx + 1 }}</el-tag>
                <div class="path-detail" v-if="typeof cp === 'object'">
                  <div class="path-main">
                    <span class="path-type" v-if="(cp as Record<string, unknown>).type">{{ (cp as Record<string, unknown>).type }}</span>
                    <span class="path-desc" v-if="(cp as Record<string, unknown>).description">{{ (cp as Record<string, unknown>).description }}</span>
                  </div>
                  <span class="path-price" v-if="(cp as Record<string, unknown>).price_range">💰 {{ (cp as Record<string, unknown>).price_range }}</span>
                </div>
                <span v-else>{{ cp }}</span>
              </div>
            </div>
          </div>

          <div class="detail-section" v-if="topicData.content_angles?.length">
            <h4>内容角度</h4>
            <div class="angles-list">
              <div v-for="(angle, idx) in topicData.content_angles" :key="idx" class="angle-item">
                <span class="angle-num">{{ idx + 1 }}</span>
                <span class="angle-text">{{ angle }}</span>
              </div>
            </div>
          </div>

          <div class="detail-section" v-if="topicData.risk_warnings?.length">
            <h4>风险提示</h4>
            <div class="risk-list">
              <el-alert v-for="(rw, idx) in topicData.risk_warnings" :key="idx" :title="rw" type="warning" :closable="false" show-icon />
            </div>
          </div>

          <div class="detail-section" v-if="topicData.risk_matrix">
            <h4>风险矩阵</h4>
            <div class="risk-matrix-grid">
              <div v-for="(val, key) in topicData.risk_matrix" :key="key" class="rm-item">
                <span class="rm-label">{{ riskLabel(String(key)) }}</span>
                <el-rate :model-value="Number(val)" :max="10" disabled size="small" />
              </div>
            </div>
          </div>

          <div class="detail-section" v-if="topicData.tags?.length">
            <h4>标签</h4>
            <div class="tag-list">
              <el-tag v-for="tag in topicData.tags" :key="tag" size="small" type="info" effect="plain">{{ tag }}</el-tag>
            </div>
          </div>
        </template>
      </div>
      <template #footer>
        <el-button v-if="isAdmin()" @click="handleDelete(detailItem)" type="danger" size="small">删除</el-button>
        <el-button @click="exportJSON([detailItem], detailItem?.title || '选题')" size="small">导出</el-button>
        <el-button @click="detailVisible = false" size="small">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue"
import api from "@/utils/api"
import { exportJSON, exportCSV, deleteItem, formatValue, isAdmin } from "@/utils/intel"

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

const topicData = computed(() => {
  if (!detailItem.value?.topic_data) return {} as any
  return detailItem.value.topic_data as any
})

const SCORE_LABELS: Record<string, string> = {
  traffic_growth: "流量增长",
  willingness_to_pay: "付费意愿",
  competition_level: "竞争水平",
  platform_support: "平台支持",
  ai_scalability: "AI可扩展性",
  virtual_product_fit: "虚拟产品适配",
  anxiety_intensity: "焦虑强度",
  lifecycle: "生命周期",
  low_cost_entry: "低成本进入",
  ordinary_person_fit: "普通人适配",
}

function scoreLabel(key: string): string {
  return SCORE_LABELS[key] || key
}

const RISK_LABELS: Record<string, string> = {
  time_cost: "时间成本",
  money_cost: "资金成本",
  execution_difficulty: "执行难度",
  platform_risk: "平台风险",
}

function riskLabel(key: string): string {
  return RISK_LABELS[key] || key
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
.text-block {
  font-size: 13px;
  color: #606266;
  line-height: 1.8;
  background: #f8f9fa;
  padding: 12px;
  border-radius: 6px;
}
.score-display {
  display: flex;
  align-items: center;
  gap: 16px;
}
.score-number {
  font-size: 32px;
  font-weight: 700;
}
.score-bars {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.score-bar-item {
  background: #f8f9fa;
  border-radius: 6px;
  padding: 8px 12px;
}
.score-bar-label {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
}
.score-key {
  font-size: 13px;
  color: #606266;
}
.score-val {
  font-size: 13px;
  font-weight: 700;
  color: #303133;
}
.lifecycle-row {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
}
.lifecycle-pred {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.pred-item {
  display: flex;
  gap: 8px;
  font-size: 13px;
}
.pred-key {
  color: #909399;
  min-width: 60px;
  font-weight: 500;
}
.pred-val { color: #303133; }
.decision-info { }
.decision-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.decision-sub {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
}
.persona-maps {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.persona-card {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 12px;
}
.persona-header { margin-bottom: 8px; }
.persona-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.persona-row {
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
  padding: 4px 0;
}
.persona-row .plabel {
  color: #909399;
  font-weight: 500;
  margin-right: 8px;
}
.persona-row.highlight {
  background: #ecf5ff;
  border-radius: 4px;
  padding: 6px 8px;
  color: #303133;
  font-weight: 500;
}
.persona-row.warn {
  background: #fdf6ec;
  border-radius: 4px;
  padding: 6px 8px;
  color: #e6a23c;
}
.psychology-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.psy-item {
  background: #f8f9fa;
  border-radius: 6px;
  padding: 10px 12px;
}
.psy-label {
  display: block;
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}
.psy-val {
  font-size: 13px;
  color: #303133;
  line-height: 1.5;
}
.paths-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.path-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.path-detail {
  flex: 1;
  background: #f0f9eb;
  border-radius: 6px;
  padding: 8px 12px;
}
.path-main {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.path-type {
  font-weight: 600;
  color: #67c23a;
}
.path-desc { color: #303133; }
.path-price {
  font-size: 12px;
  color: #e6a23c;
  margin-top: 4px;
  display: block;
}
.angles-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.angle-item {
  display: flex;
  gap: 8px;
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
}
.angle-num {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #409eff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  flex-shrink: 0;
  margin-top: 2px;
}
.angle-text { flex: 1; }
.risk-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.risk-matrix-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.rm-item {
  display: flex;
  align-items: center;
  gap: 8px;
}
.rm-label {
  font-size: 13px;
  color: #606266;
  min-width: 70px;
}
</style>
