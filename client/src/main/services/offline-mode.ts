import { EventEmitter } from "events";
import { BrowserWindow } from "electron";
import * as dns from "dns";
import * as https from "https";
import { getStorage } from "../storage/sqlite";
import { cloudSync } from "../sync/cloud-sync";
import { logger } from "../logger/logger";

export interface OfflineOperation {
  id: string;
  type: string;
  payload: string;
  createdAt: string;
  retryCount: number;
  maxRetries: number;
}

export interface OfflineStatus {
  isOnline: boolean;
  lastOnlineAt: string | null;
  lastOfflineAt: string | null;
  pendingOperations: number;
  connectionType: string;
  serverReachable: boolean;
}

const CHECK_INTERVAL = 15000;
const CHECK_URLS = ["https://www.baidu.com", "https://www.google.com"];
const MAX_RETRIES = 5;
const RETRY_DELAYS = [1000, 5000, 15000, 30000, 60000];

class OfflineModeManager extends EventEmitter {
  private mainWindow: BrowserWindow | null = null;
  private isOnline: boolean = true;
  private serverReachable: boolean = true;
  private lastOnlineAt: string | null = null;
  private lastOfflineAt: string | null = null;
  private checkTimer: ReturnType<typeof setInterval> | null = null;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;
  private pendingOperations: OfflineOperation[] = [];
  private connectionType: string = "unknown";

  constructor() {
    super();
    this.loadPendingOperations();
  }

  setMainWindow(window: BrowserWindow): void {
    this.mainWindow = window;
  }

  async start(): Promise<void> {
    await this.checkConnectivity();
    this.checkTimer = setInterval(() => this.checkConnectivity(), CHECK_INTERVAL);
    logger.info("OfflineModeManager", "离线模式管理器已启动");
  }

  stop(): void {
    if (this.checkTimer) {
      clearInterval(this.checkTimer);
      this.checkTimer = null;
    }
    if (this.retryTimer) {
      clearTimeout(this.retryTimer);
      this.retryTimer = null;
    }
  }

  async checkConnectivity(): Promise<boolean> {
    const wasOnline = this.isOnline;
    const networkOk = await this.checkNetwork();
    const serverOk = networkOk ? await this.checkServer() : false;

    this.isOnline = networkOk;
    this.serverReachable = serverOk;

    if (wasOnline && !this.isOnline) {
      this.lastOfflineAt = new Date().toISOString();
      this.emit("offline");
      this.sendToRenderer("offline:status", this.getStatus());
      logger.warn("OfflineModeManager", "网络连接已断开");
    } else if (!wasOnline && this.isOnline) {
      this.lastOnlineAt = new Date().toISOString();
      this.emit("online");
      this.sendToRenderer("offline:status", this.getStatus());
      logger.info("OfflineModeManager", "网络连接已恢复");
      this.processPendingOperations();
    }

    this.sendToRenderer("offline:status", this.getStatus());
    return this.isOnline;
  }

  private async checkNetwork(): Promise<boolean> {
    try {
      return await new Promise<boolean>((resolve) => {
        dns.lookup("baidu.com", (err) => {
          resolve(!err);
        });
      });
    } catch {
      return false;
    }
  }

  private async checkServer(): Promise<boolean> {
    try {
      return await new Promise<boolean>((resolve) => {
        const req = https.get("https://www.baidu.com", { timeout: 5000 }, (res) => {
          resolve(res.statusCode === 200);
        });
        req.on("error", () => resolve(false));
        req.on("timeout", () => {
          req.destroy();
          resolve(false);
        });
      });
    } catch {
      return false;
    }
  }

  async enqueueOperation(type: string, payload: unknown): Promise<string> {
    const id = crypto.randomUUID();
    const operation: OfflineOperation = {
      id,
      type,
      payload: JSON.stringify(payload),
      createdAt: new Date().toISOString(),
      retryCount: 0,
      maxRetries: MAX_RETRIES,
    };

    this.pendingOperations.push(operation);
    this.savePendingOperations();

    if (this.isOnline) {
      this.processPendingOperations();
    }

    return id;
  }

  private async processPendingOperations(): Promise<void> {
    if (!this.isOnline || this.pendingOperations.length === 0) return;

    const operations = [...this.pendingOperations];
    this.pendingOperations = [];

    for (const op of operations) {
      try {
        await this.executeOperation(op);
        logger.info("OfflineModeManager", `离线操作执行成功: ${op.type} (${op.id})`);
      } catch (err) {
        op.retryCount++;
        if (op.retryCount < op.maxRetries) {
          this.pendingOperations.push(op);
          logger.warn("OfflineModeManager", `离线操作失败，将重试: ${op.type} (${op.id}), 重试次数: ${op.retryCount}`);
        } else {
          logger.error("OfflineModeManager", `离线操作已达最大重试次数: ${op.type} (${op.id})`);
          this.emit("operation:failed", op);
        }
      }
    }

    this.savePendingOperations();

    if (this.pendingOperations.length > 0) {
      this.scheduleRetry();
    }
  }

  private async executeOperation(op: OfflineOperation): Promise<void> {
    const payload = JSON.parse(op.payload);

    switch (op.type) {
      case "sync:product":
        cloudSync.enqueueProduct(payload, "create");
        break;
      case "sync:feature":
        cloudSync.enqueueFeature(payload.productId, payload.feature);
        break;
      case "sync:ai":
        await cloudSync.requestAIAnalysis(payload.productId, payload.analysisType);
        break;
      case "collect:task":
        break;
      default:
        logger.warn("OfflineModeManager", `未知离线操作类型: ${op.type}`);
    }
  }

  private scheduleRetry(): void {
    if (this.retryTimer) return;

    const minRetryCount = Math.min(...this.pendingOperations.map((o) => o.retryCount));
    const delay = RETRY_DELAYS[Math.min(minRetryCount, RETRY_DELAYS.length - 1)];

    this.retryTimer = setTimeout(() => {
      this.retryTimer = null;
      this.processPendingOperations();
    }, delay);
  }

  getStatus(): OfflineStatus {
    return {
      isOnline: this.isOnline,
      lastOnlineAt: this.lastOnlineAt,
      lastOfflineAt: this.lastOfflineAt,
      pendingOperations: this.pendingOperations.length,
      connectionType: this.connectionType,
      serverReachable: this.serverReachable,
    };
  }

  getPendingOperations(): OfflineOperation[] {
    return [...this.pendingOperations];
  }

  clearPendingOperations(): number {
    const count = this.pendingOperations.length;
    this.pendingOperations = [];
    this.savePendingOperations();
    return count;
  }

  isNetworkAvailable(): boolean {
    return this.isOnline;
  }

  isServerReachable(): boolean {
    return this.serverReachable;
  }

  private savePendingOperations(): void {
    try {
      const storage = getStorage();
      storage.run("DELETE FROM offline_operations");
      const stmt = storage.prepare(
        "INSERT INTO offline_operations (id, type, payload, created_at, retry_count, max_retries) VALUES (?, ?, ?, ?, ?, ?)"
      );
      for (const op of this.pendingOperations) {
        stmt.run(op.id, op.type, op.payload, op.createdAt, op.retryCount, op.maxRetries);
      }
    } catch (err) {
      logger.error("OfflineModeManager", `保存离线操作失败: ${err}`);
    }
  }

  private loadPendingOperations(): void {
    try {
      const storage = getStorage();
      const rows = storage.all(
        "SELECT id, type, payload, created_at, retry_count, max_retries FROM offline_operations ORDER BY created_at"
      );
      this.pendingOperations = (rows || []).map((row: any) => ({
        id: row.id,
        type: row.type,
        payload: row.payload,
        createdAt: row.created_at,
        retryCount: row.retry_count,
        maxRetries: row.max_retries,
      }));
    } catch (err) {
      logger.error("OfflineModeManager", `加载离线操作失败: ${err}`);
    }
  }

  private sendToRenderer(channel: string, data: unknown): void {
    if (this.mainWindow && !this.mainWindow.isDestroyed()) {
      this.mainWindow.webContents.send(channel, data);
    }
  }
}

export const offlineMode = new OfflineModeManager();