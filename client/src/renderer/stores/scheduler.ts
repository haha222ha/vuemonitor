import { defineStore } from "pinia";
import { ref, computed } from "vue";
import api from "../utils/api";

export interface ScheduledTask {
  id: string;
  product_id: string;
  platform: string;
  platform_product_id: string;
  product_name: string;
  frequency_minutes: number;
  is_active: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  created_at: string;
}

export interface SchedulerState {
  isRunning: boolean;
  activeTasks: number;
  totalTasks: number;
  nextRunAt: string | null;
}

export const useSchedulerStore = defineStore("scheduler", () => {
  const tasks = ref<ScheduledTask[]>([]);
  const state = ref<SchedulerState>({
    isRunning: false,
    activeTasks: 0,
    totalTasks: 0,
    nextRunAt: null,
  });
  const loading = ref(false);
  const error = ref<string | null>(null);

  const activeTasks = computed(() => tasks.value.filter((t) => t.is_active));
  const isRunning = computed(() => state.value.isRunning);

  async function fetchState() {
    try {
      if (window.electronAPI) {
        const result = await window.electronAPI.invoke("scheduler:state");
        state.value = result as SchedulerState;
      } else {
        const { data } = await api.get("/collect/tasks");
        if (data.code === 0 && data.data) {
          const items = data.data.items || data.data || [];
          state.value.totalTasks = items.length;
          state.value.activeTasks = items.filter((t: any) => t.status === "running" || t.is_active).length;
          state.value.isRunning = state.value.activeTasks > 0;
        }
      }
    } catch {}
  }

  async function fetchTasks() {
    loading.value = true;
    try {
      if (window.electronAPI) {
        const result = await window.electronAPI.invoke("scheduler:get-tasks");
        tasks.value = result as ScheduledTask[];
      } else {
        const { data } = await api.get("/collect/tasks");
        if (data.code === 0 && data.data) {
          tasks.value = data.data.items || data.data || [];
        }
      }
    } catch (err) {
      error.value = String(err);
    } finally {
      loading.value = false;
    }
  }

  async function start() {
    try {
      if (window.electronAPI) {
        const result = await window.electronAPI.invoke("scheduler:start");
        state.value = result as SchedulerState;
      }
    } catch (err) {
      error.value = String(err);
    }
  }

  async function stop() {
    try {
      if (window.electronAPI) {
        const result = await window.electronAPI.invoke("scheduler:stop");
        state.value = result as SchedulerState;
      }
    } catch (err) {
      error.value = String(err);
    }
  }

  async function addTask(task: Omit<ScheduledTask, "id" | "last_run_at" | "next_run_at" | "created_at">) {
    loading.value = true;
    try {
      if (window.electronAPI) {
        const result = await window.electronAPI.invoke("scheduler:add-task", task);
        tasks.value.push(result as ScheduledTask);
        state.value.totalTasks++;
        state.value.activeTasks++;
      }
    } catch (err) {
      error.value = String(err);
    } finally {
      loading.value = false;
    }
  }

  async function removeTask(taskId: string) {
    try {
      if (window.electronAPI) {
        await window.electronAPI.invoke("scheduler:remove-task", taskId);
      }
      const task = tasks.value.find((t) => t.id === taskId);
      tasks.value = tasks.value.filter((t) => t.id !== taskId);
      state.value.totalTasks--;
      if (task?.is_active) state.value.activeTasks--;
    } catch (err) {
      error.value = String(err);
    }
  }

  async function toggleTask(taskId: string, active: boolean) {
    try {
      if (window.electronAPI) {
        const result = await window.electronAPI.invoke("scheduler:toggle-task", taskId, active);
        const idx = tasks.value.findIndex((t) => t.id === taskId);
        if (idx !== -1 && result) {
          tasks.value[idx] = result as ScheduledTask;
        }
      }
      state.value.activeTasks = tasks.value.filter((t) => t.is_active).length;
    } catch (err) {
      error.value = String(err);
    }
  }

  async function updateFrequency(taskId: string, frequencyMinutes: number) {
    try {
      if (window.electronAPI) {
        const result = await window.electronAPI.invoke("scheduler:update-frequency", taskId, frequencyMinutes);
        const idx = tasks.value.findIndex((t) => t.id === taskId);
        if (idx !== -1 && result) {
          tasks.value[idx] = result as ScheduledTask;
        }
      }
    } catch (err) {
      error.value = String(err);
    }
  }

  return {
    tasks,
    state,
    loading,
    error,
    activeTasks,
    isRunning,
    fetchState,
    fetchTasks,
    start,
    stop,
    addTask,
    removeTask,
    toggleTask,
    updateFrequency,
  };
});
