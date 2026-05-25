<template>
  <div class="dashboard fade-in">
    <PageHeader title="工作台" subtitle="发现商机，洞察异动，把握趋势">
      <el-button class="dashboard__customize-btn" @click="showCustomize = true">
        <el-icon><Setting /></el-icon>
        自定义看板
      </el-button>
    </PageHeader>

    <QuickStartPanel
      v-if="layoutCards.includes('quickstart')"
      :show-add-product="() => showAddProduct = true"
      :show-ai-panel="() => $router.push('/ai')"
      :show-reports="() => $router.push('/notifications')"
    />

    <div v-if="layoutCards.includes('stats')" class="dashboard__stats">
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
        :icon="Goods"
        variant="info"
        label="监控商品"
        :value="bizStats.productCount"
        :trend="bizStats.productCountTrend"
        :trend-type="bizStats.productCountTrendType"
      />
      <StatCard
        :icon="DataLine"
        variant="warning"
        label="今日采集"
        :value="bizStats.todayCollect"
        :trend="bizStats.collectTrend"
        :trend-type="bizStats.collectTrendType"
      />
      <StatCard
        :icon="Warning"
        variant="danger"
        label="异动提醒"
        :value="bizStats.alertCount"
        :trend="bizStats.alertTrend"
        :trend-type="bizStats.alertCount > 0 ? 'up' : 'neutral'"
      />
      <StatCard
        :icon="MagicStick"
        variant="success"
        label="AI洞察"
        :value="bizStats.aiInsightCount"
        trend="今日分析"
        trend-type="neutral"
      />
    </div>

    <div v-if="layoutCards.includes('opportunity')" class="dashboard__biz-grid">
      <div class="card">
        <OpportunityCard
          :rankings="opportunityRankings"
          :loading="opportunityLoading"
          @refresh="fetchOpportunityRankings"
          @item-click="(item) => $router.push(`/products/${item.product_id}`)"
        />
      </div>

      <div class="card">
        <AlertEventCard
          :events="alertEvents"
          :loading="alertLoading"
          @refresh="fetchAlertEvents"
          @acknowledge="acknowledgeAlert"
        />
      </div>
    </div>

    <div v-if="layoutCards.includes('anomaly')" class="card">
      <div class="card__header">
        <div class="card__title-group">
          <el-icon class="card__icon" :size="20"><Warning /></el-icon>
          <h3 class="card__title">异常检测</h3>
        </div>
        <div class="card__actions">
          <el-select v-model="anomalyDays" size="small" style="width: 100px" @change="fetchAnomalies">
            <el-option :value="7" label="近7天" />
            <el-option :value="14" label="近14天" />
            <el-option :value="30" label="近30天" />
          </el-select>
          <el-button size="small" :loading="anomalyLoading" @click="fetchAnomalies">刷新</el-button>
        </div>
      </div>
      <div v-if="anomalySummary" class="anomaly-summary">
        <div class="anomaly-summary__item">
          <span class="anomaly-summary__value">{{ anomalySummary.total_anomalies }}</span>
          <span class="anomaly-summary__label">异常总数</span>
        </div>
        <div class="anomaly-summary__item anomaly-summary__item--price">
          <span class="anomaly-summary__value">{{ anomalySummary.price_anomalies }}</span>
          <span class="anomaly-summary__label">价格异常</span>
        </div>
        <div class="anomaly-summary__item anomaly-summary__item--sales">
          <span class="anomaly-summary__value">{{ anomalySummary.sales_anomalies }}</span>
          <span class="anomaly-summary__label">销量异常</span>
        </div>
        <div class="anomaly-summary__item">
          <span class="anomaly-summary__value">{{ anomalySummary.products_affected }}</span>
          <span class="anomaly-summary__label">涉及商品</span>
        </div>
      </div>
      <el-table v-if="anomalies.length > 0" :data="anomalies.slice(0, 10)" stripe size="small" style="margin-top: 12px">
        <el-table-column prop="product_name" label="商品" min-width="140">
          <template #default="{ row }">
            <span class="anomaly-product-name" @click="$router.push(`/products/${row.product_id}`)">{{ row.product_name || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.anomaly_type.startsWith('price') ? 'danger' : 'warning'" size="small" effect="light">
              {{ anomalyTypeLabel(row.anomaly_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="当前值" width="100">
          <template #default="{ row }">
            {{ row.metric === 'price' ? '¥' : '' }}{{ row.current_value }}
          </template>
        </el-table-column>
        <el-table-column label="均值" width="100">
          <template #default="{ row }">
            {{ row.metric === 'price' ? '¥' : '' }}{{ row.average_value }}
          </template>
        </el-table-column>
        <el-table-column prop="z_score" label="Z值" width="80" sortable>
          <template #default="{ row }">
            <span class="anomaly-zscore">{{ row.z_score }}</span>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else-if="!anomalyLoading" description="暂无异常数据" :image-size="60" />
    </div>

    <div v-if="layoutCards.includes('crowd')" class="card">
      <MarketInsightSection
        :heatmap="crowdHeatmap"
        :patterns="crowdPatterns"
        :trend-series="crowdTrendSeries"
        :loading="crowdLoading"
        @refresh="fetchCrowdInsights"
      />
    </div>

    <div v-if="layoutCards.includes('recommendations')" class="card">
      <AIRecommendationSection
        :recommendations="recommendations"
        :loading="recLoading"
        @refresh="fetchRecommendations"
        @item-click="handleRecClick"
      />
    </div>

    <el-dialog v-model="showAddProduct" title="添加商品" width="640px">
      <el-tabs v-model="addTab">
        <el-tab-pane label="粘贴链接" name="link">
          <el-input v-model="productUrl" placeholder="粘贴小红书商品链接..." size="large" />
          <el-button type="primary" size="large" style="margin-top: 12px; width: 100%" @click="addByLink">
            <el-icon><Plus /></el-icon> 添加商品
          </el-button>
        </el-tab-pane>
        <el-tab-pane label="搜索添加" name="search">
          <el-input v-model="searchKeyword" placeholder="搜索商品标题或店铺名称..." size="large" @keyup.enter="searchProduct">
            <template #append>
              <el-button type="primary" @click="searchProduct">搜索</el-button>
            </template>
          </el-input>
        </el-tab-pane>
      </el-tabs>
    </el-dialog>

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

    <OnboardingDialog :visible="showOnboarding" @close="showOnboarding = false" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import draggable from "vuedraggable";
import {
  Warning, Setting, Rank, TrendCharts,
  Opportunity, MagicStick, Plus, Goods, DataLine
} from "@element-plus/icons-vue";
import PageHeader from "../components/PageHeader.vue";
import StatCard from "../components/StatCard.vue";
import OpportunityCard from "../components/OpportunityCard.vue";
import AlertEventCard from "../components/AlertEventCard.vue";
import MarketInsightSection from "../components/MarketInsightSection.vue";
import AIRecommendationSection from "../components/AIRecommendationSection.vue";
import QuickStartPanel from "../components/QuickStartPanel.vue";
import OnboardingDialog from "../components/OnboardingDialog.vue";
import { useDashboardData } from "../composables/useDashboardData";
import api from "../utils/api";

const router = useRouter();

const {
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
  startAutoRefresh,
  stopAutoRefresh,
} = useDashboardData();

const anomalies = ref<any[]>([]);
const anomalySummary = ref<any>(null);
const anomalyLoading = ref(false);
const anomalyDays = ref(7);

async function fetchAnomalies() {
  anomalyLoading.value = true;
  try {
    const { data } = await api.get("/monitor/auto-detect", { params: { days: anomalyDays.value } });
    if (data) {
      anomalies.value = data.anomalies || [];
      anomalySummary.value = data.summary || null;
    }
  } catch { anomalies.value = []; anomalySummary.value = null; }
  anomalyLoading.value = false;
}

function anomalyTypeLabel(type: string): string {
  const map: Record<string, string> = {
    price_spike: "价格飙升",
    price_drop: "价格骤降",
    sales_surge: "销量激增",
    sales_drop: "销量骤降",
  };
  return map[type] || type;
}

const showCustomize = ref(false);
const showAddProduct = ref(false);
const showOnboarding = ref(false);
const addTab = ref("link");
const productUrl = ref("");
const searchKeyword = ref("");

const ALL_CARDS = [
  { key: "quickstart", label: "快速操作", visible: true },
  { key: "stats", label: "统计概览", visible: true },
  { key: "opportunity", label: "机会榜与异动", visible: true },
  { key: "anomaly", label: "异常检测", visible: true },
  { key: "crowd", label: "市场洞察", visible: true },
  { key: "recommendations", label: "AI智能推荐", visible: true },
];

const editableCards = ref([...ALL_CARDS]);

function loadLayout() {
  try {
    const saved = localStorage.getItem("dashboard-layout");
    if (saved) {
      const parsed = JSON.parse(saved);
      if (Array.isArray(parsed)) editableCards.value = parsed;
    }
  } catch (e) { console.warn("[Dashboard] load layout failed:", e); }
}

function saveLayout() {
  localStorage.setItem("dashboard-layout", JSON.stringify(editableCards.value));
}

function resetLayout() {
  editableCards.value = ALL_CARDS.map((c) => ({ ...c, visible: true }));
  localStorage.removeItem("dashboard-layout");
}

const layoutCards = computed(() => editableCards.value.filter((c) => c.visible).map((c) => c.key));

function handleRecClick(rec: any) {
  if (rec.type === "alert" && rec.event_id) {
    router.push("/notifications");
  } else if (rec.product_id) {
    router.push(`/products/${rec.product_id}`);
  } else if (rec.type === "category_insight" && rec.category) {
    router.push("/dashboard");
  }
}

function addByLink() {
  if (!productUrl.value) return;
  router.push({ path: "/products", query: { url: productUrl.value } });
  showAddProduct.value = false;
}

function searchProduct() {
  if (!searchKeyword.value) return;
  router.push({ path: "/discovery", query: { q: searchKeyword.value } });
  showAddProduct.value = false;
}

onMounted(() => {
  loadLayout();
  startAutoRefresh();
  fetchAnomalies();
});

onUnmounted(() => {
  stopAutoRefresh();
});
</script>

<style scoped>
.dashboard {
  padding: var(--space-xl);
  min-height: 100%;
}

.dashboard__stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-lg);
  margin-bottom: var(--space-xl);
}

.dashboard__customize-btn {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  border-radius: var(--radius-base);
}

.dashboard__biz-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-lg);
  margin-bottom: var(--space-xl);
}

.card {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-border-light);
  overflow: hidden;
  transition: box-shadow var(--duration-normal) var(--ease-out);
}

.card:hover {
  box-shadow: var(--shadow-md);
}

.customize-desc {
  margin: 0 0 var(--space-base);
  font-size: var(--text-base);
  color: var(--color-text-secondary);
}

.customize-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.customize-item {
  display: flex;
  align-items: center;
  gap: var(--space-base);
  padding: var(--space-base) var(--space-lg);
  background: var(--color-bg-page);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-base);
  cursor: move;
  transition: all var(--duration-fast) var(--ease-out);
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

.card__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.card__title-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card__icon {
  color: var(--color-primary);
}

.card__title {
  margin: 0;
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--color-text-primary);
}

.card__actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.anomaly-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.anomaly-summary__item {
  text-align: center;
  padding: 12px;
  background: var(--color-bg-page);
  border-radius: var(--radius-base);
}

.anomaly-summary__value {
  display: block;
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.anomaly-summary__label {
  display: block;
  font-size: 12px;
  color: var(--color-text-tertiary);
  margin-top: 4px;
}

.anomaly-summary__item--price .anomaly-summary__value {
  color: var(--color-danger);
}

.anomaly-summary__item--sales .anomaly-summary__value {
  color: var(--color-warning);
}

.anomaly-product-name {
  color: var(--color-primary);
  cursor: pointer;
  font-weight: 500;
}

.anomaly-product-name:hover {
  text-decoration: underline;
}

.anomaly-zscore {
  font-weight: 700;
  color: var(--color-danger);
}

@media (max-width: 1200px) {
  .dashboard__stats {
    grid-template-columns: repeat(2, 1fr);
  }
  .dashboard__biz-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .dashboard {
    padding: var(--space-base);
  }
  .dashboard__stats {
    grid-template-columns: 1fr;
  }
}
</style>
