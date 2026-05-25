<template>
  <div class="panel opportunity-card">
    <div class="panel-header">
      <div class="header-left">
        <h3>🚀 今日机会榜</h3>
        <el-tag v-if="items.length > 0" type="success" size="small" effect="dark">
          {{ items.length }} 个机会
        </el-tag>
      </div>
      <el-button type="primary" size="small" text @click="$router.push('/dashboard/opportunities')">
        查看全部
        <el-icon class="el-icon--right"><ArrowRight /></el-icon>
      </el-button>
    </div>

    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="3" animated />
    </div>

    <div v-else-if="items.length === 0" class="empty-state">
      <div class="empty-icon">📊</div>
      <p class="empty-title">暂无机会数据</p>
      <p class="empty-hint">添加更多商品后自动生成排名</p>
      <el-button type="primary" size="small" @click="$router.push('/dashboard/discovery')">
        探索商品
      </el-button>
    </div>

    <div v-else class="opportunity-list">
      <div
        v-for="item in items"
        :key="item.product_id"
        class="opportunity-item"
        @click="goToProduct(item.product_id)"
      >
        <div class="opportunity-rank" :class="getRankClass(item.rank)">
          {{ item.rank }}
        </div>
        <div class="opportunity-product">
          <div
            v-if="item.image_url"
            class="product-thumb"
            :style="{ backgroundImage: `url(${item.image_url})` }"
          ></div>
          <div v-else class="product-thumb placeholder">
            {{ getPlatformEmoji(item.platform) }}
          </div>
          <div class="product-info">
            <div class="product-name">{{ item.product_name }}</div>
            <div class="product-meta">
              <span class="percentile">
                超过同类 {{ item.percentile }}%
              </span>
              <span v-if="item.platform" class="platform-tag">
                {{ getPlatformLabel(item.platform) }}
              </span>
            </div>
          </div>
        </div>
        <div class="opportunity-trend">
          <span :class="['trend-badge', item.trend_direction]">
            {{ item.trend_direction === 'up' ? '↑' : '↓' }}
            {{ Math.abs(item.growth_rate_7d) }}%
          </span>
        </div>
        <div class="opportunity-lifecycle">
          <el-tag :type="lifecycleTagType(item.lifecycle_stage)" size="small" effect="plain">
            {{ lifecycleLabel(item.lifecycle_stage) }}
          </el-tag>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight } from '@element-plus/icons-vue'
import api from '@/utils/api'

interface OpportunityItem {
  product_id: string
  product_name: string
  image_url?: string
  platform?: string
  rank: number
  percentile: number
  trend_direction: 'up' | 'down'
  growth_rate_7d: number
  lifecycle_stage: string
}

const router = useRouter()
const items = ref<OpportunityItem[]>([])
const loading = ref(true)
const error = ref<string | null>(null)

const lifecycleMap: Record<string, string> = {
  rising: '上升期',
  hot: '爆款',
  stable: '稳定期',
  declining: '衰退期',
}

const platformEmojiMap: Record<string, string> = {
  xhs: '📕',
  jd: '🟰',
  pdd: '🟢',
  dy: '🎵',
  mt: '🍔',
  ele: '🟠',
}

const platformLabelMap: Record<string, string> = {
  xhs: '小红书',
  jd: '京东',
  pdd: '拼多多',
  dy: '抖音',
  mt: '美团',
  ele: '饿了么',
}

function lifecycleLabel(stage: string) {
  return lifecycleMap[stage] || stage
}

function lifecycleTagType(stage: string) {
  const map: Record<string, any> = {
    rising: 'success',
    hot: 'danger',
    stable: 'info',
    declining: 'warning',
  }
  return map[stage] || 'info'
}

function getPlatformEmoji(platform?: string) {
  return platform ? (platformEmojiMap[platform] || '📦') : '📦'
}

function getPlatformLabel(platform?: string) {
  return platform ? (platformLabelMap[platform] || platform) : ''
}

function getRankClass(rank: number) {
  if (rank <= 3) return 'rank-top'
  if (rank <= 10) return 'rank-high'
  return 'rank-normal'
}

async function loadOpportunities() {
  try {
    loading.value = true
    error.value = null

    const res = await api.get('/feature/product-rankings')
    const rankings = res.data?.items || []

    const topPercent = rankings.slice(0, Math.ceil(rankings.length * 0.3))

    items.value = topPercent.map((r: any, idx: number) => ({
      product_id: r.product_id,
      product_name: r.product_name || '未知商品',
      image_url: r.image_url,
      platform: r.platform,
      rank: idx + 1,
      percentile: r.percentile || Math.round((1 - idx / rankings.length) * 100),
      trend_direction: (r.growth_rate_7d || 0) >= 0 ? 'up' : 'down',
      growth_rate_7d: r.growth_rate_7d || 0,
      lifecycle_stage: r.lifecycle_stage || 'stable',
    }))
  } catch (e: any) {
    console.error('Failed to load opportunities:', e)
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

function goToProduct(productId: string) {
  router.push(`/dashboard/product/${productId}`)
}

onMounted(() => {
  loadOpportunities()
})
</script>

<style scoped>
.opportunity-card {
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

.empty-title {
  font-size: 16px;
  color: #8a8a9a;
  margin: 0 0 8px 0;
}

.empty-hint {
  font-size: 14px;
  color: #6a6a7a;
  margin: 0 0 20px 0;
}

.opportunity-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.opportunity-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.opportunity-item:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.1);
  transform: translateX(4px);
}

.opportunity-rank {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 14px;
  flex-shrink: 0;
}

.rank-top {
  background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
  color: #1a1a2e;
}

.rank-high {
  background: rgba(139, 92, 246, 0.2);
  color: #a78bfa;
}

.rank-normal {
  background: rgba(255, 255, 255, 0.05);
  color: #6a6a7a;
}

.opportunity-product {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.product-thumb {
  width: 40px;
  height: 40px;
  border-radius: 8px;
  background-size: cover;
  background-position: center;
  background-color: rgba(255, 255, 255, 0.05);
  flex-shrink: 0;
}

.product-thumb.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  background: rgba(255, 255, 255, 0.05);
}

.product-info {
  flex: 1;
  min-width: 0;
}

.product-name {
  font-size: 14px;
  font-weight: 500;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.product-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.percentile {
  font-size: 12px;
  color: #4ade80;
  font-weight: 500;
}

.platform-tag {
  font-size: 11px;
  color: #6a6a7a;
  background: rgba(255, 255, 255, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
}

.opportunity-trend {
  flex-shrink: 0;
}

.trend-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}

.trend-badge.up {
  background: rgba(239, 68, 68, 0.15);
  color: #f87171;
}

.trend-badge.down {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
}

.opportunity-lifecycle {
  flex-shrink: 0;
}
</style>
