<template>
  <el-row :gutter="20" class="stats-row">
    <el-col :span="6">
      <div class="stat-card stat-card--purple" @click="$emit('navigate', 'opportunities')">
        <div class="stat-icon-wrap">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
            <path d="M2 17l10 5 10-5"/>
            <path d="M2 12l10 5 10-5"/>
          </svg>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ animatedStats.opportunityCount }}</div>
          <div class="stat-label">机会商品</div>
          <div class="stat-sub" v-if="loading">加载中...</div>
          <div class="stat-sub" v-else>排名前30%商品</div>
        </div>
      </div>
    </el-col>

    <el-col :span="6">
      <div class="stat-card stat-card--green" @click="$emit('navigate', 'trend')">
        <div class="stat-icon-wrap">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/>
            <polyline points="16 7 22 7 22 13"/>
          </svg>
        </div>
        <div class="stat-info">
          <div class="stat-value" :class="trendClass">{{ stats.todayTrend }}</div>
          <div class="stat-label">今日趋势</div>
          <div class="stat-sub">
            <span class="trend-up">↑{{ stats.trendUpCount }}</span>
            <span class="trend-separator">/</span>
            <span class="trend-down">↓{{ stats.trendDownCount }}</span>
          </div>
        </div>
      </div>
    </el-col>

    <el-col :span="6">
      <div class="stat-card stat-card--amber" @click="$emit('navigate', 'alerts')">
        <div class="stat-icon-wrap">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ alertCount }}</div>
          <div class="stat-label">异动提醒</div>
          <div class="stat-sub" v-if="alertCount > 0">
            <span class="alert-badge">{{ alertCount }} 待确认</span>
          </div>
          <div class="stat-sub" v-else>一切正常</div>
        </div>
      </div>
    </el-col>

    <el-col :span="6">
      <div class="stat-card stat-card--blue" @click="$emit('navigate', 'ai')">
        <div class="stat-icon-wrap">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 16v-4"/>
            <path d="M12 8h.01"/>
          </svg>
        </div>
        <div class="stat-info">
          <div class="stat-value">{{ stats.todayAiCount }}</div>
          <div class="stat-label">AI洞察</div>
          <div class="stat-sub">今日分析 {{ stats.todayAiCount }} 次</div>
        </div>
      </div>
    </el-col>
  </el-row>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'

interface DashboardStats {
  todayTrend: string
  trendUpCount: number
  trendDownCount: number
  todayAiCount: number
}

interface Props {
  initialStats?: DashboardStats
  initialOpportunityCount?: number
  initialAlertCount?: number
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  initialStats: () => ({
    todayTrend: '0%',
    trendUpCount: 0,
    trendDownCount: 0,
    todayAiCount: 0,
  }),
  initialOpportunityCount: 0,
  initialAlertCount: 0,
  loading: false,
})

defineEmits<{
  navigate: [type: string]
}>()

const stats = reactive<DashboardStats>({
  todayTrend: '0%',
  trendUpCount: 0,
  trendDownCount: 0,
  todayAiCount: 0,
})

const opportunityCount = ref(0)
const alertCount = ref(0)
const loading = ref(false)

const animatedStats = reactive({
  opportunityCount: 0,
})

const trendClass = computed(() => {
  if (stats.todayTrend.startsWith('+')) return 'trend-up'
  if (stats.todayTrend.startsWith('-')) return 'trend-down'
  return ''
})

function animateValue(obj: any, key: string, target: number, duration: number = 500) {
  const start = obj[key]
  const change = target - start
  const startTime = performance.now()

  function update(currentTime: number) {
    const elapsed = currentTime - startTime
    const progress = Math.min(elapsed / duration, 1)
    const easeProgress = 1 - Math.pow(1 - progress, 3)
    obj[key] = Math.round(start + change * easeProgress)

    if (progress < 1) {
      requestAnimationFrame(update)
    }
  }

  requestAnimationFrame(update)
}

watch(() => props.initialStats, (newStats) => {
  Object.assign(stats, newStats)
}, { immediate: true, deep: true })

watch(() => props.initialOpportunityCount, (newCount) => {
  animateValue(animatedStats, 'opportunityCount', newCount)
}, { immediate: true })

watch(() => props.initialAlertCount, (newCount) => {
  alertCount.value = newCount
}, { immediate: true })

onMounted(() => {
  if (props.initialOpportunityCount > 0) {
    animateValue(animatedStats, 'opportunityCount', props.initialOpportunityCount)
  }
})
</script>

<style scoped>
.stats-row {
  margin-bottom: 0;
}

.stat-card {
  background: linear-gradient(135deg, rgba(30, 30, 50, 0.9) 0%, rgba(20, 20, 35, 0.95) 100%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-card:hover {
  transform: translateY(-2px);
  border-color: rgba(255, 255, 255, 0.15);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.stat-card--purple {
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.15) 0%, rgba(20, 20, 35, 0.95) 100%);
  border-color: rgba(139, 92, 246, 0.3);
}

.stat-card--purple:hover {
  border-color: rgba(139, 92, 246, 0.5);
  box-shadow: 0 8px 32px rgba(139, 92, 246, 0.2);
}

.stat-card--green {
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.15) 0%, rgba(20, 20, 35, 0.95) 100%);
  border-color: rgba(34, 197, 94, 0.3);
}

.stat-card--green:hover {
  border-color: rgba(34, 197, 94, 0.5);
  box-shadow: 0 8px 32px rgba(34, 197, 94, 0.2);
}

.stat-card--amber {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(20, 20, 35, 0.95) 100%);
  border-color: rgba(245, 158, 11, 0.3);
}

.stat-card--amber:hover {
  border-color: rgba(245, 158, 11, 0.5);
  box-shadow: 0 8px 32px rgba(245, 158, 11, 0.2);
}

.stat-card--blue {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.15) 0%, rgba(20, 20, 35, 0.95) 100%);
  border-color: rgba(59, 130, 246, 0.3);
}

.stat-card--blue:hover {
  border-color: rgba(59, 130, 246, 0.5);
  box-shadow: 0 8px 32px rgba(59, 130, 246, 0.2);
}

.stat-icon-wrap {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-card--purple .stat-icon-wrap {
  background: rgba(139, 92, 246, 0.2);
  color: #a78bfa;
}

.stat-card--green .stat-icon-wrap {
  background: rgba(34, 197, 94, 0.2);
  color: #4ade80;
}

.stat-card--amber .stat-icon-wrap {
  background: rgba(245, 158, 11, 0.2);
  color: #fbbf24;
}

.stat-card--blue .stat-icon-wrap {
  background: rgba(59, 130, 246, 0.2);
  color: #60a5fa;
}

.stat-icon-wrap svg {
  width: 24px;
  height: 24px;
}

.stat-info {
  flex: 1;
  min-width: 0;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
  line-height: 1.2;
}

.stat-label {
  font-size: 14px;
  color: #8a8a9a;
  margin-top: 4px;
}

.stat-sub {
  font-size: 12px;
  color: #6a6a7a;
  margin-top: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.trend-up {
  color: #4ade80;
  font-weight: 600;
}

.trend-down {
  color: #f87171;
  font-weight: 600;
}

.trend-separator {
  color: #4a4a5a;
  margin: 0 2px;
}

.trend-up, .trend-down {
  display: inline-block;
}

.trendClass.trend-up {
  color: #4ade80;
}

.trendClass.trend-down {
  color: #f87171;
}

.alert-badge {
  background: rgba(239, 68, 68, 0.2);
  color: #f87171;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}
</style>
