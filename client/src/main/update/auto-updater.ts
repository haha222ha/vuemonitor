import { app, BrowserWindow, dialog } from "electron";
import { autoUpdater, UpdateInfo } from "electron-updater";
import { EventEmitter } from "events";
import * as fs from "fs";
import * as path from "path";

export interface AutoUpdateStatus {
  checking: boolean;
  downloading: boolean;
  downloadProgress: number;
  updateAvailable: boolean;
  version: string | null;
  error: string | null;
  downloadSpeed: number;
  eta: number;
  forceUpdate: boolean;
  updateHistory: UpdateHistoryEntry[];
}

export interface UpdateHistoryEntry {
  version: string;
  fromVersion: string;
  timestamp: string;
  success: boolean;
  error?: string;
}

const HISTORY_FILE = "update-history.json";
const MIN_VERSION_KEY = "min-version";

class AutoUpdateManager extends EventEmitter {
  private mainWindow: BrowserWindow | null = null;
  private status: AutoUpdateStatus = {
    checking: false,
    downloading: false,
    downloadProgress: 0,
    updateAvailable: false,
    version: null,
    error: null,
    downloadSpeed: 0,
    eta: 0,
    forceUpdate: false,
    updateHistory: [],
  };
  private lastProgressTime: number = 0;
  private lastProgressBytes: number = 0;
  private minRequiredVersion: string | null = null;

  constructor() {
    super();
    this.loadUpdateHistory();
    this.setupAutoUpdater();
  }

  setMainWindow(window: BrowserWindow): void {
    this.mainWindow = window;
  }

  private loadUpdateHistory(): void {
    try {
      const historyPath = path.join(app.getPath("userData"), HISTORY_FILE);
      if (fs.existsSync(historyPath)) {
        const data = fs.readFileSync(historyPath, "utf-8");
        this.status.updateHistory = JSON.parse(data);
      }
    } catch {
      this.status.updateHistory = [];
    }
  }

  private saveUpdateHistory(): void {
    try {
      const historyPath = path.join(app.getPath("userData"), HISTORY_FILE);
      fs.writeFileSync(historyPath, JSON.stringify(this.status.updateHistory, null, 2));
    } catch {}
  }

  private setupAutoUpdater(): void {
    autoUpdater.autoDownload = false;
    autoUpdater.autoInstallOnAppQuit = true;
    autoUpdater.allowDowngrade = true;
    autoUpdater.allowPrerelease = false;
    autoUpdater.channel = "latest";

    autoUpdater.on("checking-for-update", () => {
      this.status.checking = true;
      this.status.error = null;
      this.sendStatusToRenderer();
    });

    autoUpdater.on("update-available", (info: UpdateInfo) => {
      this.status.checking = false;
      this.status.updateAvailable = true;
      this.status.version = info.version;

      if (this.minRequiredVersion) {
        this.status.forceUpdate = this.compareVersions(info.version, this.minRequiredVersion) >= 0;
      }

      this.sendStatusToRenderer();
      this.emit("update:available", info);

      if (this.mainWindow && !this.mainWindow.isDestroyed()) {
        this.mainWindow.webContents.send("update:available", {
          version: info.version,
          releaseNotes: info.releaseNotes,
          releaseDate: info.releaseDate,
          forceUpdate: this.status.forceUpdate,
        });
      }
    });

    autoUpdater.on("update-not-available", () => {
      this.status.checking = false;
      this.status.updateAvailable = false;
      this.sendStatusToRenderer();
      this.emit("update:not-available");
    });

    autoUpdater.on("download-progress", (progressInfo) => {
      const now = Date.now();
      this.status.downloading = true;
      this.status.downloadProgress = Math.round(progressInfo.percent);

      if (this.lastProgressTime > 0 && this.lastProgressBytes > 0) {
        const timeDelta = (now - this.lastProgressTime) / 1000;
        const bytesDelta = progressInfo.transferred - this.lastProgressBytes;
        if (timeDelta > 0) {
          this.status.downloadSpeed = Math.round(bytesDelta / timeDelta);
          const remaining = progressInfo.total - progressInfo.transferred;
          this.status.eta = this.status.downloadSpeed > 0 ? Math.round(remaining / this.status.downloadSpeed) : 0;
        }
      }

      this.lastProgressTime = now;
      this.lastProgressBytes = progressInfo.transferred;

      this.sendStatusToRenderer();

      if (this.mainWindow && !this.mainWindow.isDestroyed()) {
        this.mainWindow.webContents.send("update:progress", {
          percent: this.status.downloadProgress,
          bytesPerSecond: progressInfo.bytesPerSecond,
          transferred: progressInfo.transferred,
          total: progressInfo.total,
          speed: this.status.downloadSpeed,
          eta: this.status.eta,
        });
      }
    });

    autoUpdater.on("update-downloaded", (info: UpdateInfo) => {
      this.status.downloading = false;
      this.status.downloadProgress = 100;
      this.status.downloadSpeed = 0;
      this.status.eta = 0;
      this.sendStatusToRenderer();
      this.emit("update:downloaded", info);

      if (this.mainWindow && !this.mainWindow.isDestroyed()) {
        this.mainWindow.webContents.send("update:downloaded", {
          version: info.version,
        });
      }
    });

    autoUpdater.on("error", (err) => {
      this.status.checking = false;
      this.status.downloading = false;
      this.status.error = err?.message || "Unknown error";
      this.sendStatusToRenderer();
      this.emit("update:error", err);

      this.status.updateHistory.push({
        version: this.status.version || "unknown",
        fromVersion: app.getVersion(),
        timestamp: new Date().toISOString(),
        success: false,
        error: err?.message,
      });
      this.saveUpdateHistory();
    });
  }

  async checkForUpdate(silent: boolean = true): Promise<void> {
    try {
      if (silent) {
        await autoUpdater.checkForUpdates();
      } else {
        const result = await autoUpdater.checkForUpdates();
        if (!result?.updateInfo) {
          this.status.updateAvailable = false;
          this.sendStatusToRenderer();
        }
      }
    } catch (err) {
      this.status.error = (err as Error).message;
      this.sendStatusToRenderer();
    }
  }

  async downloadUpdate(): Promise<void> {
    try {
      this.lastProgressTime = 0;
      this.lastProgressBytes = 0;
      await autoUpdater.downloadUpdate();
    } catch (err) {
      this.status.error = (err as Error).message;
      this.sendStatusToRenderer();
    }
  }

  async installUpdate(): Promise<void> {
    if (this.mainWindow && !this.mainWindow.isDestroyed()) {
      this.mainWindow.webContents.send("update:installing");
    }

    this.status.updateHistory.push({
      version: this.status.version || "unknown",
      fromVersion: app.getVersion(),
      timestamp: new Date().toISOString(),
      success: true,
    });
    this.saveUpdateHistory();

    setImmediate(() => {
      autoUpdater.quitAndInstall(false, true);
    });
  }

  async rollbackUpdate(): Promise<void> {
    const history = this.status.updateHistory;
    if (history.length < 2) {
      throw new Error("No previous version to rollback to");
    }

    const lastSuccessful = [...history].reverse().find((e) => e.success);
    if (!lastSuccessful) {
      throw new Error("No successful update to rollback to");
    }

    this.status.updateHistory.push({
      version: lastSuccessful.fromVersion,
      fromVersion: app.getVersion(),
      timestamp: new Date().toISOString(),
      success: true,
    });
    this.saveUpdateHistory();

    if (this.mainWindow && !this.mainWindow.isDestroyed()) {
      dialog.showMessageBox(this.mainWindow, {
        type: "info",
        title: "版本回滚",
        message: `即将回滚到版本 ${lastSuccessful.fromVersion}`,
        detail: "请手动下载并安装旧版本安装包。",
      });
    }
  }

  setMinRequiredVersion(version: string): void {
    this.minRequiredVersion = version;
  }

  getMinRequiredVersion(): string | null {
    return this.minRequiredVersion;
  }

  getStatus(): AutoUpdateStatus {
    return { ...this.status, updateHistory: [...this.status.updateHistory] };
  }

  getUpdateHistory(): UpdateHistoryEntry[] {
    return [...this.status.updateHistory];
  }

  clearUpdateHistory(): void {
    this.status.updateHistory = [];
    this.saveUpdateHistory();
  }

  private compareVersions(a: string, b: string): number {
    const pa = a.replace(/^v/, "").split(".").map(Number);
    const pb = b.replace(/^v/, "").split(".").map(Number);
    for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
      const va = pa[i] || 0;
      const vb = pb[i] || 0;
      if (va > vb) return 1;
      if (va < vb) return -1;
    }
    return 0;
  }

  private sendStatusToRenderer(): void {
    if (this.mainWindow && !this.mainWindow.isDestroyed()) {
      this.mainWindow.webContents.send("update:status", this.status);
    }
  }
}

export const autoUpdateManager = new AutoUpdateManager();