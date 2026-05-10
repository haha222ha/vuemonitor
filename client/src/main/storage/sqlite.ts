import Database from "better-sqlite3";
import * as path from "path";
import { app } from "electron";

let db: Database.Database | null = null;
let storage: SQLiteStorage | null = null;

export class SQLiteStorage {
  private db: Database.Database;

  constructor(dbPath: string) {
    this.db = new Database(dbPath);
    this.db.pragma("journal_mode = WAL");
    this.db.pragma("foreign_keys = ON");
    this.initTables();
  }

  private initTables(): void {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS products (
        id TEXT PRIMARY KEY,
        platform TEXT NOT NULL,
        platform_product_id TEXT NOT NULL,
        product_name TEXT NOT NULL,
        shop_name TEXT,
        category TEXT,
        image_url TEXT,
        product_url TEXT,
        is_active INTEGER NOT NULL DEFAULT 1,
        last_collected_at TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(platform, platform_product_id)
      );

      CREATE TABLE IF NOT EXISTS product_features (
        id TEXT PRIMARY KEY,
        product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
        price REAL,
        original_price REAL,
        sales_count INTEGER,
        monthly_sales INTEGER,
        rating REAL,
        review_count INTEGER,
        favorite_count INTEGER,
        stock_status TEXT,
        extra_features TEXT DEFAULT '{}',
        collected_at TEXT NOT NULL DEFAULT (datetime('now')),
        source TEXT NOT NULL DEFAULT 'local',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      );

      CREATE TABLE IF NOT EXISTS monitor_rules (
        id TEXT PRIMARY KEY,
        product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
        rule_name TEXT NOT NULL,
        rule_type TEXT NOT NULL,
        conditions TEXT NOT NULL DEFAULT '{}',
        is_active INTEGER NOT NULL DEFAULT 1,
        last_triggered_at TEXT,
        trigger_count INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      );

      CREATE TABLE IF NOT EXISTS sync_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_name TEXT NOT NULL,
        record_id TEXT NOT NULL,
        action TEXT NOT NULL,
        data TEXT DEFAULT '{}',
        synced INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      );

      CREATE TABLE IF NOT EXISTS ai_analysis (
        id TEXT PRIMARY KEY,
        product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
        analysis_type TEXT NOT NULL,
        result TEXT NOT NULL DEFAULT '{}',
        confidence REAL DEFAULT 0,
        analyzed_at TEXT NOT NULL DEFAULT (datetime('now'))
      );

      CREATE TABLE IF NOT EXISTS scheduled_tasks (
        id TEXT PRIMARY KEY,
        product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
        platform TEXT NOT NULL DEFAULT 'xhs',
        platform_product_id TEXT NOT NULL,
        product_name TEXT NOT NULL,
        frequency_minutes INTEGER NOT NULL DEFAULT 60,
        is_active INTEGER NOT NULL DEFAULT 1,
        last_run_at TEXT,
        next_run_at TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      );

      CREATE INDEX IF NOT EXISTS idx_product_features_product_id ON product_features(product_id);
      CREATE INDEX IF NOT EXISTS idx_product_features_collected_at ON product_features(collected_at);
      CREATE INDEX IF NOT EXISTS idx_sync_queue_synced ON sync_queue(synced);
      CREATE INDEX IF NOT EXISTS idx_ai_analysis_product_id ON ai_analysis(product_id);
      CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_active ON scheduled_tasks(is_active);
    `);
  }

  query(sql: string, params?: unknown[]): unknown[] {
    return this.db.prepare(sql).all(...(params || []));
  }

  run(sql: string, params?: unknown[]): Database.RunResult {
    return this.db.prepare(sql).run(...(params || []));
  }

  insertProduct(product: Record<string, unknown>): Database.RunResult {
    const id = product.id || crypto.randomUUID();
    const result = this.db.prepare(`
      INSERT OR REPLACE INTO products (id, platform, platform_product_id, product_name, shop_name, category, image_url, product_url)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `).run(id, product.platform, product.platform_product_id, product.product_name, product.shop_name || null, product.category || null, product.image_url || null, product.product_url || null);

    this.addToSyncQueue("products", id, "upsert", product);
    return result;
  }

  getProducts(filters?: Record<string, unknown>): unknown[] {
    let sql = "SELECT * FROM products WHERE is_active = 1";
    const params: unknown[] = [];
    if (filters?.platform) {
      sql += " AND platform = ?";
      params.push(filters.platform);
    }
    sql += " ORDER BY updated_at DESC";
    return this.db.prepare(sql).all(...params);
  }

  saveFeatures(productId: string, features: Record<string, unknown>): Database.RunResult {
    const id = features.id || crypto.randomUUID();
    const result = this.db.prepare(`
      INSERT INTO product_features (id, product_id, price, original_price, sales_count, monthly_sales, rating, review_count, favorite_count, stock_status, extra_features, source)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      id, productId, features.price || null, features.original_price || null,
      features.sales_count || null, features.monthly_sales || null,
      features.rating || null, features.review_count || null,
      features.favorite_count || null, features.stock_status || null,
      JSON.stringify(features.extra_features || {}), features.source || "local"
    );

    this.db.prepare("UPDATE products SET last_collected_at = datetime('now'), updated_at = datetime('now') WHERE id = ?").run(productId);
    this.addToSyncQueue("product_features", id, "insert", features);
    return result;
  }

  private addToSyncQueue(table: string, recordId: string, action: string, data: unknown): void {
    this.db.prepare(`
      INSERT INTO sync_queue (table_name, record_id, action, data)
      VALUES (?, ?, ?, ?)
    `).run(table, recordId, action, JSON.stringify(data));
  }

  getPendingSync(limit: number = 100): unknown[] {
    return this.db.prepare("SELECT * FROM sync_queue WHERE synced = 0 ORDER BY created_at ASC LIMIT ?").all(limit);
  }

  markSynced(ids: number[]): void {
    const placeholders = ids.map(() => "?").join(",");
    this.db.prepare(`UPDATE sync_queue SET synced = 1 WHERE id IN (${placeholders})`).run(...ids);
  }

  flush(): void {
    this.db.pragma("wal_checkpoint(TRUNCATE)");
  }
}

export function initStorage(): SQLiteStorage {
  if (!storage) {
    const dbPath = path.join(app.getPath("userData"), "vuemonitor.db");
    storage = new SQLiteStorage(dbPath);
  }
  return storage;
}

export function getStorage(): SQLiteStorage {
  if (!storage) {
    return initStorage();
  }
  return storage;
}
