import { app } from "electron";
import * as fs from "fs";
import * as path from "path";

export type LogLevel = "debug" | "info" | "warn" | "error" | "fatal";

export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  module: string;
  message: string;
  data?: Record<string, unknown>;
  error?: string;
  stack?: string;
  sessionId: string;
}

export interface LogConfig {
  level: LogLevel;
  maxFileSize: number;
  maxFiles: number;
  enableConsole: boolean;
  enableFile: boolean;
  uploadEndpoint: string | null;
}

const LOG_LEVEL_PRIORITY: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
  fatal: 4,
};

const DEFAULT_CONFIG: LogConfig = {
  level: "info",
  maxFileSize: 10 * 1024 * 1024,
  maxFiles: 5,
  enableConsole: true,
  enableFile: true,
  uploadEndpoint: null,
};

export class StructuredLogger {
  private config: LogConfig;
  private logDir: string;
  private currentLogFile: string;
  private sessionId: string;
  private buffer: LogEntry[] = [];
  private flushTimer: ReturnType<typeof setInterval> | null = null;
  private writeStream: fs.WriteStream | null = null;
  private uploadQueue: LogEntry[] = [];
  private uploading: boolean = false;

  constructor(config?: Partial<LogConfig>) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.sessionId = crypto.randomUUID().substring(0, 8);

    const userDataPath = app.getPath("userData");
    this.logDir = path.join(userDataPath, "logs");

    if (!fs.existsSync(this.logDir)) {
      fs.mkdirSync(this.logDir, { recursive: true });
    }

    const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, "");
    this.currentLogFile = path.join(this.logDir, `xhs365_${dateStr}.log`);

    this.openStream();
    this.cleanOldLogs();

    this.flushTimer = setInterval(() => this.flush(), 5000);
  }

  private openStream(): void {
    if (!this.config.enableFile) return;
    try {
      this.writeStream = fs.createWriteStream(this.currentLogFile, {
        flags: "a",
        encoding: "utf8",
      });
    } catch {
      this.config.enableFile = false;
    }
  }

  private cleanOldLogs(): void {
    try {
      const files = fs
        .readdirSync(this.logDir)
        .filter((f) => f.startsWith("xhs365_") && f.endsWith(".log"))
        .sort();

      while (files.length > this.config.maxFiles) {
        const toDelete = files.shift();
        if (toDelete) {
          fs.unlinkSync(path.join(this.logDir, toDelete));
        }
      }
    } catch {}
  }

  private checkRotation(): void {
    if (!this.config.enableFile) return;
    try {
      const stat = fs.statSync(this.currentLogFile);
      if (stat.size >= this.config.maxFileSize) {
        this.writeStream?.end();
        const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
        const rotatedFile = this.currentLogFile.replace(".log", `_${timestamp}.log`);
        fs.renameSync(this.currentLogFile, rotatedFile);

        const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, "");
        this.currentLogFile = path.join(this.logDir, `xhs365_${dateStr}.log`);
        this.openStream();
        this.cleanOldLogs();
      }
    } catch {}
  }

  debug(module: string, message: string, data?: Record<string, unknown>): void {
    this.log("debug", module, message, data);
  }

  info(module: string, message: string, data?: Record<string, unknown>): void {
    this.log("info", module, message, data);
  }

  warn(module: string, message: string, data?: Record<string, unknown>): void {
    this.log("warn", module, message, data);
  }

  error(module: string, message: string, error?: Error | unknown, data?: Record<string, unknown>): void {
    const entry: Partial<LogEntry> = { data };
    if (error instanceof Error) {
      entry.error = error.message;
      entry.stack = error.stack;
    } else if (error) {
      entry.error = String(error);
    }
    this.log("error", module, message, data, entry.error, entry.stack);
  }

  fatal(module: string, message: string, error?: Error | unknown, data?: Record<string, unknown>): void {
    const entry: Partial<LogEntry> = { data };
    if (error instanceof Error) {
      entry.error = error.message;
      entry.stack = error.stack;
    } else if (error) {
      entry.error = String(error);
    }
    this.log("fatal", module, message, data, entry.error, entry.stack);
  }

  private log(
    level: LogLevel,
    module: string,
    message: string,
    data?: Record<string, unknown>,
    error?: string,
    stack?: string
  ): void {
    if (LOG_LEVEL_PRIORITY[level] < LOG_LEVEL_PRIORITY[this.config.level]) return;

    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level,
      module,
      message,
      data,
      error,
      stack,
      sessionId: this.sessionId,
    };

    this.buffer.push(entry);

    if (this.config.enableConsole) {
      this.consoleOutput(entry);
    }

    if (level === "error" || level === "fatal") {
      this.flush();
    }

    if (this.config.uploadEndpoint) {
      this.uploadQueue.push(entry);
    }
  }

  private consoleOutput(entry: LogEntry): void {
    const prefix = `[${entry.timestamp}] [${entry.level.toUpperCase()}] [${entry.module}]`;
    const msg = `${prefix} ${entry.message}`;
    switch (entry.level) {
      case "debug":
        console.debug(msg, entry.data || "");
        break;
      case "info":
        console.info(msg, entry.data || "");
        break;
      case "warn":
        console.warn(msg, entry.data || "");
        break;
      case "error":
      case "fatal":
        console.error(msg, entry.error || "", entry.data || "");
        break;
    }
  }

  flush(): void {
    if (this.buffer.length === 0) return;
    if (!this.config.enableFile || !this.writeStream) return;

    const entries = this.buffer.splice(0);
    const lines = entries.map((e) => JSON.stringify(e)).join("\n") + "\n";

    try {
      this.writeStream.write(lines);
      this.checkRotation();
    } catch {}
  }

  getRecentLogs(count: number = 100, level?: LogLevel, module?: string): LogEntry[] {
    const entries: LogEntry[] = [];
    try {
      const content = fs.readFileSync(this.currentLogFile, "utf8");
      const lines = content.trim().split("\n").filter(Boolean);

      for (const line of lines) {
        try {
          const entry = JSON.parse(line) as LogEntry;
          if (level && LOG_LEVEL_PRIORITY[entry.level] < LOG_LEVEL_PRIORITY[level]) continue;
          if (module && entry.module !== module) continue;
          entries.push(entry);
        } catch {}
      }
    } catch {}

    return entries.slice(-count);
  }

  getLogFiles(): Array<{ name: string; size: number; modified: string }> {
    const files: Array<{ name: string; size: number; modified: string }> = [];
    try {
      const items = fs.readdirSync(this.logDir);
      for (const item of items) {
        if (!item.startsWith("xhs365_") || !item.endsWith(".log")) continue;
        const fullPath = path.join(this.logDir, item);
        const stat = fs.statSync(fullPath);
        files.push({
          name: item,
          size: stat.size,
          modified: stat.mtime.toISOString(),
        });
      }
      files.sort((a, b) => b.modified.localeCompare(a.modified));
    } catch {}
    return files;
  }

  exportLogs(format: "json" | "text" = "json"): string {
    this.flush();

    const files = this.getLogFiles();
    const allEntries: LogEntry[] = [];

    for (const file of files) {
      try {
        const content = fs.readFileSync(path.join(this.logDir, file.name), "utf8");
        const lines = content.trim().split("\n").filter(Boolean);
        for (const line of lines) {
          try {
            allEntries.push(JSON.parse(line) as LogEntry);
          } catch {}
        }
      } catch {}
    }

    allEntries.sort((a, b) => a.timestamp.localeCompare(b.timestamp));

    if (format === "json") {
      return JSON.stringify(allEntries, null, 2);
    }

    return allEntries
      .map((e) => {
        let line = `[${e.timestamp}] [${e.level.toUpperCase()}] [${e.module}] ${e.message}`;
        if (e.data) line += ` | data: ${JSON.stringify(e.data)}`;
        if (e.error) line += ` | error: ${e.error}`;
        return line;
      })
      .join("\n");
  }

  async uploadLogs(): Promise<{ success: boolean; uploaded: number }> {
    if (!this.config.uploadEndpoint) {
      return { success: false, uploaded: 0 };
    }

    if (this.uploading || this.uploadQueue.length === 0) {
      return { success: false, uploaded: 0 };
    }

    this.uploading = true;
    const batch = this.uploadQueue.splice(0, 50);

    try {
      const axios = require("axios");
      await axios.post(this.config.uploadEndpoint!, {
        logs: batch,
        sessionId: this.sessionId,
        appVersion: app.getVersion(),
        platform: process.platform,
      }, { timeout: 10000 });
      return { success: true, uploaded: batch.length };
    } catch {
      this.uploadQueue.unshift(...batch);
      return { success: false, uploaded: 0 };
    } finally {
      this.uploading = false;
    }
  }

  setLevel(level: LogLevel): void {
    this.config.level = level;
  }

  setUploadEndpoint(endpoint: string | null): void {
    this.config.uploadEndpoint = endpoint;
  }

  getLogDir(): string {
    return this.logDir;
  }

  getStats(): {
    sessionId: string;
    bufferSize: number;
    uploadQueueSize: number;
    logFiles: number;
    currentLogFile: string;
    config: LogConfig;
  } {
    return {
      sessionId: this.sessionId,
      bufferSize: this.buffer.length,
      uploadQueueSize: this.uploadQueue.length,
      logFiles: this.getLogFiles().length,
      currentLogFile: this.currentLogFile,
      config: { ...this.config },
    };
  }

  clearLogs(): number {
    let deleted = 0;
    try {
      const files = fs.readdirSync(this.logDir);
      for (const file of files) {
        if (file.startsWith("xhs365_") && file.endsWith(".log")) {
          fs.unlinkSync(path.join(this.logDir, file));
          deleted++;
        }
      }
      this.writeStream?.end();
      const dateStr = new Date().toISOString().slice(0, 10).replace(/-/g, "");
      this.currentLogFile = path.join(this.logDir, `xhs365_${dateStr}.log`);
      this.openStream();
    } catch {}
    return deleted;
  }

  destroy(): void {
    this.flush();
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
      this.flushTimer = null;
    }
    this.writeStream?.end();
    this.writeStream = null;
  }
}

export const logger = new StructuredLogger();
