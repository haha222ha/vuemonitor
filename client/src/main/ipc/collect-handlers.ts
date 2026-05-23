import { ipcMain } from "electron";
import { CollectTask } from "../collect/chromium-worker";
import { localScheduler, ScheduledTask } from "../collect/local-scheduler";
import { dataMart } from "../collect/data-mart";
import { PlaywrightTask } from "../collect/playwright-collector";
import {
  getWorker,
  getWorkerInitPromise,
  clearWorkerInitPromise,
  getConcurrencyCtrl,
  getPlaywrightCollector,
  wireSchedulerEvents,
  getChromiumWorkerInternal,
} from "./worker-registry";

export function registerCollectHandlers(): void {
  ipcMain.handle("collect:start", async (_event, tasks: CollectTask[]) => {
    const worker = getWorker();
    const initPromise = getWorkerInitPromise();
    if (initPromise) {
      await initPromise;
      clearWorkerInitPromise();
    }
    worker.enqueueBatch(tasks);
    return { queued: tasks.length, activeCount: worker.getActiveCount(), queueLength: worker.getQueueLength() };
  });

  ipcMain.handle("collect:cancel", async (_event, taskId: string) => {
    const worker = getWorker();
    const initPromise = getWorkerInitPromise();
    if (initPromise) { await initPromise; clearWorkerInitPromise(); }
    return worker.cancelTask(taskId);
  });

  ipcMain.handle("collect:clear-queue", async () => {
    const worker = getWorker();
    const initPromise = getWorkerInitPromise();
    if (initPromise) { await initPromise; clearWorkerInitPromise(); }
    return worker.clearQueue();
  });

  ipcMain.handle("collect:status", async () => {
    const worker = getWorker();
    const initPromise = getWorkerInitPromise();
    if (initPromise) { await initPromise; clearWorkerInitPromise(); }
    const ctrl = getConcurrencyCtrl();
    return {
      isRunning: worker.getActiveCount() > 0,
      activeCount: worker.getActiveCount(),
      queueLength: worker.getQueueLength(),
      concurrency: ctrl.getConcurrency(),
      resourceUsage: ctrl.getResourceUsage(),
      isPaused: worker.isQueuePaused(),
      riskStats: worker.getRiskStats(),
    };
  });

  ipcMain.handle("collect:resume-queue", async () => {
    const worker = getWorker();
    worker.resumeQueue();
    return { resumed: true };
  });

  ipcMain.handle("collect:pause-queue", async () => {
    const worker = getWorker();
    worker.pauseQueue();
    return { paused: true, pendingCount: worker.getQueueLength() };
  });

  ipcMain.handle("collect:cookie-health", async () => {
    const worker = getWorker();
    return worker.checkCookieHealth();
  });

  ipcMain.handle("collect:set-cookies", async (_event, cookies: Array<{ name: string; value: string; domain?: string; path?: string }>) => {
    const worker = getWorker();
    await worker.setCookies(cookies);
    return { set: true, count: cookies.length };
  });

  ipcMain.handle("collect:clear-cookies", async () => {
    const worker = getWorker();
    await worker.clearCookies();
    return { cleared: true };
  });

  ipcMain.handle("collect:get-cookies", async () => {
    const worker = getWorker();
    const cookies = await worker.getCookies();
    return cookies.map(c => ({ name: c.name, value: c.value, domain: c.domain, path: c.path }));
  });

  ipcMain.handle("collect:enqueue-sharded", async (_event, tasks: CollectTask[], shardSize?: number) => {
    const worker = getWorker();
    worker.enqueueBatchSharded(tasks, shardSize || 5);
    return { queued: tasks.length, queueLength: worker.getQueueLength() };
  });

  ipcMain.handle("collect:resume-checkpoint", async () => {
    const worker = getWorker();
    const count = worker.resumeFromCheckpoint();
    return { resumed: count, queueLength: worker.getQueueLength() };
  });

  ipcMain.handle("collect:clear-checkpoint", async () => {
    const worker = getWorker();
    worker.clearCheckpoint();
    return { cleared: true };
  });

  ipcMain.handle("collect:memory-usage", async () => {
    const worker = getWorker();
    return worker.getMemoryUsage();
  });

  ipcMain.handle("collect:set-max-memory", async (_event, mb: number) => {
    const worker = getWorker();
    worker.setMaxMemory(mb);
    return { maxMemoryMB: mb };
  });

  ipcMain.handle("collect:open-xhs-login", async () => {
    const { BrowserView, BrowserWindow } = require("electron");
    const mainWindow = BrowserWindow.getAllWindows()[0];
    if (!mainWindow) return { error: "No main window" };

    const chromiumWorker = getChromiumWorkerInternal();
    const loginView = new BrowserView({
      webPreferences: {
        session: chromiumWorker?.["collectSession"] || undefined,
        nodeIntegration: false,
        contextIsolation: true,
      },
    });
    mainWindow.setBrowserView(loginView);
    const bounds = mainWindow.getBounds();
    loginView.setBounds({ x: 200, y: 50, width: bounds.width - 400, height: bounds.height - 100 });
    loginView.webContents.loadURL("https://www.xiaohongshu.com");
    return { opened: true };
  });

  ipcMain.handle("concurrency:get", async () => {
    const ctrl = getConcurrencyCtrl();
    return {
      current: ctrl.getConcurrency(),
      activeCount: ctrl.getActiveCount(),
      waitingCount: ctrl.getWaitingCount(),
      config: ctrl.getConfig(),
      resourceUsage: ctrl.getResourceUsage(),
    };
  });

  ipcMain.handle("concurrency:set", async (_event, value: number) => {
    const ctrl = getConcurrencyCtrl();
    const worker = getWorker();
    const newValue = ctrl.setConcurrency(value, "user");
    worker.setConcurrency(newValue);
    return { current: newValue, config: ctrl.getConfig() };
  });

  ipcMain.handle("scheduler:start", async () => {
    wireSchedulerEvents();
    await localScheduler.start();
    return localScheduler.getState();
  });

  ipcMain.handle("scheduler:stop", async () => {
    localScheduler.stop();
    return localScheduler.getState();
  });

  ipcMain.handle("scheduler:state", async () => {
    return localScheduler.getState();
  });

  ipcMain.handle("scheduler:add-task", async (_event, task: Omit<ScheduledTask, "id" | "last_run_at" | "last_run_status" | "next_run_at" | "retry_count" | "max_retries" | "consecutive_failures" | "created_at">) => {
    return localScheduler.addTask(task);
  });

  ipcMain.handle("scheduler:remove-task", async (_event, taskId: string) => {
    return localScheduler.removeTask(taskId);
  });

  ipcMain.handle("scheduler:toggle-task", async (_event, taskId: string, active: boolean) => {
    return localScheduler.toggleTask(taskId, active);
  });

  ipcMain.handle("scheduler:update-frequency", async (_event, taskId: string, frequencyMinutes: number) => {
    return localScheduler.updateFrequency(taskId, frequencyMinutes);
  });

  ipcMain.handle("scheduler:get-tasks", async () => {
    return localScheduler.getAllTasks();
  });

  ipcMain.handle("scheduler:timeline", async () => {
    const tasks = localScheduler.getAllTasks();
    const state = localScheduler.getState();
    const now = Date.now();
    const timeline = tasks.map((task) => {
      const nextRun = task.next_run_at ? new Date(task.next_run_at).getTime() : 0;
      const lastRun = task.last_run_at ? new Date(task.last_run_at).getTime() : 0;
      const delay = Math.max(0, nextRun - now);
      return {
        id: task.id,
        product_name: task.product_name,
        platform: task.platform,
        is_active: task.is_active,
        frequency_minutes: task.frequency_minutes,
        last_run_at: task.last_run_at,
        last_run_status: task.last_run_status,
        next_run_at: task.next_run_at,
        retry_count: task.retry_count,
        max_retries: task.max_retries,
        consecutive_failures: task.consecutive_failures,
        delay_ms: delay,
        progress: task.is_active && nextRun > 0 && lastRun > 0
          ? Math.min(100, Math.round(((now - lastRun) / (nextRun - lastRun)) * 100))
          : 0,
        status: !task.is_active ? (task.consecutive_failures >= 5 ? "auto_disabled" : "paused") : task.consecutive_failures > 0 ? "degraded" : delay <= 0 ? "due" : "scheduled",
      };
    });
    return { tasks: timeline, state };
  });

  ipcMain.handle("scheduler:report-result", async (_event, taskId: string, status: "success" | "failed" | "risk_detected") => {
    await localScheduler.reportTaskResult(taskId, status);
    return { reported: true };
  });

  ipcMain.handle("scheduler:retry-failed", async (_event, taskId: string) => {
    return localScheduler.retryFailedTask(taskId);
  });

  ipcMain.handle("scheduler:failed-tasks", async () => {
    return localScheduler.getFailedTasks();
  });

  ipcMain.handle("scheduler:stats", async () => {
    return localScheduler.getStats();
  });

  ipcMain.handle("scheduler:set-max-retries", async (_event, taskId: string, maxRetries: number) => {
    return localScheduler.setMaxRetries(taskId, maxRetries);
  });

  ipcMain.handle("datamart:list-products", async (_event, platform?: string, limit?: number) => {
    return dataMart.listProducts(platform, limit);
  });

  ipcMain.handle("datamart:get-product", async (_event, productId: string) => {
    return dataMart.getProduct(productId);
  });

  ipcMain.handle("datamart:invalidate-cache", async () => {
    dataMart.invalidateCache();
    return true;
  });

  ipcMain.handle("playwright:start", async (_event, tasks: PlaywrightTask[]) => {
    const collector = getPlaywrightCollector();
    await collector.launch();
    collector.enqueueBatch(tasks);
    return { queued: tasks.length, activeCount: collector.getActiveCount(), queueLength: collector.getQueueLength() };
  });

  ipcMain.handle("playwright:status", async () => {
    const { getPlaywrightCollectorInternal } = require("./worker-registry");
    const collector = getPlaywrightCollectorInternal();
    if (!collector) {
      return { isRunning: false, activeCount: 0, queueLength: 0 };
    }
    return {
      isRunning: collector.getActiveCount() > 0,
      activeCount: collector.getActiveCount(),
      queueLength: collector.getQueueLength(),
    };
  });

  ipcMain.handle("playwright:cancel", async (_event, taskId: string) => {
    const { getPlaywrightCollectorInternal } = require("./worker-registry");
    const collector = getPlaywrightCollectorInternal();
    if (!collector) return false;
    return collector.cancelTask(taskId);
  });

  ipcMain.handle("playwright:close", async () => {
    const { getPlaywrightCollectorInternal, clearPlaywrightCollector } = require("./worker-registry");
    const collector = getPlaywrightCollectorInternal();
    if (collector) {
      await collector.close();
      clearPlaywrightCollector();
    }
    return true;
  });
}
