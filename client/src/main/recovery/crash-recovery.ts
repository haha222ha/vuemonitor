import { getStorage } from "../storage/sqlite";
import { EventEmitter } from "events";
import * as fs from "fs";
import * as path from "path";
import { app } from "electron";
import { logger } from "../logger/logger";

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

export interface TaskCheckpoint {
  taskId: string;
  phase: "loading" | "extracting" | "risk_check" | "normalizing" | "saving";
  progress: number;
  partialData: string | null;
  timestamp: string;
}

export type RecoveryStrategy = "retry" | "skip" | "manual" | "resume_from_checkpoint";

export interface RecoveryPlan {
  taskId: string;
  strategy: RecoveryStrategy;
  reason: string;
  retryDelay: number;
  checkpoint: TaskCheckpoint | null;
}

export interface RecoveryResult {
  recovered: number;
  tasks: TaskSnapshot[];
  discarded: number;
  plans: RecoveryPlan[];
}

export interface RecoveryStats {
  totalRecoveries: number;
  successfulRecoveries: number;
  failedRecoveries: number;
  lastRecoveryAt: string | null;
  averageRecoveryTimeMs: number;
}

const BACKOFF_BASE_MS = 5000;
const BACKOFF_MAX_MS = 300000;
const CHECKPOINT_INTERVAL_MS = 5000;
const MAX_CHECKPOINT_AGE_MS = 48 * 60 * 60 * 1000;

class CrashRecoveryManager extends EventEmitter {
  private initialized = false;
  private checkpointTimers: Map<string, NodeJS.Timeout> = new Map();
  private activeCheckpoints: Map<string, TaskCheckpoint> = new Map();
  private checkpointDir: string;
  private stats: RecoveryStats = {
    totalRecoveries: 0,
    successfulRecoveries: 0,
    failedRecoveries: 0,
    lastRecoveryAt: null,
    averageRecoveryTimeMs: 0,
  };
  private recoveryStartTimes: Map<string, number> = new Map();

  constructor() {
    super();
    this.checkpointDir = path.join(app.getPath("userData"), "recovery-checkpoints");
  }

  init(): void {
    if (this.initialized) return;
    this.initialized = true;
    this.ensureTable();
    this.ensureCheckpointDir();
    this.loadStats();
    this.cleanupExpiredCheckpoints();
    logger.info("CrashRecovery", "崩溃恢复管理器初始化完成");
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

  private ensureCheckpointDir(): void {
    try {
      if (!fs.existsSync(this.checkpointDir)) {
        fs.mkdirSync(this.checkpointDir, { recursive: true });
      }
    } catch (e) {
      logger.warn("CrashRecovery", "创建检查点目录失败", { error: String(e) });
    }
  }

  private checkpointPath(taskId: string): string {
    return path.join(this.checkpointDir, `${taskId}.json`);
  }

  private loadStats(): void {
    try {
      const statsPath = path.join(this.checkpointDir, "recovery-stats.json");
      if (fs.existsSync(statsPath)) {
        const raw = fs.readFileSync(statsPath, "utf-8");
        const loaded = JSON.parse(raw);
        this.stats = { ...this.stats, ...loaded };
      }
    } catch (e) {
      logger.warn("CrashRecovery", "加载恢复统计失败", { error: String(e) });
    }
  }

  private persistStats(): void {
    try {
      const statsPath = path.join(this.checkpointDir, "recovery-stats.json");
      fs.writeFileSync(statsPath, JSON.stringify(this.stats, null, 2), "utf-8");
    } catch (e) {
      logger.warn("CrashRecovery", "持久化恢复统计失败", { error: String(e) });
    }
  }

  private cleanupExpiredCheckpoints(): void {
    try {
      if (!fs.existsSync(this.checkpointDir)) return;
      const files = fs.readdirSync(this.checkpointDir);
      const now = Date.now();
      let cleaned = 0;

      for (const file of files) {
        if (!file.endsWith(".json") || file === "recovery-stats.json") continue;
        try {
          const filePath = path.join(this.checkpointDir, file);
          const raw = fs.readFileSync(filePath, "utf-8");
          const checkpoint: TaskCheckpoint = JSON.parse(raw);
          const age = now - new Date(checkpoint.timestamp).getTime();
          if (age > MAX_CHECKPOINT_AGE_MS) {
            fs.unlinkSync(filePath);
            cleaned++;
          }
        } catch {
          const filePath = path.join(this.checkpointDir, file);
          try { fs.unlinkSync(filePath); cleaned++; } catch {}
        }
      }

      if (cleaned > 0) {
        logger.info("CrashRecovery", "清理过期检查点", { cleaned });
      }
    } catch (e) {
      logger.warn("CrashRecovery", "清理检查点失败", { error: String(e) });
    }
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

    if (status === "completed") {
      this.recordRecoverySuccess(taskId);
    } else if (status === "failed") {
      this.recordRecoveryFailure(taskId);
    }
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
    this.deleteCheckpoint(taskId);
  }

  saveCheckpoint(checkpoint: TaskCheckpoint): void {
    this.activeCheckpoints.set(checkpoint.taskId, checkpoint);

    try {
      const filePath = this.checkpointPath(checkpoint.taskId);
      fs.writeFileSync(filePath, JSON.stringify(checkpoint, null, 2), "utf-8");
    } catch (e) {
      logger.warn("CrashRecovery", "保存检查点失败", { taskId: checkpoint.taskId, error: String(e) });
    }

    this.emit("checkpoint:saved", checkpoint.taskId, checkpoint.phase, checkpoint.progress);
  }

  loadCheckpoint(taskId: string): TaskCheckpoint | null {
    const inMemory = this.activeCheckpoints.get(taskId);
    if (inMemory) return inMemory;

    try {
      const filePath = this.checkpointPath(taskId);
      if (fs.existsSync(filePath)) {
        const raw = fs.readFileSync(filePath, "utf-8");
        return JSON.parse(raw) as TaskCheckpoint;
      }
    } catch (e) {
      logger.warn("CrashRecovery", "加载检查点失败", { taskId, error: String(e) });
    }
    return null;
  }

  deleteCheckpoint(taskId: string): void {
    this.activeCheckpoints.delete(taskId);

    try {
      const filePath = this.checkpointPath(taskId);
      if (fs.existsSync(filePath)) {
        fs.unlinkSync(filePath);
      }
    } catch {}
  }

  startPeriodicCheckpoint(taskId: string, getProgress: () => { phase: TaskCheckpoint["phase"]; progress: number; partialData?: string | null }): void {
    this.stopPeriodicCheckpoint(taskId);

    const timer = setInterval(() => {
      try {
        const state = getProgress();
        this.saveCheckpoint({
          taskId,
          phase: state.phase,
          progress: state.progress,
          partialData: state.partialData ?? null,
          timestamp: new Date().toISOString(),
        });
      } catch {}
    }, CHECKPOINT_INTERVAL_MS);

    this.checkpointTimers.set(taskId, timer);
  }

  stopPeriodicCheckpoint(taskId: string): void {
    const timer = this.checkpointTimers.get(taskId);
    if (timer) {
      clearInterval(timer);
      this.checkpointTimers.delete(taskId);
    }
  }

  calculateBackoffDelay(retryCount: number): number {
    const delay = Math.min(BACKOFF_BASE_MS * Math.pow(2, retryCount), BACKOFF_MAX_MS);
    const jitter = Math.random() * 0.3 * delay;
    return Math.floor(delay + jitter);
  }

  createRecoveryPlan(task: TaskSnapshot): RecoveryPlan {
    const checkpoint = this.loadCheckpoint(task.id);

    if (checkpoint && checkpoint.phase === "saving" && checkpoint.progress >= 80) {
      return {
        taskId: task.id,
        strategy: "resume_from_checkpoint",
        reason: `任务在${checkpoint.phase}阶段中断，进度${checkpoint.progress}%，可从检查点恢复`,
        retryDelay: 0,
        checkpoint,
      };
    }

    if (task.retryCount >= task.maxRetries) {
      return {
        taskId: task.id,
        strategy: "manual",
        reason: `已达到最大重试次数(${task.maxRetries})，需要手动处理`,
        retryDelay: 0,
        checkpoint: null,
      };
    }

    if (task.error) {
      const isTransientError = this.isTransientError(task.error);
      if (!isTransientError) {
        return {
          taskId: task.id,
          strategy: "skip",
          reason: `非瞬态错误: ${task.error.substring(0, 100)}`,
          retryDelay: 0,
          checkpoint: null,
        };
      }
    }

    if (task.status === "risk_detected") {
      return {
        taskId: task.id,
        strategy: "manual",
        reason: "任务因风控检测中断，需要手动确认后重试",
        retryDelay: this.calculateBackoffDelay(task.retryCount),
        checkpoint: null,
      };
    }

    const retryDelay = this.calculateBackoffDelay(task.retryCount);
    return {
      taskId: task.id,
      strategy: "retry",
      reason: `自动重试(第${task.retryCount + 1}次)，延迟${Math.round(retryDelay / 1000)}秒`,
      retryDelay,
      checkpoint,
    };
  }

  private isTransientError(error: string): boolean {
    const transientPatterns = [
      /timeout/i, /ETIMEDOUT/i, /ECONNRESET/i, /ECONNREFUSED/i,
      /ENOTFOUND/i, /socket hang up/i, /network/i, /临时/i,
      /超时/i, /rate limit/i, /429/i, /503/i, /502/i,
      /页面加载失败/i, /采集超时/i,
    ];
    return transientPatterns.some((p) => p.test(error));
  }

  resolveConflict(task: TaskSnapshot): "re_collect" | "use_partial" | "discard" {
    const checkpoint = this.loadCheckpoint(task.id);

    if (!checkpoint || !checkpoint.partialData) {
      return "re_collect";
    }

    try {
      const partial = JSON.parse(checkpoint.partialData);
      const hasEssentialFields = partial.product_name && partial.platform_product_id;

      if (hasEssentialFields && checkpoint.progress >= 60) {
        logger.info("CrashRecovery", "检测到有效部分数据，选择使用部分数据", { taskId: task.id, progress: checkpoint.progress });
        return "use_partial";
      }
    } catch {}

    return "re_collect";
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
      this.deleteCheckpoint(row.id);
      discarded++;
    }

    const plans: RecoveryPlan[] = [];
    for (const task of pending) {
      if (task.status === "running") {
        this.updateSnapshotStatus(task.id, "pending", 0);
        task.status = "pending";
        task.progress = 0;
      }

      const plan = this.createRecoveryPlan(task);
      plans.push(plan);
      this.recoveryStartTimes.set(task.id, Date.now());
    }

    this.stats.totalRecoveries += pending.length;
    this.stats.lastRecoveryAt = new Date().toISOString();
    this.persistStats();

    if (pending.length > 0) {
      this.emit("recovery:pending", pending, plans);
      logger.info("CrashRecovery", "崩溃恢复完成", {
        recovered: pending.length,
        discarded,
        strategies: plans.map((p) => `${p.taskId}:${p.strategy}`).join(","),
      });
    }

    return {
      recovered: pending.length,
      tasks: pending,
      discarded,
      plans,
    };
  }

  private recordRecoverySuccess(taskId: string): void {
    this.stats.successfulRecoveries++;
    const startTime = this.recoveryStartTimes.get(taskId);
    if (startTime) {
      const elapsed = Date.now() - startTime;
      const total = this.stats.successfulRecoveries;
      this.stats.averageRecoveryTimeMs = Math.round(
        (this.stats.averageRecoveryTimeMs * (total - 1) + elapsed) / total
      );
      this.recoveryStartTimes.delete(taskId);
    }
    this.persistStats();
    this.emit("recovery:success", taskId);
  }

  private recordRecoveryFailure(taskId: string): void {
    this.stats.failedRecoveries++;
    this.recoveryStartTimes.delete(taskId);
    this.persistStats();
    this.emit("recovery:failed", taskId);
  }

  getRecoveryStats(): RecoveryStats {
    return { ...this.stats };
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
      this.deleteCheckpoint(row.id);
    }
    return result.length;
  }

  clearAll(): void {
    const storage = getStorage();
    storage.run("DELETE FROM task_snapshots");
    for (const [taskId] of this.activeCheckpoints) {
      this.deleteCheckpoint(taskId);
    }
    this.activeCheckpoints.clear();
  }

  destroy(): void {
    for (const [_, timer] of this.checkpointTimers) {
      clearInterval(timer);
    }
    this.checkpointTimers.clear();
    this.activeCheckpoints.clear();
    this.recoveryStartTimes.clear();
    this.removeAllListeners();
  }
}

export const crashRecovery = new CrashRecoveryManager();
