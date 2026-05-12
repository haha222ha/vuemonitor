import { getStorage } from "../storage/sqlite";

export interface FeatureRecord {
  id: string;
  product_id: string;
  category: string | null;
  sales_velocity: number | null;
  growth_rate_7d: number | null;
  growth_rate_30d: number | null;
  volatility: number | null;
  competition_index: number | null;
  lifecycle_stage: string | null;
  trend_short: string | null;
  trend_long: string | null;
  calculated_at: string;
}

export interface FeatureEngineStats {
  totalComputed: number;
  lastRunAt: string | null;
  errors: number;
}

export class FeatureEngine {
  private stats: FeatureEngineStats = {
    totalComputed: 0,
    lastRunAt: null,
    errors: 0,
  };

  computeForProduct(productId: string): FeatureRecord | null {
    try {
      const storage = getStorage();

      const productRows = storage.query(
        "SELECT * FROM products WHERE id = ? AND is_active = 1",
        [productId]
      ) as Record<string, unknown>[];

      if (productRows.length === 0) return null;

      const features = storage.query(
        `SELECT * FROM product_features
         WHERE product_id = ? AND sales_count IS NOT NULL
         ORDER BY collected_at ASC`,
        [productId]
      ) as Record<string, unknown>[];

      if (features.length < 2) {
        return this.createMinimalRecord(productId, productRows[0], features);
      }

      const salesData = features
        .filter((f) => f.sales_count !== null && f.sales_count !== undefined)
        .map((f) => ({
          date: new Date(f.collected_at as string),
          sales: f.sales_count as number,
          price: f.price as number | null,
          rating: f.rating as number | null,
        }))
        .sort((a, b) => a.date.getTime() - b.date.getTime());

      const priceData = features
        .filter((f) => f.price !== null && f.price !== undefined)
        .map((f) => ({
          date: new Date(f.collected_at as string),
          price: f.price as number,
        }))
        .sort((a, b) => a.date.getTime() - b.date.getTime());

      const now = new Date();
      const sevenDaysAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);

      const salesVelocity = this.computeSalesVelocity(salesData);
      const growthRate7d = this.computeGrowthRate(salesData, sevenDaysAgo);
      const growthRate30d = this.computeGrowthRate(salesData, thirtyDaysAgo);
      const volatility = this.computeVolatility(priceData);
      const competitionIndex = this.computeCompetitionIndex(productRows[0], features);
      const lifecycleStage = this.computeLifecycleStage(salesData, growthRate7d);
      const trendShort = this.computeTrend(growthRate7d);
      const trendLong = this.computeTrend(growthRate30d);

      const record: FeatureRecord = {
        id: crypto.randomUUID(),
        product_id: productId,
        category: (productRows[0].category as string) || null,
        sales_velocity: salesVelocity,
        growth_rate_7d: growthRate7d,
        growth_rate_30d: growthRate30d,
        volatility: volatility,
        competition_index: competitionIndex,
        lifecycle_stage: lifecycleStage,
        trend_short: trendShort,
        trend_long: trendLong,
        calculated_at: new Date().toISOString(),
      };

      this.saveFeatureRecord(record, storage);
      this.stats.totalComputed++;
      this.stats.lastRunAt = new Date().toISOString();

      return record;
    } catch {
      this.stats.errors++;
      return null;
    }
  }

  computeAll(): number {
    try {
      const storage = getStorage();
      const products = storage.query(
        "SELECT id FROM products WHERE is_active = 1"
      ) as Array<{ id: string }>;

      let computed = 0;
      for (const product of products) {
        const result = this.computeForProduct(product.id);
        if (result) computed++;
      }
      return computed;
    } catch {
      return 0;
    }
  }

  getFeaturesForProduct(productId: string): FeatureRecord | null {
    try {
      const storage = getStorage();
      const rows = storage.query(
        "SELECT * FROM local_features WHERE product_id = ? ORDER BY calculated_at DESC LIMIT 1",
        [productId]
      ) as FeatureRecord[];
      return rows.length > 0 ? rows[0] : null;
    } catch {
      return null;
    }
  }

  getStats(): FeatureEngineStats {
    return { ...this.stats };
  }

  private createMinimalRecord(
    productId: string,
    product: Record<string, unknown>,
    features: Record<string, unknown>[]
  ): FeatureRecord {
    const storage = getStorage();
    const latestFeature = features.length > 0 ? features[features.length - 1] : null;

    const record: FeatureRecord = {
      id: crypto.randomUUID(),
      product_id: productId,
      category: (product.category as string) || null,
      sales_velocity: latestFeature?.sales_count
        ? (latestFeature.sales_count as number) / 1
        : null,
      growth_rate_7d: null,
      growth_rate_30d: null,
      volatility: null,
      competition_index: null,
      lifecycle_stage: "new",
      trend_short: null,
      trend_long: null,
      calculated_at: new Date().toISOString(),
    };

    this.saveFeatureRecord(record, storage);
    this.stats.totalComputed++;
    this.stats.lastRunAt = new Date().toISOString();

    return record;
  }

  private computeSalesVelocity(
    data: Array<{ date: Date; sales: number }>
  ): number | null {
    if (data.length < 2) return null;

    const first = data[0];
    const last = data[data.length - 1];
    const daysDiff = (last.date.getTime() - first.date.getTime()) / (1000 * 60 * 60 * 24);

    if (daysDiff < 0.5) return null;

    const salesDelta = last.sales - first.sales;
    return Math.max(0, salesDelta / daysDiff);
  }

  private computeGrowthRate(
    data: Array<{ date: Date; sales: number }>,
    sinceDate: Date
  ): number | null {
    const recent = data.filter((d) => d.date >= sinceDate);
    if (recent.length < 2) return null;

    const first = recent[0];
    const last = recent[recent.length - 1];

    if (first.sales === 0) return last.sales > 0 ? 1.0 : 0;

    return (last.sales - first.sales) / first.sales;
  }

  private computeVolatility(
    data: Array<{ date: Date; price: number }>
  ): number | null {
    if (data.length < 3) return null;

    const prices = data.map((d) => d.price);
    const mean = prices.reduce((a, b) => a + b, 0) / prices.length;
    const variance =
      prices.reduce((sum, p) => sum + Math.pow(p - mean, 2), 0) / prices.length;

    if (mean === 0) return null;

    return Math.sqrt(variance) / mean;
  }

  private computeCompetitionIndex(
    product: Record<string, unknown>,
    features: Record<string, unknown>[]
  ): number | null {
    if (features.length === 0) return null;

    const latest = features[features.length - 1];
    let score = 50;

    if (latest.rating && typeof latest.rating === "number") {
      score += (latest.rating - 3) * 10;
    }

    if (latest.review_count && typeof latest.review_count === "number") {
      if (latest.review_count > 100) score += 15;
      else if (latest.review_count > 50) score += 10;
      else if (latest.review_count > 10) score += 5;
    }

    if (latest.favorite_count && typeof latest.favorite_count === "number") {
      if (latest.favorite_count > 1000) score += 15;
      else if (latest.favorite_count > 500) score += 10;
      else if (latest.favorite_count > 100) score += 5;
    }

    if (latest.sales_count && typeof latest.sales_count === "number") {
      if (latest.sales_count > 10000) score += 10;
      else if (latest.sales_count > 1000) score += 5;
    }

    return Math.max(0, Math.min(100, score));
  }

  private computeLifecycleStage(
    data: Array<{ date: Date; sales: number }>,
    growthRate: number | null
  ): string {
    if (data.length < 2) return "new";

    if (growthRate === null) return "stable";

    if (growthRate > 0.5) return "growth";
    if (growthRate > 0.1) return "rising";
    if (growthRate > -0.1) return "stable";
    if (growthRate > -0.3) return "declining";
    return "decline";
  }

  private computeTrend(growthRate: number | null): string {
    if (growthRate === null) return "unknown";
    if (growthRate > 0.1) return "up";
    if (growthRate < -0.1) return "down";
    return "stable";
  }

  private saveFeatureRecord(record: FeatureRecord, storage: ReturnType<typeof getStorage>): void {
    storage.run(
      `CREATE TABLE IF NOT EXISTS local_features (
        id TEXT PRIMARY KEY,
        product_id TEXT NOT NULL,
        category TEXT,
        sales_velocity REAL,
        growth_rate_7d REAL,
        growth_rate_30d REAL,
        volatility REAL,
        competition_index REAL,
        lifecycle_stage TEXT,
        trend_short TEXT,
        trend_long TEXT,
        calculated_at TEXT NOT NULL
      )`
    );

    storage.run(
      `INSERT OR REPLACE INTO local_features
       (id, product_id, category, sales_velocity, growth_rate_7d, growth_rate_30d,
        volatility, competition_index, lifecycle_stage, trend_short, trend_long, calculated_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        record.id,
        record.product_id,
        record.category,
        record.sales_velocity,
        record.growth_rate_7d,
        record.growth_rate_30d,
        record.volatility,
        record.competition_index,
        record.lifecycle_stage,
        record.trend_short,
        record.trend_long,
        record.calculated_at,
      ]
    );
  }
}

export const featureEngine = new FeatureEngine();
