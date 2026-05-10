import { EventEmitter } from "events";

export interface ConcurrencyConfig {
  min: number;
  max: number;
  default: number;
  recommended: { low: number; high: number };
}

export interface ResourceUsage {
  cpu: number;
  memory: number;
  memoryMB: number;
}

const DEFAULT_CONFIG: ConcurrencyConfig = {
  min: 1,
  max: 10,
  default: 3,
  recommended: { low: 2, high: 5 },
};

export class ConcurrencyController extends EventEmitter {
  private current: number;
  private config: ConcurrencyConfig;
  private activeCount: number = 0;
  private waitingQueue: Array<{ resolve: () => void; task: string }> = [];
  private resourceCheckInterval: NodeJS.Timeout | null = null;
  private lastResourceUsage: ResourceUsage = { cpu: 0, memory: 0, memoryMB: 0 };

  constructor(config?: Partial<ConcurrencyConfig>) {
    super();
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.current = this.config.default;
    this.startResourceMonitor();
  }

  getConcurrency(): number {
    return this.current;
  }

  setConcurrency(value: number, reason?: string): number {
    const clamped = Math.max(this.config.min, Math.min(this.config.max, value));
    if (clamped !== this.current) {
      const old = this.current;
      this.current = clamped;
      this.emit("concurrency:changed", { from: old, to: clamped, reason: reason || "user" });
      this.processWaitingQueue();
    }
    return this.current;
  }

  getConfig(): ConcurrencyConfig {
    return { ...this.config };
  }

  getActiveCount(): number {
    return this.activeCount;
  }

  getWaitingCount(): number {
    return this.waitingQueue.length;
  }

  getResourceUsage(): ResourceUsage {
    return { ...this.lastResourceUsage };
  }

  async acquire(taskId: string): Promise<void> {
    if (this.activeCount < this.current) {
      this.activeCount++;
      this.emit("slot:acquired", { taskId, activeCount: this.activeCount, maxConcurrency: this.current });
      return;
    }

    return new Promise<void>((resolve) => {
      this.waitingQueue.push({ resolve, task: taskId });
      this.emit("slot:waiting", { taskId, waitingCount: this.waitingQueue.length });
    });
  }

  release(taskId: string): void {
    this.activeCount = Math.max(0, this.activeCount - 1);
    this.emit("slot:released", { taskId, activeCount: this.activeCount });
    this.processWaitingQueue();
  }

  private processWaitingQueue(): void {
    while (this.activeCount < this.current && this.waitingQueue.length > 0) {
      const entry = this.waitingQueue.shift()!;
      this.activeCount++;
      this.emit("slot:acquired", { taskId: entry.task, activeCount: this.activeCount, maxConcurrency: this.current });
      entry.resolve();
    }
  }

  private startResourceMonitor(): void {
    this.resourceCheckInterval = setInterval(() => {
      this.checkResources();
    }, 5000);
  }

  private checkResources(): void {
    try {
      const usage = process.memoryUsage();
      this.lastResourceUsage = {
        cpu: 0,
        memory: usage.heapUsed / usage.heapTotal,
        memoryMB: Math.round(usage.rss / 1024 / 1024),
      };

      if (this.lastResourceUsage.memory > 0.85) {
        const recommended = Math.max(this.config.min, this.current - 1);
        if (recommended < this.current) {
          this.setConcurrency(recommended, "memory_pressure");
          this.emit("resource:warning", {
            type: "memory",
            usage: this.lastResourceUsage.memory,
            message: `内存使用率过高(${(this.lastResourceUsage.memory * 100).toFixed(1)}%)，并发数已自动调整为${recommended}`,
          });
        }
      }
    } catch {}
  }

  destroy(): void {
    if (this.resourceCheckInterval) {
      clearInterval(this.resourceCheckInterval);
      this.resourceCheckInterval = null;
    }
    for (const entry of this.waitingQueue) {
      entry.resolve();
    }
    this.waitingQueue = [];
    this.activeCount = 0;
    this.removeAllListeners();
  }
}
