import { EventEmitter } from "events";
import { getStorage } from "../storage/sqlite";
import { licenseManager } from "../license/license-manager";
import { logger } from "../logger/logger";
import axios from "axios";

export interface SyncRecord {
  id: string;
  type: "product" | "feature" | "ai_result" | "category";
  localId: string;
  action: "create" | "update" | "delete";
  data: Record<string, unknown>;
  syncedAt: string | null;
  syncStatus: "pending" | "synced" | "failed" | "conflict";
  retryCount: number;
  createdAt: string;
  version: number;
  updatedAt: string;
}

export interface SyncStatus {
  lastSyncAt: string | null;
  pendingCount: number;
  syncedCount: number;
  failedCount: number;
  conflictCount: number;
  isSyncing: boolean;
  serverUrl: string | null;
}

export interface SyncConflict {
  id: string;
  type: "product" | "feature" | "category";
  localId: string;
  localData: Record<string, unknown>;
  localVersion: number;
  localUpdatedAt: string;
  serverData: Record<string, unknown>;
  serverVersion: number;
  serverUpdatedAt: string;
  resolution: "pending" | "local_wins" | "server_wins" | "merged";
  resolvedAt: string | null;
  createdAt: string;
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
  private conflicts: SyncConflict[] = [];
  private stats = {
    lastSyncAt: null as string | null,
    syncedCount: 0,
    failedCount: 0,
    conflictCount: 0,
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
      conflictCount: this.conflicts.length,
      isSyncing: this.isSyncing,
      serverUrl: this.serverUrl,
    };
  }

  getConflicts(): SyncConflict[] {
    return this.conflicts.filter(c => c.resolution === "pending");
  }

  getAllConflicts(): SyncConflict[] {
    return [...this.conflicts];
  }

  resolveConflict(conflictId: string, resolution: "local_wins" | "server_wins" | "merged"): boolean {
    const conflict = this.conflicts.find(c => c.id === conflictId);
    if (!conflict || conflict.resolution !== "pending") return false;

    conflict.resolution = resolution;
    conflict.resolvedAt = new Date().toISOString();

    const storage = getStorage();

    if (resolution === "local_wins") {
      this.reapplyLocalData(conflict, storage);
    } else if (resolution === "server_wins") {
      this.applyServerData(conflict, storage);
    } else {
      this.mergeData(conflict, storage);
    }

    storage.run(
      `UPDATE sync_conflicts SET resolution = ?, resolved_at = ? WHERE id = ?`,
      [resolution, conflict.resolvedAt, conflictId]
    );

    this.incrementLocalVersion(conflict.type, conflict.localId);

    this.emit("sync:conflict:resolved", { conflictId, resolution });
    return true;
  }

  private reapplyLocalData(conflict: SyncConflict, storage: ReturnType<typeof getStorage>): void {
    if (conflict.type === "product") {
      storage.run(
        `UPDATE products SET product_name = ?, shop_name = ?, image_url = ?, updated_at = datetime('now') WHERE id = ?`,
        [conflict.localData.product_name, conflict.localData.shop_name, conflict.localData.image_url, conflict.localId]
      );
    } else if (conflict.type === "feature") {
      storage.run(
        `UPDATE product_features SET price = ?, sales_count = ?, rating = ?, review_count = ?, favorite_count = ? WHERE id = ?`,
        [conflict.localData.price, conflict.localData.sales_count, conflict.localData.rating, conflict.localData.review_count, conflict.localData.favorite_count, conflict.localId]
      );
    } else if (conflict.type === "category") {
      storage.run(
        `UPDATE categories SET name = ?, icon = ?, color = ?, sort_order = ?, updated_at = datetime('now') WHERE id = ?`,
        [conflict.localData.name, conflict.localData.icon, conflict.localData.color, conflict.localData.sort_order, conflict.localId]
      );
    }
  }

  private applyServerData(conflict: SyncConflict, storage: ReturnType<typeof getStorage>): void {
    if (conflict.type === "product") {
      storage.run(
        `UPDATE products SET product_name = ?, shop_name = ?, image_url = ?, updated_at = datetime('now') WHERE id = ?`,
        [conflict.serverData.product_name, conflict.serverData.shop_name, conflict.serverData.image_url, conflict.localId]
      );
    } else if (conflict.type === "feature") {
      storage.run(
        `UPDATE product_features SET price = ?, sales_count = ?, rating = ?, review_count = ?, favorite_count = ? WHERE id = ?`,
        [conflict.serverData.price, conflict.serverData.sales_count, conflict.serverData.rating, conflict.serverData.review_count, conflict.serverData.favorite_count, conflict.localId]
      );
    } else if (conflict.type === "category") {
      storage.run(
        `UPDATE categories SET name = ?, icon = ?, color = ?, sort_order = ?, updated_at = datetime('now') WHERE id = ?`,
        [conflict.serverData.name, conflict.serverData.icon, conflict.serverData.color, conflict.serverData.sort_order, conflict.localId]
      );
    }
  }

  private mergeData(conflict: SyncConflict, storage: ReturnType<typeof getStorage>): void {
    const merged = { ...conflict.serverData, ...conflict.localData };
    if (conflict.type === "product") {
      storage.run(
        `UPDATE products SET product_name = ?, shop_name = ?, image_url = ?, updated_at = datetime('now') WHERE id = ?`,
        [merged.product_name, merged.shop_name, merged.image_url, conflict.localId]
      );
    } else if (conflict.type === "feature") {
      storage.run(
        `UPDATE product_features SET price = ?, sales_count = ?, rating = ?, review_count = ?, favorite_count = ? WHERE id = ?`,
        [merged.price, merged.sales_count, merged.rating, merged.review_count, merged.favorite_count, conflict.localId]
      );
    } else if (conflict.type === "category") {
      storage.run(
        `UPDATE categories SET name = ?, icon = ?, color = ?, sort_order = ?, updated_at = datetime('now') WHERE id = ?`,
        [merged.name, merged.icon, merged.color, merged.sort_order, conflict.localId]
      );
    }
  }

  private getLocalVersion(type: string, localId: string): number {
    const storage = getStorage();
    try {
      const rows = storage.query(
        "SELECT version FROM sync_versions WHERE record_type = ? AND record_id = ?",
        [type, localId]
      ) as Array<{ version: number }>;
      return rows.length > 0 ? rows[0].version : 1;
    } catch {
      return 1;
    }
  }

  private incrementLocalVersion(type: string, localId: string): void {
    const storage = getStorage();
    const current = this.getLocalVersion(type, localId);
    storage.run(
      `INSERT OR REPLACE INTO sync_versions (record_type, record_id, version, updated_at) VALUES (?, ?, ?, datetime('now'))`,
      [type, localId, current + 1]
    );
  }

  private ensureSyncTables(): void {
    const storage = getStorage();
    storage.run(`
      CREATE TABLE IF NOT EXISTS sync_versions (
        record_type TEXT NOT NULL,
        record_id TEXT NOT NULL,
        version INTEGER NOT NULL DEFAULT 1,
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        PRIMARY KEY (record_type, record_id)
      )
    `);
    storage.run(`
      CREATE TABLE IF NOT EXISTS sync_conflicts (
        id TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        local_id TEXT NOT NULL,
        local_data TEXT NOT NULL,
        local_version INTEGER NOT NULL,
        local_updated_at TEXT NOT NULL,
        server_data TEXT NOT NULL,
        server_version INTEGER NOT NULL,
        server_updated_at TEXT NOT NULL,
        resolution TEXT NOT NULL DEFAULT 'pending',
        resolved_at TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      )
    `);
  }

  enqueueProduct(product: Record<string, unknown>, action: "create" | "update" | "delete"): void {
    const localId = product.id as string;
    const version = action === "create" ? 1 : this.getLocalVersion("product", localId) + 1;
    this.incrementLocalVersion("product", localId);

    const record: SyncRecord = {
      id: crypto.randomUUID(),
      type: "product",
      localId,
      action,
      data: product,
      syncedAt: null,
      syncStatus: "pending",
      retryCount: 0,
      createdAt: new Date().toISOString(),
      version,
      updatedAt: new Date().toISOString(),
    };
    this.pendingQueue.push(record);
    this.emit("sync:queued", record);
  }

  enqueueFeature(productId: string, feature: Record<string, unknown>): void {
    const localId = (feature.id as string) || crypto.randomUUID();
    const version = this.getLocalVersion("feature", localId) + 1;
    this.incrementLocalVersion("feature", localId);

    const record: SyncRecord = {
      id: crypto.randomUUID(),
      type: "feature",
      localId,
      action: "create",
      data: { productId, ...feature },
      syncedAt: null,
      syncStatus: "pending",
      retryCount: 0,
      createdAt: new Date().toISOString(),
      version,
      updatedAt: new Date().toISOString(),
    };
    this.pendingQueue.push(record);
    this.emit("sync:queued", record);
  }

  enqueueCategory(category: Record<string, unknown>, action: "create" | "update" | "delete"): void {
    const localId = category.id as string;
    const version = action === "create" ? 1 : this.getLocalVersion("category", localId) + 1;
    this.incrementLocalVersion("category", localId);

    const record: SyncRecord = {
      id: crypto.randomUUID(),
      type: "category",
      localId,
      action,
      data: category,
      syncedAt: null,
      syncStatus: "pending",
      retryCount: 0,
      createdAt: new Date().toISOString(),
      version,
      updatedAt: new Date().toISOString(),
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
    logger.info("CloudSync", "开始同步", { pendingCount: this.pendingQueue.length });

    let pushed = 0;
    let errors = 0;

    try {
      pushed = await this.pushToServer();
      const pulled = await this.pullChangesFromServer();
      this.stats.lastSyncAt = new Date().toISOString();
      this.persistLastSyncAt();
      logger.info("CloudSync", "同步完成", { pushed, pulled, errors });
      this.emit("sync:complete", { pushed, pulled, errors });
      return { pushed, pulled, errors };
    } catch (err) {
      errors++;
      logger.error("CloudSync", "同步失败", err);
      this.emit("sync:error", { error: (err as Error).message });
      return { pushed, errors, pulled: 0 };
    } finally {
      this.isSyncing = false;
    }
  }

  async fullSync(): Promise<{ pushed: number; pulled: number; errors: number }> {
    if (this.isSyncing || !this.serverUrl || !this.token) {
      return { pushed: 0, pulled: 0, errors: 0 };
    }

    this.isSyncing = true;
    this.emit("sync:start");
    logger.info("CloudSync", "开始全量同步");

    let pushed = 0;
    let errors = 0;

    try {
      pushed = await this.batchPushToServer();
      const pulled = await this.pullChangesFromServer(true);
      this.stats.lastSyncAt = new Date().toISOString();
      this.persistLastSyncAt();
      logger.info("CloudSync", "全量同步完成", { pushed, pulled, errors });
      this.emit("sync:complete", { pushed, pulled, errors, fullSync: true });
      return { pushed, pulled, errors };
    } catch (err) {
      errors++;
      logger.error("CloudSync", "全量同步失败", err);
      this.emit("sync:error", { error: (err as Error).message });
      return { pushed, errors, pulled: 0 };
    } finally {
      this.isSyncing = false;
    }
  }

  private async batchPushToServer(): Promise<number> {
    if (this.pendingQueue.length === 0) return 0;
    if (!this.serverUrl || !this.token) return 0;

    const storage = getStorage();
    const products: Record<string, unknown>[] = [];
    const features: Record<string, unknown>[] = [];
    const categories: Record<string, unknown>[] = [];
    const deletions: Record<string, unknown>[] = [];

    const batch = this.pendingQueue.splice(0, SYNC_BATCH_SIZE);

    for (const record of batch) {
      if (record.action === "delete") {
        deletions.push({ type: record.type, id: record.localId });
        continue;
      }
      if (record.type === "product") {
        products.push(record.data);
      } else if (record.type === "feature") {
        features.push(record.data);
      } else if (record.type === "category") {
        categories.push(record.data);
      }
    }

    try {
      const { data } = await axios.post(
        `${this.serverUrl}/api/v1/sync/batch-push`,
        { products, features, categories, deletions },
        { headers: { Authorization: `Bearer ${this.token}` }, timeout: 60000 }
      );

      if (data && data.code === 0) {
        const result = data.data || {};
        const pushed = (result.products || 0) + (result.features || 0) + (result.categories || 0) + (result.deletions || 0);
        this.stats.syncedCount += pushed;

        for (const record of batch) {
          record.syncedAt = new Date().toISOString();
          record.syncStatus = "synced";
        }

        if (result.errors > 0) {
          logger.warn("CloudSync", "批量推送部分失败", { errors: result.errors });
        }

        return pushed;
      } else {
        for (const record of batch) {
          this.handleSinglePushFailure(record);
        }
        return 0;
      }
    } catch (err) {
      logger.error("CloudSync", "批量推送失败", err);
      for (const record of batch) {
        this.handleSinglePushFailure(record);
      }
      return 0;
    }
  }

  private async pullChangesFromServer(full: boolean = false): Promise<number> {
    if (!this.serverUrl || !this.token) return 0;

    const storage = getStorage();
    this.ensureSyncTables();

    try {
      const endpoint = full
        ? `${this.serverUrl}/api/v1/sync/full-pull`
        : `${this.serverUrl}/api/v1/sync/changes`;

      const requestBody: Record<string, unknown> = {
        include_products: true,
        include_features: true,
        include_categories: true,
        include_deletions: true,
      };

      if (!full && this.stats.lastSyncAt) {
        requestBody.since = this.stats.lastSyncAt;
      }

      const { data } = await axios.post(endpoint, requestBody, {
        headers: { Authorization: `Bearer ${this.token}` },
        timeout: 60000,
      });

      if (!data || data.code !== 0 || !data.data) return 0;

      const serverData = data.data;
      let pulled = 0;

      if (serverData.products && Array.isArray(serverData.products)) {
        for (const prod of serverData.products as Array<Record<string, unknown>>) {
          try {
            const existingRows = storage.query(
              "SELECT id FROM products WHERE id = ?",
              [prod.id]
            ) as Array<{ id: string }>;

            if (existingRows.length === 0) {
              storage.run(
                `INSERT INTO products (id, platform, platform_product_id, product_name, shop_name, image_url, category, category_id, product_url, is_active, last_collected_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
                [
                  prod.id,
                  prod.platform || "xhs",
                  prod.platform_product_id || "",
                  prod.product_name || "",
                  prod.shop_name || null,
                  prod.image_url || null,
                  prod.category || null,
                  prod.category_id || null,
                  prod.product_url || null,
                  prod.is_active !== false ? 1 : 0,
                  prod.last_collected_at || null,
                ]
              );
              pulled++;
            } else {
              const conflictDetected = this.detectConflictOnPull(storage, "product", prod.id as string, prod);
              if (conflictDetected) continue;

              storage.run(
                `UPDATE products SET product_name = ?, shop_name = ?, image_url = ?, category = ?, category_id = ?, product_url = ?, is_active = ?, last_collected_at = ?, updated_at = datetime('now')
                 WHERE id = ?`,
                [
                  prod.product_name,
                  prod.shop_name || null,
                  prod.image_url || null,
                  prod.category || null,
                  prod.category_id || null,
                  prod.product_url || null,
                  prod.is_active !== false ? 1 : 0,
                  prod.last_collected_at || null,
                  prod.id,
                ]
              );
              pulled++;
            }
          } catch (err) {
            logger.warn("CloudSync", "拉取产品失败", { id: prod.id, err });
          }
        }
      }

      if (serverData.features && Array.isArray(serverData.features)) {
        for (const feat of serverData.features as Array<Record<string, unknown>>) {
          try {
            if (!feat.product_id) continue;

            const existingFeatures = storage.query(
              "SELECT id FROM product_features WHERE id = ?",
              [feat.id]
            ) as Array<{ id: string }>;

            if (existingFeatures.length === 0) {
              const productRows = storage.query(
                "SELECT id FROM products WHERE id = ?",
                [feat.product_id]
              ) as Array<{ id: string }>;

              if (productRows.length === 0) continue;

              storage.run(
                `INSERT INTO product_features (id, product_id, price, original_price, sales_count, monthly_sales, rating, review_count, favorite_count, stock_status, extra_features, source, collected_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
                [
                  feat.id || crypto.randomUUID(),
                  feat.product_id,
                  feat.price ?? null,
                  feat.original_price ?? null,
                  feat.sales_count ?? null,
                  feat.monthly_sales ?? null,
                  feat.rating ?? null,
                  feat.review_count ?? null,
                  feat.favorite_count ?? null,
                  feat.stock_status ?? null,
                  JSON.stringify(feat.extra_features || {}),
                  feat.source || "cloud",
                  feat.collected_at || new Date().toISOString(),
                ]
              );
              pulled++;
            }
          } catch (err) {
            logger.warn("CloudSync", "拉取特征失败", { id: feat.id, err });
          }
        }
      }

      if (serverData.categories && Array.isArray(serverData.categories)) {
        for (const cat of serverData.categories as Array<Record<string, unknown>>) {
          try {
            const existingCats = storage.query(
              "SELECT id FROM categories WHERE id = ?",
              [cat.id]
            ) as Array<{ id: string }>;

            if (existingCats.length === 0) {
              storage.run(
                `INSERT INTO categories (id, name, icon, color, sort_order, parent_id, is_active, created_at, updated_at)
                 VALUES (?, ?, ?, ?, ?, ?, 1, datetime('now'), datetime('now'))`,
                [cat.id, cat.name, cat.icon || null, cat.color || null, cat.sort_order || 0, cat.parent_id || null]
              );
              pulled++;
            } else {
              storage.run(
                `UPDATE categories SET name = ?, icon = ?, color = ?, sort_order = ?, parent_id = ?, updated_at = datetime('now') WHERE id = ?`,
                [cat.name, cat.icon || null, cat.color || null, cat.sort_order || 0, cat.parent_id || null, cat.id]
              );
              pulled++;
            }
          } catch (err) {
            logger.warn("CloudSync", "拉取分类失败", { id: cat.id, err });
          }
        }
      }

      if (serverData.deletions && Array.isArray(serverData.deletions)) {
        for (const del of serverData.deletions as Array<Record<string, unknown>>) {
          try {
            if (del.type === "product" && del.id) {
              storage.run(
                "UPDATE products SET is_active = 0, updated_at = datetime('now') WHERE id = ?",
                [del.id]
              );
              pulled++;
            } else if (del.type === "category" && del.id) {
              storage.run("DELETE FROM categories WHERE id = ?", [del.id]);
              pulled++;
            }
          } catch (err) {
            logger.warn("CloudSync", "应用删除失败", { type: del.type, id: del.id, err });
          }
        }
      }

      this.emit("sync:pulled", { count: pulled });
      const pendingConflicts = this.conflicts.filter(c => c.resolution === "pending");
      if (pendingConflicts.length > 0) {
        this.emit("sync:conflict:detected", { count: pendingConflicts.length });
      }
      return pulled;
    } catch (err) {
      logger.error("CloudSync", "增量拉取失败", err);
      return 0;
    }
  }

  async getServerSyncStatus(): Promise<Record<string, unknown> | null> {
    if (!this.serverUrl || !this.token) return null;

    try {
      const { data } = await axios.get(
        `${this.serverUrl}/api/v1/sync/status`,
        { headers: { Authorization: `Bearer ${this.token}` }, timeout: 10000 }
      );
      if (data && data.code === 0) {
        return data.data;
      }
      return null;
    } catch {
      return null;
    }
  }

  private persistLastSyncAt(): void {
    const storage = getStorage();
    this.ensureSyncTables();
    storage.run(
      `INSERT OR REPLACE INTO sync_versions (record_type, record_id, version, updated_at) VALUES ('__last_sync', '__global', 1, ?)`,
      [this.stats.lastSyncAt || new Date().toISOString()]
    );
  }

  loadLastSyncAt(): void {
    const storage = getStorage();
    this.ensureSyncTables();
    try {
      const rows = storage.query(
        "SELECT updated_at FROM sync_versions WHERE record_type = '__last_sync' AND record_id = '__global'"
      ) as Array<{ updated_at: string }>;
      if (rows.length > 0) {
        this.stats.lastSyncAt = rows[0].updated_at;
      }
    } catch {
      this.stats.lastSyncAt = null;
    }
  }

  private async pushToServer(): Promise<number> {
    if (this.pendingQueue.length === 0) return 0;
    if (!this.serverUrl || !this.token) return 0;

    let pushed = 0;
    const batch = this.pendingQueue.splice(0, SYNC_BATCH_SIZE);

    const categoryRecords = batch.filter(r => r.type === "category");
    const productFeatureRecords = batch.filter(r => r.type !== "category");

    for (const record of categoryRecords) {
      try {
        const catData = record.data;
        let response: { data: { code: number } };

        if (record.action === "create") {
          response = await axios.post(
            `${this.serverUrl}/api/v1/categories`,
            {
              name: catData.name,
              icon: catData.icon || null,
              color: catData.color || null,
              sort_order: catData.sort_order || 0,
              parent_id: catData.parent_id || null,
            },
            { headers: { Authorization: `Bearer ${this.token}` }, timeout: 15000 }
          );
        } else if (record.action === "update") {
          response = await axios.put(
            `${this.serverUrl}/api/v1/categories/${record.localId}`,
            {
              name: catData.name,
              icon: catData.icon,
              color: catData.color,
              sort_order: catData.sort_order,
              parent_id: catData.parent_id,
            },
            { headers: { Authorization: `Bearer ${this.token}` }, timeout: 15000 }
          );
        } else {
          response = await axios.delete(
            `${this.serverUrl}/api/v1/categories/${record.localId}`,
            { headers: { Authorization: `Bearer ${this.token}` }, timeout: 15000 }
          );
        }

        if (response.data && response.data.code === 0) {
          pushed++;
          this.stats.syncedCount++;
          record.syncedAt = new Date().toISOString();
          record.syncStatus = "synced";
        } else {
          this.handleSinglePushFailure(record);
        }
      } catch {
        this.handleSinglePushFailure(record);
      }
    }

    const grouped = new Map<string, { product: SyncRecord | null; features: SyncRecord[] }>();

    for (const record of productFeatureRecords) {
      const ppid = (record.data.platform_product_id as string) || record.localId;
      if (!grouped.has(ppid)) {
        grouped.set(ppid, { product: null, features: [] });
      }
      const group = grouped.get(ppid)!;
      if (record.type === "product") {
        group.product = record;
      } else if (record.type === "feature") {
        group.features.push(record);
      }
    }

    for (const [ppid, group] of grouped) {
      try {
        const platform = (group.product?.data.platform as string) || "xhs";
        const features = group.features.length > 0
          ? group.features.map(f => ({
              ...f.data,
              collected_at: f.data.collected_at || new Date().toISOString(),
            }))
          : group.product
            ? [{
                product_name: group.product.data.product_name,
                shop_name: group.product.data.shop_name,
                price: group.product.data.latest_price ?? group.product.data.price,
                sales_count: group.product.data.latest_sales ?? group.product.data.sales_count,
                monthly_sales: group.product.data.monthly_sales,
                rating: group.product.data.latest_rating ?? group.product.data.rating,
                collected_at: group.product.data.last_collected_at || new Date().toISOString(),
              }]
            : [];

        const response = await axios.post(
          `${this.serverUrl}/api/v1/sync/push`,
          {
            platform,
            platform_product_id: ppid,
            features,
          },
          {
            headers: { Authorization: `Bearer ${this.token}` },
            timeout: 30000,
          }
        );

        if (response.data && response.data.code === 0) {
          pushed++;
          this.stats.syncedCount++;
          const allRecords = [group.product, ...group.features].filter(Boolean) as SyncRecord[];
          for (const r of allRecords) {
            r.syncedAt = new Date().toISOString();
            r.syncStatus = "synced";
          }
        } else {
          this.handlePushFailure(group);
        }
      } catch {
        this.handlePushFailure(group);
      }
    }

    return pushed;
  }

  private handlePushFailure(group: { product: SyncRecord | null; features: SyncRecord[] }): void {
    const allRecords = [group.product, ...group.features].filter(Boolean) as SyncRecord[];
    for (const r of allRecords) {
      r.retryCount++;
      if (r.retryCount < MAX_RETRY) {
        this.pendingQueue.push(r);
      } else {
        r.syncStatus = "failed";
        this.stats.failedCount++;
      }
    }
  }

  private handleSinglePushFailure(record: SyncRecord): void {
    record.retryCount++;
    if (record.retryCount < MAX_RETRY) {
      this.pendingQueue.push(record);
    } else {
      record.syncStatus = "failed";
      this.stats.failedCount++;
    }
  }

  private async pullFromServer(): Promise<number> {
    if (!this.serverUrl || !this.token) return 0;

    try {
      const { data } = await axios.post(
        `${this.serverUrl}/api/v1/sync/pull`,
        {
          since: this.stats.lastSyncAt,
        },
        {
          headers: { Authorization: `Bearer ${this.token}` },
          timeout: 30000,
        }
      );

      if (!data || data.code !== 0 || !data.data) return 0;

      let pulled = 0;
      const storage = getStorage();
      this.ensureSyncTables();
      const features = Array.isArray(data.data) ? data.data : data.data.features || [];

      for (const feat of features) {
        try {
          if (feat.product_id) {
            const productRows = storage.query(
              "SELECT id FROM products WHERE platform_product_id = ?",
              [feat.platform_product_id]
            ) as Array<{ id: string }>;

            if (productRows.length === 0 && feat.product_name) {
              storage.run(
                `INSERT INTO products (id, platform, platform_product_id, product_name, shop_name, image_url, last_collected_at)
                 VALUES (?, ?, ?, ?, ?, ?, datetime('now'))`,
                [
                  feat.product_id || crypto.randomUUID(),
                  feat.platform || "xhs",
                  feat.platform_product_id,
                  feat.product_name,
                  feat.shop_name,
                  feat.image_url || null,
                ]
              );
              pulled++;
            } else if (productRows.length > 0) {
              const localId = productRows[0].id;
              const conflictDetected = this.detectConflictOnPull(storage, "product", localId, feat);
              if (conflictDetected) {
                continue;
              }
            }

            if (feat.id) {
              const featureRows = storage.query(
                "SELECT id FROM product_features WHERE product_id = ? ORDER BY collected_at DESC LIMIT 1",
                [feat.product_id]
              ) as Array<{ id: string }>;

              if (featureRows.length > 0) {
                const localFeatureId = featureRows[0].id;
                const conflictDetected = this.detectConflictOnPull(storage, "feature", localFeatureId, feat);
                if (conflictDetected) {
                  continue;
                }
              }

              storage.run(
                `INSERT OR REPLACE INTO product_features (id, product_id, price, original_price, sales_count, monthly_sales,
                 rating, review_count, favorite_count, stock_status, extra_features, source, collected_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
                [
                  feat.id || crypto.randomUUID(),
                  feat.product_id,
                  feat.price ?? null,
                  feat.original_price ?? null,
                  feat.sales_count ?? null,
                  feat.monthly_sales ?? null,
                  feat.rating ?? null,
                  feat.review_count ?? null,
                  feat.favorite_count ?? null,
                  feat.stock_status ?? null,
                  JSON.stringify(feat.extra_features || {}),
                  feat.source || "cloud",
                  feat.collected_at || new Date().toISOString(),
                ]
              );
              pulled++;
            }
          }
        } catch (err) { logger.warn("[Main] operation failed:", err); }
      }

      try {
        const catResponse = await axios.get(
          `${this.serverUrl}/api/v1/categories`,
          { headers: { Authorization: `Bearer ${this.token}` }, timeout: 15000 }
        );
        if (catResponse.data?.code === 0 && catResponse.data?.data?.categories) {
          const serverCategories = catResponse.data.data.categories as Array<Record<string, unknown>>;
          for (const cat of serverCategories) {
            const localRows = storage.query(
              "SELECT id FROM categories WHERE id = ?",
              [cat.id]
            ) as Array<{ id: string }>;
            if (localRows.length === 0) {
              storage.run(
                `INSERT INTO categories (id, name, icon, color, sort_order, parent_id, is_active, created_at, updated_at)
                 VALUES (?, ?, ?, ?, ?, ?, 1, datetime('now'), datetime('now'))`,
                [cat.id, cat.name, cat.icon || null, cat.color || null, cat.sort_order || 0, cat.parent_id || null]
              );
              pulled++;
            } else {
              storage.run(
                `UPDATE categories SET name = ?, icon = ?, color = ?, sort_order = ?, parent_id = ?, updated_at = datetime('now') WHERE id = ?`,
                [cat.name, cat.icon || null, cat.color || null, cat.sort_order || 0, cat.parent_id || null, cat.id]
              );
            }
          }
        }
      } catch (err) { logger.warn("[CloudSync] category pull failed:", err); }

      this.emit("sync:pulled", { count: pulled });
      if (this.conflicts.filter(c => c.resolution === "pending").length > 0) {
        this.emit("sync:conflict:detected", { count: this.conflicts.filter(c => c.resolution === "pending").length });
      }
      return pulled;
    } catch {
      return 0;
    }
  }

  private detectConflictOnPull(
    storage: ReturnType<typeof getStorage>,
    type: "product" | "feature" | "category",
    localId: string,
    serverData: Record<string, unknown>
  ): boolean {
    const localVersion = this.getLocalVersion(type, localId);
    const serverVersion = (serverData.version as number) || 1;
    const serverUpdatedAt = (serverData.updated_at as string) || new Date().toISOString();

    const localData = this.getLocalData(storage, type, localId);
    if (!localData) return false;

    const localUpdatedAt = (localData.updated_at as string) || (localData.last_collected_at as string) || "";

    const hasLocalChanges = this.hasLocalModifications(type, localData, serverData);

    if (localVersion > 1 && hasLocalChanges && serverVersion > localVersion) {
      const conflict: SyncConflict = {
        id: crypto.randomUUID(),
        type,
        localId,
        localData,
        localVersion,
        localUpdatedAt,
        serverData,
        serverVersion,
        serverUpdatedAt,
        resolution: "pending",
        resolvedAt: null,
        createdAt: new Date().toISOString(),
      };

      this.conflicts.push(conflict);
      this.persistConflict(storage, conflict);

      const record = this.pendingQueue.find(
        r => r.type === type && r.localId === localId
      );
      if (record) {
        record.syncStatus = "conflict";
      }

      this.stats.conflictCount++;
      return true;
    }

    return false;
  }

  private getLocalData(
    storage: ReturnType<typeof getStorage>,
    type: "product" | "feature" | "category",
    localId: string
  ): Record<string, unknown> | null {
    try {
      if (type === "product") {
        const rows = storage.query("SELECT * FROM products WHERE id = ?", [localId]) as Record<string, unknown>[];
        return rows.length > 0 ? rows[0] : null;
      } else if (type === "feature") {
        const rows = storage.query("SELECT * FROM product_features WHERE id = ?", [localId]) as Record<string, unknown>[];
        return rows.length > 0 ? rows[0] : null;
      } else if (type === "category") {
        const rows = storage.query("SELECT * FROM categories WHERE id = ?", [localId]) as Record<string, unknown>[];
        return rows.length > 0 ? rows[0] : null;
      }
    } catch (err) { logger.warn("[Main] operation failed:", err); }
    return null;
  }

  private hasLocalModifications(
    type: "product" | "feature" | "category",
    localData: Record<string, unknown>,
    serverData: Record<string, unknown>
  ): boolean {
    if (type === "product") {
      const fields = ["product_name", "shop_name", "image_url"] as const;
      return fields.some(f => localData[f] !== serverData[f]);
    } else if (type === "feature") {
      const fields = ["price", "sales_count", "rating", "review_count", "favorite_count"] as const;
      return fields.some(f => localData[f] !== serverData[f]);
    } else if (type === "category") {
      const fields = ["name", "icon", "color", "sort_order"] as const;
      return fields.some(f => localData[f] !== serverData[f]);
    }
    return false;
  }

  private persistConflict(storage: ReturnType<typeof getStorage>, conflict: SyncConflict): void {
    storage.run(
      `INSERT OR REPLACE INTO sync_conflicts
       (id, type, local_id, local_data, local_version, local_updated_at, server_data, server_version, server_updated_at, resolution, resolved_at, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        conflict.id,
        conflict.type,
        conflict.localId,
        JSON.stringify(conflict.localData),
        conflict.localVersion,
        conflict.localUpdatedAt,
        JSON.stringify(conflict.serverData),
        conflict.serverVersion,
        conflict.serverUpdatedAt,
        conflict.resolution,
        conflict.resolvedAt,
        conflict.createdAt,
      ]
    );
  }

  loadPersistedConflicts(): void {
    const storage = getStorage();
    this.ensureSyncTables();
    try {
      const rows = storage.query(
        "SELECT * FROM sync_conflicts WHERE resolution = 'pending' ORDER BY created_at DESC"
      ) as Array<Record<string, unknown>>;
      this.conflicts = rows.map(row => ({
        id: row.id as string,
        type: row.type as "product" | "feature",
        localId: row.local_id as string,
        localData: JSON.parse(row.local_data as string),
        localVersion: row.local_version as number,
        localUpdatedAt: row.local_updated_at as string,
        serverData: JSON.parse(row.server_data as string),
        serverVersion: row.server_version as number,
        serverUpdatedAt: row.server_updated_at as string,
        resolution: row.resolution as "pending" | "local_wins" | "server_wins" | "merged",
        resolvedAt: row.resolved_at as string | null,
        createdAt: row.created_at as string,
      }));
    } catch {
      this.conflicts = [];
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
    if (!this.serverUrl || !this.token) {
      throw new Error("network: 未连接到服务器，请先登录");
    }

    try {
      const { data } = await axios.post(
        `${this.serverUrl}/api/v1/ai/analyze`,
        { product_id: productId, analysis_type: analysisType },
        { headers: { Authorization: `Bearer ${this.token}` }, timeout: 60000 }
      );

      if (data && data.code === 0 && data.data) {
        const aiData = data.data;
        const aiResult: AIAnalysisResult = {
          id: aiData.id || crypto.randomUUID(),
          productId,
          analysisType,
          result: aiData.result || {},
          confidence: aiData.result?.confidence || 0,
          analyzedAt: new Date().toISOString(),
        };

        const storage = getStorage();
        this.saveAIResult(aiResult, storage);

        this.emit("ai:result", aiResult);
        return aiResult;
      }

      const errMsg = data?.message || data?.data?.message || "AI分析请求失败";
      if (errMsg.includes("permission") || errMsg.includes("gate") || errMsg.includes("权限")) {
        throw new Error(`permission: ${errMsg}`);
      }
      if (errMsg.includes("quota") || errMsg.includes("配额") || errMsg.includes("limit")) {
        throw new Error(`quota: ${errMsg}`);
      }
      throw new Error(`provider: ${errMsg}`);
    } catch (err) {
      if (err instanceof Error && (err.message.startsWith("permission:") || err.message.startsWith("quota:") || err.message.startsWith("provider:"))) {
        throw err;
      }
      const axiosErr = err as { code?: string; message?: string };
      if (axiosErr.code === "ECONNREFUSED" || axiosErr.code === "ETIMEDOUT" || axiosErr.code === "ERR_NETWORK") {
        throw new Error("network: 网络连接失败，请检查网络后重试");
      }
      if (axiosErr.message?.includes("timeout")) {
        throw new Error("network: 请求超时，请稍后重试");
      }
      logger.error("CloudSync", "AI分析请求失败", err);
      throw new Error(`unknown: ${err instanceof Error ? err.message : "AI分析请求失败"}`);
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
