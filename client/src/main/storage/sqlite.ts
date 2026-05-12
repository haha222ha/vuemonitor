import initSqlJs, { Database as SqlJsDatabase } from "sql.js";
import * as path from "path";
import * as fs from "fs";
import { app } from "electron";
import { encryptRow, decryptRow } from "../crypto/encryption";

let db: SqlJsDatabase | null = null;
let storage: SQLiteStorage | null = null;
let dbPath: string = "";
let wasmPath: string = "";

export class SQLiteStorage {
  private db: SqlJsDatabase;
  private dbPath: string;

  constructor(database: SqlJsDatabase, filePath: string) {
    this.db = database;
    this.dbPath = filePath;
    this.initTables();
  }

  private initTables(): void {
    this.db.run(`
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
    `);

    this.db.run(`
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
    `);

    this.db.run(`
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
    `);

    this.db.run(`
      CREATE TABLE IF NOT EXISTS sync_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_name TEXT NOT NULL,
        record_id TEXT NOT NULL,
        action TEXT NOT NULL,
        data TEXT DEFAULT '{}',
        synced INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      );
    `);

    this.db.run(`
      CREATE TABLE IF NOT EXISTS ai_analysis (
        id TEXT PRIMARY KEY,
        product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
        analysis_type TEXT NOT NULL,
        result TEXT NOT NULL DEFAULT '{}',
        confidence REAL DEFAULT 0,
        analyzed_at TEXT NOT NULL DEFAULT (datetime('now'))
      );
    `);

    this.db.run(`
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
    `);

    this.db.run(`CREATE INDEX IF NOT EXISTS idx_product_features_product_id ON product_features(product_id)`);
    this.db.run(`CREATE INDEX IF NOT EXISTS idx_product_features_collected_at ON product_features(collected_at)`);
    this.db.run(`CREATE INDEX IF NOT EXISTS idx_sync_queue_synced ON sync_queue(synced)`);
    this.db.run(`CREATE INDEX IF NOT EXISTS idx_ai_analysis_product_id ON ai_analysis(product_id)`);
    this.db.run(`CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_active ON scheduled_tasks(is_active)`);

    this.db.run(`
      CREATE TABLE IF NOT EXISTS offline_operations (
        id TEXT PRIMARY KEY,
        type TEXT NOT NULL,
        payload TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        retry_count INTEGER NOT NULL DEFAULT 0,
        max_retries INTEGER NOT NULL DEFAULT 5
      );
    `);

    this.save();
  }

  query(sql: string, params?: unknown[]): unknown[] {
    try {
      const stmt = this.db.prepare(sql);
      if (params && params.length > 0) {
        stmt.bind(params as (string | number | null | Uint8Array)[]);
      }
      const results: unknown[] = [];
      while (stmt.step()) {
        const row = stmt.getAsObject() as Record<string, any>;
        results.push(decryptRow(row));
      }
      stmt.free();
      return results;
    } catch {
      return [];
    }
  }

  run(sql: string, params?: unknown[]): void {
    try {
      if (params && params.length > 0) {
        this.db.run(sql, params as (string | number | null | Uint8Array)[]);
      } else {
        this.db.run(sql);
      }
      this.save();
    } catch {}
  }

  secureRun(sql: string, params?: unknown[]): void {
    try {
      if (params && params.length > 0) {
        const encryptedParams = (params as Record<string, any>[]).map((p) => {
          if (p != null && typeof p === "object") return encryptRow(p);
          return p;
        });
        this.db.run(sql, encryptedParams as (string | number | null | Uint8Array)[]);
      } else {
        this.db.run(sql);
      }
      this.save();
    } catch {}
  }

  insertProduct(product: Record<string, unknown>): void {
    const id = (product.id as string) || crypto.randomUUID();
    this.db.run(
      `INSERT OR REPLACE INTO products (id, platform, platform_product_id, product_name, shop_name, category, image_url, product_url)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
      [id, product.platform, product.platform_product_id, product.product_name, product.shop_name || null, product.category || null, product.image_url || null, product.product_url || null]
    );
    this.addToSyncQueue("products", id, "upsert", product);
    this.save();
  }

  getProducts(filters?: Record<string, unknown>): unknown[] {
    let sql = "SELECT * FROM products WHERE is_active = 1";
    const params: unknown[] = [];
    if (filters?.platform) {
      sql += " AND platform = ?";
      params.push(filters.platform);
    }
    sql += " ORDER BY updated_at DESC";
    return this.query(sql, params);
  }

  saveFeatures(productId: string, features: Record<string, unknown>): void {
    const id = (features.id as string) || crypto.randomUUID();
    this.db.run(
      `INSERT INTO product_features (id, product_id, price, original_price, sales_count, monthly_sales, rating, review_count, favorite_count, stock_status, extra_features, source)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        id, productId, features.price || null, features.original_price || null,
        features.sales_count || null, features.monthly_sales || null,
        features.rating || null, features.review_count || null,
        features.favorite_count || null, features.stock_status || null,
        JSON.stringify(features.extra_features || {}), features.source || "local"
      ]
    );
    this.db.run("UPDATE products SET last_collected_at = datetime('now'), updated_at = datetime('now') WHERE id = ?", [productId]);
    this.addToSyncQueue("product_features", id, "insert", features);
    this.save();
  }

  private addToSyncQueue(table: string, recordId: string, action: string, data: unknown): void {
    this.db.run(
      `INSERT INTO sync_queue (table_name, record_id, action, data) VALUES (?, ?, ?, ?)`,
      [table, recordId, action, JSON.stringify(data)]
    );
  }

  getPendingSync(limit: number = 100): unknown[] {
    return this.query("SELECT * FROM sync_queue WHERE synced = 0 ORDER BY created_at ASC LIMIT ?", [limit]);
  }

  markSynced(ids: number[]): void {
    if (ids.length === 0) return;
    const placeholders = ids.map(() => "?").join(",");
    this.db.run(`UPDATE sync_queue SET synced = 1 WHERE id IN (${placeholders})`, ids as number[]);
    this.save();
  }

  private save(): void {
    try {
      const data = this.db.export();
      const buffer = Buffer.from(data);
      fs.writeFileSync(this.dbPath, buffer);
    } catch {}
  }

  flush(): void {
    this.save();
  }
}

export async function initStorage(): Promise<SQLiteStorage> {
  if (storage) return storage;

  const userDataPath = app.getPath("userData");
  dbPath = path.join(userDataPath, "vuemonitor.db");

  const isDev = process.env.NODE_ENV === "development";
  let wasmBinary: Buffer;

  const wasmSearchPaths = [
    path.join(process.cwd(), "node_modules", "sql.js", "dist", "sql-wasm.wasm"),
    path.join(app.getAppPath(), "node_modules", "sql.js", "dist", "sql-wasm.wasm"),
    path.join(__dirname, "..", "sql-wasm.wasm"),
    path.join(__dirname, "sql-wasm.wasm"),
    path.join(process.resourcesPath, "sql-wasm.wasm"),
  ];

  let wasmPath = "";
  for (const p of wasmSearchPaths) {
    if (fs.existsSync(p)) {
      wasmPath = p;
      break;
    }
  }

  if (!wasmPath) {
    throw new Error("sql-wasm.wasm not found in any search path");
  }

  wasmBinary = fs.readFileSync(wasmPath);

  const SQL = await initSqlJs({
    wasmBinary,
  });

  let database: SqlJsDatabase;
  if (fs.existsSync(dbPath)) {
    const fileBuffer = fs.readFileSync(dbPath);
    database = new SQL.Database(fileBuffer);
  } else {
    database = new SQL.Database();
  }

  storage = new SQLiteStorage(database, dbPath);
  return storage;
}

export function getStorage(): SQLiteStorage {
  if (!storage) {
    throw new Error("Storage not initialized. Call initStorage() first.");
  }
  return storage;
}
