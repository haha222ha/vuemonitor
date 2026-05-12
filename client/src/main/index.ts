import { app, BrowserWindow, Tray } from "electron";
import { initServices, AppLifecycle, WindowManager, TrayManager } from "./services";
import { localScheduler } from "./collect/local-scheduler";
import { dataMart } from "./collect/data-mart";
import { licenseManager } from "./license/license-manager";
import { cloudSync } from "./sync/cloud-sync";
import { getCommunication } from "./communication/ws-client";
import { crashRecovery } from "./recovery/crash-recovery";
import { localRuleEvaluator } from "./monitor/local-evaluator";
import { autoUpdateManager } from "./update/auto-updater";
import { logger } from "./logger/logger";
import { offlineMode } from "./services/offline-mode";
import { performanceMonitor } from "./services/performance-monitor";

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

  // Crash recovery retry
  const recoveryResult = crashRecovery.recoverPendingTasks();
  if (recoveryResult.recovered > 0) {
    for (const task of recoveryResult.tasks) {
      if (task.retryCount < task.maxRetries) {
        crashRecovery.incrementRetry(task.id);
        logger.info("Main", `Retrying task ${task.id} (${task.targetUrl || task.targetId}), attempt ${task.retryCount + 1}/${task.maxRetries}`);
      } else {
        crashRecovery.updateSnapshotStatus(task.id, "failed", undefined, "Exceeded max retries after crash");
        logger.info("Main", `Task ${task.id} exceeded max retries, marking as failed`);
      }
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
