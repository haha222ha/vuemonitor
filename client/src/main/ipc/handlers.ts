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

let chromiumWorker: ChromiumCollectWorker | null = null;
let concurrencyController: ConcurrencyController | null = null;
let permissionCache: LocalPermissionCache | null = null;
let playwrightCollector: PlaywrightCollector | null = null;

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
    };
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

  ipcMain.handle("auth:login", async (_event, email: string, password: string, serverUrl: string) => {
    try {
      const axios = require("axios");
      const { data } = await axios.post(`${serverUrl}/api/v1/auth/login`, { email, password });
      if (data.access_token) {
        const comm = getCommunication();
        comm.connect(serverUrl, data.access_token);
        const cache = getPermissionCache();
        await cache.refreshFromServer(serverUrl, data.access_token);
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

  ipcMain.handle("license:deactivate", async () => {
    return licenseManager.deactivate();
  });

  ipcMain.handle("license:get-device-id", async () => {
    return {
      deviceId: licenseManager.generateDeviceId(),
      fingerprint: licenseManager.getMachineFingerprint(),
    };
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
}
