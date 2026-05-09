import { ipcMain, app } from "electron";
import { getStorage } from "../storage/sqlite";
import { getCommunication } from "../communication/ws-client";

ipcMain.handle("get-app-version", () => app.getVersion());

ipcMain.handle("storage:query", async (_event, sql: string, params?: unknown[]) => {
  const storage = getStorage();
  return storage.query(sql, params);
});

ipcMain.handle("storage:run", async (_event, sql: string, params?: unknown[]) => {
  const storage = getStorage();
  return storage.run(sql, params);
});

ipcMain.handle("storage:insert-product", async (_event, product: Record<string, unknown>) => {
  const storage = getStorage();
  return storage.insertProduct(product);
});

ipcMain.handle("storage:get-products", async (_event, filters?: Record<string, unknown>) => {
  const storage = getStorage();
  return storage.getProducts(filters);
});

ipcMain.handle("storage:save-features", async (_event, productId: string, features: Record<string, unknown>) => {
  const storage = getStorage();
  return storage.saveFeatures(productId, features);
});

ipcMain.handle("comm:connect", async (_event, serverUrl: string, token: string) => {
  const comm = getCommunication();
  return comm.connect(serverUrl, token);
});

ipcMain.handle("comm:disconnect", async () => {
  const comm = getCommunication();
  comm.disconnect();
});

ipcMain.handle("comm:send", async (_event, type: string, data: unknown) => {
  const comm = getCommunication();
  return comm.send(type, data);
});

ipcMain.handle("sync:push-to-cloud", async (_event, data: unknown) => {
  const comm = getCommunication();
  return comm.pushToCloud(data);
});
