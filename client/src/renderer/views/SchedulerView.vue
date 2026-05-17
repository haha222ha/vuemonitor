<template>
  <div class="scheduler fade-in">
    <PageHeader title="采集调度" subtitle="管理定时采集任务，实时追踪采集进度">
      <el-button type="primary" @click="showCreateDialog = true">新建采集</el-button>
      <el-button :type="schedulerRunning ? 'danger' : 'success'" @click="toggleScheduler">
        {{ schedulerRunning ? '停止调度' : '启动调度' }}
      </el-button>
      <el-button @click="refreshAll">刷新</el-button>
    </PageHeader>

    <div class="scheduler__stats">
      <StatCard :icon="Cpu" variant="primary" label="运行中" :value="runningCount" />
      <StatCard :icon="List" variant="info" label="总任务" :value="totalTaskCount" />
      <StatCard :icon="schedulerRunning ? VideoPlay : VideoPause" :variant="schedulerRunning ? 'success' : 'warning'" label="调度状态" :value="schedulerRunning ? '运行中' : '已停止'" />
      <StatCard :icon="Clock" variant="info" label="完成率" :value="completionRate" />
    </div>

    <div class="card">
      <div class="card__header">
        <div class="card__title-group">
          <el-icon class="card__icon" :size="20"><Timer /></el-icon>
          <h3 class="card__title">采集任务</h3>
        </div>
        <div class="card__actions">
          <el-radio-group v-model="taskFilter" size="small" @change="refreshAll">
            <el-radio-button value="all">全部</el-radio-button>
            <el-radio-button value="running">运行中</el-radio-button>
            <el-radio-button value="pending">待执行</el-radio-button>
            <el-radio-button value="completed">已完成</el-radio-button>
            <el-radio-button value="failed">失败</el-radio-button>
          </el-radio-group>
          <el-tag v-if="!cloudAvailable" type="warning" effect="light" size="small">本地模式</el-tag>
        </div>
      </div>

      <div v-if="cloudTasks.length > 0" class="scheduler__task-list">
        <TaskItem
          v-for="task in cloudTasks"
          :key="task.id"
          :task="task"
          @cancel="cancelTask"
          @retry="retryTask"
          @detail="openDetail"
        />
      </div>

      <EmptyState v-else-if="!tasksLoading" :icon="Timer" title="暂无采集任务" description="创建采集任务以自动监控商品数据" action-label="新建采集" :action-icon="Plus" @action="showCreateDialog = true" />
    </div>

    <div class="card" style="margin-top: 20px">
      <div class="card__header">
        <div class="card__title-group">
          <el-icon class="card__icon" :size="20"><TrendCharts /></el-icon>
          <h3 class="card__title">调度时间线</h3>
        </div>
      </div>
      <div ref="ganttChartRef" class="scheduler__chart"></div>
    </div>

    <el-dialog v-model="showCreateDialog" title="新建采集任务" width="520px" class="modern-dialog">
      <el-form :model="createForm" label-width="80px" :rules="createRules" ref="createFormRef">
        <el-form-item label="平台" prop="platform">
          <el-select v-model="createForm.platform" style="width: 100%">
            <el-option label="小红书" value="xhs" />
            <el-option label="淘宝" value="taobao" />
            <el-option label="京东" value="jd" />
            <el-option label="拼多多" value="pdd" />
            <el-option label="抖音" value="douyin" />
          </el-select>
        </el-form-item>
        <el-form-item label="类型" prop="task_type">
          <el-select v-model="createForm.task_type" style="width: 100%">
            <el-option label="商品采集" value="product" />
            <el-option label="店铺采集" value="shop" />
            <el-option label="品类采集" value="category" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标ID" prop="target_ids">
          <el-input v-model="targetIdsText" type="textarea" :rows="3" placeholder="输入目标ID，每行一个" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreateTask">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showDetailDialog" title="任务详情" width="600px" class="modern-dialog">
      <div v-if="currentDetail" class="task-detail">
        <div class="task-detail__row">
          <span class="task-detail__label">任务ID</span>
          <span class="task-detail__value">{{ currentDetail.id }}</span>
        </div>
        <div class="task-detail__row">
          <span class="task-detail__label">状态</span>
          <el-tag :type="statusTagType(currentDetail.status)">{{ statusLabel(currentDetail.status) }}</el-tag>
        </div>
        <div class="task-detail__row">
          <span class="task-detail__label">平台</span>
          <el-tag :type="platformTagType(currentDetail.platform)">{{ currentDetail.platform }}</el-tag>
        </div>
        <div class="task-detail__row">
          <span class="task-detail__label">类型</span>
          <span>{{ taskTypeLabel(currentDetail.task_type) }}</span>
        </div>
        <div class="task-detail__row" v-if="currentDetail.progress != null">
          <span class="task-detail__label">进度</span>
          <el-progress :percentage="currentDetail.progress" :stroke-width="8" style="flex: 1" />
        </div>
        <div class="task-detail__row" v-if="currentDetail.result_summary">
          <span class="task-detail__label">结果</span>
          <span>{{ currentDetail.result_summary }}</span>
        </div>
        <div class="task-detail__row" v-if="currentDetail.error_message">
          <span class="task-detail__label">错误</span>
          <span class="task-detail__error">{{ currentDetail.error_message }}</span>
        </div>
        <div v-if="currentDetail.items?.length" class="task-detail__items">
          <h4>子任务</h4>
          <div v-for="item in currentDetail.items" :key="item.id" class="task-detail__item">
            <span>{{ item.target_id }}</span>
            <el-tag size="small" :type="item.status === 'completed' ? 'success' : item.status === 'failed' ? 'danger' : 'info'">{{ item.status }}</el-tag>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import PageHeader from "../components/PageHeader.vue";
import StatCard from "../components/StatCard.vue";
import EmptyState from "../components/EmptyState.vue";
import TaskItem from "../components/TaskItem.vue";
import { useSchedulerData } from "../composables/useSchedulerData";
import { Cpu, List, Clock, Timer, TrendCharts, VideoPlay, VideoPause, Plus } from "@element-plus/icons-vue";

const {
  cloudTasks, tasksLoading, cloudAvailable, schedulerRunning, taskFilter, ganttChartRef,
  runningCount, totalTaskCount, completionRate,
  toggleScheduler, cancelTask, retryTask, viewTaskDetail, createTask,
  refreshAll, startAutoRefresh, stopAutoRefresh,
} = useSchedulerData();

const showCreateDialog = ref(false);
const creating = ref(false);
const createForm = ref({ platform: "xhs", task_type: "product" });
const targetIdsText = ref("");
const createFormRef = ref();
const createRules = {
  platform: [{ required: true, message: "请选择平台" }],
  task_type: [{ required: true, message: "请选择类型" }],
};

const showDetailDialog = ref(false);
const currentDetail = ref<any>(null);

function statusTagType(status: string) {
  const map: Record<string, string> = { pending: "info", running: "", completed: "success", failed: "danger", cancelled: "warning" };
  return map[status] || "info";
}

function statusLabel(status: string) {
  const map: Record<string, string> = { pending: "待执行", running: "运行中", completed: "已完成", failed: "失败", cancelled: "已取消" };
  return map[status] || status;
}

function platformTagType(platform: string) {
  const map: Record<string, string> = { xhs: "danger", taobao: "warning", jd: "primary", pdd: "success", douyin: "" };
  return map[platform] || "info";
}

function taskTypeLabel(type: string) {
  const map: Record<string, string> = { product: "商品采集", shop: "店铺采集", category: "品类采集" };
  return map[type] || type;
}

async function openDetail(taskId: string) {
  const detail = await viewTaskDetail(taskId);
  if (detail) {
    currentDetail.value = detail;
    showDetailDialog.value = true;
  }
}

async function handleCreateTask() {
  creating.value = true;
  try {
    const ok = await createTask(createForm.value, targetIdsText.value);
    if (ok) {
      showCreateDialog.value = false;
      targetIdsText.value = "";
    }
  } finally {
    creating.value = false;
  }
}

onMounted(() => { startAutoRefresh(); });
onUnmounted(() => { stopAutoRefresh(); });
</script>

<style scoped>
.scheduler {
  padding: 0;
}

.scheduler__stats {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.scheduler__task-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0 4px;
}

.scheduler__chart {
  height: 300px;
}

.task-detail {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.task-detail__row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.task-detail__label {
  font-size: var(--text-sm);
  color: var(--color-text-tertiary);
  width: 60px;
  flex-shrink: 0;
}

.task-detail__value {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  font-family: monospace;
}

.task-detail__error {
  color: #EF4444;
}

.task-detail__items {
  margin-top: 8px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border-light);
}

.task-detail__items h4 {
  font-size: var(--text-sm);
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--color-text-primary);
}

.task-detail__item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}

.modern-dialog :deep(.el-dialog__header) {
  padding: 20px 24px;
  border-bottom: 1px solid var(--color-border-light);
  margin-right: 0;
}

.modern-dialog :deep(.el-dialog__title) {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-text-primary);
}

.modern-dialog :deep(.el-dialog__body) {
  padding: 24px;
}

.modern-dialog :deep(.el-dialog__footer) {
  padding: 16px 24px;
  border-top: 1px solid var(--color-border-light);
}

@media (max-width: 768px) {
  .scheduler__stats {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
