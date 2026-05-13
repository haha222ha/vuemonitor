import { app, BrowserWindow, Tray } from "electron";
import { initServices, AppLifecycle, WindowManager, TrayManager } from "./services";
import { localScheduler } from "./collect/local-scheduler";
import { licenseManager } from "./license/license-manager";
import { cloudSync } from "./sync/cloud-sync";
import { getCommunication } from "./communication/ws-client";
import { crashRecovery, RecoveryPlan } from "./recovery/crash-recovery";
import { localRuleEvaluator } from "./monitor/local-evaluator";
import { autoUpdateManager } from "./update/auto-updater";
import { logger } from "./logger/logger";
import { offlineMode } from "./services/offline-mode";
import { performanceMonitor } from "./services/performance-monitor";
import { ChromiumCollectWorker, CollectTask } from "./collect/chromium-worker";
import { PlaywrightCollector, PlaywrightTask } from "./collect/playwright-collector";
import { normalizer } from "./collect/normalizer";
import { dataMart } from "./collect/data-mart";

// Service layer singletons
let lifecycle: AppLifecycle;
let windowManager: WindowManager;
let trayManager: TrayManager;

function getMainWindowRef(): BrowserWindow | null {
  return windowManager?.getMainWindow() ?? null;
}

function showMainWindow(): void {
  windowManager?.showMainWindow();
}

async function bootstrap(): Promise<void> {
  // Initialize service layer
  const services = initServices();
  lifecycle = services.lifecycle;
  windowManager = services.windows;
  trayManager = services.tray;

  // Wire tray to window manager
  trayManager.setMainWindowGetter(() => windowManager.getMainWindow());

  // Initialize core services (storage, crash recovery, IPC)
  await lifecycle.initialize();

  const license = licenseManager.getCurrentLicense();
  if (license?.isValid) {
    await localScheduler.start();
  }

  // Create window and tray
  const mainWindow = windowManager.createMainWindow();
  trayManager.createTray();

  offlineMode.setMainWindow(mainWindow);
  offlineMode.start();

  performanceMonitor.setMainWindow(mainWindow);
  performanceMonitor.start();

  logger.info("Main", "应用启动完成", { version: app.getVersion() });

  // Enhanced crash recovery with auto-restart
  const recoveryResult = crashRecovery.recoverPendingTasks();
  if (recoveryResult.recovered > 0) {
    logger.info("Main", "崩溃恢复发现待恢复任务", {
      recovered: recoveryResult.recovered,
      discarded: recoveryResult.discarded,
    });

    const retryablePlans = recoveryResult.plans.filter(
      (p) => p.strategy === "retry" || p.strategy === "resume_from_checkpoint"
    );

    for (const plan of retryablePlans) {
      const task = recoveryResult.tasks.find((t) => t.id === plan.taskId);
      if (!task) continue;

      crashRecovery.incrementRetry(task.id);

      const retryTask = async () => {
        try {
          if (task.taskType === "chromium") {
            const { getWorker } = require("./ipc/handlers");
            const worker = getWorker() as ChromiumCollectWorker;
            const collectTask: CollectTask = {
              id: task.id,
              targetId: task.targetId,
              targetType: task.targetType as CollectTask["targetType"],
              targetUrl: task.targetUrl || undefined,
            };
            worker.enqueueBatchSharded([collectTask]);
          } else if (task.taskType === "playwright") {
            const { getPlaywrightCollector } = require("./ipc/handlers");
            const collector = getPlaywrightCollector() as PlaywrightCollector;
            const pwTask: PlaywrightTask = {
              id: task.id,
              targetId: task.targetId,
              targetType: task.targetType as PlaywrightTask["targetType"],
              targetUrl: task.targetUrl || "",
            };
            collector.enqueue(pwTask);
          }
          logger.info("Main", `自动重启任务 ${task.id}`, {
            strategy: plan.strategy,
            type: task.taskType,
            target: task.targetUrl || task.targetId,
          });
        } catch (err) {
          logger.error("Main", `自动重启任务失败 ${task.id}`, { error: String(err) });
          crashRecovery.updateSnapshotStatus(task.id, "failed", undefined, `Auto-restart failed: ${String(err)}`);
        }
      };

      if (plan.retryDelay > 0) {
        setTimeout(retryTask, plan.retryDelay);
      } else {
        retryTask();
      }
    }

    for (const plan of recoveryResult.plans.filter((p) => p.strategy === "skip")) {
      crashRecovery.updateSnapshotStatus(plan.taskId, "failed", undefined, plan.reason);
      logger.info("Main", `跳过不可恢复任务 ${plan.taskId}`, { reason: plan.reason });
    }

    const manualPlans = recoveryResult.plans.filter((p) => p.strategy === "manual");
    if (manualPlans.length > 0) {
      windowManager.sendToRenderer("recovery:manual_required", {
        tasks: manualPlans.map((p) => ({ taskId: p.taskId, reason: p.reason })),
      });
    }
  }

  // Cloud sync events
  cloudSync.on("sync:complete", (info) => {
    windowManager.sendToRenderer("sync:complete", info);
  });
  cloudSync.on("ai:result", (result) => {
    windowManager.sendToRenderer("ai:result", result);
  });
  cloudSync.on("conflict:detected", (info) => {
    windowManager.sendToRenderer("sync:conflict:detected", info);
  });
  cloudSync.on("conflict:resolved", (info) => {
    windowManager.sendToRenderer("sync:conflict:resolved", info);
  });

  // Local monitor events
  localRuleEvaluator.on("notification:created", (notification) => {
    windowManager.sendToRenderer("notification:new", notification);
  });
  localRuleEvaluator.on("rule:triggered", (info) => {
    windowManager.sendToRenderer("monitor:triggered", info);
  });

  // Auto-update check (delayed in production)
  if (process.env.NODE_ENV !== "development") {
    setTimeout(() => {
      autoUpdateManager.checkForUpdate(true);
    }, 10000);
  }
}

app.whenReady().then(bootstrap);

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    windowManager?.createMainWindow();
  } else {
    windowManager?.showMainWindow();
  }
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  lifecycle?.shutdown();
});

app.on("will-quit", () => {
  trayManager?.destroyTray();
});
