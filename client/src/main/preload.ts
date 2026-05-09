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
};

const ALLOWED_LISTEN_CHANNELS: Record<string, boolean> = {
  "ws:connected": true,
  "ws:disconnected": true,
  "ws:message": true,
  "notification": true,
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
