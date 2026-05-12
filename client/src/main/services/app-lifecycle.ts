import { initStorage } from "../storage/sqlite";
import { crashRecovery } from "../recovery/crash-recovery";
import { registerIpcHandlers } from "../ipc/handlers";
import { localScheduler } from "../collect/local-scheduler";
import { dataMart } from "../collect/data-mart";
import { licenseManager } from "../license/license-manager";
import { cloudSync } from "../sync/cloud-sync";
import { logger } from "../logger/logger";

export class AppLifecycle {
  private static instance: AppLifecycle;
  private initialized: boolean = false;
  private startTime: number = 0;

  private constructor() {}

  public static getInstance(): AppLifecycle {
    if (!AppLifecycle.instance) {
      AppLifecycle.instance = new AppLifecycle();
    }
    return AppLifecycle.instance;
  }

  public async initialize(): Promise<void> {
    if (this.initialized) {
      return;
    }

    try {
      await initStorage();
      logger.info("AppLifecycle", "存储初始化完成");
    } catch (err) {
      logger.error("AppLifecycle", "存储初始化失败", err);
      throw err;
    }

    crashRecovery.init();
    const recoveryResult = crashRecovery.recoverPendingTasks();
    if (recoveryResult.recovered > 0) {
      logger.info("AppLifecycle", "崩溃恢复完成", { recovered: recoveryResult.recovered, discarded: recoveryResult.discarded });
    }

    registerIpcHandlers();
    logger.info("AppLifecycle", "IPC处理器注册完成");

    this.initialized = true;
    this.startTime = Date.now();
    logger.info("AppLifecycle", "应用生命周期初始化完成");
  }

  public async shutdown(): Promise<void> {
    if (!this.initialized) {
      return;
    }

    try {
      localScheduler.destroy();
      dataMart.destroy();
      cloudSync.destroy();
      licenseManager.destroy();

      // Flush storage
      try {
        const { getStorage } = require("../storage/sqlite");
        const storage = getStorage();
        storage.flush();
      } catch (err) {
        logger.error("AppLifecycle", "存储刷新失败", err);
      }

      this.initialized = false;
      logger.info("AppLifecycle", "应用生命周期关闭完成");
    } catch (err) {
      logger.error("AppLifecycle", "应用生命周期关闭失败", err);
      throw err;
    }
  }

  public getStatus(): { initialized: boolean; uptime: number } {
    return {
      initialized: this.initialized,
      uptime: this.initialized ? Date.now() - this.startTime : 0
    };
  }
}

// Export a singleton instance for convenience
export const appLifecycle = AppLifecycle.getInstance();