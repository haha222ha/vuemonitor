﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿<template>
  <div class="dashboard">
    <div class="dashboard-header">
      <div class="header-left">
        <h1 class="page-title">{{ t('nav.dashboard') }}</h1>
        <p class="page-subtitle">实时监控您的商品数据变化</p>
      </div>
      <div class="header-actions">
        <el-button class="btn-customize" @click="showCustomize = true">
          <el-icon><Setting /></el-icon>
          自定义看板
        </el-button>
      </div>
    </div>

    <div class="stats-grid" v-if="layoutCards.includes('stats')">
      <div class="stat-card stat-card-primary">
        <div class="stat-icon-wrapper">
          <el-icon class="stat-icon"><Monitor /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">{{ t('dashboard.monitoredProducts') }}</div>
          <div class="stat-value">{{ productStore.productCount }}</div>
          <div class="stat-trend">
            <el-icon><TrendCharts /></el-icon>
            <span>监控中</span>
          </div>
        </div>
      </div>

      <div class="stat-card stat-card-success">
        <div class="stat-icon-wrapper">
          <el-icon class="stat-icon"><Download /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">{{ t('dashboard.activeCollect') }}</div>
          <div class="stat-value">{{ collectStore.status.activeCount }}</div>
          <div class="stat-trend">
            <el-icon><VideoPlay /></el-icon>
            <span>采集中</span>
          </div>
        </div>
      </div>

      <div class="stat-card stat-card-warning">
        <div class="stat-icon-wrapper">
          <el-icon class="stat-icon"><Clock /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">{{ t('dashboard.queueTasks') }}</div>
          <div class="stat-value">{{ collectStore.status.queueLength }}</div>
          <div class="stat-trend">
            <el-icon><Timer /></el-icon>
            <span>队列中</span>
          </div>
        </div>
      </div>

      <div class="stat-card stat-card-info">
        <div class="stat-icon-wrapper">
          <el-icon class="stat-icon"><Calendar /></el-icon>
        </div>
        <div class="stat-content">
          <div class="stat-label">{{ t('dashboard.scheduledTasks') }}</div>
          <div class="stat-value">{{ schedulerStore.state.activeTasks }}</div>
          <div class="stat-trend">
            <el-icon><Bell /></el-icon>
            <span>已调度</span>
          </div>
        </div>
      </div>
    </div>

    <div class="content-grid" v-if="layoutCards.includes('collect')">
      <div class="card collect-status-card">
        <div class="card-header">
          <div class="card-title-wrapper">
            <el-icon class="card-icon"><Cpu /></el-icon>
            <h3 class="card-title">{{ t('dashboard.collectStatus') }}</h3>
          </div>
          <el-tag 
            :type="collectStore.isCollecting ? 'success' : 'info'" 
            :class="['status-badge', { 'status-active': collectStore.isCollecting }]"
            effect="dark"
          >
            <el-icon v-if="collectStore.isCollecting" class="status-pulse"><Loading /></el-icon>
            {{ collectStore.isCollecting ? t('dashboard.collecting') : t('dashboard.idle') }}
          </el-tag>
        </div>
        <div class="card-body">
          <div class="info-row">
            <div class="info-label">
              <el-icon><Grid /></el-icon>
              {{ t('dashboard.concurrency') }}
            </div>
            <div class="info-value">
              <el-slider v-model="concurrency" :min="1" :max="10" class="concurrency-slider" @change="handleConcurrencyChange" />
              <span class="concurrency-value">{{ concurrency }}</span>
            </div>
          </div>
          <div class="info-row">
            <div class="info-label">
              <el-icon><Histogram /></el-icon>
              {{ t('dashboard.memoryUsage') }}
            </div>
            <div class="info-value">
              <div class="memory-bar">
                <div class="memory-fill" :style="{ width: `${Math.min((collectStore.status.resourceUsage.memoryMB / 1024) * 100, 100)}%` }"></div>
              </div>
              <span class="memory-text">{{ collectStore.status.resourceUsage.memoryMB }} MB</span>
            </div>
          </div>
          <div class="info-row">
            <div class="info-label">
              <el-icon><Trophy /></el-icon>
              {{ t('dashboard.currentPlan') }}
            </div>
            <div class="info-value">
              <el-tag class="plan-tag" effect="plain">{{ planLabels[permissionStore.plan] || permissionStore.plan }}</el-tag>
            </div>
          </div>
        </div>
      </div>

      <div class="card risk-alerts-card" v-if="layoutCards.includes('risk')">
        <div class="card-header">
          <div class="card-title-wrapper">
            <el-icon class="card-icon"><Warning /></el-icon>
            <h3 class="card-title">{{ t('dashboard.riskAlerts') }}</h3>
            <el-badge v-if="collectStore.riskAlerts.length > 0" :value="collectStore.riskAlerts.length" :max="99" class="risk-badge" />
          </div>
        </div>
        <div class="card-body">
          <div v-if="collectStore.riskAlerts.length === 0" class="empty-state">
            <el-icon class="empty-icon"><CircleCheck /></el-icon>
            <p class="empty-text">{{ t('dashboard.noRiskAlerts') }}</p>
          </div>
          <div v-else class="risk-list">
            <div v-for="alert in collectStore.riskAlerts.slice(0, 5)" :key="alert.taskId" class="risk-item">
              <div class="risk-item-header">
                <span class="risk-target">{{ alert.targetId }}</span>
                <el-tag type="danger" size="small" effect="light">风控</el-tag>
              </div>
              <p class="risk-error">{{ alert.error }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="card results-card" v-if="layoutCards.includes('results')">
      <div class="card-header">
        <div class="card-title-wrapper">
          <el-icon class="card-icon"><List /></el-icon>
          <h3 class="card-title">{{ t('dashboard.recentResults') }}</h3>
        </div>
        <el-button size="small" @click="collectStore.clearResults()" class="btn-clear">
          <el-icon><Delete /></el-icon>
          {{ t('common.clear') }}
        </el-button>
      </div>
      <div class="card-body">
        <el-table :data="collectStore.results.slice(0, 10)" class="modern-table" stripe>
          <el-table-column prop="targetId" :label="t('product.productId')" min-width="200">
            <template #default="{ row }">
              <div class="table-cell-primary">{{ row.targetId }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="status" :label="t('common.status')" width="140">
            <template #default="{ row }">
              <el-tag :type="statusTagType(row.status)" size="small" effect="light" class="status-tag">
                {{ statusLabels[row.status] || row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="collectedAt" :label="t('common.time')" width="180">
            <template #default="{ row }">
              <div class="table-cell-time">{{ formatDate(row.collectedAt) }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="error" :label="t('common.error')" min-width="200">
            <template #default="{ row }">
              <div class="table-cell-error" v-if="row.error">{{ row.error }}</div>
              <span v-else class="table-cell-success">✓</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <el-dialog 
      v-model="showCustomize" 
      title="自定义看板" 
      width="560px"
      class="customize-dialog"
      :close-on-click-modal="true"
      :close-on-press-escape="true"
      :show-close="true"
    >
      <div class="customize-content">
        <p class="customize-desc">选择要显示的卡片模块，拖拽调整顺序</p>
        <draggable v-model="editableCards" item-key="key" handle=".drag-handle" class="customize-list">
          <template #item="{ element }">
            <div class="customize-item">
              <el-icon class="drag-handle"><Rank /></el-icon>
              <el-checkbox v-model="element.visible" @change="saveLayout">{{ element.label }}</el-checkbox>
            </div>
          </template>
        </draggable>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="resetLayout">重置默认</el-button>
          <el-button type="primary" @click="showCustomize = false">完成</el-button>
        </div>
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
import { 
  Monitor, Download, Clock, Calendar, Cpu, Grid, Histogram, Trophy, 
  Warning, List, Delete, Setting, TrendCharts, VideoPlay, Timer, 
  Bell, Loading, CircleCheck, Rank 
} from "@element-plus/icons-vue";

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
];

const editableCards = ref([...ALL_CARDS]);

function loadLayout() {
  try {
    const saved = localStorage.getItem("dashboard-layout");
    if (saved) {
      const parsed = JSON.parse(saved);
      if (Array.isArray(parsed)) {
        editableCards.value = parsed;
      }
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

const layoutCards = computed(() => {
  return editableCards.value.filter((c) => c.visible).map((c) => c.key);
});

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

let refreshTimer: ReturnType<typeof setInterval> | null = null;

onMounted(() => {
  loadLayout();
  productStore.fetchProducts();
  collectStore.setupListeners();
  collectStore.fetchStatus();
  schedulerStore.fetchState();
  permissionStore.fetchPermissions();

  refreshTimer = setInterval(() => {
    collectStore.fetchStatus();
    schedulerStore.fetchState();
  }, 5000);
});

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer);
  }
});
</script>

<style scoped>
.dashboard {
  padding: 24px;
  background: #f5f7fa;
  min-height: 100vh;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
  gap: 16px;
}

.header-left {
  flex: 1;
}

.page-title {
  margin: 0 0 8px;
  font-size: 28px;
  font-weight: 700;
  color: #1a1a2e;
  letter-spacing: -0.5px;
}

.page-subtitle {
  margin: 0;
  font-size: 14px;
  color: #6b7280;
}

.btn-customize {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  border-radius: 10px;
  font-weight: 500;
  background: #fff;
  border: 1px solid #e5e7eb;
  color: #374151;
  transition: all 0.2s;
}

.btn-customize:hover {
  background: #f9fafb;
  border-color: #d1d5db;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.stat-card {
  background: #fff;
  border-radius: 16px;
  padding: 24px;
  display: flex;
  align-items: flex-start;
  gap: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  border: 1px solid #f3f4f6;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
}

.stat-icon-wrapper {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-card-primary .stat-icon-wrapper {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
}

.stat-card-success .stat-icon-wrapper {
  background: linear-gradient(135deg, #10b981, #34d399);
}

.stat-card-warning .stat-icon-wrapper {
  background: linear-gradient(135deg, #f59e0b, #fbbf24);
}

.stat-card-info .stat-icon-wrapper {
  background: linear-gradient(135deg, #3b82f6, #60a5fa);
}

.stat-icon {
  font-size: 24px;
  color: #fff;
}

.stat-content {
  flex: 1;
}

.stat-label {
  font-size: 13px;
  color: #6b7280;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: #1a1a2e;
  line-height: 1;
  margin-bottom: 8px;
}

.stat-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #9ca3af;
}

.stat-trend .el-icon {
  font-size: 14px;
}

.content-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.card {
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  border: 1px solid #f3f4f6;
  overflow: hidden;
}

.card-header {
  padding: 20px 24px;
  border-bottom: 1px solid #f3f4f6;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
}

.card-icon {
  font-size: 20px;
  color: #6366f1;
}

.card-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
}

.card-body {
  padding: 20px 24px;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 8px;
}

.status-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
  border-bottom: 1px solid #f3f4f6;
}

.info-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.info-row:first-child {
  padding-top: 0;
}

.info-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #6b7280;
}

.info-label .el-icon {
  font-size: 16px;
  color: #9ca3af;
}

.info-value {
  display: flex;
  align-items: center;
  gap: 12px;
}

.concurrency-slider {
  width: 120px;
}

.concurrency-value {
  font-size: 16px;
  font-weight: 600;
  color: #6366f1;
  min-width: 24px;
  text-align: center;
}

.memory-bar {
  width: 100px;
  height: 6px;
  background: #f3f4f6;
  border-radius: 3px;
  overflow: hidden;
}

.memory-fill {
  height: 100%;
  background: linear-gradient(90deg, #10b981, #34d399);
  border-radius: 3px;
  transition: width 0.3s;
}

.memory-text {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  min-width: 60px;
}

.plan-tag {
  padding: 6px 12px;
  border-radius: 8px;
  font-weight: 500;
}

.risk-badge {
  margin-left: 8px;
}

.empty-state {
  text-align: center;
  padding: 32px 0;
}

.empty-icon {
  font-size: 48px;
  color: #10b981;
  margin-bottom: 12px;
}

.empty-text {
  margin: 0;
  font-size: 14px;
  color: #6b7280;
}

.risk-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.risk-item {
  padding: 12px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 10px;
  transition: all 0.2s;
}

.risk-item:hover {
  background: #fee2e2;
}

.risk-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.risk-target {
  font-size: 14px;
  font-weight: 500;
  color: #1a1a2e;
}

.risk-error {
  margin: 0;
  font-size: 13px;
  color: #991b1b;
  line-height: 1.5;
}

.btn-clear {
  display: flex;
  align-items: center;
  gap: 6px;
  border-radius: 8px;
}

.modern-table {
  border-radius: 8px;
}

.table-cell-primary {
  font-weight: 500;
  color: #1a1a2e;
}

.table-cell-time {
  color: #6b7280;
  font-size: 13px;
}

.table-cell-error {
  color: #dc2626;
  font-size: 13px;
}

.table-cell-success {
  color: #10b981;
  font-size: 16px;
}

.customize-dialog :deep(.el-dialog__header) {
  padding: 20px 24px;
  border-bottom: 1px solid #f3f4f6;
}

.customize-dialog :deep(.el-dialog__body) {
  padding: 24px;
}

.customize-dialog :deep(.el-dialog__footer) {
  padding: 16px 24px;
  border-top: 1px solid #f3f4f6;
}

.customize-content {
  padding: 8px 0;
}

.customize-desc {
  margin: 0 0 16px;
  font-size: 14px;
  color: #6b7280;
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
  background: #f9fafb;
  border: 1px solid #f3f4f6;
  border-radius: 10px;
  cursor: move;
  transition: all 0.2s;
}

.customize-item:hover {
  background: #f3f4f6;
  border-color: #e5e7eb;
}

.drag-handle {
  cursor: grab;
  color: #9ca3af;
  font-size: 16px;
}

.drag-handle:active {
  cursor: grabbing;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .content-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .dashboard {
    padding: 16px;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .dashboard-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .page-title {
    font-size: 24px;
  }
}
</style>
