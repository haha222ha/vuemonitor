import { ref, reactive } from "vue";
import { useProductStore } from "../stores/product";
import { useCollectStore } from "../stores/collect";
import { useSchedulerStore } from "../stores/scheduler";
import { usePermissionStore } from "../stores/permission";
import api, { isNetworkError } from "../utils/api";

export interface BizStats {
  opportunityCount: number;
  opportunityTrend: string;
  opportunityTrendType: "up" | "down" | "neutral";
  todayTrend: string;
  todayTrendLabel: string;
  todayTrendType: "up" | "down" | "neutral";
  alertCount: number;
  alertTrend: string;
  aiInsightCount: number;
  cloudConnected: boolean;
}

export interface TrendSeriesItem {
  category: string;
  sparklinePoints: string;
  sparklineWidth: number;
  latestGrowth: number | null;
}

interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

const CACHE_TTL = 30_000;

const cache = new Map<string, CacheEntry<any>>();

function getCached<T>(key: string): T | null {
  const entry = cache.get(key);
  if (!entry) return null;
  if (Date.now() - entry.timestamp > CACHE_TTL) {
    cache.delete(key);
    return null;
  }
  return entry.data as T;
}

function setCache<T>(key: string, data: T): void {
  cache.set(key, { data, timestamp: Date.now() });
}

function invalidateCache(key?: string): void {
  if (key) cache.delete(key);
  else cache.clear();
}

const pendingRequests = new Map<string, Promise<any>>();

async function dedupedFetch<T>(key: string, fetcher: () => Promise<T>): Promise<T> {
  const pending = pendingRequests.get(key);
  if (pending) return pending as Promise<T>;

  const cached = getCached<T>(key);
  if (cached !== null) return cached;

  const promise = fetcher().then((data) => {
    setCache(key, data);
    pendingRequests.delete(key);
    return data;
  }).catch((err) => {
    pendingRequests.delete(key);
    throw err;
  });

  pendingRequests.set(key, promise);
  return promise;
}

export function useDashboardData() {
  const productStore = useProductStore();
  const collectStore = useCollectStore();
  const schedulerStore = useSchedulerStore();
  const permissionStore = usePermissionStore();

  const bizStats = reactive<BizStats>({
    opportunityCount: 0,
    opportunityTrend: "加载中",
    opportunityTrendType: "neutral",
    todayTrend: "-",
    todayTrendLabel: "较昨日",
    todayTrendType: "neutral",
    alertCount: 0,
    alertTrend: "暂无异动",
    aiInsightCount: 0,
    cloudConnected: false,
  });

  const opportunityRankings = ref<any[]>([]);
  const opportunityLoading = ref(false);
  const alertEvents = ref<any[]>([]);
  const alertLoading = ref(false);
  const crowdHeatmap = ref<any[]>([]);
  const crowdPatterns = ref<any>(null);
  const crowdLoading = ref(false);
  const crowdTrendSeries = ref<TrendSeriesItem[]>([]);
  const recommendations = ref<any[]>([]);
  const recLoading = ref(false);

  function processTrendSeries(seriesMap: Record<string, any[]>) {
    const processed: TrendSeriesItem[] = [];
    for (const [category, points] of Object.entries(seriesMap)) {
      if (points.length < 2) continue;
      const salesValues = points.map((p: any) => p.avg_sales || 0);
      const minVal = Math.min(...salesValues);
      const maxVal = Math.max(...salesValues);
      const range = maxVal - minVal || 1;
      const w = 120;
      const h = 32;
      const sparklinePoints = salesValues
        .map((v: number, i: number) => {
          const x = (i / (salesValues.length - 1)) * w;
          const y = h - ((v - minVal) / range) * (h - 4) - 2;
          return `${x.toFixed(1)},${y.toFixed(1)}`;
        })
        .join(" ");
      const lastPoint = points[points.length - 1];
      processed.push({
        category,
        sparklinePoints,
        sparklineWidth: w,
        latestGrowth: lastPoint?.sales_growth_rate ?? null,
      });
    }
    processed.sort((a, b) => {
      const ga = Math.abs(a.latestGrowth || 0);
      const gb = Math.abs(b.latestGrowth || 0);
      return gb - ga;
    });
    crowdTrendSeries.value = processed;
  }

  function applyLocalFallback() {
    bizStats.cloudConnected = false;
    bizStats.opportunityCount = productStore.productCount;
    bizStats.opportunityTrend = "本地商品数";
    bizStats.opportunityTrendType = "neutral";
    bizStats.todayTrend = "-";
    bizStats.todayTrendLabel = "连接云端查看";
    bizStats.todayTrendType = "neutral";
    bizStats.alertCount = collectStore.riskAlerts.length;
    bizStats.alertTrend = bizStats.alertCount > 0 ? `${bizStats.alertCount}条本地告警` : "暂无异动";
    bizStats.aiInsightCount = 0;
  }

  function applyHomeData(d: any) {
    const stats = d.biz_stats;
    bizStats.cloudConnected = true;
    bizStats.opportunityCount = stats.opportunity_count || 0;
    bizStats.opportunityTrend = stats.opportunity_count > 0 ? `${stats.opportunity_count}个上榜` : "暂无排名";
    bizStats.opportunityTrendType = stats.opportunity_count > 0 ? "up" : "neutral";
    bizStats.todayTrend = stats.today_trend || "0%";
    const pct = parseFloat(bizStats.todayTrend);
    if (!isNaN(pct)) {
      bizStats.todayTrendType = pct > 0 ? "up" : pct < 0 ? "down" : "neutral";
      bizStats.todayTrendLabel = pct > 0 ? "较昨日上涨" : pct < 0 ? "较昨日下降" : "较昨日持平";
    }
    bizStats.alertCount = stats.alert_count || 0;
    bizStats.alertTrend = bizStats.alertCount > 0 ? `${bizStats.alertCount}条未处理` : "暂无异动";
    bizStats.aiInsightCount = stats.ai_insight_count || 0;

    if (d.rankings && d.rankings.length > 0) opportunityRankings.value = d.rankings;
    if (d.alert_events && d.alert_events.length > 0) alertEvents.value = d.alert_events;
    if (d.category_heatmap && d.category_heatmap.length > 0) crowdHeatmap.value = d.category_heatmap;
    if (d.behavior_patterns) crowdPatterns.value = d.behavior_patterns;
    if (d.trend_timeseries && Object.keys(d.trend_timeseries).length > 0) processTrendSeries(d.trend_timeseries);
  }

  async function fetchBizStats() {
    try {
      const homeData = await dedupedFetch("dashboard:home", async () => {
        const res = await api.get("/dashboard/home");
        return res.data?.code === 0 ? res.data.data : null;
      });
      if (homeData) {
        applyHomeData(homeData);
      } else {
        applyLocalFallback();
      }
    } catch (err) {
      if (isNetworkError(err)) {
        console.warn("[Dashboard] 服务端不可达，使用本地降级数据");
      }
      applyLocalFallback();
    }
  }

  async function fetchOpportunityRankings() {
    opportunityLoading.value = true;
    try {
      const data = await dedupedFetch("feature:rankings", async () => {
        const res = await api.get("/feature/product-rankings");
        return res.data?.rankings || null;
      });
      if (data) opportunityRankings.value = data;
    } catch {} finally {
      opportunityLoading.value = false;
    }
  }

  async function fetchAlertEvents() {
    alertLoading.value = true;
    try {
      const data = await dedupedFetch("alert:events", async () => {
        const res = await api.get("/alert-rules/events/all", { params: { limit: 10 } });
        return res.data?.code === 0 ? res.data.data : null;
      });
      if (data) alertEvents.value = data;
    } catch {} finally {
      alertLoading.value = false;
    }
  }

  async function acknowledgeAlert(eventId: string) {
    try {
      await api.post(`/alert-rules/events/${eventId}/acknowledge`);
      invalidateCache("alert:events");
      invalidateCache("dashboard:home");
      await fetchAlertEvents();
      await fetchBizStats();
    } catch {}
  }

  async function fetchCrowdInsights() {
    crowdLoading.value = true;
    try {
      const homeData = await dedupedFetch("dashboard:home", async () => {
        const res = await api.get("/dashboard/home");
        return res.data?.code === 0 ? res.data.data : null;
      });
      if (homeData) {
        if (homeData.category_heatmap) crowdHeatmap.value = homeData.category_heatmap;
        if (homeData.behavior_patterns) crowdPatterns.value = homeData.behavior_patterns;
        if (homeData.trend_timeseries) processTrendSeries(homeData.trend_timeseries);
      }
    } catch {} finally {
      crowdLoading.value = false;
    }
  }

  async function fetchRecommendations() {
    recLoading.value = true;
    try {
      const data = await dedupedFetch("ai:recommendations", async () => {
        const { data } = await api.get("/ai/recommendations", { params: { limit: 8 } });
        return data?.data?.items || data?.items || [];
      });
      recommendations.value = data || [];
    } catch {
      recommendations.value = [];
    } finally {
      recLoading.value = false;
    }
  }

  let refreshTimer: ReturnType<typeof setInterval> | null = null;

  function startAutoRefresh(interval = 30000) {
    productStore.fetchProducts();
    collectStore.setupListeners();
    collectStore.fetchStatus();
    schedulerStore.fetchState();
    permissionStore.fetchPermissions();
    fetchBizStats();
    fetchRecommendations();
    refreshTimer = setInterval(() => {
      invalidateCache();
      collectStore.fetchStatus();
      schedulerStore.fetchState();
      fetchBizStats();
    }, interval);
  }

  function stopAutoRefresh() {
    if (refreshTimer) clearInterval(refreshTimer);
  }

  return {
    bizStats,
    opportunityRankings,
    opportunityLoading,
    fetchOpportunityRankings,
    alertEvents,
    alertLoading,
    fetchAlertEvents,
    acknowledgeAlert,
    crowdHeatmap,
    crowdPatterns,
    crowdLoading,
    crowdTrendSeries,
    fetchCrowdInsights,
    recommendations,
    recLoading,
    fetchRecommendations,
    fetchBizStats,
    startAutoRefresh,
    stopAutoRefresh,
  };
}
