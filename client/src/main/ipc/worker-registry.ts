import { BrowserWindow } from "electron";
import { ChromiumCollectWorker, CollectTask, CollectResult } from "../collect/chromium-worker";
import { ConcurrencyController } from "../collect/concurrency-controller";
import { normalizer } from "../collect/normalizer";
import { dataMart } from "../collect/data-mart";
import { localScheduler } from "../collect/local-scheduler";
import { LocalPermissionCache } from "../permission/permission-cache";
import { PlaywrightCollector, PlaywrightTask, PlaywrightResult } from "../collect/playwright-collector";
import { logger } from "../logger/logger";

let chromiumWorker: ChromiumCollectWorker | null = null;
let concurrencyController: ConcurrencyController | null = null;
let permissionCache: LocalPermissionCache | null = null;
let playwrightCollector: PlaywrightCollector | null = null;
let dataMartSyncWired: boolean = false;

export function wireDataMartSync(): void {
  if (dataMartSyncWired) return;
  dataMartSyncWired = true;

  dataMart.on("data:created", (result: { action: string; product_id: string; quality_score: number }) => {
    const storage = getStorage();
    const rows = storage.query("SELECT * FROM products WHERE id = ?", [result.product_id]) as Record<string, unknown>[];
    if (rows.length > 0) {
      const { cloudSync } = require("../sync/cloud-sync");
      cloudSync.enqueueProduct(rows[0], "create");
    }
    const features = storage.query("SELECT * FROM product_features WHERE product_id = ? ORDER BY collected_at DESC LIMIT 1", [result.product_id]) as Record<string, unknown>[];
    if (features.length > 0) {
      const { cloudSync } = require("../sync/cloud-sync");
      cloudSync.enqueueFeature(result.product_id, features[0]);
    }
  });

  dataMart.on("data:updated", (result: { action: string; product_id: string; quality_score: number }) => {
    const storage = getStorage();
    const rows = storage.query("SELECT * FROM products WHERE id = ?", [result.product_id]) as Record<string, unknown>[];
    if (rows.length > 0) {
      const { cloudSync } = require("../sync/cloud-sync");
      cloudSync.enqueueProduct(rows[0], "update");
    }
    const features = storage.query("SELECT * FROM product_features WHERE product_id = ? ORDER BY collected_at DESC LIMIT 1", [result.product_id]) as Record<string, unknown>[];
    if (features.length > 0) {
      const { cloudSync } = require("../sync/cloud-sync");
      cloudSync.enqueueFeature(result.product_id, features[0]);
    }
  });
}

let workerInitPromise: Promise<void> | null = null;

export function getWorker(): ChromiumCollectWorker {
  if (!chromiumWorker) {
    chromiumWorker = new ChromiumCollectWorker();
    workerInitPromise = chromiumWorker.init();

    chromiumWorker.on("task:result", (result: CollectResult) => {
      if (result.status === "success" && result.data) {
        const normalized = normalizer.normalize(result.data);
        if (normalized.success && normalized.data) {
          dataMart.ingest(normalized.data, "local-user");
        }
      }

      localScheduler.reportTaskResult(result.taskId, result.status === "success" ? "success" : result.status === "risk_detected" ? "risk_detected" : "failed").catch(() => {});

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

export function getWorkerInitPromise(): Promise<void> | null {
  return workerInitPromise;
}

export function clearWorkerInitPromise(): void {
  workerInitPromise = null;
}

export function getConcurrencyCtrl(): ConcurrencyController {
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

export function getPermissionCache(): LocalPermissionCache {
  if (!permissionCache) {
    permissionCache = new LocalPermissionCache();
  }
  return permissionCache;
}

export function getPlaywrightCollector(): PlaywrightCollector {
  if (!playwrightCollector) {
    playwrightCollector = new PlaywrightCollector();
    playwrightCollector.on("task:result", (result: PlaywrightResult) => {
      if (result.status === "success" && result.data) {
        const normalized = normalizer.normalize(result.data);
        if (normalized.success && normalized.data) {
          dataMart.ingest(normalized.data, "local-user");
        }
      }

      localScheduler.reportTaskResult(result.taskId, result.status === "success" ? "success" : result.status === "risk_detected" ? "risk_detected" : "failed").catch(() => {});

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
  return playwrightCollector;
}

let schedulerEventsWired = false;
export function wireSchedulerEvents(): void {
  if (schedulerEventsWired) return;
  schedulerEventsWired = true;

  localScheduler.on("task:auto_disabled", (info) => {
    const mainWindow = BrowserWindow.getAllWindows()[0];
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send("scheduler:task_auto_disabled", info);
    }
  });

  localScheduler.on("task:retry_scheduled", (info) => {
    const mainWindow = BrowserWindow.getAllWindows()[0];
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send("scheduler:task_retry_scheduled", info);
    }
  });

  localScheduler.on("scheduler:task_executed", (info) => {
    const mainWindow = BrowserWindow.getAllWindows()[0];
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send("scheduler:task_executed", info);
    }
  });
}

export function getChromiumWorkerInternal(): ChromiumCollectWorker | null {
  return chromiumWorker;
}

export function getPlaywrightCollectorInternal(): PlaywrightCollector | null {
  return playwrightCollector;
}

export function clearPlaywrightCollector(): void {
  playwrightCollector = null;
}

import { getStorage } from "../storage/sqlite";
