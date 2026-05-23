<template>
  <div class="monitor fade-in">
    <PageHeader title="告警中心" subtitle="设置商品异动监控，价格/销量/评分变化自动预警">
      <el-tag v-if="!cloudAvailable" type="warning" effect="dark" size="small" style="margin-right: 8px">离线模式</el-tag>
      <el-button @click="showTemplateDialog = true">从模板创建</el-button>
      <el-button type="primary" @click="openCreateDialog">新建规则</el-button>
    </PageHeader>

    <div v-if="alertStats.total_rules > 0" class="monitor__stats">
      <div class="monitor__stat-card">
        <span class="monitor__stat-value">{{ alertStats.total_rules }}</span>
        <span class="monitor__stat-label">告警规则</span>
      </div>
      <div class="monitor__stat-card">
        <span class="monitor__stat-value monitor__stat-value--success">{{ alertStats.active_rules }}</span>
        <span class="monitor__stat-label">已启用</span>
      </div>
      <div class="monitor__stat-card">
        <span class="monitor__stat-value monitor__stat-value--danger">{{ alertStats.unacknowledged_events }}</span>
        <span class="monitor__stat-label">未确认事件</span>
      </div>
      <div class="monitor__stat-card">
        <span class="monitor__stat-value">{{ alertStats.total_events }}</span>
        <span class="monitor__stat-label">累计事件</span>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="monitor__tabs">
      <el-tab-pane label="告警规则" name="rules">
        <div v-if="rules.length === 0 && !loading" class="monitor__empty">
          <EmptyState :icon="Bell" title="暂无异动规则" description="创建异动规则，当商品价格、销量、评分等发生变化时自动预警" action-label="新建规则" :action-icon="Bell" @action="openCreateDialog" />
        </div>
        <div v-else class="monitor__grid">
          <RuleCard v-for="rule in rules" :key="rule.id" :rule="rule" @toggle="toggleRule" @edit="openEditDialog" @delete="deleteRule" />
        </div>
      </el-tab-pane>

      <el-tab-pane name="events">
        <template #label>
          告警事件
          <el-badge v-if="alertStats.unacknowledged_events > 0" :value="alertStats.unacknowledged_events" :max="99" style="margin-left: 6px" />
        </template>
        <AlertEventList :events="events" :loading="eventsLoading" :severity-filter="eventSeverityFilter" @filter-change="handleEventFilterChange" @acknowledge="acknowledgeEvent" @batch-acknowledge="batchAcknowledge" />
      </el-tab-pane>

      <el-tab-pane label="异常检测" name="anomaly">
        <div class="anomaly-toolbar">
          <div class="anomaly-toolbar__filters">
            <el-select v-model="autoDetectMetric" style="width: 140px" size="default">
              <el-option label="销量异常" value="sales_count" />
              <el-option label="价格异常" value="price" />
              <el-option label="评分异常" value="rating" />
            </el-select>
            <el-select v-model="autoDetectZThreshold" style="width: 120px" size="default">
              <el-option label="Z ≥ 2.0" :value="2.0" />
              <el-option label="Z ≥ 2.5" :value="2.5" />
              <el-option label="Z ≥ 3.0" :value="3.0" />
            </el-select>
            <el-select v-model="autoDetectDays" style="width: 100px" size="default">
              <el-option label="7天" :value="7" />
              <el-option label="14天" :value="14" />
              <el-option label="30天" :value="30" />
            </el-select>
          </div>
          <el-button type="primary" :loading="anomaliesLoading" @click="runAutoDetect(autoDetectMetric, autoDetectZThreshold, autoDetectDays)">
            开始检测
          </el-button>
        </div>

        <div v-if="anomalies.length > 0 && autoDetectResult" class="anomaly-summary">
          <span>共扫描 {{ autoDetectResult.total_scanned }} 个商品，发现 <strong>{{ autoDetectResult.anomaly_count }}</strong> 个异常</span>
        </div>

        <div v-if="anomaliesLoading" class="monitor__empty">
          <EmptyState :icon="Loading" title="正在分析..." description="基于 Z-score 统计方法自动检测异常商品" />
        </div>
        <div v-else-if="anomalies.length === 0 && autoDetectResult" class="monitor__empty">
          <EmptyState :icon="CircleCheck" title="未发现异常" description="当前指标范围内所有商品表现正常，可尝试调整阈值或扩大时间范围" />
        </div>
        <div v-else-if="anomalies.length > 0" class="anomaly-list">
          <div
            v-for="item in anomalies"
            :key="item.id"
            class="anomaly-card"
            :class="'anomaly-card--' + item.severity"
          >
            <div class="anomaly-card__header">
              <el-tag :type="item.severity === 'critical' ? 'danger' : 'warning'" size="small" effect="dark">
                {{ item.severity === 'critical' ? '严重' : '警告' }}
              </el-tag>
              <span class="anomaly-card__metric">{{ { price: '价格', sales_count: '销量', rating: '评分', review_count: '评论', favorite_count: '收藏' }[item.metric] || item.metric }}</span>
              <span class="anomaly-card__direction" :class="item.direction === 'up' ? 'up' : 'down'">
                {{ item.direction === 'up' ? '↑ 异常升高' : '↓ 异常下降' }}
              </span>
            </div>
            <div class="anomaly-card__title">{{ item.title }}</div>
            <div class="anomaly-card__detail">{{ item.detail }}</div>
            <div class="anomaly-card__stats">
              <div class="anomaly-card__stat">
                <span class="anomaly-card__stat-label">当前值</span>
                <span class="anomaly-card__stat-value">{{ formatAnomalyValue(item.latest_value, item.metric) }}</span>
              </div>
              <div class="anomaly-card__stat">
                <span class="anomaly-card__stat-label">历史均值</span>
                <span class="anomaly-card__stat-value">{{ formatAnomalyValue(item.mean, item.metric) }}</span>
              </div>
              <div class="anomaly-card__stat">
                <span class="anomaly-card__stat-label">Z-score</span>
                <span class="anomaly-card__stat-value anomaly-card__stat-value--zscore" :class="Math.abs(item.z_score) >= 3 ? '--critical' : ''">
                  {{ item.z_score >= 0 ? '+' : '' }}{{ item.z_score.toFixed(2) }}
                </span>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="monitor__empty">
          <EmptyState :icon="DataAnalysis" title="智能异常检测" description="无需手动创建规则，系统将基于统计方法（Z-score）自动识别异常波动的商品。选择指标和阈值后点击开始检测。" action-label="开始检测" :action-icon="DataAnalysis" @action="runAutoDetect()" />
        </div>
      </el-tab-pane>
    </el-tabs>

    <RuleFormDialog
      v-model="showCreateDialog"
      :products="products"
      :editing-rule="editingRule"
      :template="selectedTemplate"
      :submit-rule="submitRule"
      @close="editingRule = null"
    />

    <RuleTemplateDialog v-model="showTemplateDialog" @select="applyTemplate" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { Bell, CircleCheck, DataAnalysis, Loading } from "@element-plus/icons-vue";
import PageHeader from "../components/PageHeader.vue";
import EmptyState from "../components/EmptyState.vue";
import RuleCard from "../components/RuleCard.vue";
import AlertEventList from "../components/AlertEventList.vue";
import RuleFormDialog from "../components/monitor/RuleFormDialog.vue";
import RuleTemplateDialog from "../components/monitor/RuleTemplateDialog.vue";
import { useAlertData } from "../composables/useAlertData";
import type { AlertRule } from "../composables/useAlertData";

const {
  rules, products, loading, cloudAvailable,
  events, eventsLoading, eventSeverityFilter, alertStats,
  fetchRules, fetchAlertStats, fetchEvents,
  toggleRule, deleteRule, acknowledgeEvent, batchAcknowledge, submitRule,
  anomalies, anomaliesLoading, autoDetectResult, runAutoDetect,
} = useAlertData();

const activeTab = ref("rules");
const showCreateDialog = ref(false);
const showTemplateDialog = ref(false);
const editingRule = ref<AlertRule | null>(null);
const selectedTemplate = ref<any | null>(null);

const autoDetectMetric = ref("sales_count");
const autoDetectZThreshold = ref(2.0);
const autoDetectDays = ref(7);

function formatAnomalyValue(value: number, metric: string): string {
  if (metric === "price") return `¥${value.toFixed(2)}`;
  if (metric === "rating") return value.toFixed(1);
  if (value >= 10000) return `${(value / 10000).toFixed(1)}w`;
  return Math.round(value).toLocaleString();
}

function openCreateDialog() {
  editingRule.value = null;
  selectedTemplate.value = null;
  showCreateDialog.value = true;
}

function openEditDialog(rule: AlertRule) {
  editingRule.value = rule;
  selectedTemplate.value = null;
  showCreateDialog.value = true;
}

function applyTemplate(tpl: any) {
  editingRule.value = null;
  selectedTemplate.value = tpl;
  showTemplateDialog.value = false;
  showCreateDialog.value = true;
}

function handleEventFilterChange(value: string) {
  eventSeverityFilter.value = value;
  fetchEvents();
}

onMounted(() => {
  fetchRules();
  fetchAlertStats();
  fetchEvents();
});
</script>

<style scoped>
.monitor { padding: 0; }
.monitor__stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px; }
.monitor__stat-card { background: var(--color-bg-card); border: 1px solid var(--color-border-light); border-radius: var(--radius-lg); padding: 16px 20px; display: flex; flex-direction: column; gap: 4px; }
.monitor__stat-value { font-size: 28px; font-weight: 700; color: var(--color-text-primary); line-height: 1.2; }
.monitor__stat-value--success { color: var(--color-success, #10B981); }
.monitor__stat-value--danger { color: var(--color-danger, #EF4444); }
.monitor__stat-label { font-size: var(--text-xs); color: var(--color-text-tertiary); }
.monitor__tabs :deep(.el-tabs__header) { margin-bottom: 16px; }
.monitor__grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 16px; }

.anomaly-toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.anomaly-toolbar__filters { display: flex; gap: 8px; }
.anomaly-summary { padding: 10px 16px; background: var(--color-bg-card); border: 1px solid var(--color-border-light); border-radius: var(--radius-lg); margin-bottom: 16px; font-size: 14px; color: var(--color-text-secondary); }
.anomaly-summary strong { color: var(--color-danger, #EF4444); }
.anomaly-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 16px; }
.anomaly-card { background: var(--color-bg-card); border: 1px solid var(--color-border-light); border-radius: var(--radius-lg); padding: 16px; transition: border-color 0.2s; }
.anomaly-card:hover { border-color: var(--color-border); }
.anomaly-card--critical { border-left: 3px solid var(--color-danger, #EF4444); }
.anomaly-card--warning { border-left: 3px solid var(--color-warning, #F59E0B); }
.anomaly-card__header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.anomaly-card__metric { font-size: 13px; color: var(--color-text-secondary); }
.anomaly-card__direction { font-size: 13px; font-weight: 600; }
.anomaly-card__direction.up { color: var(--color-danger, #EF4444); }
.anomaly-card__direction.down { color: var(--color-success, #10B981); }
.anomaly-card__title { font-size: 15px; font-weight: 600; color: var(--color-text-primary); margin-bottom: 4px; }
.anomaly-card__detail { font-size: 13px; color: var(--color-text-tertiary); line-height: 1.5; margin-bottom: 12px; }
.anomaly-card__stats { display: flex; gap: 20px; padding-top: 12px; border-top: 1px solid var(--color-border-light); }
.anomaly-card__stat { display: flex; flex-direction: column; gap: 2px; }
.anomaly-card__stat-label { font-size: 11px; color: var(--color-text-tertiary); }
.anomaly-card__stat-value { font-size: 15px; font-weight: 600; color: var(--color-text-primary); }
.anomaly-card__stat-value--zscore { color: var(--color-warning, #F59E0B); }
.anomaly-card__stat-value--zscore.--critical { color: var(--color-danger, #EF4444); }
</style>
