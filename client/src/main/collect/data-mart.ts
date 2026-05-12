import { EventEmitter } from "events";
import { getStorage } from "../storage/sqlite";
import { normalizer, NormalizedXHSData, NormalizationResult } from "../collect/normalizer";
import { featureEngine } from "../feature/feature-engine";
import { localRuleEvaluator } from "../monitor/local-evaluator";
import { logger } from "../logger/logger";

export interface DataMartEntry {
  id: string;
  platform: string;
  platform_product_id: string;
  product_name: string;
  shop_name: string | null;
  category: string | null;
  image_url: string | null;
  product_url: string | null;
  latest_price: number | null;
  latest_sales: number | null;
  latest_rating: number | null;
  quality_score: number;
  anomaly_flags: string[];
  feature_count: number;
  last_collected_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface FusionResult {
  action: "created" | "updated" | "skipped";
  product_id: string;
  quality_score: number;
  anomalies: string[];
  daily_sales_delta: number | null;
}

export class DataMart extends EventEmitter {
  private dedupCache: Map<string, { id: string; lastCollected: string }> = new Map();
  private cacheLoaded: boolean = false;

  async ingest(normalized: NormalizationProduct, userId: string): Promise<FusionResult> {
    if (!this.cacheLoaded) {
      await this.loadDedupCache();
    }

    const key = `${normalized.platform}:${normalized.platform_product_id}`;
    const storage = getStorage();
    const anomalies = this.detectAnomalies(normalized);

    const existing = this.findExistingProduct(key);

    if (existing) {
      logger.debug("DataMart", "更新已有商品数据", { key, productId: existing.id });
      return this.updateExisting(existing.id, normalized, anomalies, key);
    } else {
      logger.debug("DataMart", "创建新商品数据", { key });
      return this.createNew(normalized, userId, anomalies, key);
    }
  }

  private async loadDedupCache(): Promise<void> {
    try {
      const storage = getStorage();
      const rows = storage.query("SELECT id, platform, platform_product_id, last_collected_at FROM products") as Array<{
        id: string;
        platform: string;
        platform_product_id: string;
        last_collected_at: string | null;
      }>;
      for (const row of rows) {
        const key = `${row.platform}:${row.platform_product_id}`;
        this.dedupCache.set(key, { id: row.id, lastCollected: row.last_collected_at || "" });
      }
      this.cacheLoaded = true;
    } catch {}
  }

  private findExistingProduct(key: string): { id: string; lastCollected: string } | null {
    return this.dedupCache.get(key) || null;
  }

  private updateExisting(
    existing: { id: string; lastCollected: string },
    normalized: NormalizationProduct,
    anomalies: string[],
    cacheKey: string
  ): FusionResult {
    const storage = getStorage();

    storage.run(
      `UPDATE products SET product_name = ?, shop_name = ?, category = ?, image_url = ?,
       product_url = ?, last_collected_at = datetime('now'), updated_at = datetime('now')
       WHERE id = ?`,
      [
        normalized.product_name,
        normalized.shop_name || null,
        normalized.category || null,
        normalized.image_url || null,
        normalized.product_url || null,
        existing.id,
      ]
    );

    const dailyDelta = this.calculateDailyDelta(existing.id, normalized);

    storage.run(
      `INSERT INTO product_features (id, product_id, price, original_price, sales_count, monthly_sales,
       rating, review_count, favorite_count, stock_status, extra_features, source, collected_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))`,
      [
        crypto.randomUUID(),
        existing.id,
        normalized.price ?? null,
        normalized.original_price ?? null,
        normalized.sales_count ?? null,
        normalized.monthly_sales ?? null,
        normalized.rating ?? null,
        normalized.review_count ?? null,
        normalized.favorite_count ?? null,
        normalized.stock_status ?? null,
        JSON.stringify({ anomalies, quality_score: this.scoreData(normalized) }),
        "local",
      ]
    );

    this.dedupCache.set(cacheKey, { id: existing.id, lastCollected: new Date().toISOString() });

    const result: FusionResult = {
      action: "updated",
      product_id: existing.id,
      quality_score: this.scoreData(normalized),
      anomalies,
      daily_sales_delta: dailyDelta,
    };

    this.emit("data:updated", result);
    setImmediate(() => featureEngine.computeForProduct(existing.id));
    setImmediate(() => {
      try {
        const triggered = localRuleEvaluator.evaluateForProduct(existing.id);
        if (triggered > 0) {
          this.emit("monitor:triggered", { productId: existing.id, count: triggered });
        }
      } catch {}
    });
    return result;
  }

  private createNew(
    normalized: NormalizationProduct,
    userId: string,
    anomalies: string[],
    cacheKey: string
  ): FusionResult {
    const storage = getStorage();
    const productId = crypto.randomUUID();

    storage.run(
      `INSERT INTO products (id, platform, platform_product_id, product_name, shop_name, category,
       image_url, product_url, last_collected_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))`,
      [
        productId,
        normalized.platform,
        normalized.platform_product_id,
        normalized.product_name,
        normalized.shop_name || null,
        normalized.category || null,
        normalized.image_url || null,
        normalized.product_url || null,
      ]
    );

    storage.run(
      `INSERT INTO product_features (id, product_id, price, original_price, sales_count, monthly_sales,
       rating, review_count, favorite_count, stock_status, extra_features, source, collected_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))`,
      [
        crypto.randomUUID(),
        productId,
        normalized.price ?? null,
        normalized.original_price ?? null,
        normalized.sales_count ?? null,
        normalized.monthly_sales ?? null,
        normalized.rating ?? null,
        normalized.review_count ?? null,
        normalized.favorite_count ?? null,
        normalized.stock_status ?? null,
        JSON.stringify({ anomalies, quality_score: this.scoreData(normalized) }),
        "local",
      ]
    );

    this.dedupCache.set(cacheKey, { id: productId, lastCollected: new Date().toISOString() });

    const result: FusionResult = {
      action: "created",
      product_id: productId,
      quality_score: this.scoreData(normalized),
      anomalies,
      daily_sales_delta: null,
    };

    this.emit("data:created", result);
    setImmediate(() => featureEngine.computeForProduct(productId));
    return result;
  }

  private calculateDailyDelta(productId: string, normalized: NormalizationProduct): number | null {
    if (normalized.sales_count === null || normalized.sales_count === undefined) return null;

    try {
      const storage = getStorage();
      const rows = storage.query(
        `SELECT sales_count FROM product_features
         WHERE product_id = ? AND sales_count IS NOT NULL
         ORDER BY collected_at DESC LIMIT 1`,
        [productId]
      ) as Array<{ sales_count: number }>;

      if (rows.length > 0 && rows[0].sales_count !== null) {
        return Math.max(0, normalized.sales_count - rows[0].sales_count);
      }
    } catch {}

    return null;
  }

  private detectAnomalies(data: NormalizationProduct): string[] {
    const anomalies: string[] = [];

    if (data.price !== null && data.price !== undefined && data.price <= 0) {
      anomalies.push("price_zero_or_negative");
    }
    if (data.price !== null && data.price !== undefined && data.price > 999999) {
      anomalies.push("price_abnormally_high");
    }
    if (data.sales_count !== null && data.sales_count !== undefined && data.sales_count < 0) {
      anomalies.push("sales_negative");
    }
    if (data.rating !== null && data.rating !== undefined && (data.rating < 0 || data.rating > 5)) {
      anomalies.push("rating_out_of_range");
    }
    if (!data.product_name || data.product_name.trim().length < 2) {
      anomalies.push("name_too_short");
    }
    if (!data.image_url) {
      anomalies.push("missing_image");
    }

    return anomalies;
  }

  private scoreData(data: NormalizationProduct): number {
    let score = 100;
    if (!data.price && data.price !== 0) score -= 15;
    if (!data.sales_count && data.sales_count !== 0) score -= 10;
    if (!data.rating && data.rating !== 0) score -= 10;
    if (!data.review_count && data.review_count !== 0) score -= 5;
    if (!data.shop_name) score -= 5;
    if (!data.image_url) score -= 5;
    if (!data.category) score -= 3;
    return Math.max(0, score);
  }

  getProduct(productId: string): DataMartEntry | null {
    try {
      const storage = getStorage();
      const rows = storage.query(
        `SELECT p.*, COUNT(pf.id) as feature_count
         FROM products p LEFT JOIN product_features pf ON p.id = pf.product_id
         WHERE p.id = ? GROUP BY p.id`,
        [productId]
      ) as DataMartEntry[];
      return rows.length > 0 ? rows[0] : null;
    } catch {
      return null;
    }
  }

  listProducts(platform?: string, limit: number = 50): DataMartEntry[] {
    try {
      const storage = getStorage();
      let sql = `SELECT p.*, COUNT(pf.id) as feature_count
                 FROM products p LEFT JOIN product_features pf ON p.id = pf.product_id
                 WHERE p.is_active = 1`;
      const params: unknown[] = [];
      if (platform) {
        sql += ` AND p.platform = ?`;
        params.push(platform);
      }
      sql += ` GROUP BY p.id ORDER BY p.updated_at DESC LIMIT ?`;
      params.push(limit);
      return storage.query(sql, params) as DataMartEntry[];
    } catch {
      return [];
    }
  }

  invalidateCache(): void {
    this.dedupCache.clear();
    this.cacheLoaded = false;
  }

  destroy(): void {
    this.dedupCache.clear();
    this.removeAllListeners();
  }
}

type NormalizationProduct = NormalizedXHSData;

export const dataMart = new DataMart();
