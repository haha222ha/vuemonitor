import { contextBridge, ipcRenderer } from "electron";

const ALLOWED_CHANNELS: Record<string, boolean> = {
  "get-app-version": true,
  "storage:query": true,
  "storage:run": true,
  "storage:insert-product": true,
  "storage:get-products": true,
  "storage:save-features": true,
  "comm:connect": true,
  "comm:disconnect": true,
  "comm:send": true,
  "sync:push-to-cloud": true,
  "collect:start": true,
  "collect:cancel": true,
  "collect:clear-queue": true,
  "collect:status": true,
  "concurrency:get": true,
  "concurrency:set": true,
  "scheduler:start": true,
  "scheduler:stop": true,
  "scheduler:state": true,
  "scheduler:add-task": true,
  "scheduler:remove-task": true,
  "scheduler:toggle-task": true,
  "scheduler:update-frequency": true,
  "scheduler:get-tasks": true,
  "datamart:list-products": true,
  "datamart:get-product": true,
  "datamart:invalidate-cache": true,
  "auth:login": true,
  "auth:logout": true,
  "permission:check": true,
  "permission:get-all": true,
  "permission:refresh": true,
  "app:minimize-to-tray": true,
  "app:get-platform": true,
  "playwright:start": true,
  "playwright:status": true,
  "playwright:cancel": true,
  "playwright:close": true,
  "license:activate": true,
  "license:get-current": true,
  "license:get-plan": true,
  "license:check-feature": true,
  "license:deactivate": true,
  "license:get-device-id": true,
  "sync:configure": true,
  "sync:start": true,
  "sync:stop": true,
  "sync:now": true,
  "sync:status": true,
  "sync:enqueue-product": true,
  "sync:enqueue-feature": true,
  "sync:ai-analyze": true,
  "sync:clear-pending": true,
};

const ALLOWED_LISTEN_CHANNELS: Record<string, boolean> = {
  "ws:connected": true,
  "ws:disconnected": true,
  "ws:message": true,
  "notification": true,
  "collect:result": true,
  "collect:risk_alert": true,
  "concurrency:changed": true,
  "resource:warning": true,
  "scheduler:task_executed": true,
  "sync:start": true,
  "sync:complete": true,
  "sync:error": true,
  "sync:pulled": true,
  "ai:result": true,
};

contextBridge.exposeInMainWorld("electronAPI", {
  invoke: (channel: string, ...args: unknown[]) => {
    if (!ALLOWED_CHANNELS[channel]) {
      throw new Error(`IPC channel "${channel}" is not allowed`);
    }
    return ipcRenderer.invoke(channel, ...args);
  },
  on: (channel: string, callback: (...args: unknown[]) => void) => {
    if (!ALLOWED_LISTEN_CHANNELS[channel]) {
      throw new Error(`IPC listen channel "${channel}" is not allowed`);
    }
    const subscription = (_event: Electron.IpcRendererEvent, ...args: unknown[]) => callback(...args);
    ipcRenderer.on(channel, subscription);
    return () => ipcRenderer.removeListener(channel, subscription);
  },
  getAppVersion: () => ipcRenderer.invoke("get-app-version"),
  getPlatform: () => process.platform,
});
