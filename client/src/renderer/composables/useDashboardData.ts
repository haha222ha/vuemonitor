import { ref, reactive } from "vue";
import { useProductStore } from "../stores/product";
import { useCollectStore } from "../stores/collect";
import { useSchedulerStore } from "../stores/scheduler";
import { usePermissionStore } from "../stores/permission";
import api, { isNetworkError } from "../utils/api";
import type { OpportunityItem, AlertEvent, HeatmapItem, AIRecommendation, WeekOverWeek } from "@shared/types";

export interface WeekOverWeekMetric {
  this_week: number;
  last_week: number;
  change_pct: number | null;
}

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
  productCount: number;
  productCountTrend: string;
  productCountTrendType: "up" | "down" | "neutral";
  todayCollect: number;
  collectTrend: string;
  collectTrendType: "up" | "down" | "neutral";
  weekOverWeek: WeekOverWeek | null;
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
    productCount: 0,
    productCountTrend: "-",
    productCountTrendType: "neutral",
    todayCollect: 0,
    collectTrend: "-",
    collectTrendType: "neutral",
    weekOverWeek: null,
  });

  const opportunityRankings = ref<OpportunityItem[]>([]);
  const opportunityLoading = ref(false);
  const alertEvents = ref<AlertEvent[]>([]);
  const alertLoading = ref(false);
  const crowdHeatmap = ref<HeatmapItem[]>([]);
  const crowdPatterns = ref<Record<string, unknown> | null>(null);
  const crowdLoading = ref(false);
  const crowdTrendSeries = ref<TrendSeriesItem[]>([]);
  const recommendations = ref<AIRecommendation[]>([]);
  const recLoading = ref(false);

  function processTrendSeries(seriesMap: Record<string, any[]>) {
    const processed: TrendSeriesItem[] = [];
    for (const [category, points] of Object.entries(seriesMap)) {
      if (points.length < 2) continue;
      const salesValues = points.map((p: Record<string, unknown>) => Number(p.avg_sales || 0));
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
      const lastPoint = points[points.length - 1] as Record<string, unknown>;
      processed.push({
        category,
        sparklinePoints,
        sparklineWidth: w,
        latestGrowth: (lastPoint?.sales_growth_rate as number) ?? null,
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
    bizStats.productCount = productStore.productCount;
    bizStats.productCountTrend = "本地模式";
    bizStats.productCountTrendType = "neutral";
    bizStats.todayCollect = 0;
    bizStats.collectTrend = "本地模式";
    bizStats.collectTrendType = "neutral";
  }

  function applyHomeData(d: Record<string, unknown>) {
    const stats = d.biz_stats as Record<string, any>;
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
    bizStats.productCount = stats.product_count || 0;
    const pcc = stats.product_count_change;
    if (pcc != null) {
      const pv = Number(pcc);
      bizStats.productCountTrend = pv >= 0 ? `+${pv}%` : `${pv}%`;
      bizStats.productCountTrendType = pv > 0 ? "up" : pv < 0 ? "down" : "neutral";
    } else {
      bizStats.productCountTrend = `今日+${stats.today_new_products || 0}`;
      bizStats.productCountTrendType = "neutral";
    }
    bizStats.todayCollect = stats.today_collect || 0;
    const ccc = stats.collect_count_change;
    if (ccc != null) {
      const cv = Number(ccc);
      bizStats.collectTrend = cv >= 0 ? `+${cv}%` : `${cv}%`;
      bizStats.collectTrendType = cv > 0 ? "up" : cv < 0 ? "down" : "neutral";
    } else {
      bizStats.collectTrend = `今日${stats.today_collect || 0}次`;
      bizStats.collectTrendType = "neutral";
    }

    if (stats.week_over_week) {
      bizStats.weekOverWeek = {
        products: stats.week_over_week.products,
        collects: stats.week_over_week.collects,
        ai_analyses: stats.week_over_week.ai_analyses,
      } as WeekOverWeek;
    } else {
      bizStats.weekOverWeek = null;
    }

    if (d.rankings && Array.isArray(d.rankings)) opportunityRankings.value = d.rankings as OpportunityItem[];
    if (d.alert_events && Array.isArray(d.alert_events)) alertEvents.value = d.alert_events as AlertEvent[];
    if (d.category_heatmap && Array.isArray(d.category_heatmap)) crowdHeatmap.value = d.category_heatmap as HeatmapItem[];
    if (d.behavior_patterns) crowdPatterns.value = d.behavior_patterns as Record<string, unknown>;
    if (d.trend_timeseries && typeof d.trend_timeseries === "object" && Object.keys(d.trend_timeseries).length > 0) processTrendSeries(d.trend_timeseries as Record<string, TrendSeriesItem[]>);
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
    } catch (err) { console.warn("[Composable] operation failed:", err); } finally {
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
    } catch (err) { console.warn("[Composable] operation failed:", err); } finally {
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
    } catch (err) { console.warn("[Composable] operation failed:", err); }
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
    } catch (err) { console.warn("[Composable] operation failed:", err); } finally {
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
