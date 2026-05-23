import { ipcMain, app } from "electron";
import { wireDataMartSync } from "./worker-registry";
import { registerStorageHandlers } from "./storage-handlers";
import { registerCollectHandlers } from "./collect-handlers";
import { registerSyncHandlers } from "./sync-handlers";
import { registerServiceHandlers } from "./service-handlers";

export { getWorker, getPlaywrightCollector } from "./worker-registry";

export function registerIpcHandlers(): void {
  wireDataMartSync();

  ipcMain.handle("get-app-version", () => app.getVersion());

  registerStorageHandlers();
  registerCollectHandlers();
  registerSyncHandlers();
  registerServiceHandlers();
}
