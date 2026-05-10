import { app, BrowserWindow, Tray, Menu, nativeImage } from "electron";
import * as path from "path";
import { registerIpcHandlers } from "./ipc/handlers";
import { initStorage } from "./storage/sqlite";
import { localScheduler } from "./collect/local-scheduler";
import { dataMart } from "./collect/data-mart";
import { licenseManager } from "./license/license-manager";
import { cloudSync } from "./sync/cloud-sync";
import { getCommunication } from "./communication/ws-client";

let mainWindow: BrowserWindow | null = null;
let tray: Tray | null = null;

function createMainWindow(): BrowserWindow {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 960,
    minHeight: 600,
    title: "XHS365 - 小红书AI选品",
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      session: undefined,
    },
  });

  mainWindow.once("ready-to-show", () => {
    mainWindow?.show();
  });

  if (process.env.NODE_ENV === "development") {
    mainWindow.loadURL("http://localhost:5173");
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, "../renderer/index.html"));
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  mainWindow.on("minimize", (event) => {
    event.preventDefault();
    mainWindow?.hide();
  });

  const comm = getCommunication();
  comm.setMainWindow(mainWindow);

  return mainWindow;
}

function createTray(): void {
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

  tray = new Tray(icon);
  const contextMenu = Menu.buildFromTemplate([
    { label: "显示主窗口", click: () => showMainWindow() },
    { type: "separator" },
    { label: "采集状态", click: () => sendTrayAction("show-collect-status") },
    { label: "定时任务", click: () => sendTrayAction("show-scheduler") },
    { type: "separator" },
    { label: "授权信息", click: () => sendTrayAction("show-license") },
    { type: "separator" },
    { label: "退出", click: () => app.quit() },
  ]);

  tray.setToolTip("XHS365 小红书AI选品");
  tray.setContextMenu(contextMenu);

  tray.on("double-click", () => {
    showMainWindow();
  });
}

function showMainWindow(): void {
  if (!mainWindow) {
    createMainWindow();
  }
  mainWindow?.show();
  mainWindow?.focus();
}

function sendTrayAction(action: string): void {
  showMainWindow();
  mainWindow?.webContents.send("tray:action", action);
}

async function bootstrap(): Promise<void> {
  initStorage();

  registerIpcHandlers();

  createMainWindow();
  createTray();

  const license = licenseManager.getCurrentLicense();
  if (license?.isValid) {
    await localScheduler.start();
  }

  cloudSync.on("sync:complete", (info) => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send("sync:complete", info);
    }
  });
  cloudSync.on("ai:result", (result) => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send("ai:result", result);
    }
  });
}

app.whenReady().then(bootstrap);

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createMainWindow();
  } else {
    showMainWindow();
  }
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  localScheduler.destroy();
  dataMart.destroy();
  cloudSync.destroy();
  licenseManager.destroy();

  try {
    const { getStorage } = require("./storage/sqlite");
    const storage = getStorage();
    storage.flush();
  } catch {}
});

app.on("will-quit", () => {
  if (tray) {
    tray.destroy();
  }
});
