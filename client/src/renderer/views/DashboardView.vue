<template>
  <div class="dashboard fade-in">
    <PageHeader title="机会雷达" subtitle="发现商机，洞察异动，把握趋势">
      <el-button @click="showCustomize = true" class="dashboard__customize-btn">
        <el-icon><Setting /></el-icon>
        自定义看板
      </el-button>
    </PageHeader>

    <div class="dashboard__stats" v-if="layoutCards.includes('stats')">
      <StatCard
        :icon="Opportunity"
        variant="amber"
        label="机会商品"
        :value="bizStats.opportunityCount"
        :trend="bizStats.opportunityTrend"
        :trend-type="bizStats.opportunityTrendType"
      />
      <StatCard
        :icon="TrendCharts"
        variant="primary"
        label="今日趋势"
        :value="bizStats.todayTrend"
        :trend="bizStats.todayTrendLabel"
        :trend-type="bizStats.todayTrendType"
      />
      <StatCard
        :icon="Warning"
        variant="danger"
        label="异动提醒"
        :value="bizStats.alertCount"
        :trend="bizStats.alertTrend"
        trend-type="neutral"
      />
      <StatCard
        :icon="MagicStick"
        variant="success"
        label="AI洞察"
        :value="bizStats.aiInsightCount"
        trend="今日分析"
        trend-type="up"
      />
    </div>

    <div class="dashboard__biz-grid" v-if="layoutCards.includes('opportunity')">
      <div class="card">
        <div class="card__header">
          <div class="card__title-group">
            <el-icon class="card__icon card__icon--amber" :size="20"><Opportunity /></el-icon>
            <h3 class="card__title">今日机会榜</h3>
            <el-tag v-if="opportunityRankings.length > 0" type="warning" size="small" effect="light">
              TOP {{ opportunityRankings.length }}
            </el-tag>
          </div>
          <el-button size="small" @click="fetchOpportunityRankings">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
        <div class="card__body">
          <div v-if="opportunityLoading" class="opportunity-loading">
            <el-skeleton :rows="4" animated />
          </div>
          <div v-else-if="opportunityRankings.length > 0" class="opportunity-list">
            <div
              v-for="(item, idx) in opportunityRankings.slice(0, 5)"
              :key="item.product_id || idx"
              class="opportunity-item"
            >
              <div class="opportunity-item__rank" :class="{ 'opportunity-item__rank--top': idx < 3 }">
                {{ idx + 1 }}
              </div>
              <div class="opportunity-item__info">
                <div class="opportunity-item__name">{{ item.product_name || item.product_id }}</div>
                <div class="opportunity-item__meta">
                  <span v-if="item.category">{{ item.category }}</span>
                  <span v-if="item.overall_score !== undefined" class="opportunity-item__score">
                    评分 {{ item.overall_score }}
                  </span>
                </div>
              </div>
              <div class="opportunity-item__trend">
                <el-tag
                  v-if="item.trend_short"
                  :type="item.trend_short === 'up' ? 'success' : item.trend_short === 'down' ? 'danger' : 'info'"
                  size="small"
                  effect="light"
                >
                  {{ trendLabel(item.trend_short) }}
                </el-tag>
                <el-tag
                  v-if="item.lifecycle_stage"
                  size="small"
                  effect="plain"
                >
                  {{ lifecycleLabel(item.lifecycle_stage) }}
                </el-tag>
              </div>
            </div>
          </div>
          <EmptyState
            v-else
            :icon="Opportunity"
            title="暂无排名数据"
            description="添加更多商品并采集数据后自动生成排名"
          />
        </div>
      </div>

      <div class="card">
        <div class="card__header">
          <div class="card__title-group">
            <el-icon class="card__icon card__icon--danger" :size="20"><Warning /></el-icon>
            <h3 class="card__title">异动监控</h3>
            <el-badge v-if="alertEvents.length > 0" :value="alertEvents.length" :max="99" />
          </div>
          <el-button size="small" @click="fetchAlertEvents">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
        <div class="card__body">
          <div v-if="alertLoading" class="opportunity-loading">
            <el-skeleton :rows="3" animated />
          </div>
          <div v-else-if="alertEvents.length > 0" class="alert-list">
            <div v-for="evt in alertEvents.slice(0, 5)" :key="evt.id" class="alert-item">
              <div class="alert-item__severity" :class="`alert-item__severity--${evt.severity}`" />
              <div class="alert-item__content">
                <div class="alert-item__title">{{ evt.title }}</div>
                <div class="alert-item__detail">{{ evt.detail }}</div>
                <div class="alert-item__time">{{ formatAlertTime(evt.created_at) }}</div>
              </div>
              <el-button
                v-if="!evt.is_acknowledged"
                size="small"
                text
                @click="acknowledgeAlert(evt.id)"
              >
                确认
              </el-button>
            </div>
          </div>
          <EmptyState
            v-else
            :icon="CircleCheck"
            title="一切正常"
            description="暂无异动，商品数据平稳"
          />
        </div>
      </div>
    </div>

    <div class="dashboard__grid" v-if="layoutCards.includes('collect')">
      <div class="card">
        <div class="card__header">
          <div class="card__title-group">
            <el-icon class="card__icon" :size="20"><Cpu /></el-icon>
            <h3 class="card__title">{{ t('dashboard.collectStatus') }}</h3>
          </div>
          <el-tag
            :type="collectStore.isCollecting ? 'success' : 'info'"
            :class="{ 'animate-pulse': collectStore.isCollecting }"
            effect="dark"
          >
            {{ collectStore.isCollecting ? t('dashboard.collecting') : t('dashboard.idle') }}
          </el-tag>
        </div>
        <div class="card__body">
          <div class="info-row">
            <div class="info-row__label">
              <el-icon :size="16"><Grid /></el-icon>
              {{ t('dashboard.concurrency') }}
            </div>
            <div class="info-row__value">
              <el-slider v-model="concurrency" :min="1" :max="10" class="info-row__slider" @change="handleConcurrencyChange" />
              <span class="info-row__number">{{ concurrency }}</span>
            </div>
          </div>
          <div class="info-row">
            <div class="info-row__label">
              <el-icon :size="16"><Histogram /></el-icon>
              {{ t('dashboard.memoryUsage') }}
            </div>
            <div class="info-row__value">
              <div class="memory-bar">
                <div class="memory-bar__fill" :style="{ width: `${Math.min((collectStore.status.resourceUsage.memoryMB / 1024) * 100, 100)}%` }" />
              </div>
              <span class="info-row__number">{{ collectStore.status.resourceUsage.memoryMB }} MB</span>
            </div>
          </div>
          <div class="info-row">
            <div class="info-row__label">
              <el-icon :size="16"><Trophy /></el-icon>
              {{ t('dashboard.currentPlan') }}
            </div>
            <div class="info-row__value">
              <el-tag effect="plain">{{ planLabels[permissionStore.plan] || permissionStore.plan }}</el-tag>
            </div>
          </div>
        </div>
      </div>

      <div class="card" v-if="layoutCards.includes('risk')">
        <div class="card__header">
          <div class="card__title-group">
            <el-icon class="card__icon" :size="20"><Warning /></el-icon>
            <h3 class="card__title">{{ t('dashboard.riskAlerts') }}</h3>
            <el-badge v-if="collectStore.riskAlerts.length > 0" :value="collectStore.riskAlerts.length" :max="99" />
          </div>
        </div>
        <div class="card__body">
          <EmptyState
            v-if="collectStore.riskAlerts.length === 0"
            :icon="CircleCheck"
            title="安全"
            description="当前无风控告警"
          />
          <div v-else class="risk-list">
            <div v-for="alert in collectStore.riskAlerts.slice(0, 5)" :key="alert.taskId" class="risk-item">
              <div class="risk-item__header">
                <span class="risk-item__target">{{ alert.targetId }}</span>
                <el-tag type="danger" size="small" effect="light">风控</el-tag>
              </div>
              <p class="risk-item__error">{{ alert.error }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="card" v-if="layoutCards.includes('results')">
      <div class="card__header">
        <div class="card__title-group">
          <el-icon class="card__icon" :size="20"><List /></el-icon>
          <h3 class="card__title">{{ t('dashboard.recentResults') }}</h3>
        </div>
        <el-button size="small" @click="collectStore.clearResults()">
          <el-icon><Delete /></el-icon>
          {{ t('common.clear') }}
        </el-button>
      </div>
      <div class="card__body">
        <el-table :data="collectStore.results.slice(0, 10)" stripe>
          <el-table-column prop="targetId" :label="t('product.productId')" min-width="200">
            <template #default="{ row }">
              <span class="cell-primary">{{ row.targetId }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="status" :label="t('common.status')" width="140">
            <template #default="{ row }">
              <el-tag :type="statusTagType[row.status]" size="small" effect="light">
                {{ statusLabels[row.status] || row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="collectedAt" :label="t('common.time')" width="180">
            <template #default="{ row }">
              <span class="cell-secondary">{{ formatDate(row.collectedAt) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="error" :label="t('common.error')" min-width="200">
            <template #default="{ row }">
              <span v-if="row.error" class="cell-danger">{{ row.error }}</span>
              <span v-else class="cell-success">✓</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <div class="card" v-if="layoutCards.includes('crowd')">
      <div class="card__header">
        <div class="card__title-group">
          <el-icon class="card__icon" :size="20"><TrendCharts /></el-icon>
          <h3 class="card__title">市场洞察</h3>
        </div>
        <el-button size="small" @click="fetchCrowdInsights">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
      <div class="card__body">
        <div v-if="crowdLoading" class="crowd-loading">
          <el-skeleton :rows="3" animated />
        </div>
        <div v-else-if="crowdHeatmap.length > 0" class="crowd-section">
          <h4 class="crowd-section__title">品类热度</h4>
          <div class="crowd-heatmap">
            <div v-for="item in crowdHeatmap.slice(0, 8)" :key="item.category" class="crowd-heatmap__item">
              <div class="crowd-heatmap__label">{{ item.category }}</div>
              <div class="crowd-heatmap__bar">
                <div
                  class="crowd-heatmap__fill"
                  :style="{ width: `${item.heat_score}%` }"
                  :class="item.heat_level"
                />
              </div>
              <div class="crowd-heatmap__score">
                <el-tag :type="item.heat_level === 'hot' ? 'danger' : item.heat_level === 'warm' ? 'warning' : 'info'" size="small" effect="light">
                  {{ item.heat_score }}
                </el-tag>
              </div>
            </div>
          </div>

          <div v-if="crowdPatterns" class="crowd-patterns">
            <div class="crowd-patterns__row" v-if="crowdPatterns.dominant_lifecycle">
              <span class="crowd-patterns__label">主流生命周期</span>
              <el-tag size="small" effect="light">{{ lifecycleLabel(crowdPatterns.dominant_lifecycle) }}</el-tag>
            </div>
            <div class="crowd-patterns__row" v-if="crowdPatterns.dominant_trend">
              <span class="crowd-patterns__label">主流趋势</span>
              <el-tag :type="crowdPatterns.dominant_trend === 'up' ? 'success' : crowdPatterns.dominant_trend === 'down' ? 'danger' : 'info'" size="small" effect="light">
                {{ trendLabel(crowdPatterns.dominant_trend) }}
              </el-tag>
            </div>
            <div class="crowd-patterns__row" v-if="crowdPatterns.best_seller_price_band">
              <span class="crowd-patterns__label">最佳价格带</span>
              <el-tag size="small" type="success" effect="light">{{ priceBandLabel(crowdPatterns.best_seller_price_band.band) }}</el-tag>
            </div>
          </div>

          <div v-if="crowdTrendSeries.length > 0" class="crowd-trends">
            <h4 class="crowd-section__title">市场趋势（近30天）</h4>
            <div class="trend-categories">
              <div
                v-for="cat in crowdTrendSeries.slice(0, 3)"
                :key="cat.category"
                class="trend-category"
              >
                <div class="trend-category__header">
                  <span class="trend-category__name">{{ cat.category }}</span>
                  <span
                    v-if="cat.latestGrowth !== null"
                    class="trend-category__growth"
                    :class="cat.latestGrowth > 0 ? 'trend-category__growth--up' : cat.latestGrowth < 0 ? 'trend-category__growth--down' : ''"
                  >
                    {{ cat.latestGrowth > 0 ? '+' : '' }}{{ (cat.latestGrowth * 100).toFixed(1) }}%
                  </span>
                </div>
                <div class="trend-category__sparkline">
                  <svg :viewBox="`0 0 ${cat.sparklineWidth} 32`" preserveAspectRatio="none" class="sparkline">
                    <polyline
                      :points="cat.sparklinePoints"
                      fill="none"
                      :stroke="cat.latestGrowth > 0 ? '#10B981' : cat.latestGrowth < 0 ? '#EF4444' : '#6366f1'"
                      stroke-width="1.5"
                      stroke-linejoin="round"
                    />
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="crowd-empty">
          <span class="cell-secondary">暂无群体数据，需连接云端服务</span>
        </div>
      </div>
    </div>

    <el-dialog v-model="showCustomize" title="自定义看板" width="560px">
      <p class="customize-desc">选择要显示的卡片模块，拖拽调整顺序</p>
      <draggable v-model="editableCards" item-key="key" handle=".drag-handle" class="customize-list">
        <template #item="{ element }">
          <div class="customize-item">
            <el-icon class="drag-handle"><Rank /></el-icon>
            <el-checkbox v-model="element.visible" @change="saveLayout">{{ element.label }}</el-checkbox>
          </div>
        </template>
      </draggable>
      <template #footer>
        <el-button @click="resetLayout">重置默认</el-button>
        <el-button type="primary" @click="showCustomize = false">完成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, computed } from "vue";
import { useProductStore } from "../stores/product";
import { useCollectStore } from "../stores/collect";
import { useSchedulerStore } from "../stores/scheduler";
import { usePermissionStore } from "../stores/permission";
import { useI18n } from "../i18n";
import draggable from "vuedraggable";
import api from "../utils/api";
import {
  Cpu, Grid, Histogram, Trophy,
  Warning, List, Delete, Setting, CircleCheck, Rank, TrendCharts, Refresh,
  Opportunity, MagicStick
} from "@element-plus/icons-vue";
import PageHeader from "../components/PageHeader.vue";
import StatCard from "../components/StatCard.vue";
import EmptyState from "../components/EmptyState.vue";

const { t } = useI18n();

const productStore = useProductStore();
const collectStore = useCollectStore();
const schedulerStore = useSchedulerStore();
const permissionStore = usePermissionStore();

const concurrency = ref(collectStore.status.concurrency);
const showCustomize = ref(false);

const bizStats = reactive({
  opportunityCount: 0,
  opportunityTrend: "加载中",
  opportunityTrendType: "neutral" as "up" | "down" | "neutral",
  todayTrend: "-",
  todayTrendLabel: "较昨日",
  todayTrendType: "neutral" as "up" | "down" | "neutral",
  alertCount: 0,
  alertTrend: "暂无异动",
  aiInsightCount: 0,
  cloudConnected: false,
});

async function fetchBizStats() {
  try {
    const homeRes = await api.get("/dashboard/home");
    if (homeRes.data?.code === 0 && homeRes.data.data) {
      const d = homeRes.data.data;
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

      if (d.rankings && d.rankings.length > 0) {
        opportunityRankings.value = d.rankings;
      }
      if (d.alert_events && d.alert_events.length > 0) {
        alertEvents.value = d.alert_events;
      }
    } else {
      applyLocalFallback();
    }
  } catch {
    applyLocalFallback();
  }
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

const ALL_CARDS = [
  { key: "stats", label: "统计概览", visible: true },
  { key: "opportunity", label: "机会榜与异动", visible: true },
  { key: "collect", label: "采集状态", visible: true },
  { key: "risk", label: "风控告警", visible: true },
  { key: "results", label: "最近结果", visible: true },
  { key: "crowd", label: "市场洞察", visible: true },
];

const opportunityRankings = ref<any[]>([]);
const opportunityLoading = ref(false);

async function fetchOpportunityRankings() {
  opportunityLoading.value = true;
  try {
    const res = await api.get("/feature/product-rankings");
    if (res.data?.rankings) {
      opportunityRankings.value = res.data.rankings;
    }
  } catch {} finally {
    opportunityLoading.value = false;
  }
}

const alertEvents = ref<any[]>([]);
const alertLoading = ref(false);

async function fetchAlertEvents() {
  alertLoading.value = true;
  try {
    const res = await api.get("/alert-rules/events/all", { params: { limit: 10 } });
    if (res.data?.code === 0 && Array.isArray(res.data.data)) {
      alertEvents.value = res.data.data;
    }
  } catch {} finally {
    alertLoading.value = false;
  }
}

async function acknowledgeAlert(eventId: string) {
  try {
    await api.post(`/alert-rules/events/${eventId}/acknowledge`);
    await fetchAlertEvents();
    await fetchBizStats();
  } catch {}
}

function formatAlertTime(dateStr: string | null): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "刚刚";
  if (diffMin < 60) return `${diffMin}分钟前`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}小时前`;
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")}`;
}

const editableCards = ref([...ALL_CARDS]);

function loadLayout() {
  try {
    const saved = localStorage.getItem("dashboard-layout");
    if (saved) {
      const parsed = JSON.parse(saved);
      if (Array.isArray(parsed)) editableCards.value = parsed;
    }
  } catch {}
}

function saveLayout() {
  localStorage.setItem("dashboard-layout", JSON.stringify(editableCards.value));
}

function resetLayout() {
  editableCards.value = ALL_CARDS.map((c) => ({ ...c, visible: true }));
  localStorage.removeItem("dashboard-layout");
}

const layoutCards = computed(() => editableCards.value.filter((c) => c.visible).map((c) => c.key));

const planLabels: Record<string, string> = { free: "免费版", pro: "专业版", premium: "高级版", enterprise: "企业版" };
const statusLabels: Record<string, string> = { success: "成功", failed: "失败", risk_detected: "风控" };
const statusTagType: Record<string, string> = { success: "success", failed: "danger", risk_detected: "warning" };

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")}`;
}

async function handleConcurrencyChange(val: number) {
  await collectStore.setConcurrency(val);
}

const crowdHeatmap = ref<any[]>([]);
const crowdPatterns = ref<any>(null);
const crowdLoading = ref(false);
const crowdTrendSeries = ref<any[]>([]);

async function fetchCrowdInsights() {
  crowdLoading.value = true;
  try {
    const [heatmapRes, patternsRes, trendRes] = await Promise.allSettled([
      api.get("/feature/crowd/category-heatmap"),
      api.get("/feature/crowd/behavior-patterns"),
      api.get("/feature/crowd/trend-timeseries", { params: { days: 30 } }),
    ]);
    if (heatmapRes.status === "fulfilled" && heatmapRes.value.data?.heatmap) {
      crowdHeatmap.value = heatmapRes.value.data.heatmap;
    }
    if (patternsRes.status === "fulfilled" && patternsRes.value.data) {
      crowdPatterns.value = patternsRes.value.data;
    }
    if (trendRes.status === "fulfilled" && trendRes.value.data?.series) {
      const seriesMap = trendRes.value.data.series;
      const processed: any[] = [];
      for (const [category, points] of Object.entries(seriesMap)) {
        const dataPoints = points as any[];
        if (dataPoints.length < 2) continue;
        const salesValues = dataPoints.map((p: any) => p.avg_sales || 0);
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
        const lastPoint = dataPoints[dataPoints.length - 1];
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
  } catch {} finally {
    crowdLoading.value = false;
  }
}

function lifecycleLabel(stage: string): string {
  const map: Record<string, string> = { new: "新品期", growth: "成长期", rising: "上升期", stable: "稳定期", declining: "衰退期", decline: "衰退期", mature: "成熟期" };
  return map[stage] || stage;
}

function trendLabel(trend: string): string {
  const map: Record<string, string> = { up: "上升", down: "下降", stable: "平稳", unknown: "未知" };
  return map[trend] || trend;
}

function priceBandLabel(band: string): string {
  const map: Record<string, string> = { under_50: "¥50以下", "50_100": "¥50-100", "100_200": "¥100-200", "200_500": "¥200-500", over_500: "¥500+" };
  return map[band] || band;
}

let refreshTimer: ReturnType<typeof setInterval> | null = null;

onMounted(() => {
  loadLayout();
  productStore.fetchProducts();
  collectStore.setupListeners();
  collectStore.fetchStatus();
  schedulerStore.fetchState();
  permissionStore.fetchPermissions();
  fetchBizStats();
  fetchCrowdInsights();
  refreshTimer = setInterval(() => {
    collectStore.fetchStatus();
    schedulerStore.fetchState();
    fetchBizStats();
  }, 30000);
});

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer);
});
</script>

<style scoped>
.dashboard {
  padding: 24px;
  min-height: 100%;
}

.dashboard__stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.dashboard__customize-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  border-radius: var(--radius-base);
}

.dashboard__grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.dashboard__biz-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.card__icon--amber {
  color: #F59E0B;
}

.card__icon--danger {
  color: #EF4444;
}

.opportunity-loading {
  padding: 16px 0;
}

.opportunity-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.opportunity-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--color-bg-page);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-base);
  transition: all 0.2s;
}

.opportunity-item:hover {
  background: var(--color-bg-hover);
  border-color: var(--color-border);
}

.opportunity-item__rank {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text-tertiary);
  background: var(--color-border-light);
  flex-shrink: 0;
}

.opportunity-item__rank--top {
  background: linear-gradient(135deg, #F59E0B, #D97706);
  color: #fff;
}

.opportunity-item__info {
  flex: 1;
  min-width: 0;
}

.opportunity-item__name {
  font-size: var(--text-base);
  font-weight: 500;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.opportunity-item__meta {
  display: flex;
  gap: 8px;
  margin-top: 4px;
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.opportunity-item__score {
  color: #F59E0B;
  font-weight: 600;
}

.opportunity-item__trend {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.alert-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.alert-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px;
  background: var(--color-bg-page);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-base);
  transition: all 0.2s;
}

.alert-item:hover {
  background: var(--color-bg-hover);
}

.alert-item__severity {
  width: 4px;
  height: 100%;
  min-height: 36px;
  border-radius: 2px;
  flex-shrink: 0;
}

.alert-item__severity--critical {
  background: #EF4444;
}

.alert-item__severity--warning {
  background: #F59E0B;
}

.alert-item__severity--info {
  background: #3B82F6;
}

.alert-item__content {
  flex: 1;
  min-width: 0;
}

.alert-item__title {
  font-size: var(--text-base);
  font-weight: 500;
  color: var(--color-text-primary);
}

.alert-item__detail {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  margin-top: 2px;
  line-height: 1.5;
}

.alert-item__time {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-top: 4px;
}

.card {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-border-light);
  overflow: hidden;
}

.card__header {
  padding: 20px 24px;
  border-bottom: 1px solid var(--color-border-light);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card__title-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.card__icon {
  color: var(--color-primary);
}

.card__title {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-text-primary);
}

.card__body {
  padding: 20px 24px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
  border-bottom: 1px solid var(--color-border-light);
}

.info-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.info-row:first-child {
  padding-top: 0;
}

.info-row__label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--text-base);
  color: var(--color-text-secondary);
}

.info-row__label .el-icon {
  color: var(--color-text-tertiary);
}

.info-row__value {
  display: flex;
  align-items: center;
  gap: 12px;
}

.info-row__slider {
  width: 120px;
}

.info-row__number {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-primary);
  min-width: 32px;
  text-align: center;
}

.memory-bar {
  width: 100px;
  height: 6px;
  background: var(--color-border-light);
  border-radius: 3px;
  overflow: hidden;
}

.memory-bar__fill {
  height: 100%;
  background: var(--gradient-success);
  border-radius: 3px;
  transition: width 0.3s;
}

.risk-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.risk-item {
  padding: 12px;
  background: var(--color-danger-bg);
  border: 1px solid #fecaca;
  border-radius: var(--radius-base);
  transition: background 0.2s;
}

.risk-item:hover {
  background: #fee2e2;
}

.risk-item__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.risk-item__target {
  font-size: var(--text-base);
  font-weight: 500;
  color: var(--color-text-primary);
}

.risk-item__error {
  margin: 0;
  font-size: var(--text-sm);
  color: #991b1b;
  line-height: 1.5;
}

.cell-primary {
  font-weight: 500;
  color: var(--color-text-primary);
}

.cell-secondary {
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.cell-danger {
  color: var(--color-danger);
  font-size: var(--text-sm);
}

.cell-success {
  color: var(--color-success);
  font-size: var(--text-lg);
}

.customize-desc {
  margin: 0 0 16px;
  font-size: var(--text-base);
  color: var(--color-text-secondary);
}

.customize-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.customize-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--color-bg-page);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-base);
  cursor: move;
  transition: all 0.2s;
}

.customize-item:hover {
  background: var(--color-bg-hover);
  border-color: var(--color-border);
}

.drag-handle {
  cursor: grab;
  color: var(--color-text-tertiary);
}

.drag-handle:active {
  cursor: grabbing;
}

@media (max-width: 1200px) {
  .dashboard__stats {
    grid-template-columns: repeat(2, 1fr);
  }
  .dashboard__grid {
    grid-template-columns: 1fr;
  }
  .dashboard__biz-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .dashboard {
    padding: 16px;
  }
  .dashboard__stats {
    grid-template-columns: 1fr;
  }
}

.crowd-loading {
  padding: 16px 0;
}

.crowd-section__title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin: 0 0 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.crowd-heatmap {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.crowd-heatmap__item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.crowd-heatmap__label {
  font-size: 12px;
  color: var(--color-text-primary);
  min-width: 80px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.crowd-heatmap__bar {
  flex: 1;
  height: 6px;
  border-radius: 3px;
  background: var(--color-bg-page);
  overflow: hidden;
}

.crowd-heatmap__fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.6s ease;
}

.crowd-heatmap__fill.hot {
  background: linear-gradient(90deg, #ef4444, #f97316);
}

.crowd-heatmap__fill.warm {
  background: linear-gradient(90deg, #f59e0b, #eab308);
}

.crowd-heatmap__fill.cold {
  background: linear-gradient(90deg, #6366f1, #818cf8);
}

.crowd-heatmap__score {
  min-width: 40px;
  text-align: right;
}

.crowd-patterns {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border-lighter);
}

.crowd-patterns__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.crowd-patterns__label {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.crowd-empty {
  padding: 24px 0;
  text-align: center;
}

.crowd-trends {
  padding-top: 16px;
  border-top: 1px solid var(--color-border-lighter);
}

.trend-categories {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.trend-category {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: var(--color-bg-page);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-base);
}

.trend-category__header {
  min-width: 100px;
  flex-shrink: 0;
}

.trend-category__name {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-primary);
  display: block;
}

.trend-category__growth {
  font-size: 12px;
  font-weight: 600;
  margin-top: 2px;
  display: block;
}

.trend-category__growth--up {
  color: #10B981;
}

.trend-category__growth--down {
  color: #EF4444;
}

.trend-category__sparkline {
  flex: 1;
  height: 32px;
}

.sparkline {
  width: 100%;
  height: 100%;
}
</style>
