export * from "./app-lifecycle";
export * from "./window-manager";
export * from "./tray-manager";
export * from "./service-registry";

import { AppLifecycle } from "./app-lifecycle";
import { WindowManager } from "./window-manager";
import { TrayManager } from "./tray-manager";

export function initServices() {
  const lifecycle = AppLifecycle.getInstance();
  const windows = WindowManager.getInstance();
  const tray = TrayManager.getInstance();
  return { lifecycle, windows, tray };
}