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

    <div class="card" v-if="layoutCards.includes('crowd')">
      <MarketInsightSection
        :heatmap="crowdHeatmap"
        :patterns="crowdPatterns"
        :trend-series="crowdTrendSeries"
        :loading="crowdLoading"
        @refresh="fetchCrowdInsights"
      />
    </div>

    <div class="card" v-if="layoutCards.includes('recommendations')">
      <AIRecommendationSection
        :recommendations="recommendations"
        :loading="recLoading"
        @refresh="fetchRecommendations"
        @item-click="handleRecClick"
      />
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
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import draggable from "vuedraggable";
import {
  Warning, Setting, Rank, TrendCharts,
  Opportunity, MagicStick
} from "@element-plus/icons-vue";
import PageHeader from "../components/PageHeader.vue";
import StatCard from "../components/StatCard.vue";
import OpportunityCard from "../components/OpportunityCard.vue";
import AlertEventCard from "../components/AlertEventCard.vue";
import MarketInsightSection from "../components/MarketInsightSection.vue";
import AIRecommendationSection from "../components/AIRecommendationSection.vue";
import { useDashboardData } from "../composables/useDashboardData";

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

const showCustomize = ref(false);

const ALL_CARDS = [
  { key: "stats", label: "统计概览", visible: true },
  { key: "opportunity", label: "机会榜与异动", visible: true },
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

function handleRecClick(rec: any) {
  if (rec.type === "alert" && rec.event_id) {
    router.push("/notifications");
  } else if (rec.product_id) {
    router.push(`/products/${rec.product_id}`);
  } else if (rec.type === "category_insight" && rec.category) {
    router.push("/dashboard");
  }
}

onMounted(() => {
  loadLayout();
  startAutoRefresh();
});

onUnmounted(() => {
  stopAutoRefresh();
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

.dashboard__biz-grid {
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
  transition: box-shadow 0.3s;
}

.card:hover {
  box-shadow: var(--shadow-md);
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
</style>
