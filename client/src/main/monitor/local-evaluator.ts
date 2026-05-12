import { getStorage } from "../storage/sqlite";
import { EventEmitter } from "events";

export interface LocalMonitorRule {
  id: string;
  product_id: string;
  rule_name: string;
  rule_type: "price_drop" | "sales_surge" | "stock_change" | "rating_drop" | "custom";
  conditions: Record<string, unknown>;
  is_active: boolean;
  last_triggered_at: string | null;
  trigger_count: number;
  cooldown_minutes: number;
}

export interface LocalNotification {
  id: string;
  type: string;
  title: string;
  content: string;
  is_read: boolean;
  related_id: string | null;
  related_type: string | null;
  created_at: string;
}

interface ProductRow {
  id: string;
  product_name: string;
  platform_product_id: string;
}

interface FeatureRow {
  id: string;
  product_id: string;
  price: number | null;
  original_price: number | null;
  sales_count: number | null;
  monthly_sales: number | null;
  rating: number | null;
  review_count: number | null;
  favorite_count: number | null;
  stock_status: string | null;
  collected_at: string;
}

const RULE_TYPE_LABELS: Record<string, string> = {
  price_drop: "价格下跌",
  sales_surge: "销量激增",
  stock_change: "库存变化",
  rating_drop: "评分下降",
  custom: "自定义规则",
};

class LocalRuleEvaluator extends EventEmitter {
  private initialized = false;

  init(): void {
    if (this.initialized) return;
    this.initialized = true;
    this.ensureTables();
  }

  private ensureTables(): void {
    const storage = getStorage();
    storage.run(`
      CREATE TABLE IF NOT EXISTS local_notifications (
        id TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        is_read INTEGER NOT NULL DEFAULT 0,
        related_id TEXT,
        related_type TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      )
    `);
    storage.run(`CREATE INDEX IF NOT EXISTS idx_local_notifications_is_read ON local_notifications(is_read)`);
    storage.run(`CREATE INDEX IF NOT EXISTS idx_local_notifications_created ON local_notifications(created_at)`);
  }

  evaluateForProduct(productId: string): number {
    this.init();
    const storage = getStorage();

    const rules = storage.query(
      `SELECT * FROM monitor_rules WHERE product_id = ? AND is_active = 1`,
      [productId]
    ) as LocalMonitorRule[];

    if (rules.length === 0) return 0;

    const features = storage.query(
      `SELECT * FROM product_features WHERE product_id = ? ORDER BY collected_at DESC LIMIT 2`,
      [productId]
    ) as FeatureRow[];

    if (features.length < 2) return 0;

    const latest = features[0];
    const prev = features[1];

    const products = storage.query(`SELECT * FROM products WHERE id = ?`, [productId]) as ProductRow[];
    const productName = products.length > 0 ? products[0].product_name : "未知商品";

    let triggeredCount = 0;

    for (const rule of rules) {
      if (rule.last_triggered_at) {
        const lastTriggered = new Date(rule.last_triggered_at).getTime();
        const cooldownMs = (rule.cooldown_minutes || 30) * 60 * 1000;
        if (Date.now() - lastTriggered < cooldownMs) continue;
      }

      const matched = this.checkConditions(rule, latest, prev);
      if (matched) {
        this.createNotification(rule, productName, latest, prev);
        storage.run(
          `UPDATE monitor_rules SET last_triggered_at = datetime('now'), trigger_count = trigger_count + 1 WHERE id = ?`,
          [rule.id]
        );
        triggeredCount++;
        this.emit("rule:triggered", { ruleId: rule.id, ruleType: rule.rule_type, productId, productName });
      }
    }

    return triggeredCount;
  }

  evaluateAll(): number {
    this.init();
    const storage = getStorage();
    const activeRules = storage.query(
      `SELECT DISTINCT product_id FROM monitor_rules WHERE is_active = 1`
    ) as Array<{ product_id: string }>;

    let totalTriggered = 0;
    for (const row of activeRules) {
      totalTriggered += this.evaluateForProduct(row.product_id);
    }
    return totalTriggered;
  }

  private checkConditions(rule: LocalMonitorRule, latest: FeatureRow, prev: FeatureRow): boolean {
    const conditions = rule.conditions;
    switch (rule.rule_type) {
      case "price_drop":
        return this.checkPriceDrop(conditions, latest, prev);
      case "sales_surge":
        return this.checkSalesSurge(conditions, latest, prev);
      case "stock_change":
        return this.checkStockChange(conditions, latest, prev);
      case "rating_drop":
        return this.checkRatingDrop(conditions, latest, prev);
      default:
        return false;
    }
  }

  private checkPriceDrop(conditions: Record<string, unknown>, latest: FeatureRow, prev: FeatureRow): boolean {
    if (latest.price === null || prev.price === null) return false;
    const threshold = (conditions.threshold as number) || 10;
    if (prev.price === 0) return false;
    const dropPct = ((prev.price - latest.price) / prev.price) * 100;
    return dropPct >= threshold;
  }

  private checkSalesSurge(conditions: Record<string, unknown>, latest: FeatureRow, prev: FeatureRow): boolean {
    if (latest.sales_count === null || prev.sales_count === null) return false;
    const threshold = (conditions.threshold as number) || 50;
    if (prev.sales_count === 0) return latest.sales_count > 0;
    const surgePct = ((latest.sales_count - prev.sales_count) / prev.sales_count) * 100;
    return surgePct >= threshold;
  }

  private checkStockChange(_conditions: Record<string, unknown>, latest: FeatureRow, prev: FeatureRow): boolean {
    if (latest.stock_status === null || prev.stock_status === null) return false;
    return latest.stock_status !== prev.stock_status;
  }

  private checkRatingDrop(conditions: Record<string, unknown>, latest: FeatureRow, prev: FeatureRow): boolean {
    if (latest.rating === null || prev.rating === null) return false;
    const threshold = (conditions.threshold as number) || 0.5;
    return prev.rating - latest.rating >= threshold;
  }

  private createNotification(
    rule: LocalMonitorRule,
    productName: string,
    latest: FeatureRow,
    prev: FeatureRow
  ): void {
    const storage = getStorage();
    const id = crypto.randomUUID();
    const ruleLabel = RULE_TYPE_LABELS[rule.rule_type] || rule.rule_type;
    const content = this.buildContent(rule, productName, latest, prev);

    storage.run(
      `INSERT INTO local_notifications (id, type, title, content, related_id, related_type) VALUES (?, ?, ?, ?, ?, ?)`,
      [id, "monitor_triggered", `[${ruleLabel}] ${productName}`, content, rule.product_id, "product"]
    );

    this.emit("notification:created", {
      id,
      type: "monitor_triggered",
      title: `[${ruleLabel}] ${productName}`,
      content,
      related_id: rule.product_id,
    });
  }

  private buildContent(
    rule: LocalMonitorRule,
    productName: string,
    latest: FeatureRow,
    prev: FeatureRow
  ): string {
    switch (rule.rule_type) {
      case "price_drop": {
        const oldPrice = prev.price || 0;
        const newPrice = latest.price || 0;
        const dropPct = oldPrice > 0 ? ((oldPrice - newPrice) / oldPrice * 100).toFixed(1) : "0";
        return `商品「${productName}」价格从 ¥${oldPrice.toFixed(2)} 降至 ¥${newPrice.toFixed(2)}，降幅${dropPct}%`;
      }
      case "sales_surge": {
        const oldSales = prev.sales_count || 0;
        const newSales = latest.sales_count || 0;
        const surgePct = oldSales > 0 ? ((newSales - oldSales) / oldSales * 100).toFixed(1) : "∞";
        return `商品「${productName}」销量从 ${oldSales} 增至 ${newSales}，增幅${surgePct}%`;
      }
      case "stock_change":
        return `商品「${productName}」库存状态从「${prev.stock_status}」变为「${latest.stock_status}」`;
      case "rating_drop": {
        const oldRating = prev.rating || 0;
        const newRating = latest.rating || 0;
        return `商品「${productName}」评分从 ${oldRating.toFixed(1)} 降至 ${newRating.toFixed(1)}`;
      }
      default:
        return `商品「${productName}」触发了监控规则「${rule.rule_name}」`;
    }
  }

  getNotifications(limit: number = 50): LocalNotification[] {
    this.init();
    const storage = getStorage();
    return storage.query(
      `SELECT * FROM local_notifications ORDER BY created_at DESC LIMIT ?`,
      [limit]
    ) as LocalNotification[];
  }

  getUnreadCount(): number {
    this.init();
    const storage = getStorage();
    const rows = storage.query(
      `SELECT COUNT(*) as cnt FROM local_notifications WHERE is_read = 0`
    ) as Array<{ cnt: number }>;
    return rows.length > 0 ? rows[0].cnt : 0;
  }

  markAsRead(notificationId: string): void {
    this.init();
    const storage = getStorage();
    storage.run(`UPDATE local_notifications SET is_read = 1 WHERE id = ?`, [notificationId]);
  }

  markAllAsRead(): number {
    this.init();
    const storage = getStorage();
    const result = storage.query(
      `SELECT id FROM local_notifications WHERE is_read = 0`
    ) as Array<{ id: string }>;
    for (const row of result) {
      storage.run(`UPDATE local_notifications SET is_read = 1 WHERE id = ?`, [row.id]);
    }
    return result.length;
  }

  clearOldNotifications(maxAge: number = 30 * 24 * 60 * 60 * 1000): number {
    this.init();
    const storage = getStorage();
    const cutoff = new Date(Date.now() - maxAge).toISOString();
    const result = storage.query(
      `SELECT id FROM local_notifications WHERE created_at < ?`,
      [cutoff]
    ) as Array<{ id: string }>;
    for (const row of result) {
      storage.run(`DELETE FROM local_notifications WHERE id = ?`, [row.id]);
    }
    return result.length;
  }

  deleteNotification(notificationId: string): boolean {
    this.init();
    const storage = getStorage();
    const rows = storage.query(`SELECT id FROM local_notifications WHERE id = ?`, [notificationId]) as Array<{ id: string }>;
    if (rows.length === 0) return false;
    storage.run(`DELETE FROM local_notifications WHERE id = ?`, [notificationId]);
    return true;
  }
}

export const localRuleEvaluator = new LocalRuleEvaluator();
