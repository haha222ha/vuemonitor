<template>
  <div class="dashboard fade-in">
    <PageHeader title="数据盘面" subtitle="实时监控您的商品数据变化">
      <el-button @click="showCustomize = true" class="dashboard__customize-btn">
        <el-icon><Setting /></el-icon>
        自定义看板
      </el-button>
    </PageHeader>

    <div class="dashboard__stats" v-if="layoutCards.includes('stats')">
      <StatCard
        :icon="Monitor"
        variant="primary"
        :label="t('dashboard.monitoredProducts')"
        :value="productStore.productCount"
        trend="监控中"
        trend-type="neutral"
      />
      <StatCard
        :icon="Download"
        variant="success"
        :label="t('dashboard.activeCollect')"
        :value="collectStore.status.activeCount"
        trend="采集中"
        trend-type="up"
      />
      <StatCard
        :icon="Clock"
        variant="warning"
        :label="t('dashboard.queueTasks')"
        :value="collectStore.status.queueLength"
        trend="队列中"
        trend-type="neutral"
      />
      <StatCard
        :icon="Calendar"
        variant="info"
        :label="t('dashboard.scheduledTasks')"
        :value="schedulerStore.state.activeTasks"
        trend="已调度"
        trend-type="neutral"
      />
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
          <h3 class="card__title">群体洞察</h3>
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
import { ref, onMounted, onUnmounted, computed } from "vue";
import { useProductStore } from "../stores/product";
import { useCollectStore } from "../stores/collect";
import { useSchedulerStore } from "../stores/scheduler";
import { usePermissionStore } from "../stores/permission";
import { useI18n } from "../i18n";
import draggable from "vuedraggable";
import api from "../utils/api";
import {
  Monitor, Download, Clock, Calendar, Cpu, Grid, Histogram, Trophy,
  Warning, List, Delete, Setting, CircleCheck, Rank, TrendCharts, Refresh
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

const ALL_CARDS = [
  { key: "stats", label: "统计概览", visible: true },
  { key: "collect", label: "采集状态", visible: true },
  { key: "risk", label: "风控告警", visible: true },
  { key: "results", label: "最近结果", visible: true },
  { key: "crowd", label: "群体洞察", visible: true },
];

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

async function fetchCrowdInsights() {
  crowdLoading.value = true;
  try {
    const [heatmapRes, patternsRes] = await Promise.allSettled([
      api.get("/feature/crowd/category-heatmap"),
      api.get("/feature/crowd/behavior-patterns"),
    ]);
    if (heatmapRes.status === "fulfilled" && heatmapRes.value.data?.heatmap) {
      crowdHeatmap.value = heatmapRes.value.data.heatmap;
    }
    if (patternsRes.status === "fulfilled" && patternsRes.value.data) {
      crowdPatterns.value = patternsRes.value.data;
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
  fetchCrowdInsights();
  refreshTimer = setInterval(() => {
    collectStore.fetchStatus();
    schedulerStore.fetchState();
  }, 5000);
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
</style>
