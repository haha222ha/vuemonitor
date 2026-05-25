<template>
  <div class="dashboard-home opportunity-radar">
    <div class="welcome-bar">
      <div class="welcome-text">
        <h2>{{ greeting }}，{{ auth.user?.nickname || auth.user?.email || '用户' }}</h2>
        <p>欢迎回到机会雷达</p>
      </div>
      <div class="welcome-actions">
        <el-tag :type="planTagType" effect="dark" size="large">{{ planLabel }}</el-tag>
        <el-button size="small" :icon="Refresh" circle @click="refreshAll" :loading="refreshing" />
      </div>
    </div>

    <OpportunityRadarStats
      :initial-stats="dashboardStats"
      :initial-opportunity-count="opportunityCount"
      :initial-alert-count="alertCount"
      @navigate="handleNavigate"
    />

    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="16">
        <OpportunityCard />

        <CategoryHeatmap style="margin-top: 20px;" />
      </el-col>

      <el-col :span="8">
        <AlertEventCard />

        <div class="panel quick-nav-panel" style="margin-top: 20px;">
          <div class="panel-header">
            <h3>快捷操作</h3>
          </div>
          <div class="quick-nav-grid">
            <div class="quick-nav-item" @click="$router.push('/dashboard/monitor')">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
              <span>商品监控</span>
            </div>
            <div class="quick-nav-item" @click="$router.push('/dashboard/collect')">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
              <span>数据采集</span>
            </div>
            <div class="quick-nav-item" @click="$router.push('/dashboard/ai')">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
              <span>AI分析</span>
            </div>
            <div class="quick-nav-item" @click="$router.push('/dashboard/settings')">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
              <span>设置</span>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../../stores/auth";
import api from "../../utils/api";
import { Refresh } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";

import OpportunityRadarStats from "@/components/OpportunityRadarStats.vue";
import OpportunityCard from "@/components/OpportunityCard.vue";
import AlertEventCard from "@/components/AlertEventCard.vue";
import CategoryHeatmap from "@/components/CategoryHeatmap.vue";
import "./dashboard-home.css";

const auth = useAuthStore();
const router = useRouter();

const stats = reactive({
  productCount: 0,
  activeProductCount: 0,
  todayTrend: "0%",
  trendUpCount: 0,
  trendDownCount: 0,
  aiRecommendations: 0,
  riskAlerts: 0,
  todayCollect: 0,
  activeTasks: 0,
  successRate: 0,
  todayAiCount: 0,
  productCountChange: null as number | null,
  collectCountChange: null as number | null,
  aiCountChange: null as number | null,
  riskCountChange: null as number | null,
  todayNewProducts: 0,
  yesterdayNewProducts: 0,
  todayCollectCount: 0,
  yesterdayCollect: 0,
});

const animatedStats = reactive({
  productCount: 0,
  aiRecommendations: 0,
  riskAlerts: 0,
});

const recentProducts = ref<any[]>([]);
const platformDist = ref<Record<string, number>>({});
const collectRunning = ref(false);
const activities = ref<any[]>([]);
const refreshing = ref(false);
const detecting = ref(false);
const anomalyResults = ref<any[]>([]);

const opportunityCount = ref(0);
const alertCount = ref(0);

const dashboardStats = computed(() => ({
  todayTrend: stats.todayTrend,
  trendUpCount: stats.trendUpCount,
  trendDownCount: stats.trendDownCount,
  todayAiCount: stats.todayAiCount,
}))

const trendData = reactive({
  dates: [] as string[],
  products: [] as number[],
  collects: [] as number[],
  aiAnalyses: [] as number[],
});

let refreshTimer: ReturnType<typeof setInterval> | null = null;

const greeting = computed(() => {
  const h = new Date().getHours();
  if (h < 6) return "夜深了";
  if (h < 12) return "早上好";
  if (h < 14) return "中午好";
  if (h < 18) return "下午好";
  return "晚上好";
});

const planLabel = computed(() => {
  const map: Record<string, string> = { free: "免费版", pro: "Pro", premium: "Premium", enterprise: "Enterprise" };
  return map[auth.userPlan] || "免费版";
});

const planTagType = computed(() => {
  const map: Record<string, 'primary' | 'success' | 'info' | 'warning' | 'danger'> = { pro: "primary", premium: "warning", enterprise: "danger" };
  return map[auth.userPlan] || "info";
});

const trendClass = computed(() => {
  if (stats.todayTrend.startsWith("+")) return "trend-up";
  if (stats.todayTrend.startsWith("-")) return "trend-down";
  return "";
});

const successRateClass = computed(() => {
  if (stats.successRate >= 80) return "value-good";
  if (stats.successRate >= 50) return "value-warn";
  return "value-bad";
});

const trendChartOption = computed(() => ({
  tooltip: {
    trigger: "axis",
    backgroundColor: "rgba(20,20,30,0.9)",
    borderColor: "rgba(255,255,255,0.1)",
    textStyle: { color: "#e0e0ea", fontSize: 12 },
  },
  grid: { left: 40, right: 20, top: 20, bottom: 30 },
  xAxis: {
    type: "category",
    data: trendData.dates.map((d) => d.slice(5)),
    axisLine: { lineStyle: { color: "rgba(255,255,255,0.08)" } },
    axisLabel: { color: "#6a6a7a", fontSize: 11 },
  },
  yAxis: {
    type: "value",
    splitLine: { lineStyle: { color: "rgba(255,255,255,0.04)" } },
    axisLabel: { color: "#6a6a7a", fontSize: 11 },
  },
  series: [
    {
      name: "新增商品",
      type: "line",
      data: trendData.products,
      smooth: true,
      symbol: "circle",
      symbolSize: 6,
      lineStyle: { color: "#6366f1", width: 2 },
      itemStyle: { color: "#6366f1" },
      areaStyle: { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: "rgba(99,102,241,0.25)" }, { offset: 1, color: "rgba(99,102,241,0)" }] } },
    },
    {
      name: "采集任务",
      type: "line",
      data: trendData.collects,
      smooth: true,
      symbol: "circle",
      symbolSize: 6,
      lineStyle: { color: "#22c55e", width: 2 },
      itemStyle: { color: "#22c55e" },
      areaStyle: { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: "rgba(34,197,94,0.2)" }, { offset: 1, color: "rgba(34,197,94,0)" }] } },
    },
    {
      name: "AI分析",
      type: "line",
      data: trendData.aiAnalyses,
      smooth: true,
      symbol: "circle",
      symbolSize: 6,
      lineStyle: { color: "#f59e0b", width: 2 },
      itemStyle: { color: "#f59e0b" },
      areaStyle: { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: "rgba(245,158,11,0.15)" }, { offset: 1, color: "rgba(245,158,11,0)" }] } },
    },
  ],
}));

function platformLabel(p: string) {
  const map: Record<string, string> = { xhs: "小红书", taobao: "淘宝", jd: "京东", pdd: "拼多多", douyin: "抖音" };
  return map[p] || p;
}

function platformTagType(p: string) {
  const map: Record<string, string> = { xhs: "danger", taobao: "warning", jd: "", pdd: "success", douyin: "" };
  return map[p] || "info";
}

function barWidth(count: number) {
  const max = Math.max(...Object.values(platformDist.value), 1);
  return `${Math.round((count / max) * 100)}%`;
}

function timeAgo(dateStr: string | null) {
  if (!dateStr) return "";
  const now = new Date();
  const d = new Date(dateStr);
  const diff = (now.getTime() - d.getTime()) / 1000;
  if (diff < 60) return "刚刚";
  if (diff < 3600) return Math.floor(diff / 60) + "分钟前";
  if (diff < 86400) return Math.floor(diff / 3600) + "小时前";
  return Math.floor(diff / 86400) + "天前";
}

function activityStatusType(status: string): 'primary' | 'success' | 'info' | 'warning' | 'danger' {
  const map: Record<string, 'primary' | 'success' | 'info' | 'warning' | 'danger'> = { completed: "success", running: "primary", pending: "warning", failed: "danger", cancelled: "info" };
  return map[status] || "info";
}

function activityStatusLabel(status: string) {
  const map: Record<string, string> = { completed: "完成", running: "运行中", pending: "等待", failed: "失败", cancelled: "已取消" };
  return map[status] || status;
}

function animateNumber(target: keyof typeof animatedStats, end: number, duration = 800) {
  const start = animatedStats[target];
  if (start === end) return;
  const startTime = performance.now();
  function tick(now: number) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    animatedStats[target] = Math.round(start + (end - start) * eased);
    if (progress < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

async function fetchStats() {
  try {
    const { data } = await api.get("/dashboard/stats");
    const d = data?.data || {};

    stats.productCount = d.product_count || 0;
    stats.activeProductCount = d.active_product_count || 0;
    stats.todayTrend = d.today_trend || "0%";
    stats.trendUpCount = d.trend_up_count || 0;
    stats.trendDownCount = d.trend_down_count || 0;
    stats.aiRecommendations = d.ai_recommendations || 0;
    stats.riskAlerts = d.risk_alerts || 0;
    stats.todayCollect = d.today_collect || 0;
    stats.activeTasks = d.active_tasks || 0;
    stats.successRate = d.success_rate || 0;
    stats.todayAiCount = d.today_ai_count || 0;
    collectRunning.value = d.collect_running || false;

    stats.productCountChange = d.product_count_change ?? null;
    stats.collectCountChange = d.collect_count_change ?? null;
    stats.aiCountChange = d.ai_count_change ?? null;
    stats.riskCountChange = d.risk_count_change ?? null;
    stats.todayNewProducts = d.today_new_products || 0;
    stats.yesterdayNewProducts = d.yesterday_new_products || 0;
    stats.todayCollectCount = d.today_collect || 0;
    stats.yesterdayCollect = d.yesterday_collect || 0;

    recentProducts.value = d.recent_products || [];
    platformDist.value = d.platform_distribution || {};

    animateNumber("productCount", stats.productCount);
    animateNumber("aiRecommendations", stats.aiRecommendations);
    animateNumber("riskAlerts", stats.riskAlerts);
  } catch {}
}

async function fetchOpportunityCount() {
  try {
    const res = await api.get('/feature/product-rankings')
    const rankings = res.data?.items || []
    const topPercent = Math.ceil(rankings.length * 0.3)
    opportunityCount.value = topPercent
  } catch {
    opportunityCount.value = 0
  }
}

async function fetchAlertCount() {
  try {
    const res = await api.get('/alert-rules/events/all')
    const events = res.data?.events || res.data?.items || []
    alertCount.value = events.filter((e: any) => !e.is_acknowledged).length
  } catch {
    alertCount.value = 0
  }
}

async function fetchTrend() {
  try {
    const { data } = await api.get("/dashboard/trend", { params: { days: 7 } });
    const d = data?.data || {};
    trendData.dates = d.dates || [];
    trendData.products = d.products || [];
    trendData.collects = d.collects || [];
    trendData.aiAnalyses = d.ai_analyses || [];
  } catch {}
}

async function fetchActivities() {
  try {
    const { data } = await api.get("/dashboard/activities", { params: { limit: 8 } });
    activities.value = data?.data?.items || [];
  } catch {}
}

async function refreshAll() {
  refreshing.value = true;
  await Promise.all([
    fetchStats(),
    fetchTrend(),
    fetchActivities(),
    fetchOpportunityCount(),
    fetchAlertCount()
  ]);
  refreshing.value = false;
}

function handleNavigate(type: string) {
  switch (type) {
    case 'opportunities':
      router.push('/dashboard/opportunities')
      break
    case 'trend':
      router.push('/dashboard/trend')
      break
    case 'alerts':
      router.push('/dashboard/alerts')
      break
    case 'ai':
      router.push('/dashboard/ai')
      break
    default:
      break
  }
}

async function runAnomalyDetect() {
  detecting.value = true;
  try {
    const { data } = await api.post("/alert-rules/auto-detect", null, {
      params: { metric: "sales_count", z_threshold: 2.0, days: 7 },
    });
    if (data?.code === 0) {
      anomalyResults.value = data.data.anomalies || [];
      if (anomalyResults.value.length === 0) {
        ElMessage.success("未检测到异常，所有商品数据正常");
      } else {
        ElMessage.warning(`检测到 ${anomalyResults.value.length} 项异常`);
      }
    }
  } catch {
    ElMessage.error("异常检测失败，请稍后重试");
  } finally {
    detecting.value = false;
  }
}

function goToProduct(productId: string) {
  router.push(`/dashboard/monitor/${productId}`);
}

onMounted(() => {
  refreshAll();
  refreshTimer = setInterval(() => {
    fetchStats();
    fetchActivities();
    fetchOpportunityCount();
    fetchAlertCount();
  }, 60000);
});

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
});
</script>
