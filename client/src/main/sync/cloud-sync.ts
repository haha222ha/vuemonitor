import { EventEmitter } from "events";
import { getStorage } from "../storage/sqlite";
import { getCommunication } from "../communication/ws-client";
import { licenseManager } from "../license/license-manager";

export interface SyncRecord {
  id: string;
  type: "product" | "feature" | "ai_result";
  localId: string;
  action: "create" | "update" | "delete";
  data: Record<string, unknown>;
  syncedAt: string | null;
  syncStatus: "pending" | "synced" | "failed";
  retryCount: number;
  createdAt: string;
}

export interface SyncStatus {
  lastSyncAt: string | null;
  pendingCount: number;
  syncedCount: number;
  failedCount: number;
  isSyncing: boolean;
  serverUrl: string | null;
}

export interface AIAnalysisResult {
  id: string;
  productId: string;
  analysisType: string;
  result: Record<string, unknown>;
  confidence: number;
  analyzedAt: string;
}

const MAX_RETRY = 3;
const SYNC_BATCH_SIZE = 50;
const SYNC_INTERVAL_MS = 5 * 60 * 1000;

export class CloudSyncManager extends EventEmitter {
  private syncTimer: ReturnType<typeof setInterval> | null = null;
  private isSyncing: boolean = false;
  private serverUrl: string | null = null;
  private token: string | null = null;
  private pendingQueue: SyncRecord[] = [];
  private stats = {
    lastSyncAt: null as string | null,
    syncedCount: 0,
    failedCount: 0,
  };

  configure(serverUrl: string, token: string): void {
    this.serverUrl = serverUrl;
    this.token = token;
  }

  startAutoSync(): void {
    if (this.syncTimer) return;
    this.syncTimer = setInterval(() => {
      this.syncAll();
    }, SYNC_INTERVAL_MS);
    this.syncAll();
  }

  stopAutoSync(): void {
    if (this.syncTimer) {
      clearInterval(this.syncTimer);
      this.syncTimer = null;
    }
  }

  getStatus(): SyncStatus {
    return {
      lastSyncAt: this.stats.lastSyncAt,
      pendingCount: this.pendingQueue.length,
      syncedCount: this.stats.syncedCount,
      failedCount: this.stats.failedCount,
      isSyncing: this.isSyncing,
      serverUrl: this.serverUrl,
    };
  }

  enqueueProduct(product: Record<string, unknown>, action: "create" | "update" | "delete"): void {
    const record: SyncRecord = {
      id: crypto.randomUUID(),
      type: "product",
      localId: product.id as string,
      action,
      data: product,
      syncedAt: null,
      syncStatus: "pending",
      retryCount: 0,
      createdAt: new Date().toISOString(),
    };
    this.pendingQueue.push(record);
    this.emit("sync:queued", record);
  }

  enqueueFeature(productId: string, feature: Record<string, unknown>): void {
    const record: SyncRecord = {
      id: crypto.randomUUID(),
      type: "feature",
      localId: feature.id as string || crypto.randomUUID(),
      action: "create",
      data: { productId, ...feature },
      syncedAt: null,
      syncStatus: "pending",
      retryCount: 0,
      createdAt: new Date().toISOString(),
    };
    this.pendingQueue.push(record);
    this.emit("sync:queued", record);
  }

  async syncAll(): Promise<{ pushed: number; pulled: number; errors: number }> {
    if (this.isSyncing || !this.serverUrl || !this.token) {
      return { pushed: 0, pulled: 0, errors: 0 };
    }

    this.isSyncing = true;
    this.emit("sync:start");

    let pushed = 0;
    let errors = 0;

    try {
      pushed = await this.pushToServer();
      const pulled = await this.pullFromServer();
      this.stats.lastSyncAt = new Date().toISOString();
      this.emit("sync:complete", { pushed, pulled, errors });
      return { pushed, pulled, errors };
    } catch (err) {
      errors++;
      this.emit("sync:error", { error: (err as Error).message });
      return { pushed, errors, pulled: 0 };
    } finally {
      this.isSyncing = false;
    }
  }

  private async pushToServer(): Promise<number> {
    if (this.pendingQueue.length === 0) return 0;

    const comm = getCommunication();
    let pushed = 0;

    const batch = this.pendingQueue.splice(0, SYNC_BATCH_SIZE);

    for (const record of batch) {
      try {
        const endpoint = this.getSyncEndpoint(record);
        const response = await comm.pushToCloud({
          type: record.type,
          action: record.action,
          localId: record.localId,
          data: record.data,
          deviceId: licenseManager.generateDeviceId(),
        });

        if (response && !(response as { error?: boolean }).error) {
          record.syncedAt = new Date().toISOString();
          record.syncStatus = "synced";
          pushed++;
          this.stats.syncedCount++;
        } else {
          record.retryCount++;
          if (record.retryCount < MAX_RETRY) {
            this.pendingQueue.push(record);
          } else {
            record.syncStatus = "failed";
            this.stats.failedCount++;
          }
        }
      } catch {
        record.retryCount++;
        if (record.retryCount < MAX_RETRY) {
          this.pendingQueue.push(record);
        } else {
          record.syncStatus = "failed";
          this.stats.failedCount++;
        }
      }
    }

    return pushed;
  }

  private async pullFromServer(): Promise<number> {
    if (!this.serverUrl || !this.token) return 0;

    try {
      const axios = require("axios");
      const { data } = await axios.get(`${this.serverUrl}/api/v1/sync/pull`, {
        headers: { Authorization: `Bearer ${this.token}` },
        params: {
          deviceId: licenseManager.generateDeviceId(),
          since: this.stats.lastSyncAt,
        },
      });

      if (!data || !data.items) return 0;

      let pulled = 0;
      const storage = getStorage();

      for (const item of data.items) {
        try {
          if (item.type === "ai_result" && item.data) {
            this.saveAIResult(item.data as AIAnalysisResult, storage);
            pulled++;
          } else if (item.type === "product" && item.data) {
            this.upsertProduct(item.data as Record<string, unknown>, storage);
            pulled++;
          }
        } catch {}
      }

      this.emit("sync:pulled", { count: pulled, items: data.items });
      return pulled;
    } catch {
      return 0;
    }
  }

  private saveAIResult(result: AIAnalysisResult, storage: ReturnType<typeof getStorage>): void {
    storage.run(
      `INSERT OR REPLACE INTO ai_analysis (id, product_id, analysis_type, result, confidence, analyzed_at)
       VALUES (?, ?, ?, ?, ?, ?)`,
      [
        result.id || crypto.randomUUID(),
        result.productId,
        result.analysisType,
        JSON.stringify(result.result),
        result.confidence,
        result.analyzedAt,
      ]
    );
  }

  private upsertProduct(product: Record<string, unknown>, storage: ReturnType<typeof getStorage>): void {
    const existing = storage.query(
      "SELECT id FROM products WHERE platform_product_id = ?",
      [product.platform_product_id]
    ) as Array<{ id: string }>;

    if (existing.length > 0) {
      storage.run(
        `UPDATE products SET product_name = ?, shop_name = ?, image_url = ?, updated_at = datetime('now')
         WHERE id = ?`,
        [product.product_name, product.shop_name, product.image_url, existing[0].id]
      );
    } else {
      storage.run(
        `INSERT INTO products (id, platform, platform_product_id, product_name, shop_name, image_url)
         VALUES (?, 'xhs', ?, ?, ?, ?)`,
        [
          product.id || crypto.randomUUID(),
          product.platform_product_id,
          product.product_name,
          product.shop_name,
          product.image_url,
        ]
      );
    }
  }

  private getSyncEndpoint(record: SyncRecord): string {
    const base = this.serverUrl || "";
    switch (record.type) {
      case "product":
        return `${base}/api/v1/sync/products`;
      case "feature":
        return `${base}/api/v1/sync/features`;
      case "ai_result":
        return `${base}/api/v1/sync/ai-results`;
      default:
        return `${base}/api/v1/sync/data`;
    }
  }

  async requestAIAnalysis(productId: string, analysisType: string): Promise<AIAnalysisResult | null> {
    if (!this.serverUrl || !this.token) return null;

    try {
      const axios = require("axios");
      const { data } = await axios.post(
        `${this.serverUrl}/api/v1/ai/analyze`,
        { productId, analysisType, platform: "xhs" },
        { headers: { Authorization: `Bearer ${this.token}` } }
      );

      if (data && data.result) {
        const aiResult: AIAnalysisResult = {
          id: data.id || crypto.randomUUID(),
          productId,
          analysisType,
          result: data.result,
          confidence: data.confidence || 0,
          analyzedAt: data.analyzedAt || new Date().toISOString(),
        };

        const storage = getStorage();
        this.saveAIResult(aiResult, storage);

        this.emit("ai:result", aiResult);
        return aiResult;
      }

      return null;
    } catch {
      return null;
    }
  }

  getPendingCount(): number {
    return this.pendingQueue.length;
  }

  clearPending(): number {
    const count = this.pendingQueue.length;
    this.pendingQueue = [];
    return count;
  }

  destroy(): void {
    this.stopAutoSync();
    this.pendingQueue = [];
    this.removeAllListeners();
  }
}

export const cloudSync = new CloudSyncManager();
