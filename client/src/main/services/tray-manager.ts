import { app, Tray, Menu, nativeImage, BrowserWindow } from "electron";
import * as path from "path";
import { logger } from "../logger/logger";

export interface TrayMenuAction {
  label: string;
  action: string;
  enabled?: boolean;
}

export class TrayManager {
  private static instance: TrayManager;
  private tray: Tray | null = null;
  private mainWindow: BrowserWindow | null = null;
  private mainWindowGetter: (() => BrowserWindow | null) | null = null;
  private secondaryWindows: Map<string, BrowserWindow> = new Map();
  private statusText: string = "就绪";
  private collectStatus: string = "空闲";

  private constructor() {}

  public static getInstance(): TrayManager {
    if (!TrayManager.instance) {
      TrayManager.instance = new TrayManager();
    }
    return TrayManager.instance;
  }

  setMainWindow(window: BrowserWindow): void {
    this.mainWindow = window;
  }

  setMainWindowGetter(getter: () => BrowserWindow | null): void {
    this.mainWindowGetter = getter;
  }

  private getMainWindow(): BrowserWindow | null {
    return this.mainWindowGetter ? this.mainWindowGetter() : this.mainWindow;
  }

  public createTray(): Tray {
    if (this.tray) {
      return this.tray;
    }

    const iconPath = path.join(__dirname, "../../build/icon.png");
    let icon: Electron.NativeImage;
    try {
      icon = nativeImage.createFromPath(iconPath);
      if (icon.isEmpty()) {
        icon = nativeImage.createEmpty();
      }
    } catch {
      icon = nativeImage.createEmpty();
    }

    this.tray = new Tray(icon.resize({ width: 16, height: 16 }));
    this.updateTrayMenu();
    this.tray.setToolTip("XHS365 小红书AI选品");

    this.tray.on("double-click", () => {
      this.showMainWindow();
    });

    return this.tray;
  }

  private updateTrayMenu(): void {
    if (!this.tray) return;

    const contextMenu = Menu.buildFromTemplate([
      {
        label: `采集状态: ${this.collectStatus}`,
        enabled: false,
      },
      { type: "separator" },
      { label: "显示主窗口", click: () => this.showMainWindow() },
      {
        label: "数据看板",
        click: () => this.openSecondaryWindow("dashboard", "数据看板", "/dashboard"),
      },
      {
        label: "采集任务",
        click: () => this.openSecondaryWindow("collect", "采集任务", "/collect"),
      },
      {
        label: "定时任务",
        click: () => this.openSecondaryWindow("scheduler", "定时任务", "/scheduler"),
      },
      { type: "separator" },
      {
        label: "授权信息",
        click: () => this.openSecondaryWindow("license", "授权信息", "/license"),
      },
      { type: "separator" },
      { label: "退出", click: () => this.quitApp() },
    ]);

    this.tray.setContextMenu(contextMenu);
  }

  public updateCollectStatus(status: string): void {
    this.collectStatus = status;
    this.updateTrayMenu();
  }

  public updateTooltip(text: string): void {
    if (this.tray) {
      this.tray.setToolTip(text);
    }
  }

  public showMainWindow(): void {
    const win = this.getMainWindow();
    if (!win || win.isDestroyed()) {
      return;
    }
    if (win.isMinimized()) {
      win.restore();
    }
    win.show();
    win.focus();
  }

  public openSecondaryWindow(id: string, title: string, route: string): BrowserWindow {
    const existing = this.secondaryWindows.get(id);
    if (existing && !existing.isDestroyed()) {
      existing.show();
      existing.focus();
      return existing;
    }

    const win = new BrowserWindow({
      width: 1100,
      height: 750,
      minWidth: 800,
      minHeight: 600,
      title,
      show: false,
      webPreferences: {
        nodeIntegration: false,
        contextIsolation: true,
        preload: path.join(__dirname, "../preload.js"),
      },
    });

    win.on("closed", () => {
      this.secondaryWindows.delete(id);
    });

    if (process.env.NODE_ENV === "development") {
      win.loadURL(`http://localhost:5173/#${route}`);
    } else {
      const indexPath = path.join(__dirname, "../../renderer/index.html");
      win.loadFile(indexPath, { hash: route });
    }

    win.once("ready-to-show", () => {
      win.show();
    });

    this.secondaryWindows.set(id, win);
    logger.info("TrayManager", `打开辅助窗口: ${title}`);
    return win;
  }

  public closeSecondaryWindow(id: string): void {
    const win = this.secondaryWindows.get(id);
    if (win && !win.isDestroyed()) {
      win.close();
    }
  }

  public closeAllSecondaryWindows(): void {
    for (const [id, win] of this.secondaryWindows) {
      if (!win.isDestroyed()) {
        win.close();
      }
    }
    this.secondaryWindows.clear();
  }

  public getSecondaryWindows(): string[] {
    return Array.from(this.secondaryWindows.keys());
  }

  public destroyTray(): void {
    this.closeAllSecondaryWindows();
    if (this.tray) {
      this.tray.destroy();
      this.tray = null;
    }
  }

  private quitApp(): void {
    this.closeAllSecondaryWindows();
    app.quit();
  }
}

export const trayManager = TrayManager.getInstance();