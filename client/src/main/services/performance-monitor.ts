import { EventEmitter } from "events";
import { BrowserWindow, app } from "electron";
import * as os from "os";
import { logger } from "../logger/logger";

export interface PerformanceMetrics {
  timestamp: string;
  cpu: {
    usage: number;
    processCpu: number;
    systemCpu: number;
  };
  memory: {
    rss: number;
    heapTotal: number;
    heapUsed: number;
    external: number;
    systemTotal: number;
    systemFree: number;
    systemUsedPercent: number;
  };
  process: {
    uptime: number;
    pid: number;
    ppid: number;
  };
  network: {
    bytesReceived: number;
    bytesSent: number;
  };
  disk: {
    readCount: number;
    writeCount: number;
    readBytes: number;
    writeBytes: number;
  };
}

export interface PerformanceSnapshot {
  metrics: PerformanceMetrics;
  alerts: PerformanceAlert[];
}

export interface PerformanceAlert {
  type: "cpu" | "memory" | "disk" | "network";
  severity: "warning" | "critical";
  message: string;
  threshold: number;
  current: number;
  timestamp: string;
}

const SAMPLE_INTERVAL = 5000;
const HISTORY_SIZE = 720;
const CPU_WARNING = 70;
const CPU_CRITICAL = 90;
const MEMORY_WARNING = 0.7;
const MEMORY_CRITICAL = 0.85;

class PerformanceMonitor extends EventEmitter {
  private mainWindow: BrowserWindow | null = null;
  private timer: ReturnType<typeof setInterval> | null = null;
  private history: PerformanceMetrics[] = [];
  private alerts: PerformanceAlert[] = [];
  private isRunning: boolean = false;
  private lastCpuInfo: { idle: number; total: number } | null = null;
  private lastDiskInfo: { readCount: number; writeCount: number; readBytes: number; writeBytes: number } | null = null;

  constructor() {
    super();
  }

  setMainWindow(window: BrowserWindow): void {
    this.mainWindow = window;
  }

  start(): void {
    if (this.isRunning) return;
    this.isRunning = true;
    this.timer = setInterval(() => this.sample(), SAMPLE_INTERVAL);
    logger.info("PerformanceMonitor", "性能监控已启动");
  }

  stop(): void {
    this.isRunning = false;
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }

  private async sample(): Promise<void> {
    try {
      const metrics = await this.collectMetrics();
      this.history.push(metrics);
      if (this.history.length > HISTORY_SIZE) {
        this.history.shift();
      }

      const newAlerts = this.checkThresholds(metrics);
      for (const alert of newAlerts) {
        this.alerts.push(alert);
        if (this.alerts.length > 100) {
          this.alerts.shift();
        }
        this.emit("alert", alert);
        logger.warn("PerformanceMonitor", alert.message, {
          type: alert.type,
          severity: alert.severity,
          current: alert.current,
          threshold: alert.threshold,
        });
      }

      this.sendToRenderer("perf:metrics", { metrics, alerts: newAlerts });
    } catch (err) {
      logger.error("PerformanceMonitor", `采样失败: ${err}`);
    }
  }

  private async collectMetrics(): Promise<PerformanceMetrics> {
    const memUsage = process.memoryUsage();
    const cpuUsage = process.cpuUsage();
    const totalMem = os.totalmem();
    const freeMem = os.freemem();

    let processCpu = 0;
    let systemCpu = 0;

    try {
      const cpus = os.cpus();
      let totalIdle = 0;
      let totalTick = 0;
      for (const cpu of cpus) {
        totalIdle += cpu.times.idle;
        totalTick += cpu.times.user + cpu.times.nice + cpu.times.sys + cpu.times.idle + cpu.times.irq;
      }

      if (this.lastCpuInfo) {
        const idleDelta = totalIdle - this.lastCpuInfo.idle;
        const totalDelta = totalTick - this.lastCpuInfo.total;
        systemCpu = totalDelta > 0 ? Math.round((1 - idleDelta / totalDelta) * 100) : 0;
      }

      this.lastCpuInfo = { idle: totalIdle, total: totalTick };

      const cpuPercent = (cpuUsage.user + cpuUsage.system) / 1000000;
      const uptimeSeconds = process.uptime();
      const numCpus = cpus.length;
      processCpu = uptimeSeconds > 0 ? Math.round((cpuPercent / (uptimeSeconds * numCpus)) * 100) : 0;
    } catch {
      processCpu = 0;
      systemCpu = 0;
    }

    let diskInfo = { readCount: 0, writeCount: 0, readBytes: 0, writeBytes: 0 };
    try {
      const currentDisk = {
        readCount: process.ioCounters?.readOperationCount || 0,
        writeCount: process.ioCounters?.writeOperationCount || 0,
        readBytes: process.ioCounters?.readTransferCount || 0,
        writeBytes: process.ioCounters?.writeTransferCount || 0,
      };

      if (this.lastDiskInfo) {
        diskInfo = {
          readCount: currentDisk.readCount - this.lastDiskInfo.readCount,
          writeCount: currentDisk.writeCount - this.lastDiskInfo.writeCount,
          readBytes: currentDisk.readBytes - this.lastDiskInfo.readBytes,
          writeBytes: currentDisk.writeBytes - this.lastDiskInfo.writeBytes,
        };
      }

      this.lastDiskInfo = currentDisk;
    } catch {}

    return {
      timestamp: new Date().toISOString(),
      cpu: {
        usage: Math.max(processCpu, systemCpu),
        processCpu,
        systemCpu,
      },
      memory: {
        rss: memUsage.rss,
        heapTotal: memUsage.heapTotal,
        heapUsed: memUsage.heapUsed,
        external: memUsage.external,
        systemTotal: totalMem,
        systemFree: freeMem,
        systemUsedPercent: Math.round(((totalMem - freeMem) / totalMem) * 100),
      },
      process: {
        uptime: Math.round(process.uptime()),
        pid: process.pid,
        ppid: process.ppid,
      },
      network: {
        bytesReceived: 0,
        bytesSent: 0,
      },
      disk: diskInfo,
    };
  }

  private checkThresholds(metrics: PerformanceMetrics): PerformanceAlert[] {
    const alerts: PerformanceAlert[] = [];

    if (metrics.cpu.usage > CPU_CRITICAL) {
      alerts.push({
        type: "cpu",
        severity: "critical",
        message: `CPU 使用率过高: ${metrics.cpu.usage}%`,
        threshold: CPU_CRITICAL,
        current: metrics.cpu.usage,
        timestamp: metrics.timestamp,
      });
    } else if (metrics.cpu.usage > CPU_WARNING) {
      alerts.push({
        type: "cpu",
        severity: "warning",
        message: `CPU 使用率偏高: ${metrics.cpu.usage}%`,
        threshold: CPU_WARNING,
        current: metrics.cpu.usage,
        timestamp: metrics.timestamp,
      });
    }

    const memRatio = metrics.memory.heapUsed / metrics.memory.heapTotal;
    if (memRatio > MEMORY_CRITICAL) {
      alerts.push({
        type: "memory",
        severity: "critical",
        message: `内存使用率过高: ${Math.round(memRatio * 100)}%`,
        threshold: MEMORY_CRITICAL,
        current: Math.round(memRatio * 100),
        timestamp: metrics.timestamp,
      });
    } else if (memRatio > MEMORY_WARNING) {
      alerts.push({
        type: "memory",
        severity: "warning",
        message: `内存使用率偏高: ${Math.round(memRatio * 100)}%`,
        threshold: MEMORY_WARNING,
        current: Math.round(memRatio * 100),
        timestamp: metrics.timestamp,
      });
    }

    return alerts;
  }

  getHistory(limit: number = 60): PerformanceMetrics[] {
    return this.history.slice(-limit);
  }

  getAlerts(limit: number = 20): PerformanceAlert[] {
    return this.alerts.slice(-limit);
  }

  getLatest(): PerformanceMetrics | null {
    return this.history.length > 0 ? this.history[this.history.length - 1] : null;
  }

  getSummary(): Record<string, unknown> {
    if (this.history.length === 0) return {};

    const recent = this.history.slice(-12);
    const avgCpu = Math.round(recent.reduce((s, m) => s + m.cpu.usage, 0) / recent.length);
    const avgMem = Math.round(recent.reduce((s, m) => s + m.memory.heapUsed, 0) / recent.length);
    const maxCpu = Math.max(...recent.map((m) => m.cpu.usage));
    const maxMem = Math.max(...recent.map((m) => m.memory.heapUsed));

    return {
      avgCpu,
      avgMem,
      maxCpu,
      maxMem,
      sampleCount: this.history.length,
      alertCount: this.alerts.length,
      uptime: Math.round(process.uptime()),
      latest: this.history[this.history.length - 1],
    };
  }

  clearHistory(): void {
    this.history = [];
    this.alerts = [];
  }

  private sendToRenderer(channel: string, data: unknown): void {
    if (this.mainWindow && !this.mainWindow.isDestroyed()) {
      this.mainWindow.webContents.send(channel, data);
    }
  }
}

export const performanceMonitor = new PerformanceMonitor();