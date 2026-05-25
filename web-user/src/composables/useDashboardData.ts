import { ref, onMounted, onUnmounted } from 'vue'
import api from '@/utils/api'

export interface FallbackStats {
  productCount: number
  todayTrend: string
  alertCount: number
  todayAiCount: number
  opportunityCount: number
}

export interface OpportunityItem {
  product_id: string
  product_name: string
  image_url?: string
  rank: number
  percentile: number
  trend_direction: 'up' | 'down'
  growth_rate_7d: number
  lifecycle_stage: string
}

export interface AlertEvent {
  id: string
  product_id?: string
  product_name?: string
  detail?: string
  alert_type?: string
  severity: 'critical' | 'warning' | 'info'
  is_acknowledged: boolean
  created_at?: string
}

export function useDashboardData() {
  const isOnline = ref(navigator.onLine)
  const localProducts = ref<any[]>([])
  const localAlerts = ref<any[]>([])

  function calculateLocalTrend(): string {
    if (localProducts.value.length < 2) return '0%'

    let upCount = 0
    let downCount = 0

    for (const product of localProducts.value) {
      const trend = product.trend || 0
      if (trend > 0) upCount++
      else if (trend < 0) downCount++
    }

    const total = localProducts.value.length
    const netTrend = Math.round((upCount - downCount) / total * 100)
    return netTrend >= 0 ? `+${netTrend}%` : `${netTrend}%`
  }

  function calculateOpportunityCount(): number {
    const products = localProducts.value
    if (products.length === 0) return 0

    const sortedProducts = [...products].sort((a, b) => (b.trend || 0) - (a.trend || 0))
    const top30Percent = Math.ceil(sortedProducts.length * 0.3)
    return top30Percent
  }

  function handleOnline() {
    isOnline.value = true
  }

  function handleOffline() {
    isOnline.value = false
    loadLocalData()
  }

  function loadLocalData() {
    try {
      const stored = localStorage.getItem('dashboard_cache')
      if (stored) {
        const cache = JSON.parse(stored)
        localProducts.value = cache.products || []
        localAlerts.value = cache.alerts || []
      }
    } catch (e) {
      console.error('Failed to load local data:', e)
    }
  }

  function saveLocalData() {
    try {
      const cache = {
        products: localProducts.value,
        alerts: localAlerts.value,
        timestamp: Date.now()
      }
      localStorage.setItem('dashboard_cache', JSON.stringify(cache))
    } catch (e) {
      console.error('Failed to save local data:', e)
    }
  }

  async function loadOpportunityRankings(): Promise<OpportunityItem[]> {
    if (!isOnline.value) {
      return calculateLocalOpportunities()
    }

    try {
      const res = await api.get('/feature/product-rankings')
      const items = res.data?.items || []

      if (items.length > 0) {
        localProducts.value = items
        saveLocalData()
      }

      return items.map((r: any, idx: number) => ({
        product_id: r.product_id,
        product_name: r.product_name || '未知商品',
        image_url: r.image_url,
        rank: idx + 1,
        percentile: r.percentile || Math.round((1 - idx / items.length) * 100),
        trend_direction: (r.growth_rate_7d || 0) >= 0 ? 'up' : 'down',
        growth_rate_7d: r.growth_rate_7d || 0,
        lifecycle_stage: r.lifecycle_stage || 'stable',
      }))
    } catch (e) {
      console.error('Failed to load opportunity rankings:', e)
      return calculateLocalOpportunities()
    }
  }

  function calculateLocalOpportunities(): OpportunityItem[] {
    return localProducts.value
      .sort((a, b) => (b.trend || 0) - (a.trend || 0))
      .slice(0, Math.ceil(localProducts.value.length * 0.3))
      .map((p: any, idx: number) => ({
        product_id: p.product_id || p.id,
        product_name: p.product_name || p.name || '未知商品',
        image_url: p.image_url,
        rank: idx + 1,
        percentile: Math.round((1 - idx / localProducts.value.length) * 100),
        trend_direction: (p.trend || 0) >= 0 ? 'up' : 'down',
        growth_rate_7d: p.trend || 0,
        lifecycle_stage: 'stable',
      }))
  }

  async function loadAlertEvents(): Promise<AlertEvent[]> {
    if (!isOnline.value) {
      return localAlerts.value.map((a: any) => ({
        id: a.id,
        product_id: a.product_id,
        product_name: a.product_name,
        detail: a.detail,
        alert_type: a.type,
        severity: a.severity || 'info',
        is_acknowledged: a.acknowledged || false,
        created_at: a.created_at,
      }))
    }

    try {
      const res = await api.get('/alert-rules/events/all')
      const events = res.data?.events || res.data?.items || []

      if (events.length > 0) {
        localAlerts.value = events
        saveLocalData()
      }

      return events.map((e: any) => ({
        id: e.id,
        product_id: e.product_id,
        product_name: e.product_name,
        detail: e.detail,
        alert_type: e.alert_type,
        severity: e.severity || 'info',
        is_acknowledged: e.is_acknowledged || false,
        created_at: e.created_at,
      }))
    } catch (e) {
      console.error('Failed to load alert events:', e)
      return []
    }
  }

  async function loadCategoryHeatmap(): Promise<any[]> {
    if (!isOnline.value) {
      return calculateLocalCategoryHeatmap()
    }

    try {
      const res = await api.get('/feature/crowd/category-heatmap')
      return res.data?.categories || res.data?.items || []
    } catch (e) {
      console.error('Failed to load category heatmap:', e)
      return []
    }
  }

  function calculateLocalCategoryHeatmap(): any[] {
    const categoryMap = new Map<string, number>()

    for (const product of localProducts.value) {
      const category = product.category || '其他'
      categoryMap.set(category, (categoryMap.get(category) || 0) + 1)
    }

    const total = localProducts.value.length
    if (total === 0) return []

    const categories: any[] = []

    categoryMap.forEach((count, name) => {
      categories.push({
        name,
        product_count: count,
        intensity: count / total,
        trend: 0,
      })
    })

    return categories.sort((a, b) => b.intensity - a.intensity)
  }

  onMounted(() => {
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    loadLocalData()
  })

  onUnmounted(() => {
    window.removeEventListener('online', handleOnline)
    window.removeEventListener('offline', handleOffline)
  })

  return {
    isOnline,
    loadOpportunityRankings,
    loadAlertEvents,
    loadCategoryHeatmap,
  }
}
