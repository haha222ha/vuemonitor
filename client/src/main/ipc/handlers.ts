import { ipcMain, app, BrowserWindow, Tray, Menu, nativeImage } from "electron";
import { getStorage } from "../storage/sqlite";
import { getCommunication } from "../communication/ws-client";
import { ChromiumCollectWorker, CollectTask, CollectResult } from "../collect/chromium-worker";
import { ConcurrencyController } from "../collect/concurrency-controller";
import { normalizer } from "../collect/normalizer";
import { dataMart } from "../collect/data-mart";
import { localScheduler, ScheduledTask } from "../collect/local-scheduler";
import { LocalPermissionCache } from "../permission/permission-cache";
import { PlaywrightCollector, PlaywrightTask, PlaywrightResult } from "../collect/playwright-collector";
import { licenseManager } from "../license/license-manager";
import { cloudSync } from "../sync/cloud-sync";
import { featureEngine } from "../feature/feature-engine";
import { crashRecovery } from "../recovery/crash-recovery";
import { localRuleEvaluator } from "../monitor/local-evaluator";
import { autoUpdateManager } from "../update/auto-updater";
import { logger } from "../logger/logger";
import { offlineMode } from "../services/offline-mode";
import { trayManager } from "../services/tray-manager";
import { performanceMonitor } from "../services/performance-monitor";

let chromiumWorker: ChromiumCollectWorker | null = null;
let concurrencyController: ConcurrencyController | null = null;
let permissionCache: LocalPermissionCache | null = null;
let playwrightCollector: PlaywrightCollector | null = null;
let dataMartSyncWired: boolean = false;

function wireDataMartSync(): void {
  if (dataMartSyncWired) return;
  dataMartSyncWired = true;

  dataMart.on("data:created", (result: { action: string; product_id: string; quality_score: number }) => {
    const storage = getStorage();
    const rows = storage.query("SELECT * FROM products WHERE id = ?", [result.product_id]) as Record<string, unknown>[];
    if (rows.length > 0) {
      cloudSync.enqueueProduct(rows[0], "create");
    }
    const features = storage.query("SELECT * FROM product_features WHERE product_id = ? ORDER BY collected_at DESC LIMIT 1", [result.product_id]) as Record<string, unknown>[];
    if (features.length > 0) {
      cloudSync.enqueueFeature(result.product_id, features[0]);
    }
  });

  dataMart.on("data:updated", (result: { action: string; product_id: string; quality_score: number }) => {
    const storage = getStorage();
    const rows = storage.query("SELECT * FROM products WHERE id = ?", [result.product_id]) as Record<string, unknown>[];
    if (rows.length > 0) {
      cloudSync.enqueueProduct(rows[0], "update");
    }
    const features = storage.query("SELECT * FROM product_features WHERE product_id = ? ORDER BY collected_at DESC LIMIT 1", [result.product_id]) as Record<string, unknown>[];
    if (features.length > 0) {
      cloudSync.enqueueFeature(result.product_id, features[0]);
    }
  });
}

function getWorker(): ChromiumCollectWorker {
  if (!chromiumWorker) {
    chromiumWorker = new ChromiumCollectWorker();
    chromiumWorker.init();

    chromiumWorker.on("task:result", (result: CollectResult) => {
      if (result.status === "success" && result.data) {
        const normalized = normalizer.normalize(result.data);
        if (normalized.success && normalized.data) {
          dataMart.ingest(normalized.data, "local-user");
        }
      }
      const mainWindow = BrowserWindow.getAllWindows()[0];
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send("collect:result", result);
      }
    });

    chromiumWorker.on("task:risk", (result: CollectResult) => {
      const mainWindow = BrowserWindow.getAllWindows()[0];
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send("collect:risk_alert", result);
      }
    });
  }
  return chromiumWorker;
}

function getConcurrencyCtrl(): ConcurrencyController {
  if (!concurrencyController) {
    concurrencyController = new ConcurrencyController();
    concurrencyController.on("concurrency:changed", ({ from, to, reason }) => {
      const mainWindow = BrowserWindow.getAllWindows()[0];
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send("concurrency:changed", { from, to, reason });
      }
    });
    concurrencyController.on("resource:warning", (info) => {
      const mainWindow = BrowserWindow.getAllWindows()[0];
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send("resource:warning", info);
      }
    });
  }
  return concurrencyController;
}

function getPermissionCache(): LocalPermissionCache {
  if (!permissionCache) {
    permissionCache = new LocalPermissionCache();
  }
  return permissionCache;
}

export function registerIpcHandlers(): void {
  wireDataMartSync();

  ipcMain.handle("get-app-version", () => app.getVersion());

  ipcMain.handle("storage:query", async (_event, sql: string, params?: unknown[]) => {
    const storage = getStorage();
    return storage.query(sql, params);
  });

  ipcMain.handle("storage:run", async (_event, sql: string, params?: unknown[]) => {
    const storage = getStorage();
    return storage.run(sql, params);
  });

  ipcMain.handle("storage:insert-product", async (_event, product: Record<string, unknown>) => {
    const storage = getStorage();
    return storage.insertProduct(product);
  });

  ipcMain.handle("storage:get-products", async (_event, filters?: Record<string, unknown>) => {
    const storage = getStorage();
    return storage.getProducts(filters);
  });

  ipcMain.handle("storage:save-features", async (_event, productId: string, features: Record<string, unknown>) => {
    const storage = getStorage();
    return storage.saveFeatures(productId, features);
  });

  ipcMain.handle("storage:export-all", async () => {
    const storage = getStorage();
    const tables = ["products", "product_features", "ai_analysis", "monitor_rules", "local_notifications"];
    const result: Record<string, unknown[]> = {};
    for (const table of tables) {
      try {
        result[table] = storage.query(`SELECT * FROM ${table}`) as unknown[];
      } catch {
        result[table] = [];
      }
    }
    return result;
  });

  ipcMain.handle("storage:cleanup", async (_event, days: number) => {
    const storage = getStorage();
    const cutoff = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString();
    let deleted = 0;
    try {
      const r1 = storage.run(`DELETE FROM product_features WHERE collected_at < ?`, [cutoff]);
      deleted += (r1 as any)?.changes || 0;
    } catch {}
    try {
      const r2 = storage.run(`DELETE FROM local_notifications WHERE created_at < ?`, [cutoff]);
      deleted += (r2 as any)?.changes || 0;
    } catch {}
    try {
      const r3 = storage.run(`DELETE FROM ai_analysis WHERE analyzed_at < ?`, [cutoff]);
      deleted += (r3 as any)?.changes || 0;
    } catch {}
    return { deleted };
  });

  ipcMain.handle("storage:size", async () => {
    const fs = await import("fs");
    const path = await import("path");
    const dbPath = path.join(app.getPath("userData"), "xhs365.db");
    try {
      const stat = fs.statSync(dbPath);
      return { sizeBytes: stat.size };
    } catch {
      return { sizeBytes: 0 };
    }
  });

  ipcMain.handle("comm:connect", async (_event, serverUrl: string, token: string) => {
    const comm = getCommunication();
    return comm.connect(serverUrl, token);
  });

  ipcMain.handle("comm:disconnect", async () => {
    const comm = getCommunication();
    comm.disconnect();
  });

  ipcMain.handle("comm:send", async (_event, type: string, data: unknown) => {
    const comm = getCommunication();
    return comm.send(type, data);
  });

  ipcMain.handle("sync:push-to-cloud", async (_event, data: unknown) => {
    const comm = getCommunication();
    return comm.pushToCloud(data);
  });

  ipcMain.handle("collect:start", async (_event, tasks: CollectTask[]) => {
    const worker = getWorker();
    worker.enqueueBatch(tasks);
    return { queued: tasks.length, activeCount: worker.getActiveCount(), queueLength: worker.getQueueLength() };
  });

  ipcMain.handle("collect:cancel", async (_event, taskId: string) => {
    const worker = getWorker();
    return worker.cancelTask(taskId);
  });

  ipcMain.handle("collect:clear-queue", async () => {
    const worker = getWorker();
    return worker.clearQueue();
  });

  ipcMain.handle("collect:status", async () => {
    const worker = getWorker();
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

  ipcMain.handle("scheduler:add-task", async (_event, task: Omit<ScheduledTask, "id" | "last_run_at" | "next_run_at" | "created_at">) => {
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
        next_run_at: task.next_run_at,
        delay_ms: delay,
        progress: task.is_active && nextRun > 0 && lastRun > 0
          ? Math.min(100, Math.round(((now - lastRun) / (nextRun - lastRun)) * 100))
          : 0,
        status: !task.is_active ? "paused" : delay <= 0 ? "due" : "scheduled",
      };
    });
    return { tasks: timeline, state };
  });

  ipcMain.handle("datamart:list-products", async (_event, platform?: string, limit?: number) => {
    return dataMart.listProducts(platform, limit);
  });

  ipcMain.handle("products:list", async (_event, params?: { page?: number; pageSize?: number; platform?: string }) => {
    const comm = getCommunication();
    if (!comm.isConnected()) return { data: { items: [], total: 0 } };
    const page = params?.page || 1;
    const pageSize = params?.pageSize || 20;
    const platform = params?.platform;
    let url = `/api/v1/products?page=${page}&page_size=${pageSize}`;
    if (platform) url += `&platform=${platform}`;
    return comm.request("GET", url);
  });

  ipcMain.handle("products:compare", async (_event, params: { productIds: string[] }) => {
    const comm = getCommunication();
    if (!comm.isConnected()) return { data: null };
    const ids = params.productIds.join("&product_ids=");
    return comm.request("POST", `/api/v1/products/compare?product_ids=${ids}`);
  });

  ipcMain.handle("datamart:get-product", async (_event, productId: string) => {
    return dataMart.getProduct(productId);
  });

  ipcMain.handle("datamart:invalidate-cache", async () => {
    dataMart.invalidateCache();
    return true;
  });

  ipcMain.handle("auth:login", async (_event, account: string, password: string, serverUrl: string) => {
    try {
      const axios = require("axios");
      const { data } = await axios.post(`${serverUrl}/api/v1/auth/login`, { account, password });
      if (data.access_token) {
        const comm = getCommunication();
        comm.connect(serverUrl, data.access_token);
        const cache = getPermissionCache();
        await cache.refreshFromServer(serverUrl, data.access_token);
        cloudSync.configure(serverUrl, data.access_token);
        cloudSync.startAutoSync();
      }
      return data;
    } catch (err) {
      return { error: true, message: (err as Error).message };
    }
  });

  ipcMain.handle("auth:logout", async () => {
    const comm = getCommunication();
    comm.disconnect();
    const cache = getPermissionCache();
    cache.clear();
    cloudSync.stopAutoSync();
    return true;
  });

  ipcMain.handle("permission:check", async (_event, gateKey: string) => {
    const cache = getPermissionCache();
    return cache.checkGate(gateKey);
  });

  ipcMain.handle("permission:get-all", async () => {
    const cache = getPermissionCache();
    return cache.getAllGates();
  });

  ipcMain.handle("permission:refresh", async () => {
    const cache = getPermissionCache();
    return { refreshed: true };
  });

  ipcMain.handle("app:minimize-to-tray", async () => {
    const mainWindow = BrowserWindow.getAllWindows()[0];
    if (mainWindow) {
      mainWindow.hide();
    }
    return true;
  });

  ipcMain.handle("app:get-platform", async () => {
    return process.platform;
  });

  ipcMain.handle("playwright:start", async (_event, tasks: PlaywrightTask[]) => {
    if (!playwrightCollector) {
      playwrightCollector = new PlaywrightCollector();
      playwrightCollector.on("task:result", (result: PlaywrightResult) => {
        if (result.status === "success" && result.data) {
          const normalized = normalizer.normalize(result.data);
          if (normalized.success && normalized.data) {
            dataMart.ingest(normalized.data, "local-user");
          }
        }
        const mainWindow = BrowserWindow.getAllWindows()[0];
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send("collect:result", result);
        }
      });
      playwrightCollector.on("task:risk", (result: PlaywrightResult) => {
        const mainWindow = BrowserWindow.getAllWindows()[0];
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send("collect:risk_alert", result);
        }
      });
    }
    await playwrightCollector.launch();
    playwrightCollector.enqueueBatch(tasks);
    return { queued: tasks.length, activeCount: playwrightCollector.getActiveCount(), queueLength: playwrightCollector.getQueueLength() };
  });

  ipcMain.handle("playwright:status", async () => {
    if (!playwrightCollector) {
      return { isRunning: false, activeCount: 0, queueLength: 0 };
    }
    return {
      isRunning: playwrightCollector.getActiveCount() > 0,
      activeCount: playwrightCollector.getActiveCount(),
      queueLength: playwrightCollector.getQueueLength(),
    };
  });

  ipcMain.handle("playwright:cancel", async (_event, taskId: string) => {
    if (!playwrightCollector) return false;
    return playwrightCollector.cancelTask(taskId);
  });

  ipcMain.handle("playwright:close", async () => {
    if (playwrightCollector) {
      await playwrightCollector.close();
      playwrightCollector = null;
    }
    return true;
  });

  ipcMain.handle("license:activate", async (_event, licenseKey: string, serverUrl?: string) => {
    const result = await licenseManager.activate(licenseKey, serverUrl);
    if (result.success && result.license) {
      const cache = getPermissionCache();
      cache.updateFromLicense(result.license);
    }
    return result;
  });

  ipcMain.handle("license:get-current", async () => {
    return licenseManager.getCurrentLicense();
  });

  ipcMain.handle("license:get-plan", async () => {
    return {
      plan: licenseManager.getPlan(),
      features: licenseManager.getFeatures(),
      quotas: licenseManager.getQuotas(),
    };
  });

  ipcMain.handle("license:check-feature", async (_event, gateKey: string) => {
    return licenseManager.checkFeature(gateKey);
  });

  ipcMain.handle("license:check-quota", async (_event, quotaKey: string, currentUsage: number) => {
    const quotas = licenseManager.getQuotas();
    const limit = quotas[quotaKey];
    if (limit === undefined) return { allowed: true, limit: -1, remaining: -1 };
    if (limit === -1) return { allowed: true, limit: -1, remaining: -1 };
    const remaining = Math.max(0, limit - currentUsage);
    return { allowed: currentUsage < limit, limit, remaining };
  });

  ipcMain.handle("license:deactivate", async () => {
    return licenseManager.deactivate();
  });

  ipcMain.handle("license:get-device-id", async () => {
    return {
      deviceId: licenseManager.generateDeviceId(),
      fingerprint: licenseManager.getMachineFingerprint(),
    };
  });

  ipcMain.handle("license:is-expired", async () => {
    return licenseManager.isExpired();
  });

  ipcMain.handle("sync:configure", async (_event, serverUrl: string, token: string) => {
    cloudSync.configure(serverUrl, token);
    return true;
  });

  ipcMain.handle("sync:start", async () => {
    cloudSync.startAutoSync();
    return true;
  });

  ipcMain.handle("sync:stop", async () => {
    cloudSync.stopAutoSync();
    return true;
  });

  ipcMain.handle("sync:now", async () => {
    return await cloudSync.syncAll();
  });

  ipcMain.handle("sync:status", async () => {
    return cloudSync.getStatus();
  });

  ipcMain.handle("sync:enqueue-product", async (_event, product: Record<string, unknown>, action: "create" | "update" | "delete") => {
    cloudSync.enqueueProduct(product, action);
    return true;
  });

  ipcMain.handle("sync:enqueue-feature", async (_event, productId: string, feature: Record<string, unknown>) => {
    cloudSync.enqueueFeature(productId, feature);
    return true;
  });

  ipcMain.handle("sync:ai-analyze", async (_event, productId: string, analysisType: string) => {
    return await cloudSync.requestAIAnalysis(productId, analysisType);
  });

  ipcMain.handle("sync:clear-pending", async () => {
    return cloudSync.clearPending();
  });

  ipcMain.handle("sync:get-conflicts", async () => {
    return cloudSync.getConflicts();
  });

  ipcMain.handle("sync:get-all-conflicts", async () => {
    return cloudSync.getAllConflicts();
  });

  ipcMain.handle("sync:resolve-conflict", async (_event, conflictId: string, resolution: "local_wins" | "server_wins" | "merged") => {
    return cloudSync.resolveConflict(conflictId, resolution);
  });

  ipcMain.handle("sync:load-persisted-conflicts", async () => {
    cloudSync.loadPersistedConflicts();
    return cloudSync.getConflicts();
  });

  ipcMain.handle("feature:compute", async (_event, productId: string) => {
    return featureEngine.computeForProduct(productId);
  });

  ipcMain.handle("feature:compute-all", async () => {
    return { computed: featureEngine.computeAll() };
  });

  ipcMain.handle("feature:get", async (_event, productId: string) => {
    return featureEngine.getFeaturesForProduct(productId);
  });

  ipcMain.handle("feature:stats", async () => {
    return featureEngine.getStats();
  });

  ipcMain.handle("recovery:get-active", async () => {
    return crashRecovery.getActiveSnapshots();
  });

  ipcMain.handle("recovery:get-all", async (_event, limit?: number) => {
    return crashRecovery.getAllSnapshots(limit);
  });

  ipcMain.handle("recovery:clear-completed", async () => {
    return { cleared: crashRecovery.clearCompleted() };
  });

  ipcMain.handle("recovery:clear-all", async () => {
    crashRecovery.clearAll();
    return { cleared: true };
  });

  ipcMain.handle("notifications:get", async (_event, limit?: number) => {
    return localRuleEvaluator.getNotifications(limit);
  });

  ipcMain.handle("notifications:unread-count", async () => {
    return { count: localRuleEvaluator.getUnreadCount() };
  });

  ipcMain.handle("notifications:mark-read", async (_event, notificationId: string) => {
    localRuleEvaluator.markAsRead(notificationId);
    return { read: true };
  });

  ipcMain.handle("notifications:mark-all-read", async () => {
    return { count: localRuleEvaluator.markAllAsRead() };
  });

  ipcMain.handle("notifications:delete", async (_event, notificationId: string) => {
    return { deleted: localRuleEvaluator.deleteNotification(notificationId) };
  });

  localRuleEvaluator.on("notification:created", (notification: { id: string; type: string; title: string; content: string; related_id: string | null }) => {
    const mainWindow = BrowserWindow.getAllWindows()[0];
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send("notification:local", {
        id: notification.id,
        type: notification.type,
        title: notification.title,
        content: notification.content,
        is_read: false,
        related_id: notification.related_id,
        related_type: "product",
        created_at: new Date().toISOString(),
        source: "local",
      });
    }
  });

  ipcMain.handle("monitor:evaluate", async (_event, productId?: string) => {
    if (productId) {
      return { triggered: localRuleEvaluator.evaluateForProduct(productId) };
    }
    return { triggered: localRuleEvaluator.evaluateAll() };
  });

  ipcMain.handle("update:check", async (_event, silent?: boolean) => {
    await autoUpdateManager.checkForUpdate(silent !== false);
    return autoUpdateManager.getStatus();
  });

  ipcMain.handle("update:download", async () => {
    await autoUpdateManager.downloadUpdate();
    return { downloading: true };
  });

  ipcMain.handle("update:install", async () => {
    await autoUpdateManager.installUpdate();
    return { installing: true };
  });

  ipcMain.handle("update:status", async () => {
    return autoUpdateManager.getStatus();
  });

  ipcMain.handle("log:get-recent", async (_event, count?: number, level?: string, module?: string) => {
    return logger.getRecentLogs(count || 100, level as any, module);
  });

  ipcMain.handle("log:get-files", async () => {
    return logger.getLogFiles();
  });

  ipcMain.handle("log:export", async (_event, format?: string) => {
    return logger.exportLogs((format as "json" | "text") || "json");
  });

  ipcMain.handle("log:upload", async () => {
    return logger.uploadLogs();
  });

  ipcMain.handle("log:clear", async () => {
    return { deleted: logger.clearLogs() };
  });

  ipcMain.handle("log:get-stats", async () => {
    return logger.getStats();
  });

  ipcMain.handle("log:set-level", async (_event, level: string) => {
    logger.setLevel(level as any);
    return true;
  });

  ipcMain.handle("log:set-upload-endpoint", async (_event, endpoint: string | null) => {
    logger.setUploadEndpoint(endpoint);
    return true;
  });

  ipcMain.handle("offline:status", async () => {
    return offlineMode.getStatus();
  });

  ipcMain.handle("offline:pending-operations", async () => {
    return offlineMode.getPendingOperations();
  });

  ipcMain.handle("offline:clear-pending", async () => {
    return offlineMode.clearPendingOperations();
  });

  ipcMain.handle("offline:check", async () => {
    return await offlineMode.checkConnectivity();
  });

  ipcMain.handle("offline:enqueue", async (_event, type: string, payload: unknown) => {
    return await offlineMode.enqueueOperation(type, payload);
  });

  ipcMain.handle("window:open", async (_event, id: string, title: string, route: string) => {
    trayManager.openSecondaryWindow(id, title, route);
    return true;
  });

  ipcMain.handle("window:close", async (_event, id: string) => {
    trayManager.closeSecondaryWindow(id);
    return true;
  });

  ipcMain.handle("window:list", async () => {
    return trayManager.getSecondaryWindows();
  });

  ipcMain.handle("tray:update-status", async (_event, status: string) => {
    trayManager.updateCollectStatus(status);
    return true;
  });

  ipcMain.handle("perf:latest", async () => {
    return performanceMonitor.getLatest();
  });

  ipcMain.handle("perf:history", async (_event, limit?: number) => {
    return performanceMonitor.getHistory(limit);
  });

  ipcMain.handle("perf:alerts", async (_event, limit?: number) => {
    return performanceMonitor.getAlerts(limit);
  });

  ipcMain.handle("perf:summary", async () => {
    return performanceMonitor.getSummary();
  });

  ipcMain.handle("perf:clear", async () => {
    performanceMonitor.clearHistory();
    return true;
  });
}
