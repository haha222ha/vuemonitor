import { EventEmitter } from "events";
import { getStorage } from "../storage/sqlite";

export interface ScheduledTask {
  id: string;
  product_id: string;
  platform: string;
  platform_product_id: string;
  product_name: string;
  frequency_minutes: number;
  is_active: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  created_at: string;
}

export interface SchedulerState {
  isRunning: boolean;
  activeTasks: number;
  totalTasks: number;
  nextRunAt: string | null;
}

type CollectCallback = (tasks: ScheduledTask[]) => Promise<void>;

export class LocalScheduler extends EventEmitter {
  private timers: Map<string, NodeJS.Timeout> = new Map();
  private registeredTasks: Map<string, ScheduledTask> = new Map();
  private isRunning: boolean = false;
  private collectCallback: CollectCallback | null = null;
  private mainLoopTimer: NodeJS.Timeout | null = null;
  private readonly MAIN_LOOP_INTERVAL = 60000;

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
  }

  getState(): SchedulerState {
    const activeTasks = Array.from(this.registeredTasks.values()).filter((t) => t.is_active);
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
    };
  }

  async addTask(task: Omit<ScheduledTask, "id" | "last_run_at" | "next_run_at" | "created_at">): Promise<ScheduledTask> {
    const id = crypto.randomUUID();
    const now = new Date().toISOString();
    const nextRun = new Date(Date.now() + task.frequency_minutes * 60000).toISOString();

    const scheduledTask: ScheduledTask = {
      ...task,
      id,
      last_run_at: null,
      next_run_at: nextRun,
      created_at: now,
    };

    this.registeredTasks.set(id, scheduledTask);
    await this.persistTask(scheduledTask);

    if (this.isRunning && task.is_active) {
      this.scheduleTask(scheduledTask);
    }

    this.emit("task:added", { task: scheduledTask });
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
      this.scheduleTask(task);
    }

    await this.persistTask(task);
    this.emit("task:toggled", { taskId, active });
    return task;
  }

  async updateFrequency(taskId: string, frequencyMinutes: number): Promise<ScheduledTask | null> {
    const task = this.registeredTasks.get(taskId);
    if (!task) return null;

    task.frequency_minutes = Math.max(5, frequencyMinutes);
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

  getTask(taskId: string): ScheduledTask | null {
    return this.registeredTasks.get(taskId) || null;
  }

  getAllTasks(): ScheduledTask[] {
    return Array.from(this.registeredTasks.values());
  }

  getActiveTasks(): ScheduledTask[] {
    return Array.from(this.registeredTasks.values()).filter((t) => t.is_active);
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
    this.emit("task:executing", { taskId: task.id, platform: task.platform, productName: task.product_name });

    if (this.collectCallback) {
      try {
        await this.collectCallback([task]);
      } catch (err) {
        this.emit("task:error", { taskId: task.id, error: String(err) });
      }
    }

    task.last_run_at = new Date().toISOString();
    task.next_run_at = new Date(Date.now() + task.frequency_minutes * 60000).toISOString();

    await this.persistTask(task);

    if (task.is_active && this.isRunning) {
      this.scheduleTask(task);
    }

    this.emit("task:executed", { taskId: task.id, nextRunAt: task.next_run_at });
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
      const rows = storage.query("SELECT * FROM scheduled_tasks") as ScheduledTask[];
      for (const row of rows) {
        this.registeredTasks.set(row.id, row);
        if (row.is_active) {
          this.scheduleTask(row);
        }
      }
    } catch {}
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
        next_run_at TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
      )
    `);
  }

  private async persistTask(task: ScheduledTask): Promise<void> {
    try {
      const storage = getStorage();
      this.ensureTable(storage);
      storage.run(
        `INSERT OR REPLACE INTO scheduled_tasks
         (id, product_id, platform, platform_product_id, product_name, frequency_minutes, is_active, last_run_at, next_run_at, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [
          task.id,
          task.product_id,
          task.platform,
          task.platform_product_id,
          task.product_name,
          task.frequency_minutes,
          task.is_active ? 1 : 0,
          task.last_run_at,
          task.next_run_at,
          task.created_at,
        ]
      );
    } catch {}
  }

  destroy(): void {
    this.stop();
    this.registeredTasks.clear();
    this.collectCallback = null;
    this.removeAllListeners();
  }
}

export const localScheduler = new LocalScheduler();
