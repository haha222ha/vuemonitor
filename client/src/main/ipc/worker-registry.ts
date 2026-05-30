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

function sendCollectStatusPatch(worker: ChromiumCollectWorker): void {
  const mainWindow = BrowserWindow.getAllWindows()[0];
  if (!mainWindow || mainWindow.isDestroyed()) return;
  mainWindow.webContents.send("collect:status-changed", {
    isRunning: worker.getActiveCount() > 0 || worker.getQueueLength() > 0,
    activeCount: worker.getActiveCount(),
    queueLength: worker.getQueueLength(),
  });
}

async function persistCollectResult(result: CollectResult): Promise<void> {
  if (result.status !== "success" || !result.data) return;

  const payload: Record<string, unknown> = {
    ...result.data,
    platform: result.data.platform || "xhs",
    platform_product_id: String(result.data.platform_product_id || result.targetId || "").trim(),
    product_name:
      String(result.data.product_name || "").trim() ||
      `XHS商品 ${String(result.targetId || "").slice(0, 8)}`,
    targetType: result.data.targetType || result.targetType,
  };

  const normalized = normalizer.normalize(payload);
  if (normalized.success && normalized.data) {
    await dataMart.ingest(normalized.data, "local-user");
    try {
      const { getStorage } = require("../storage/sqlite");
      getStorage().flush();
    } catch (err) {
      logger.warn("Collect", `flush after ingest failed: ${err}`);
    }
    return;
  }

  logger.warn("Collect", `normalize failed for ${result.targetId}: ${normalized.errors.join("; ")}`);
}

export function getWorker(): ChromiumCollectWorker {
  if (!chromiumWorker) {
    chromiumWorker = new ChromiumCollectWorker();
    workerInitPromise = chromiumWorker.init();

    chromiumWorker.on("task:result", (result: CollectResult) => {
      void persistCollectResult(result).finally(() => {
        localScheduler.reportTaskResult(
          result.taskId,
          result.status === "success" ? "success" : result.status === "risk_detected" ? "risk_detected" : "failed",
        ).catch(() => {});

        const mainWindow = BrowserWindow.getAllWindows()[0];
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send("collect:result", result);
        }
        sendCollectStatusPatch(chromiumWorker!);
      });
    });

    chromiumWorker.on("task:failed", (payload: { taskId: string; error?: string; targetId?: string }) => {
      const mainWindow = BrowserWindow.getAllWindows()[0];
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send("collect:result", {
          taskId: payload.taskId,
          targetId: payload.targetId || "",
          status: "failed",
          error: payload.error,
          collectedAt: new Date().toISOString(),
        });
      }
      sendCollectStatusPatch(chromiumWorker!);
    });

    chromiumWorker.on("queue:empty", () => {
      sendCollectStatusPatch(chromiumWorker!);
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
      void persistCollectResult(result as CollectResult).finally(() => {
        localScheduler.reportTaskResult(
          result.taskId,
          result.status === "success" ? "success" : result.status === "risk_detected" ? "risk_detected" : "failed",
        ).catch(() => {});

        const mainWindow = BrowserWindow.getAllWindows()[0];
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send("collect:result", result);
        }
      });
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
