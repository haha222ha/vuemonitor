import { app, BrowserWindow, nativeImage } from "electron";
import * as path from "path";
import { getCommunication } from "../communication/ws-client";
import { autoUpdateManager } from "../update/auto-updater";
import { logger } from "../logger/logger";

export class WindowManager {
  private static instance: WindowManager;
  private mainWindow: BrowserWindow | null = null;

  private constructor() {}

  public static getInstance(): WindowManager {
    if (!WindowManager.instance) {
      WindowManager.instance = new WindowManager();
    }
    return WindowManager.instance;
  }

  public createMainWindow(): BrowserWindow {
    this.mainWindow = new BrowserWindow({
      width: 1280,
      height: 800,
      minWidth: 960,
      minHeight: 600,
      title: "XHS365 - 小红书AI选品",
      show: false,
      webPreferences: {
        preload: path.join(__dirname, "../preload/preload.js"),
        contextIsolation: true,
        nodeIntegration: false,
        session: undefined,
      },
    });

    this.mainWindow.once("ready-to-show", () => {
      this.mainWindow?.show();
    });

    if (process.env.NODE_ENV === "development") {
      this.mainWindow.loadURL("http://127.0.0.1:5173");
      this.mainWindow.webContents.openDevTools();
    } else {
      this.mainWindow.loadFile(path.join(__dirname, "../renderer/index.html"));
    }

    this.mainWindow.on("closed", () => {
      this.mainWindow = null;
    });

    this.mainWindow.on("minimize", (event) => {
      event.preventDefault();
      this.mainWindow?.hide();
    });

    const comm = getCommunication();
    comm.setMainWindow(this.mainWindow);

    autoUpdateManager.setMainWindow(this.mainWindow);

    return this.mainWindow;
  }

  public showMainWindow(): void {
    if (!this.mainWindow) {
      this.createMainWindow();
    }
    this.mainWindow?.show();
    this.mainWindow?.focus();
  }

  public hideMainWindow(): void {
    this.mainWindow?.hide();
  }

  public getMainWindow(): BrowserWindow | null {
    return this.mainWindow;
  }

  public sendToRenderer(channel: string, ...args: any[]): void {
    if (this.mainWindow && !this.mainWindow.isDestroyed()) {
      this.mainWindow.webContents.send(channel, ...args);
    }
  }
}

// Export a singleton instance for convenience
export const windowManager = WindowManager.getInstance();