import { ref, computed, onMounted, onUnmounted, nextTick } from "vue";
import * as echarts from "echarts";
import { ElMessage } from "element-plus";
import api, { isNetworkError } from "../utils/api";
import type { SchedulerTask } from "../components/TaskItem.vue";

export function useSchedulerData() {
  const cloudTasks = ref<SchedulerTask[]>([]);
  const tasksLoading = ref(false);
  const cloudAvailable = ref(true);
  const schedulerRunning = ref(false);
  const taskFilter = ref("all");
  const ganttChartRef = ref<HTMLElement>();
  let ganttChart: echarts.ECharts | null = null;
  let refreshTimer: ReturnType<typeof setInterval> | null = null;
  let unsubscribeWs: (() => void) | null = null;

  const runningCount = computed(() => cloudTasks.value.filter((t) => t.status === "running").length);
  const totalTaskCount = computed(() => cloudTasks.value.length);
  const completionRate = computed(() => {
    if (cloudTasks.value.length === 0) return "0%";
    const completed = cloudTasks.value.filter((t) => t.status === "completed").length;
    return `${Math.round((completed / cloudTasks.value.length) * 100)}%`;
  });

  async function fetchCloudTasks() {
    tasksLoading.value = true;
    try {
      const params: Record<string, any> = { page: 1, page_size: 50 };
      if (taskFilter.value !== "all") params.status = taskFilter.value;
      const { data } = await api.get("/collect/tasks", { params });
      if (data?.code === 0 && data.data?.items) {
        cloudTasks.value = data.data.items;
        cloudAvailable.value = true;
        schedulerRunning.value = cloudTasks.value.some((t) => t.status === "running");
      }
    } catch (err) {
      if (isNetworkError(err)) {
        cloudAvailable.value = false;
        fetchLocalTasks();
      }
    } finally {
      tasksLoading.value = false;
    }
  }

  async function fetchLocalTasks() {
    try {
      if (!window.electronAPI) return;
      const result = await window.electronAPI.invoke("scheduler:timeline") as { tasks?: any[]; state?: { isRunning?: boolean } } | null;
      cloudTasks.value = (result?.tasks || []).map((t: any) => ({
        id: t.id,
        task_type: "product",
        platform: t.platform || "local",
        target_ids: [t.product_name],
        status: t.is_active ? "running" : "paused",
        progress: t.progress || 0,
        created_at: t.last_run_at || new Date().toISOString(),
      }));
      schedulerRunning.value = result?.state?.isRunning ?? false;
    } catch {}
  }

  async function toggleScheduler() {
    if (schedulerRunning.value) {
      try {
        const runningTasks = cloudTasks.value.filter((t) => t.status === "running");
        for (const task of runningTasks) {
          await api.post(`/collect/tasks/${task.id}/cancel`);
        }
        ElMessage.success("已停止所有运行中任务");
      } catch {
        ElMessage.error("停止失败");
      }
    } else {
      ElMessage.info("请通过新建采集来启动任务");
    }
    await fetchCloudTasks();
  }

  async function cancelTask(taskId: string) {
    try {
      await api.post(`/collect/tasks/${taskId}/cancel`);
      ElMessage.success("任务已取消");
      await fetchCloudTasks();
    } catch {
      ElMessage.error("取消失败");
    }
  }

  async function retryTask(taskId: string) {
    try {
      await api.post(`/collect/tasks/${taskId}/retry`);
      ElMessage.success("任务已重试");
      await fetchCloudTasks();
    } catch {
      ElMessage.error("重试失败");
    }
  }

  async function viewTaskDetail(taskId: string) {
    try {
      const { data } = await api.get(`/collect/tasks/${taskId}`);
      if (data?.code === 0 && data.data) {
        return data.data;
      }
    } catch {
      ElMessage.error("获取详情失败");
    }
    return null;
  }

  async function createTask(form: { platform: string; task_type: string }, targetIdsText: string) {
    if (!targetIdsText.trim()) {
      ElMessage.warning("请输入目标ID");
      return false;
    }
    const ids = targetIdsText.trim().split("\n").filter((l) => l.trim());
    try {
      await api.post("/collect/tasks", {
        platform: form.platform,
        task_type: form.task_type,
        target_type: form.task_type === "product" ? "product_id" : form.task_type === "shop" ? "shop_id" : "category_url",
        target_ids: ids,
      });
      ElMessage.success("采集任务已创建");
      await fetchCloudTasks();
      return true;
    } catch (err: any) {
      ElMessage.error(err?.response?.data?.message || "创建失败");
      return false;
    }
  }

  function renderGanttChart() {
    if (!ganttChartRef.value || cloudTasks.value.length === 0) return;
    if (!ganttChart) ganttChart = echarts.init(ganttChartRef.value);

    const now = Date.now();
    const activeTasks = cloudTasks.value.filter((t) => t.status === "running" || t.status === "pending");

    const taskTypeLabel = (type: string) => {
      const map: Record<string, string> = { product: "商品采集", shop: "店铺采集", category: "品类采集" };
      return map[type] || type;
    };
    const taskLabel = (task: SchedulerTask) => `${taskTypeLabel(task.task_type)} - ${task.platform}`;

    const data = activeTasks.map((task, i) => {
      const created = task.created_at ? new Date(task.created_at).getTime() : now;
      const completed = task.completed_at ? new Date(task.completed_at).getTime() : now + 3600000;
      const end = task.status === "running" ? Math.max(completed, now + 1800000) : completed;
      return {
        name: taskLabel(task).substring(0, 20),
        value: [i, created, end],
        itemStyle: {
          color: task.status === "running" ? "#4F46E5" : task.status === "pending" ? "#94A3B8" : "#10B981",
        },
      };
    });

    if (data.length === 0) {
      ganttChart.clear();
      return;
    }

    ganttChart.setOption({
      backgroundColor: "transparent",
      tooltip: {
        formatter(params: any) {
          const d = params.data;
          const start = new Date(d.value[1]);
          const end = new Date(d.value[2]);
          return `${d.name}<br/>开始: ${start.toLocaleTimeString()}<br/>预计: ${end.toLocaleTimeString()}`;
        },
      },
      grid: { top: 20, right: 20, bottom: 30, left: 140 },
      xAxis: { type: "time", axisLabel: { color: "#94A3B8", fontSize: 11 } },
      yAxis: {
        type: "category",
        data: data.map((d) => d.name),
        axisLabel: { color: "#94A3B8", fontSize: 11 },
      },
      series: [{
        type: "custom",
        renderItem(_params: any, api: any) {
          const categoryIndex = api.value(0);
          const start = api.coord([api.value(1), categoryIndex]);
          const end = api.coord([api.value(2), categoryIndex]);
          const height = 20;
          return {
            type: "rect",
            transition: ["shape"],
            shape: { x: start[0], y: start[1] - height / 2, width: Math.max(end[0] - start[0], 4), height },
            style: { fill: api.visual("color"), borderRadius: 4 },
          };
        },
        data,
        encode: { x: [1, 2], y: 0 },
      }],
    }, true);
  }

  function refreshAll() {
    fetchCloudTasks();
    renderGanttChart();
  }

  function startAutoRefresh() {
    fetchCloudTasks();
    refreshTimer = setInterval(fetchCloudTasks, 15000);

    try {
      if (window.electronAPI) {
        unsubscribeWs = window.electronAPI.on("ws:message", (data: unknown) => {
          const msg = data as { type: string; data: any };
          if (msg.type === "collect:progress" || msg.type === "collect:completed") {
            fetchCloudTasks();
          }
        });
      }
    } catch {}
  }

  function stopAutoRefresh() {
    if (refreshTimer) clearInterval(refreshTimer);
    if (unsubscribeWs) unsubscribeWs();
    if (ganttChart) ganttChart.dispose();
  }

  return {
    cloudTasks,
    tasksLoading,
    cloudAvailable,
    schedulerRunning,
    taskFilter,
    ganttChartRef,
    runningCount,
    totalTaskCount,
    completionRate,
    fetchCloudTasks,
    toggleScheduler,
    cancelTask,
    retryTask,
    viewTaskDetail,
    createTask,
    renderGanttChart,
    refreshAll,
    startAutoRefresh,
    stopAutoRefresh,
  };
}
