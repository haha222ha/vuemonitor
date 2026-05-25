<template>
  <div class="panel alert-event-card">
    <div class="panel-header">
      <div class="header-left">
        <h3>⚡ 异动监控</h3>
        <el-tag v-if="unacknowledgedCount > 0" type="danger" effect="dark">
          {{ unacknowledgedCount }} 待确认
        </el-tag>
        <el-tag v-else type="success" effect="plain" size="small">
          全部已确认
        </el-tag>
      </div>
      <el-button type="primary" size="small" text @click="$router.push('/dashboard/alerts')">
        查看全部
        <el-icon class="el-icon--right"><ArrowRight /></el-icon>
      </el-button>
    </div>

    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="2" animated />
    </div>

    <div v-else-if="events.length === 0" class="empty-state">
      <div class="empty-icon safe">✅</div>
      <p class="empty-title">暂无异动</p>
      <p class="empty-hint">您的商品运行一切正常</p>
    </div>

    <div v-else class="alert-list">
      <div
        v-for="event in events"
        :key="event.id"
        :class="['alert-item', `alert-item--${event.severity}`, { 'alert-item--acknowledged': event.is_acknowledged }]"
      >
        <div class="alert-severity-icon">
          <span v-if="event.severity === 'critical'">🔴</span>
          <span v-else-if="event.severity === 'warning'">🟡</span>
          <span v-else>🔵</span>
        </div>
        <div class="alert-body" @click="goToProduct(event.product_id)">
          <div class="alert-title">{{ event.product_name || '未知商品' }}</div>
          <div class="alert-detail">{{ event.detail || event.message }}</div>
          <div class="alert-meta">
            <span class="alert-type">{{ alertTypeLabel(event.alert_type || event.type) }}</span>
            <span class="alert-time">{{ timeAgo(event.created_at || event.timestamp) }}</span>
          </div>
        </div>
        <div class="alert-actions">
          <el-button
            v-if="!event.is_acknowledged"
            size="small"
            type="primary"
            :loading="acknowledgingId === event.id"
            @click.stop="acknowledge(event.id)"
          >
            确认
          </el-button>
          <span v-else class="acknowledged-badge">
            <el-icon><Check /></el-icon>
            已确认
          </span>
        </div>
      </div>
    </div>

    <div v-if="hasMore" class="load-more">
      <el-button size="small" text @click="loadMore" :loading="loadingMore">
        加载更多
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, Check } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import api from '@/utils/api'

interface AlertEvent {
  id: string
  product_id?: string
  product_name?: string
  detail?: string
  message?: string
  alert_type?: string
  type?: string
  severity: 'critical' | 'warning' | 'info'
  is_acknowledged: boolean
  created_at?: string
  timestamp?: string
}

const router = useRouter()
const events = ref<AlertEvent[]>([])
const loading = ref(true)
const loadingMore = ref(false)
const acknowledgingId = ref<string | null>(null)
const page = ref(1)
const pageSize = ref(10)

const unacknowledgedCount = computed(() =>
  events.value.filter(e => !e.is_acknowledged).length
)

const hasMore = computed(() =>
  events.value.length >= pageSize.value
)

const alertTypeMap: Record<string, string> = {
  price_drop: '价格下跌',
  price_increase: '价格上涨',
  price_change: '价格变化',
  sales_surge: '销量激增',
  sales_drop: '销量下降',
  sales_change: '销量变化',
  rating_drop: '评分下降',
  rating_increase: '评分上涨',
  stock_change: '库存变化',
  stock_out: '库存不足',
  new_review: '新评价',
  anomaly: '异常',
  trend_reversal: '趋势反转',
}

function alertTypeLabel(type?: string) {
  if (!type) return '未知'
  return alertTypeMap[type] || type
}

function timeAgo(dateStr?: string) {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}天前`
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

async function loadAlertEvents(reset = false) {
  if (reset) {
    page.value = 1
    events.value = []
  }

  try {
    if (reset) {
      loading.value = true
    } else {
      loadingMore.value = true
    }

    const res = await api.get('/alert-rules/events/all', {
      params: {
        page: page.value,
        page_size: pageSize.value,
      }
    })

    const newEvents = (res.data?.events || res.data?.items || []).map((e: any) => ({
      id: e.id,
      product_id: e.product_id,
      product_name: e.product_name,
      detail: e.detail,
      message: e.message,
      alert_type: e.alert_type,
      type: e.type,
      severity: e.severity || 'info',
      is_acknowledged: e.is_acknowledged || false,
      created_at: e.created_at,
      timestamp: e.timestamp,
    }))

    if (reset) {
      events.value = newEvents
    } else {
      events.value = [...events.value, ...newEvents]
    }
  } catch (e: any) {
    console.error('Failed to load alert events:', e)
    ElMessage.error('加载异动事件失败')
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

async function loadMore() {
  page.value++
  await loadAlertEvents(false)
}

async function acknowledge(eventId: string) {
  try {
    acknowledgingId.value = eventId
    await api.post(`/alert-rules/events/${eventId}/acknowledge`)

    const event = events.value.find(e => e.id === eventId)
    if (event) {
      event.is_acknowledged = true
    }

    ElMessage.success('已确认异动')
  } catch (e: any) {
    console.error('Failed to acknowledge event:', e)
    ElMessage.error('确认失败')
  } finally {
    acknowledgingId.value = null
  }
}

function goToProduct(productId?: string) {
  if (productId) {
    router.push(`/dashboard/product/${productId}`)
  }
}

onMounted(() => {
  loadAlertEvents(true)
})
</script>

<style scoped>
.alert-event-card {
  background: rgba(20, 20, 35, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 20px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.panel-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #fff;
}

.loading-state {
  padding: 20px 0;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-icon.safe {
  font-size: 56px;
}

.empty-title {
  font-size: 16px;
  color: #4ade80;
  margin: 0 0 8px 0;
}

.empty-hint {
  font-size: 14px;
  color: #6a6a7a;
  margin: 0;
}

.alert-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 400px;
  overflow-y: auto;
}

.alert-list::-webkit-scrollbar {
  width: 4px;
}

.alert-list::-webkit-scrollbar-track {
  background: transparent;
}

.alert-list::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
}

.alert-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 12px;
  transition: all 0.2s ease;
}

.alert-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.alert-item--critical {
  border-left: 3px solid #ef4444;
}

.alert-item--warning {
  border-left: 3px solid #f59e0b;
}

.alert-item--info {
  border-left: 3px solid #3b82f6;
}

.alert-item--acknowledged {
  opacity: 0.6;
}

.alert-severity-icon {
  font-size: 16px;
  flex-shrink: 0;
  margin-top: 2px;
}

.alert-body {
  flex: 1;
  min-width: 0;
  cursor: pointer;
}

.alert-title {
  font-size: 14px;
  font-weight: 500;
  color: #fff;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.alert-detail {
  font-size: 12px;
  color: #8a8a9a;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.alert-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
}

.alert-type {
  font-size: 11px;
  color: #6a6a7a;
  background: rgba(255, 255, 255, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
}

.alert-time {
  font-size: 11px;
  color: #6a6a7a;
}

.alert-actions {
  flex-shrink: 0;
}

.acknowledged-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #4ade80;
  background: rgba(74, 222, 128, 0.1);
  padding: 4px 8px;
  border-radius: 6px;
}

.load-more {
  text-align: center;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.04);
}
</style>
