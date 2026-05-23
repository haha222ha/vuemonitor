﻿﻿﻿﻿﻿﻿﻿import * as path from "path";
import * as fs from "fs";
import { app } from "electron";
import { encryptRow, decryptRow } from "../crypto/encryption";
import { logger } from "../logger/logger";
import type { Database as SqlJsDatabaseType } from "sql.js";
import initSqlJsModule from "sql.js";

let SqlJsDatabaseClass: typeof SqlJsDatabaseType;

const db: SqlJsDatabaseType | null = null;
let storage: SQLiteStorage | null = null;
let dbPath: string = "";
const wasmPath: string = "";

export class SQLiteStorage {
  private db: SqlJsDatabaseType;
  private dbPath: string;
  private dirty: boolean = false;
  private saveTimer: ReturnType<typeof setTimeout> | null = null;
  private static readonly SAVE_DEBOUNCE_MS = 500;

  constructor(database: SqlJsDatabaseType, filePath: string) {
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
    this.db.run(`CREATE INDEX IF NOT EXISTS idx_product_features_product_collected ON product_features(product_id, collected_at DESC)`);
    this.db.run(`CREATE INDEX IF NOT EXISTS idx_sync_queue_synced ON sync_queue(synced)`);
    this.db.run(`CREATE INDEX IF NOT EXISTS idx_ai_analysis_product_id ON ai_analysis(product_id)`);
    this.db.run(`CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_active ON scheduled_tasks(is_active)`);
    this.db.run(`CREATE INDEX IF NOT EXISTS idx_products_category_id ON products(category_id)`);
    this.db.run(`CREATE INDEX IF NOT EXISTS idx_products_platform ON products(platform)`);
    this.db.run(`CREATE INDEX IF NOT EXISTS idx_products_is_active ON products(is_active)`);
    this.db.run(`CREATE INDEX IF NOT EXISTS idx_products_last_collected ON products(last_collected_at)`);
    this.db.run(`CREATE INDEX IF NOT EXISTS idx_products_platform_pid ON products(platform, platform_product_id)`);

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

    this.db.run(`
      CREATE TABLE IF NOT EXISTS categories (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        icon TEXT,
        color TEXT,
        sort_order INTEGER NOT NULL DEFAULT 0,
        parent_id TEXT REFERENCES categories(id) ON DELETE SET NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
      );
    `);

    try {
      this.db.run("ALTER TABLE categories ADD COLUMN icon TEXT");
    } catch { /* column already exists */ }
    try {
      this.db.run("ALTER TABLE categories ADD COLUMN color TEXT");
    } catch { /* column already exists */ }
    try {
      this.db.run("ALTER TABLE categories ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0");
    } catch { /* column already exists */ }
    try {
      this.db.run("ALTER TABLE categories ADD COLUMN parent_id TEXT REFERENCES categories(id) ON DELETE SET NULL");
    } catch { /* column already exists */ }
    try {
      this.db.run("ALTER TABLE categories ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1");
    } catch { /* column already exists */ }
    try {
      this.db.run("ALTER TABLE categories ADD COLUMN updated_at TEXT NOT NULL DEFAULT (datetime('now'))");
    } catch { /* column already exists */ }

    try {
      this.db.run("ALTER TABLE products ADD COLUMN category_id TEXT REFERENCES categories(id)");
    } catch { /* column already exists */ }

    try {
      this.db.run("ALTER TABLE products ADD COLUMN last_collect_status TEXT DEFAULT 'pending'");
    } catch { /* column already exists */ }

    this.db.run(`CREATE INDEX IF NOT EXISTS idx_categories_parent_id ON categories(parent_id)`);

    this.save();
  }

  private static readonly ALLOWED_TABLES = new Set([
    "products", "product_features", "ai_analysis", "monitor_rules",
    "sync_queue", "scheduled_tasks", "offline_operations", "categories",
    "local_notifications",
  ]);

  query(sql: string, params?: unknown[]): unknown[] {
    try {
      const stmt = this.db.prepare(sql);
      if (params && params.length > 0) {
        stmt.bind(params as (string | number | null | Uint8Array)[]);
      }
      const results: unknown[] = [];
      while (stmt.step()) {
        const row = stmt.getAsObject() as Record<string, unknown>;
        results.push(decryptRow(row));
      }
      stmt.free();
      return results;
    } catch (err) {
      logger.error("SQLiteStorage", `query failed: ${err}`);
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
      this.scheduleSave();
    } catch (err) {
      logger.error("SQLiteStorage", `run failed: ${err}`);
    }
  }

  safeQuery(table: string, whereClause: string, params?: unknown[], orderBy?: string, limit?: number, offset?: number): unknown[] {
    if (!SQLiteStorage.ALLOWED_TABLES.has(table)) {
      throw new Error(`Invalid table name: ${table}`);
    }
    let sql = `SELECT * FROM ${table}`;
    if (whereClause) sql += ` WHERE ${whereClause}`;
    if (orderBy) sql += ` ORDER BY ${orderBy}`;
    if (limit != null) {
      sql += " LIMIT ?";
      if (offset != null) sql += " OFFSET ?";
    }
    const allParams = [...(params || [])];
    if (limit != null) {
      allParams.push(limit);
      if (offset != null) allParams.push(offset);
    }
    return this.query(sql, allParams);
  }

  safeRun(table: string, setClause: string, whereClause: string, params?: unknown[]): void {
    if (!SQLiteStorage.ALLOWED_TABLES.has(table)) {
      throw new Error(`Invalid table name: ${table}`);
    }
    const sql = `UPDATE ${table} SET ${setClause} WHERE ${whereClause}`;
    this.run(sql, params);
  }

  safeDelete(table: string, whereClause: string, params?: unknown[]): void {
    if (!SQLiteStorage.ALLOWED_TABLES.has(table)) {
      throw new Error(`Invalid table name: ${table}`);
    }
    const sql = `DELETE FROM ${table} WHERE ${whereClause}`;
    this.run(sql, params);
  }

  safeSelectAll(table: string): unknown[] {
    if (!SQLiteStorage.ALLOWED_TABLES.has(table)) {
      throw new Error(`Invalid table name: ${table}`);
    }
    return this.query(`SELECT * FROM ${table}`);
  }

  transaction<T>(fn: () => T): T {
    this.db.run("BEGIN TRANSACTION");
    try {
      const result = fn();
      this.db.run("COMMIT");
      this.scheduleSave();
      return result;
    } catch (err) {
      this.db.run("ROLLBACK");
      logger.error("SQLiteStorage", `transaction failed, rolled back: ${err}`);
      throw err;
    }
  }

  secureRun(sql: string, params?: unknown[]): void {
    try {
      if (params && params.length > 0) {
        const encryptedParams = (params as Record<string, unknown>[]).map((p) => {
          if (p != null && typeof p === "object") return encryptRow(p);
          return p;
        });
        this.db.run(sql, encryptedParams as (string | number | null | Uint8Array)[]);
      } else {
        this.db.run(sql);
      }
      this.scheduleSave();
    } catch (err) {
      logger.error("SQLiteStorage", `secureRun failed: ${err}`);
    }
  }

  insertProduct(product: Record<string, unknown>): void {
    const id = (product.id as string) || crypto.randomUUID();
    this.db.run(
      `INSERT OR REPLACE INTO products (id, platform, platform_product_id, product_name, shop_name, category, image_url, product_url)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
      [id, product.platform, product.platform_product_id, product.product_name, product.shop_name || null, product.category || null, product.image_url || null, product.product_url || null]
    );
    this.addToSyncQueue("products", id, "upsert", product);
    this.scheduleSave();
  }

  getProducts(filters?: Record<string, unknown>): unknown[] {
    let sql = "SELECT * FROM products WHERE is_active = 1";
    const params: unknown[] = [];
    if (filters?.platform) {
      sql += " AND platform = ?";
      params.push(filters.platform);
    }
    if (filters?.category_id) {
      sql += " AND category_id = ?";
      params.push(filters.category_id);
    }
    if (filters?.category) {
      sql += " AND category = ?";
      params.push(filters.category);
    }
    sql += " ORDER BY updated_at DESC";
    if (filters?.limit) {
      sql += " LIMIT ?";
      params.push(filters.limit);
      if (filters?.offset) {
        sql += " OFFSET ?";
        params.push(filters.offset);
      }
    }
    return this.query(sql, params);
  }

  getProductsCount(filters?: Record<string, unknown>): number {
    let sql = "SELECT COUNT(*) as cnt FROM products WHERE is_active = 1";
    const params: unknown[] = [];
    if (filters?.platform) {
      sql += " AND platform = ?";
      params.push(filters.platform);
    }
    if (filters?.category_id) {
      sql += " AND category_id = ?";
      params.push(filters.category_id);
    }
    if (filters?.category) {
      sql += " AND category = ?";
      params.push(filters.category);
    }
    const rows = this.query(sql, params) as Array<{ cnt: number }>;
    return rows.length > 0 ? rows[0].cnt : 0;
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
    this.scheduleSave();
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
    this.scheduleSave();
  }

  private scheduleSave(): void {
    this.dirty = true;
    if (this.saveTimer) return;
    this.saveTimer = setTimeout(() => {
      this.saveTimer = null;
      if (this.dirty) {
        this.save();
      }
    }, SQLiteStorage.SAVE_DEBOUNCE_MS);
  }

  private save(): void {
    try {
      const data = this.db.export();
      const buffer = Buffer.from(data);
      fs.writeFileSync(this.dbPath, buffer);
      this.dirty = false;
    } catch (err) {
      logger.error("SQLiteStorage", `save failed: ${err}`);
    }
  }

  flush(): void {
    if (this.saveTimer) {
      clearTimeout(this.saveTimer);
      this.saveTimer = null;
    }
    this.save();
  }
}

export async function initStorage(): Promise<SQLiteStorage> {
  if (storage) return storage;

  const sqlJsModule = require("sql.js");
  const initFn = sqlJsModule.default || sqlJsModule;
  SqlJsDatabaseClass = sqlJsModule.Database;

  const userDataPath = app.getPath("userData");
  dbPath = path.join(userDataPath, "vuemonitor.db");

  let wasmBinary: Buffer;

  const wasmSearchPaths = [
    path.join(process.resourcesPath, "sql-wasm.wasm"),
    path.join(__dirname, "..", "node_modules", "sql.js", "dist", "sql-wasm.wasm"),
    path.join(process.cwd(), "node_modules", "sql.js", "dist", "sql-wasm.wasm"),
    path.join(app.getAppPath(), "node_modules", "sql.js", "dist", "sql-wasm.wasm"),
    path.join(__dirname, "sql-wasm.wasm"),
  ];

  let foundWasmPath = "";
  for (const p of wasmSearchPaths) {
    try {
      if (fs.existsSync(p)) {
        foundWasmPath = p;
        break;
      }
    } catch { /* path not accessible */ }
  }

  if (!foundWasmPath) {
    throw new Error("sql-wasm.wasm not found in any search path");
  }

  wasmBinary = fs.readFileSync(foundWasmPath);

  const SQL = await initFn({
    wasmBinary,
  });

  let database: SqlJsDatabaseType;
  if (fs.existsSync(dbPath)) {
    const fileBuffer = fs.readFileSync(dbPath);
    database = new SqlJsDatabaseClass(fileBuffer);
  } else {
    database = new SqlJsDatabaseClass();
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
