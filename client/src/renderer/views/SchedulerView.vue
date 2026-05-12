<template>
  <div class="scheduler-page">
    <div class="page-header">
      <h2>采集调度</h2>
      <div style="display: flex; gap: 8px">
        <el-button :type="schedulerState.isRunning ? 'danger' : 'success'" @click="toggleScheduler">
          {{ schedulerState.isRunning ? '停止调度' : '启动调度' }}
        </el-button>
        <el-button @click="refreshTimeline">刷新</el-button>
      </div>
    </div>

    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="活跃任务" :value="schedulerState.activeTasks" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="总任务数" :value="schedulerState.totalTasks" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="调度状态">
            <template #default>
              <el-tag :type="schedulerState.isRunning ? 'success' : 'info'">
                {{ schedulerState.isRunning ? '运行中' : '已停止' }}
              </el-tag>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="下次执行" :value="formatNextRun(schedulerState.nextRunAt)" />
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" style="margin-top: 20px">
      <template #header><span>任务时间线</span></template>
      <div class="timeline-container">
        <div v-for="task in timelineTasks" :key="task.id" class="timeline-item">
          <div class="timeline-left">
            <div class="timeline-dot" :class="`dot-${task.status}`" />
            <div class="timeline-line" />
          </div>
          <div class="timeline-content">
            <div class="task-header">
              <span class="task-name">{{ task.product_name }}</span>
              <el-tag size="small" :type="platformTagType(task.platform)">{{ task.platform }}</el-tag>
              <el-tag size="small" :type="statusTagType(task.status)">{{ statusLabels[task.status] }}</el-tag>
            </div>
            <div class="task-meta">
              <span>频率: 每{{ task.frequency_minutes }}分钟</span>
              <span v-if="task.last_run_at">上次: {{ formatTime(task.last_run_at) }}</span>
              <span v-if="task.next_run_at">下次: {{ formatTime(task.next_run_at) }}</span>
            </div>
            <el-progress
              v-if="task.is_active && task.progress > 0"
              :percentage="task.progress"
              :stroke-width="4"
              :show-text="false"
              :color="progressColor(task.status)"
              style="margin-top: 6px"
            />
            <div class="task-actions">
              <el-button size="small" text @click="toggleTask(task.id, !task.is_active)">
                {{ task.is_active ? '暂停' : '启用' }}
              </el-button>
              <el-button size="small" text type="danger" @click="removeTask(task.id)">删除</el-button>
            </div>
          </div>
        </div>
        <el-empty v-if="timelineTasks.length === 0" description="暂无调度任务" />
      </div>
    </el-card>

    <el-card shadow="never" style="margin-top: 20px">
      <template #header><span>甘特图</span></template>
      <div ref="ganttChartRef" class="chart-container"></div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from "vue";
import * as echarts from "echarts";

const schedulerState = ref({ isRunning: false, activeTasks: 0, totalTasks: 0, nextRunAt: null as string | null });
const timelineTasks = ref<any[]>([]);
const ganttChartRef = ref<HTMLElement>();
let ganttChart: echarts.ECharts | null = null;
let refreshTimer: ReturnType<typeof setInterval> | null = null;

const statusLabels: Record<string, string> = { scheduled: "已排期", due: "待执行", paused: "已暂停" };

function platformTagType(platform: string) {
  const map: Record<string, string> = { xhs: "danger", taobao: "warning", jd: "primary", pdd: "success" };
  return map[platform] || "info";
}

function statusTagType(status: string) {
  const map: Record<string, string> = { scheduled: "", due: "warning", paused: "info" };
  return map[status] || "";
}

function progressColor(status: string) {
  const map: Record<string, string> = { scheduled: "#6366f1", due: "#f59e0b", paused: "#909399" };
  return map[status] || "#6366f1";
}

function formatTime(dateStr: string | null) {
  if (!dateStr) return "-";
  const d = new Date(dateStr);
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function formatNextRun(dateStr: string | null) {
  if (!dateStr) return "无";
  const diff = new Date(dateStr).getTime() - Date.now();
  if (diff <= 0) return "即将执行";
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}分钟后`;
  return `${Math.floor(mins / 60)}小时${mins % 60}分钟后`;
}

async function refreshTimeline() {
  try {
    const result = await window.electronAPI.invoke("scheduler:timeline");
    timelineTasks.value = result?.tasks || [];
    schedulerState.value = result?.state || schedulerState.value;
    await nextTick();
    renderGanttChart();
  } catch {}
}

async function toggleScheduler() {
  try {
    if (schedulerState.value.isRunning) {
      await window.electronAPI.invoke("scheduler:stop");
    } else {
      await window.electronAPI.invoke("scheduler:start");
    }
    await refreshTimeline();
  } catch {}
}

async function toggleTask(taskId: string, active: boolean) {
  try {
    await window.electronAPI.invoke("scheduler:toggle-task", taskId, active);
    await refreshTimeline();
  } catch {}
}

async function removeTask(taskId: string) {
  try {
    await window.electronAPI.invoke("scheduler:remove-task", taskId);
    await refreshTimeline();
  } catch {}
}

function renderGanttChart() {
  if (!ganttChartRef.value || timelineTasks.value.length === 0) return;
  if (!ganttChart) ganttChart = echarts.init(ganttChartRef.value);

  const now = Date.now();
  const data = timelineTasks.value
    .filter((t) => t.is_active && t.next_run_at)
    .map((task, i) => {
      const nextRun = new Date(task.next_run_at).getTime();
      const freqMs = task.frequency_minutes * 60000;
      const start = Math.max(now, nextRun - freqMs);
      return {
        name: task.product_name?.substring(0, 15) || `任务${i + 1}`,
        value: [i, start, nextRun],
        itemStyle: { color: task.status === "due" ? "#f59e0b" : "#6366f1" },
      };
    });

  ganttChart.setOption({
    backgroundColor: "transparent",
    tooltip: {
      formatter(params: any) {
        const d = params.data;
        const start = new Date(d.value[1]);
        const end = new Date(d.value[2]);
        return `${d.name}<br/>开始: ${start.toLocaleTimeString()}<br/>结束: ${end.toLocaleTimeString()}`;
      },
    },
    grid: { top: 20, right: 20, bottom: 30, left: 120 },
    xAxis: { type: "time", axisLabel: { color: "#8a8a9a", fontSize: 11 } },
    yAxis: {
      type: "category",
      data: data.map((d) => d.name),
      axisLabel: { color: "#8a8a9a", fontSize: 11 },
    },
    series: [{ type: "custom", renderItem(_params: any, api: any) {
      const categoryIndex = api.value(0);
      const start = api.coord([api.value(1), categoryIndex]);
      const end = api.coord([api.value(2), categoryIndex]);
      const height = 20;
      return {
        type: "rect",
        transition: ["shape"],
        shape: { x: start[0], y: start[1] - height / 2, width: end[0] - start[0], height },
        style: { fill: api.visual("color") },
      };
    }, data, encode: { x: [1, 2], y: 0 } }],
  });
}

onMounted(() => {
  refreshTimeline();
  refreshTimer = setInterval(refreshTimeline, 10000);
});

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer);
  if (ganttChart) ganttChart.dispose();
});
</script>

<style scoped>
.scheduler-page { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-header h2 { margin: 0; font-size: 20px; }
.timeline-container { padding: 0 12px; }
.timeline-item { display: flex; gap: 12px; margin-bottom: 16px; }
.timeline-left { display: flex; flex-direction: column; align-items: center; width: 16px; }
.timeline-dot { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }
.dot-scheduled { background: #6366f1; }
.dot-due { background: #f59e0b; }
.dot-paused { background: #909399; }
.timeline-line { width: 2px; flex: 1; background: #ebeef5; margin-top: 4px; }
.timeline-content { flex: 1; padding-bottom: 8px; border-bottom: 1px solid #f5f5f5; }
.task-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.task-name { font-weight: 600; font-size: 14px; }
.task-meta { display: flex; gap: 16px; font-size: 12px; color: #909399; }
.task-actions { margin-top: 6px; display: flex; gap: 4px; }
.chart-container { height: 300px; }
</style>
