import { ipcMain, app } from "electron";
import { getStorage } from "../storage/sqlite";
import { getSecureStorage } from "../storage/secure-storage";
import { logger } from "../logger/logger";

export function registerStorageHandlers(): void {
  ipcMain.handle("storage:insert-product", async (_event, product: Record<string, unknown>) => {
    const storage = getStorage();
    return storage.insertProduct(product);
  });

  ipcMain.handle("storage:batch-insert-products", async (_event, products: Record<string, unknown>[]) => {
    const storage = getStorage();
    let imported = 0;
    let duplicated = 0;
    let failed = 0;
    const failedItems: { platform_product_id: string; reason: string }[] = [];

    for (const p of products) {
      try {
        const existing = storage.query(
          "SELECT id FROM products WHERE platform = ? AND platform_product_id = ? AND is_active = 1",
          [p.platform || "xhs", p.platform_product_id]
        ) as Record<string, unknown>[];
        if (existing.length > 0) {
          duplicated++;
          continue;
        }
        storage.insertProduct(p);
        imported++;
      } catch (e) {
        failed++;
        failedItems.push({
          platform_product_id: String(p.platform_product_id || ""),
          reason: String(e),
        });
      }
    }

    return { total: products.length, imported, duplicated, failed, failedItems };
  });

  ipcMain.handle("storage:get-products", async (_event, filters?: Record<string, unknown>) => {
    const storage = getStorage();
    return storage.getProducts(filters);
  });

  ipcMain.handle("storage:save-features", async (_event, productId: string, features: Record<string, unknown>) => {
    const storage = getStorage();
    return storage.saveFeatures(productId, features);
  });

  ipcMain.handle("storage:get-features", async (_event, productId: string) => {
    const storage = getStorage();
    return storage.safeQuery("product_features", "product_id = ?", [productId], "collected_at DESC", 30);
  });

  ipcMain.handle("storage:deactivate-product", async (_event, productId: string) => {
    const storage = getStorage();
    storage.safeRun("products", "is_active = 0, updated_at = datetime('now')", "id = ?", [productId]);
    return { updated: true };
  });

  ipcMain.handle("storage:get-ai-analyses", async (_event, productId?: string) => {
    const storage = getStorage();
    if (productId) {
      return storage.safeQuery("ai_analysis", "product_id = ?", [productId], "analyzed_at DESC", 50);
    }
    return storage.safeQuery("ai_analysis", "", [], "analyzed_at DESC", 100);
  });

  ipcMain.handle("storage:export-all", async () => {
    const storage = getStorage();
    const tables = ["products", "product_features", "ai_analysis", "monitor_rules", "local_notifications"] as const;
    const result: Record<string, unknown[]> = {};
    for (const table of tables) {
      try {
        result[table] = storage.safeSelectAll(table);
      } catch (err) {
        logger.error("handlers", `export table ${table} failed: ${err}`);
      }
    }
    return result;
  });

  ipcMain.handle("storage:cleanup", async (_event, days: number) => {
    const storage = getStorage();
    const cutoff = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString();
    let deleted = 0;
    try {
      storage.safeDelete("product_features", "collected_at < ?", [cutoff]);
      deleted += (storage.query("SELECT changes() as cnt") as Array<{ cnt: number }>)[0]?.cnt || 0;
    } catch (err) {
      logger.error("handlers", `cleanup product_features failed: ${err}`);
    }
    try {
      storage.safeDelete("local_notifications", "created_at < ?", [cutoff]);
      deleted += (storage.query("SELECT changes() as cnt") as Array<{ cnt: number }>)[0]?.cnt || 0;
    } catch (err) {
      logger.error("handlers", `cleanup local_notifications failed: ${err}`);
    }
    try {
      storage.safeDelete("ai_analysis", "analyzed_at < ?", [cutoff]);
      deleted += (storage.query("SELECT changes() as cnt") as Array<{ cnt: number }>)[0]?.cnt || 0;
    } catch (err) {
      logger.error("handlers", `cleanup ai_analysis failed: ${err}`);
    }
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

  ipcMain.handle("secure-storage:get", async (_event, key: string) => {
    const secureStore = getSecureStorage();
    return secureStore.get(key);
  });

  ipcMain.handle("secure-storage:set", async (_event, key: string, value: string) => {
    const secureStore = getSecureStorage();
    secureStore.set(key, value);
    return true;
  });

  ipcMain.handle("secure-storage:delete", async (_event, key: string) => {
    const secureStore = getSecureStorage();
    secureStore.delete(key);
    return true;
  });
}
