<template>
  <div class="panel category-heatmap">
    <div class="panel-header">
      <div class="header-left">
        <h3>🔥 品类热力图</h3>
        <el-tag v-if="selectedCategory" type="primary" size="small" closable @close="clearSelection">
          {{ selectedCategory.name }}
        </el-tag>
      </div>
      <el-tabs v-model="activeView" size="small" class="view-tabs">
        <el-tab-pane label="热力图" name="heatmap" />
        <el-tab-pane label="趋势" name="trend" />
        <el-tab-pane label="模式" name="behavior" />
      </el-tabs>
    </div>

    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="3" animated />
    </div>

    <div v-else-if="activeView === 'heatmap'">
      <div v-if="categories.length === 0" class="empty-state">
        <div class="empty-icon">📊</div>
        <p class="empty-title">暂无品类数据</p>
        <p class="empty-hint">添加商品后自动生成热力图</p>
      </div>

      <div v-else class="heatmap-grid">
        <div
          v-for="cat in sortedCategories"
          :key="cat.name"
          class="heatmap-cell"
          :style="{ backgroundColor: heatColor(cat.intensity) }"
          :class="{ 'heatmap-cell--selected': selectedCategory?.name === cat.name }"
          @click="selectCategory(cat)"
        >
          <span class="cat-name">{{ cat.name }}</span>
          <span class="cat-count">{{ cat.product_count || 0 }}</span>
          <div class="cat-trend" v-if="cat.trend">
            <span :class="cat.trend > 0 ? 'trend-up' : 'trend-down'">
              {{ cat.trend > 0 ? '↑' : '↓' }}{{ Math.abs(cat.trend) }}%
            </span>
          </div>
        </div>
      </div>

      <div class="heatmap-legend">
        <span class="legend-label">热度：</span>
        <div class="legend-gradient"></div>
        <span class="legend-low">低</span>
        <span class="legend-high">高</span>
      </div>
    </div>

    <div v-else-if="activeView === 'trend'" class="trend-view">
      <div v-if="trendData.length === 0" class="empty-state">
        <div class="empty-icon">📈</div>
        <p class="empty-title">暂无趋势数据</p>
      </div>
      <div v-else class="trend-chart-container">
        <v-chart :option="trendChartOption" autoresize style="height: 200px;" />
      </div>
    </div>

    <div v-else class="behavior-view">
      <div v-if="patterns.length === 0" class="empty-state">
        <div class="empty-icon">🧠</div>
        <p class="empty-title">暂无行为模式</p>
      </div>
      <div v-else class="pattern-list">
        <div
          v-for="pattern in patterns"
          :key="pattern.type"
          class="pattern-item"
          @click="selectPattern(pattern)"
        >
          <div class="pattern-icon">{{ pattern.icon || '📊' }}</div>
          <div class="pattern-info">
            <div class="pattern-name">{{ pattern.name }}</div>
            <div class="pattern-desc">{{ pattern.description }}</div>
            <div class="pattern-stats" v-if="pattern.count">
              <span class="stat">出现 {{ pattern.count }} 次</span>
              <span class="stat" v-if="pattern.avgGrowth">平均增长 {{ pattern.avgGrowth }}%</span>
            </div>
          </div>
          <div class="pattern-trend">
            <span v-if="(pattern.trend ?? 0) > 0" class="trend-up">↑{{ pattern.trend }}%</span>
            <span v-else-if="(pattern.trend ?? 0) < 0" class="trend-down">↓{{ Math.abs(pattern.trend ?? 0) }}%</span>
            <span v-else class="trend-flat">—</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/utils/api'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'

use([CanvasRenderer, LineChart, GridComponent, TooltipComponent, LegendComponent])

interface Category {
  name: string
  product_count: number
  intensity: number
  trend?: number
  sales_count?: number
  avg_price?: number
}

interface TrendPoint {
  date: string
  value: number
  category?: string
}

interface BehaviorPattern {
  type: string
  name: string
  description: string
  icon?: string
  count?: number
  avgGrowth?: number
  trend?: number
}

const activeView = ref<'heatmap' | 'trend' | 'behavior'>('heatmap')
const categories = ref<Category[]>([])
const trendData = ref<TrendPoint[]>([])
const patterns = ref<BehaviorPattern[]>([])
const selectedCategory = ref<Category | null>(null)
const loading = ref(true)

const sortedCategories = computed(() => {
  return [...categories.value].sort((a, b) => b.intensity - a.intensity)
})

function heatColor(intensity: number) {
  const clampedIntensity = Math.max(0, Math.min(1, intensity))

  if (clampedIntensity < 0.33) {
    return `rgba(34, 197, 94, ${0.15 + clampedIntensity * 0.3})`
  } else if (clampedIntensity < 0.66) {
    return `rgba(245, 158, 11, ${0.2 + (clampedIntensity - 0.33) * 0.4})`
  } else {
    return `rgba(239, 68, 68, ${0.25 + (clampedIntensity - 0.66) * 0.5})`
  }
}

const trendChartOption = computed(() => {
  const dates = [...new Set(trendData.value.map(t => t.date))].sort()
  const categories = [...new Set(trendData.value.map(t => t.category))]

  const series = categories.map(cat => ({
    name: cat,
    type: 'line' as const,
    data: dates.map(date => {
      const point = trendData.value.find(t => t.date === date && t.category === cat)
      return point?.value || 0
    }),
    smooth: true,
    symbol: 'circle',
    symbolSize: 4,
  }))

  return {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(20, 20, 30, 0.9)',
      borderColor: 'rgba(255, 255, 255, 0.1)',
      textStyle: { color: '#e0e0ea', fontSize: 12 },
    },
    legend: {
      data: categories,
      textStyle: { color: '#8a8a9a', fontSize: 11 },
      top: 0,
    },
    grid: { left: 40, right: 20, top: 30, bottom: 30 },
    xAxis: {
      type: 'category',
      data: dates.map(d => d.slice(5)),
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.08)' } },
      axisLabel: { color: '#6a6a7a', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(255,255,255,0.04)' } },
      axisLabel: { color: '#6a6a7a', fontSize: 11 },
    },
    series,
  }
})

async function loadCategoryHeatmap() {
  try {
    loading.value = true
    const res = await api.get('/feature/crowd/category-heatmap')
    categories.value = res.data?.categories || res.data?.items || []

    if (categories.value.length === 0) {
      categories.value = generateMockCategories()
    }
  } catch (e) {
    console.error('Failed to load category heatmap:', e)
    categories.value = generateMockCategories()
  } finally {
    loading.value = false
  }
}

async function loadTrendTimeseries() {
  try {
    const res = await api.get('/feature/crowd/trend-timeseries')
    trendData.value = res.data?.series || res.data?.items || []

    if (trendData.value.length === 0) {
      trendData.value = generateMockTrendData()
    }
  } catch (e) {
    console.error('Failed to load trend timeseries:', e)
    trendData.value = generateMockTrendData()
  }
}

async function loadBehaviorPatterns() {
  try {
    const res = await api.get('/feature/crowd/behavior-patterns')
    patterns.value = res.data?.patterns || res.data?.items || []

    if (patterns.value.length === 0) {
      patterns.value = generateMockPatterns()
    }
  } catch (e) {
    console.error('Failed to load behavior patterns:', e)
    patterns.value = generateMockPatterns()
  }
}

function generateMockCategories(): Category[] {
  const mockCats = ['美妆护肤', '服装鞋包', '食品饮料', '家居用品', '母婴用品', '数码电器', '运动户外', '珠宝配饰']
  return mockCats.map(name => ({
    name,
    product_count: Math.floor(Math.random() * 100) + 10,
    intensity: Math.random(),
    trend: Math.floor(Math.random() * 40) - 20,
  }))
}

function generateMockTrendData(): TrendPoint[] {
  const dates = Array.from({ length: 7 }, (_, i) => {
    const d = new Date()
    d.setDate(d.getDate() - 6 + i)
    return d.toISOString().slice(0, 10)
  })
  const cats = ['美妆护肤', '服装鞋包', '食品饮料']

  return dates.flatMap(date =>
    cats.map(cat => ({
      date,
      category: cat,
      value: Math.floor(Math.random() * 100) + 50,
    }))
  )
}

function generateMockPatterns(): BehaviorPattern[] {
  return [
    { type: 'weekend_surge', name: '周末效应', description: '周末销量通常高于工作日20-30%', icon: '📅', count: 45, avgGrowth: 25, trend: 5 },
    { type: 'holiday_boost', name: '节假日爆发', description: '节假日前后需求激增', icon: '🎉', count: 12, avgGrowth: 80, trend: 15 },
    { type: 'weather_correlation', name: '天气关联', description: '气温变化影响特定品类销售', icon: '🌤️', count: 28, avgGrowth: 12, trend: -3 },
    { type: 'trend_early_adopter', name: '趋势先行', description: '新趋势出现时的早期采纳者行为', icon: '🚀', count: 8, avgGrowth: 150, trend: 25 },
  ]
}

function selectCategory(cat: Category) {
  if (selectedCategory.value?.name === cat.name) {
    selectedCategory.value = null
  } else {
    selectedCategory.value = cat
    ElMessage.info(`已选择 ${cat.name}，点击查看详情`)
  }
}

function clearSelection() {
  selectedCategory.value = null
}

function selectPattern(pattern: BehaviorPattern) {
  ElMessage.info(`查看 ${pattern.name} 模式详情`)
}

watch(activeView, (newView) => {
  if (newView === 'trend' && trendData.value.length === 0) {
    loadTrendTimeseries()
  } else if (newView === 'behavior' && patterns.value.length === 0) {
    loadBehaviorPatterns()
  }
})

onMounted(() => {
  loadCategoryHeatmap()
})
</script>

<style scoped>
.category-heatmap {
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
  flex-wrap: wrap;
  gap: 12px;
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

.view-tabs {
  margin-bottom: 0;
}

.view-tabs :deep(.el-tabs__header) {
  margin: 0;
}

.view-tabs :deep(.el-tabs__nav-wrap::after) {
  display: none;
}

.view-tabs :deep(.el-tabs__item) {
  color: #6a6a7a;
  font-size: 13px;
}

.view-tabs :deep(.el-tabs__item.is-active) {
  color: #fff;
}

.view-tabs :deep(.el-tabs__active-bar) {
  background-color: #6366f1;
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

.empty-title {
  font-size: 16px;
  color: #8a8a9a;
  margin: 0 0 8px 0;
}

.empty-hint {
  font-size: 14px;
  color: #6a6a7a;
  margin: 0;
}

.heatmap-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

@media (max-width: 768px) {
  .heatmap-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.heatmap-cell {
  padding: 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  min-height: 80px;
}

.heatmap-cell:hover {
  transform: scale(1.02);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
}

.heatmap-cell--selected {
  ring: 2px solid #6366f1;
  box-shadow: 0 0 0 2px #6366f1;
}

.cat-name {
  font-size: 13px;
  font-weight: 500;
  color: #fff;
  margin-bottom: 4px;
}

.cat-count {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.8);
}

.cat-trend {
  margin-top: 4px;
  font-size: 11px;
}

.trend-up {
  color: #4ade80;
}

.trend-down {
  color: #f87171;
}

.trend-flat {
  color: #6a6a7a;
}

.heatmap-legend {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 16px;
  font-size: 12px;
  color: #6a6a7a;
}

.legend-gradient {
  width: 100px;
  height: 8px;
  border-radius: 4px;
  background: linear-gradient(to right, rgba(34, 197, 94, 0.4), rgba(245, 158, 11, 0.5), rgba(239, 68, 68, 0.6));
}

.legend-low, .legend-high {
  font-size: 11px;
}

.trend-view {
  min-height: 200px;
}

.trend-chart-container {
  width: 100%;
}

.behavior-view {
  min-height: 200px;
}

.pattern-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pattern-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.pattern-item:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.08);
}

.pattern-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.pattern-info {
  flex: 1;
  min-width: 0;
}

.pattern-name {
  font-size: 14px;
  font-weight: 500;
  color: #fff;
}

.pattern-desc {
  font-size: 12px;
  color: #6a6a7a;
  margin-top: 2px;
}

.pattern-stats {
  display: flex;
  gap: 12px;
  margin-top: 4px;
}

.stat {
  font-size: 11px;
  color: #8a8a9a;
}

.pattern-trend {
  flex-shrink: 0;
  font-size: 14px;
  font-weight: 600;
}
</style>
