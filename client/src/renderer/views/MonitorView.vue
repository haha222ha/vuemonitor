<template>
  <div class="monitor fade-in">
    <PageHeader title="告警中心" subtitle="设置商品异动监控，价格/销量/评分变化自动预警">
      <el-tag v-if="!cloudAvailable" type="warning" effect="dark" size="small" style="margin-right: 8px">离线模式</el-tag>
      <el-button @click="showTemplateDialog = true">从模板创建</el-button>
      <el-button type="primary" @click="openCreateDialog">新建规则</el-button>
    </PageHeader>

    <div class="monitor__stats" v-if="alertStats.total_rules > 0">
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
          <RuleCard v-for="rule in rules" :key="rule.id" :rule="rule" @toggle="toggleRule as any" @edit="openEditDialog as any" @delete="deleteRule" />
        </div>
      </el-tab-pane>

      <el-tab-pane name="events">
        <template #label>
          告警事件
          <el-badge v-if="alertStats.unacknowledged_events > 0" :value="alertStats.unacknowledged_events" :max="99" style="margin-left: 6px" />
        </template>
        <AlertEventList :events="events" :loading="eventsLoading" :severity-filter="eventSeverityFilter" @filter-change="handleEventFilterChange" @acknowledge="acknowledgeEvent" @batch-acknowledge="batchAcknowledge" />
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
import { Bell } from "@element-plus/icons-vue";
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
} = useAlertData();

const activeTab = ref("rules");
const showCreateDialog = ref(false);
const showTemplateDialog = ref(false);
const editingRule = ref<AlertRule | null>(null);
const selectedTemplate = ref<any | null>(null);

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
</style>
