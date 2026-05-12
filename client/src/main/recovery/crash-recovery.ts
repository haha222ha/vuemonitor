import { getStorage } from "../storage/sqlite";
import { EventEmitter } from "events";

export interface TaskSnapshot {
  id: string;
  taskType: "chromium" | "playwright";
  targetId: string;
  targetType: string;
  targetUrl: string | null;
  status: "pending" | "running" | "completed" | "failed" | "risk_detected";
  progress: number;
  startedAt: string;
  updatedAt: string;
  retryCount: number;
  maxRetries: number;
  error: string | null;
  metadata: string;
}

export interface RecoveryResult {
  recovered: number;
  tasks: TaskSnapshot[];
  discarded: number;
}

class CrashRecoveryManager extends EventEmitter {
  private initialized = false;

  init(): void {
    if (this.initialized) return;
    this.initialized = true;
    this.ensureTable();
  }

  private ensureTable(): void {
    const storage = getStorage();
    storage.run(`
      CREATE TABLE IF NOT EXISTS task_snapshots (
        id TEXT PRIMARY KEY,
        task_type TEXT NOT NULL,
        target_id TEXT NOT NULL,
        target_type TEXT NOT NULL DEFAULT 'goods',
        target_url TEXT,
        status TEXT NOT NULL DEFAULT 'pending',
        progress INTEGER NOT NULL DEFAULT 0,
        started_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        retry_count INTEGER NOT NULL DEFAULT 0,
        max_retries INTEGER NOT NULL DEFAULT 3,
        error TEXT,
        metadata TEXT DEFAULT '{}'
      )
    `);
    storage.run(`CREATE INDEX IF NOT EXISTS idx_task_snapshots_status ON task_snapshots(status)`);
    storage.run(`CREATE INDEX IF NOT EXISTS idx_task_snapshots_updated ON task_snapshots(updated_at)`);
  }

  saveSnapshot(snapshot: Omit<TaskSnapshot, "updatedAt">): void {
    const storage = getStorage();
    const now = new Date().toISOString();
    storage.run(
      `INSERT OR REPLACE INTO task_snapshots
       (id, task_type, target_id, target_type, target_url, status, progress,
        started_at, updated_at, retry_count, max_retries, error, metadata)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      [
        snapshot.id,
        snapshot.taskType,
        snapshot.targetId,
        snapshot.targetType,
        snapshot.targetUrl,
        snapshot.status,
        snapshot.progress,
        snapshot.startedAt,
        now,
        snapshot.retryCount,
        snapshot.maxRetries,
        snapshot.error,
        snapshot.metadata,
      ]
    );
    this.emit("snapshot:saved", snapshot.id);
  }

  updateSnapshotStatus(taskId: string, status: TaskSnapshot["status"], progress?: number, error?: string | null): void {
    const storage = getStorage();
    const now = new Date().toISOString();
    const fields: string[] = ["status = ?", "updated_at = ?"];
    const values: unknown[] = [status, now];

    if (progress !== undefined) {
      fields.push("progress = ?");
      values.push(progress);
    }
    if (error !== undefined) {
      fields.push("error = ?");
      values.push(error);
    }

    values.push(taskId);
    storage.run(`UPDATE task_snapshots SET ${fields.join(", ")} WHERE id = ?`, values);
  }

  incrementRetry(taskId: string): number {
    const storage = getStorage();
    storage.run(
      `UPDATE task_snapshots SET retry_count = retry_count + 1, updated_at = ? WHERE id = ?`,
      [new Date().toISOString(), taskId]
    );
    const rows = storage.query("SELECT retry_count FROM task_snapshots WHERE id = ?", [taskId]) as Array<{ retry_count: number }>;
    return rows.length > 0 ? rows[0].retry_count : 0;
  }

  removeSnapshot(taskId: string): void {
    const storage = getStorage();
    storage.run("DELETE FROM task_snapshots WHERE id = ?", [taskId]);
  }

  recoverPendingTasks(maxAge: number = 24 * 60 * 60 * 1000): RecoveryResult {
    this.init();
    const storage = getStorage();
    const cutoff = new Date(Date.now() - maxAge).toISOString();

    const pending = storage.query(
      `SELECT * FROM task_snapshots
       WHERE status IN ('pending', 'running')
       AND updated_at > ?
       ORDER BY started_at ASC`,
      [cutoff]
    ) as TaskSnapshot[];

    const expired = storage.query(
      `SELECT id FROM task_snapshots
       WHERE status IN ('pending', 'running')
       AND updated_at <= ?`,
      [cutoff]
    ) as Array<{ id: string }>;

    const completed = storage.query(
      `SELECT id FROM task_snapshots WHERE status IN ('completed', 'failed')`
    ) as Array<{ id: string }>;

    let discarded = 0;
    for (const row of [...expired, ...completed]) {
      storage.run("DELETE FROM task_snapshots WHERE id = ?", [row.id]);
      discarded++;
    }

    for (const task of pending) {
      if (task.status === "running") {
        this.updateSnapshotStatus(task.id, "pending", 0);
        task.status = "pending";
        task.progress = 0;
      }
    }

    if (pending.length > 0) {
      this.emit("recovery:pending", pending);
    }

    return {
      recovered: pending.length,
      tasks: pending,
      discarded,
    };
  }

  getActiveSnapshots(): TaskSnapshot[] {
    const storage = getStorage();
    return storage.query(
      `SELECT * FROM task_snapshots WHERE status IN ('pending', 'running') ORDER BY started_at ASC`
    ) as TaskSnapshot[];
  }

  getAllSnapshots(limit: number = 100): TaskSnapshot[] {
    const storage = getStorage();
    return storage.query(
      `SELECT * FROM task_snapshots ORDER BY updated_at DESC LIMIT ?`,
      [limit]
    ) as TaskSnapshot[];
  }

  clearCompleted(): number {
    const storage = getStorage();
    const result = storage.query(
      `SELECT id FROM task_snapshots WHERE status IN ('completed', 'failed', 'risk_detected')`
    ) as Array<{ id: string }>;
    for (const row of result) {
      storage.run("DELETE FROM task_snapshots WHERE id = ?", [row.id]);
    }
    return result.length;
  }

  clearAll(): void {
    const storage = getStorage();
    storage.run("DELETE FROM task_snapshots");
  }
}

export const crashRecovery = new CrashRecoveryManager();
