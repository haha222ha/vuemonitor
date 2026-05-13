import { EventEmitter } from "events";
import { getStorage } from "../storage/sqlite";
import { logger } from "../logger/logger";

export interface ScheduledTask {
  id: string;
  product_id: string;
  platform: string;
  platform_product_id: string;
  product_name: string;
  frequency_minutes: number;
  is_active: boolean;
  last_run_at: string | null;
  last_run_status: "success" | "failed" | "risk_detected" | null;
  next_run_at: string | null;
  retry_count: number;
  max_retries: number;
  consecutive_failures: number;
  created_at: string;
}

export interface SchedulerState {
  isRunning: boolean;
  activeTasks: number;
  totalTasks: number;
  nextRunAt: string | null;
  failedTasks: number;
  stats: SchedulerStats;
}

export interface SchedulerStats {
  totalExecutions: number;
  successfulExecutions: number;
  failedExecutions: number;
  retriedExecutions: number;
  lastExecutionAt: string | null;
  averageIntervalMs: number;
}

type CollectCallback = (tasks: ScheduledTask[]) => Promise<void>;

const MAX_CONSECUTIVE_FAILURES = 5;
const RETRY_BACKOFF_BASE_MS = 60000;
const RETRY_BACKOFF_MAX_MS = 3600000;
const DEFAULT_MAX_RETRIES = 3;
const MIN_FREQUENCY_MINUTES = 5;

export class LocalScheduler extends EventEmitter {
  private timers: Map<string, NodeJS.Timeout> = new Map();
  private registeredTasks: Map<string, ScheduledTask> = new Map();
  private isRunning: boolean = false;
  private collectCallback: CollectCallback | null = null;
  private mainLoopTimer: NodeJS.Timeout | null = null;
  private readonly MAIN_LOOP_INTERVAL = 60000;
  private stats: SchedulerStats = {
    totalExecutions: 0,
    successfulExecutions: 0,
    failedExecutions: 0,
    retriedExecutions: 0,
    lastExecutionAt: null,
    averageIntervalMs: 0,
  };
  private lastExecutionTime: number = 0;

  constructor() {
    super();
  }

  setCollectCallback(callback: CollectCallback): void {
    this.collectCallback = callback;
  }

  async start(): Promise<void> {
    if (this.isRunning) return;
    this.isRunning = true;
    await this.loadTasks();
    this.startMainLoop();
    this.emit("scheduler:started");
    logger.info("LocalScheduler", "调度器启动", { taskCount: this.registeredTasks.size });
  }

  stop(): void {
    this.isRunning = false;
    for (const [taskId, timer] of this.timers) {
      clearTimeout(timer);
    }
    this.timers.clear();
    if (this.mainLoopTimer) {
      clearInterval(this.mainLoopTimer);
      this.mainLoopTimer = null;
    }
    this.emit("scheduler:stopped");
    logger.info("LocalScheduler", "调度器停止");
  }

  getState(): SchedulerState {
    const activeTasks = Array.from(this.registeredTasks.values()).filter((t) => t.is_active);
    const failedTasks = Array.from(this.registeredTasks.values()).filter(
      (t) => t.consecutive_failures > 0
    );
    let nextRunAt: string | null = null;
    for (const task of activeTasks) {
      if (task.next_run_at && (!nextRunAt || task.next_run_at < nextRunAt)) {
        nextRunAt = task.next_run_at;
      }
    }
    return {
      isRunning: this.isRunning,
      activeTasks: activeTasks.length,
      totalTasks: this.registeredTasks.size,
      nextRunAt,
      failedTasks: failedTasks.length,
      stats: { ...this.stats },
    };
  }

  async addTask(task: Omit<ScheduledTask, "id" | "last_run_at" | "last_run_status" | "next_run_at" | "retry_count" | "max_retries" | "consecutive_failures" | "created_at">): Promise<ScheduledTask> {
    const id = crypto.randomUUID();
    const now = new Date().toISOString();
    const nextRun = new Date(Date.now() + task.frequency_minutes * 60000).toISOString();

    const scheduledTask: ScheduledTask = {
      ...task,
      id,
      last_run_at: null,
      last_run_status: null,
      next_run_at: nextRun,
      retry_count: 0,
      max_retries: DEFAULT_MAX_RETRIES,
      consecutive_failures: 0,
      created_at: now,
    };

    this.registeredTasks.set(id, scheduledTask);
    await this.persistTask(scheduledTask);

    if (this.isRunning && task.is_active) {
      this.scheduleTask(scheduledTask);
    }

    this.emit("task:added", { task: scheduledTask });
    logger.info("LocalScheduler", "添加定时任务", { id, product: task.product_name, frequency: task.frequency_minutes });
    return scheduledTask;
  }

  async removeTask(taskId: string): Promise<boolean> {
    const task = this.registeredTasks.get(taskId);
    if (!task) return false;

    if (this.timers.has(taskId)) {
      clearTimeout(this.timers.get(taskId)!);
      this.timers.delete(taskId);
    }

    this.registeredTasks.delete(taskId);

    try {
      const storage = getStorage();
      storage.run("DELETE FROM scheduled_tasks WHERE id = ?", [taskId]);
    } catch {}

    this.emit("task:removed", { taskId });
    logger.info("LocalScheduler", "移除定时任务", { taskId });
    return true;
  }

  async toggleTask(taskId: string, active: boolean): Promise<ScheduledTask | null> {
    const task = this.registeredTasks.get(taskId);
    if (!task) return null;

    task.is_active = active;

    if (!active && this.timers.has(taskId)) {
      clearTimeout(this.timers.get(taskId)!);
      this.timers.delete(taskId);
    } else if (active && this.isRunning) {
      task.next_run_at = new Date(Date.now() + task.frequency_minutes * 60000).toISOString();
      this.scheduleTask(task);
    }

    await this.persistTask(task);
    this.emit("task:toggled", { taskId, active });
    return task;
  }

  async updateFrequency(taskId: string, frequencyMinutes: number): Promise<ScheduledTask | null> {
    const task = this.registeredTasks.get(taskId);
    if (!task) return null;

    task.frequency_minutes = Math.max(MIN_FREQUENCY_MINUTES, frequencyMinutes);
    task.next_run_at = new Date(Date.now() + task.frequency_minutes * 60000).toISOString();

    if (this.timers.has(taskId)) {
      clearTimeout(this.timers.get(taskId)!);
      this.timers.delete(taskId);
    }

    if (this.isRunning && task.is_active) {
      this.scheduleTask(task);
    }

    await this.persistTask(task);
    this.emit("task:frequency_updated", { taskId, frequencyMinutes });
    return task;
  }

  async setMaxRetries(taskId: string, maxRetries: number): Promise<ScheduledTask | null> {
    const task = this.registeredTasks.get(taskId);
    if (!task) return null;

    task.max_retries = Math.max(0, Math.min(10, maxRetries));
    await this.persistTask(task);
    return task;
  }

  async reportTaskResult(taskId: string, status: "success" | "failed" | "risk_detected"): Promise<void> {
    const task = this.registeredTasks.get(taskId);
    if (!task) return;

    task.last_run_status = status;

    if (status === "success") {
      task.consecutive_failures = 0;
      task.retry_count = 0;
      this.stats.successfulExecutions++;
    } else {
      task.consecutive_failures++;
      this.stats.failedExecutions++;

      if (task.consecutive_failures >= MAX_CONSECUTIVE_FAILURES) {
        task.is_active = false;
        if (this.timers.has(taskId)) {
          clearTimeout(this.timers.get(taskId)!);
          this.timers.delete(taskId);
        }
        this.emit("task:auto_disabled", {
          taskId,
          reason: `连续失败${task.consecutive_failures}次，已自动禁用`,
          consecutiveFailures: task.consecutive_failures,
        });
        logger.warn("LocalScheduler", "任务连续失败已自动禁用", {
          taskId,
          consecutiveFailures: task.consecutive_failures,
        });
      } else if (task.retry_count < task.max_retries) {
        this.scheduleRetry(task);
        return;
      }
    }

    await this.persistTask(task);
  }

  private scheduleRetry(task: ScheduledTask): void {
    task.retry_count++;
    this.stats.retriedExecutions++;

    const backoffDelay = Math.min(
      RETRY_BACKOFF_BASE_MS * Math.pow(2, task.retry_count - 1) + Math.random() * 30000,
      RETRY_BACKOFF_MAX_MS
    );

    const retryAt = new Date(Date.now() + backoffDelay).toISOString();
    task.next_run_at = retryAt;

    if (this.timers.has(task.id)) {
      clearTimeout(this.timers.get(task.id)!);
    }

    const timer = setTimeout(async () => {
      await this.executeTask(task);
    }, backoffDelay);

    this.timers.set(task.id, timer);
    this.persistTask(task);

    this.emit("task:retry_scheduled", {
      taskId: task.id,
      retryCount: task.retry_count,
      maxRetries: task.max_retries,
      retryAt,
    });

    logger.info("LocalScheduler", "安排任务重试", {
      taskId: task.id,
      retryCount: task.retry_count,
      maxRetries: task.max_retries,
      delayMs: Math.round(backoffDelay),
    });
  }

  async retryFailedTask(taskId: string): Promise<boolean> {
    const task = this.registeredTasks.get(taskId);
    if (!task) return false;

    task.retry_count = 0;
    task.consecutive_failures = 0;
    task.is_active = true;
    task.next_run_at = new Date().toISOString();

    await this.persistTask(task);

    if (this.isRunning) {
      this.scheduleTask(task);
    }

    this.emit("task:manual_retry", { taskId });
    logger.info("LocalScheduler", "手动重试任务", { taskId });
    return true;
  }

  getTask(taskId: string): ScheduledTask | null {
    return this.registeredTasks.get(taskId) || null;
  }

  getAllTasks(): ScheduledTask[] {
    return Array.from(this.registeredTasks.values());
  }

  getActiveTasks(): ScheduledTask[] {
    return Array.from(this.registeredTasks.values()).filter((t) => t.is_active);
  }

  getFailedTasks(): ScheduledTask[] {
    return Array.from(this.registeredTasks.values()).filter((t) => t.consecutive_failures > 0);
  }

  getStats(): SchedulerStats {
    return { ...this.stats };
  }

  private scheduleTask(task: ScheduledTask): void {
    if (this.timers.has(task.id)) {
      clearTimeout(this.timers.get(task.id)!);
    }

    const now = Date.now();
    const nextRun = task.next_run_at ? new Date(task.next_run_at).getTime() : now;
    const delay = Math.max(0, nextRun - now);

    const timer = setTimeout(async () => {
      await this.executeTask(task);
    }, delay);

    this.timers.set(task.id, timer);
  }

  private async executeTask(task: ScheduledTask): Promise<void> {
    if (!task.is_active) return;

    this.emit("task:executing", { taskId: task.id, platform: task.platform, productName: task.product_name });

    if (this.collectCallback) {
      try {
        await this.collectCallback([task]);
      } catch (err) {
        this.emit("task:error", { taskId: task.id, error: String(err) });
        await this.reportTaskResult(task.id, "failed");
      }
    }

    task.last_run_at = new Date().toISOString();

    this.stats.totalExecutions++;
    const now = Date.now();
    if (this.lastExecutionTime > 0) {
      const interval = now - this.lastExecutionTime;
      const total = this.stats.totalExecutions;
      this.stats.averageIntervalMs = Math.round(
        (this.stats.averageIntervalMs * (total - 1) + interval) / total
      );
    }
    this.lastExecutionTime = now;
    this.stats.lastExecutionAt = new Date().toISOString();

    if (task.last_run_status !== "failed") {
      task.next_run_at = new Date(Date.now() + task.frequency_minutes * 60000).toISOString();
    }

    await this.persistTask(task);

    if (task.is_active && this.isRunning) {
      this.scheduleTask(task);
    }

    this.emit("scheduler:task_executed", { taskId: task.id, nextRunAt: task.next_run_at, status: task.last_run_status });
  }

  private startMainLoop(): void {
    this.mainLoopTimer = setInterval(() => {
      this.checkAndScheduleDueTasks();
    }, this.MAIN_LOOP_INTERVAL);

    this.checkAndScheduleDueTasks();
  }

  private checkAndScheduleDueTasks(): void {
    const now = Date.now();
    for (const task of this.registeredTasks.values()) {
      if (!task.is_active) continue;

      const nextRun = task.next_run_at ? new Date(task.next_run_at).getTime() : 0;
      if (nextRun <= now && !this.timers.has(task.id)) {
        this.scheduleTask(task);
      }
    }
  }

  private async loadTasks(): Promise<void> {
    try {
      const storage = getStorage();
      this.ensureTable(storage);
      const rows = storage.query("SELECT * FROM scheduled_tasks") as Record<string, unknown>[];
      for (const row of rows) {
        const task: ScheduledTask = {
          id: row.id as string,
          product_id: row.product_id as string,
          platform: row.platform as string,
          platform_product_id: row.platform_product_id as string,
          product_name: row.product_name as string,
          frequency_minutes: (row.frequency_minutes as number) || 60,
          is_active: Boolean(row.is_active),
          last_run_at: (row.last_run_at as string) || null,
          last_run_status: (row.last_run_status as ScheduledTask["last_run_status"]) || null,
          next_run_at: (row.next_run_at as string) || null,
          retry_count: (row.retry_count as number) || 0,
          max_retries: (row.max_retries as number) || DEFAULT_MAX_RETRIES,
          consecutive_failures: (row.consecutive_failures as number) || 0,
          created_at: (row.created_at as string) || new Date().toISOString(),
        };
        this.registeredTasks.set(task.id, task);
        if (task.is_active) {
          this.scheduleTask(task);
        }
      }
      logger.info("LocalScheduler", "加载定时任务", { count: this.registeredTasks.size });
    } catch (e) {
      logger.error("LocalScheduler", "加载任务失败", { error: String(e) });
    }
  }

  private ensureTable(storage: ReturnType<typeof getStorage>): void {
    storage.run(`
      CREATE TABLE IF NOT EXISTS scheduled_tasks (
        id TEXT PRIMARY KEY,
        product_id TEXT NOT NULL,
        platform TEXT NOT NULL,
        platform_product_id TEXT NOT NULL,
        product_name TEXT NOT NULL,
        frequency_minutes INTEGER NOT NULL DEFAULT 60,
        is_active INTEGER NOT NULL DEFAULT 1,
        last_run_at TEXT,
        last_run_status TEXT,
        next_run_at TEXT,
        retry_count INTEGER NOT NULL DEFAULT 0,
        max_retries INTEGER NOT NULL DEFAULT 3,
        consecutive_failures INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      )
    `);

    try {
      storage.run(`ALTER TABLE scheduled_tasks ADD COLUMN last_run_status TEXT`);
    } catch {}
    try {
      storage.run(`ALTER TABLE scheduled_tasks ADD COLUMN retry_count INTEGER NOT NULL DEFAULT 0`);
    } catch {}
    try {
      storage.run(`ALTER TABLE scheduled_tasks ADD COLUMN max_retries INTEGER NOT NULL DEFAULT 3`);
    } catch {}
    try {
      storage.run(`ALTER TABLE scheduled_tasks ADD COLUMN consecutive_failures INTEGER NOT NULL DEFAULT 0`);
    } catch {}
  }

  private async persistTask(task: ScheduledTask): Promise<void> {
    try {
      const storage = getStorage();
      this.ensureTable(storage);
      storage.run(
        `INSERT OR REPLACE INTO scheduled_tasks
         (id, product_id, platform, platform_product_id, product_name, frequency_minutes,
          is_active, last_run_at, last_run_status, next_run_at, retry_count, max_retries,
          consecutive_failures, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [
          task.id,
          task.product_id,
          task.platform,
          task.platform_product_id,
          task.product_name,
          task.frequency_minutes,
          task.is_active ? 1 : 0,
          task.last_run_at,
          task.last_run_status,
          task.next_run_at,
          task.retry_count,
          task.max_retries,
          task.consecutive_failures,
          task.created_at,
        ]
      );
    } catch (e) {
      logger.error("LocalScheduler", "持久化任务失败", { taskId: task.id, error: String(e) });
    }
  }

  destroy(): void {
    this.stop();
    this.registeredTasks.clear();
    this.collectCallback = null;
    this.removeAllListeners();
  }
}

export const localScheduler = new LocalScheduler();
