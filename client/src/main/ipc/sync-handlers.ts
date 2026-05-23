import { ipcMain } from "electron";
import { getCommunication } from "../communication/ws-client";
import { LocalPermissionCache } from "../permission/permission-cache";
import { licenseManager } from "../license/license-manager";
import { cloudSync } from "../sync/cloud-sync";
import { getSecureStorage } from "../storage/secure-storage";
import { getPermissionCache } from "./worker-registry";
import axios from "axios";

export function registerSyncHandlers(): void {
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

  ipcMain.handle("auth:login", async (_event, account: string, password: string, serverUrl: string) => {
    try {
      const { data } = await axios.post(`${serverUrl}/api/v1/auth/login`, { account, password }, { timeout: 15000 });
      if (data.access_token) {
        const secureStore = getSecureStorage();
        secureStore.set("access_token", data.access_token);
        if (data.refresh_token) secureStore.set("refresh_token", data.refresh_token);
        const comm = getCommunication();
        comm.connect(serverUrl, data.access_token);
        const cache = getPermissionCache();
        await cache.refreshFromServer(serverUrl, data.access_token);
        cloudSync.configure(serverUrl, data.access_token);
        cloudSync.startAutoSync();
      }
      return data;
    } catch (err: any) {
      const message = err?.response?.data?.message || err?.message || "登录失败";
      return { error: true, message };
    }
  });

  ipcMain.handle("auth:register", async (_event, nickname: string, password: string, email: string | undefined, serverUrl: string) => {
    try {
      const payload: Record<string, unknown> = { nickname, password };
      if (email && email.trim()) {
        payload.email = email.trim();
      }
      const { data } = await axios.post(`${serverUrl}/api/v1/auth/register`, payload, { timeout: 15000 });
      return data;
    } catch (err: any) {
      const message = err?.response?.data?.message || err?.message || "注册失败";
      return { error: true, message };
    }
  });

  ipcMain.handle("auth:logout", async () => {
    const comm = getCommunication();
    comm.disconnect();
    const cache = getPermissionCache();
    cache.clear();
    cloudSync.stopAutoSync();
    const secureStore = getSecureStorage();
    secureStore.clear();
    return true;
  });

  ipcMain.handle("permission:check", async (_event, gateKey: string) => {
    const cache = getPermissionCache();
    return cache.checkGate(gateKey);
  });

  ipcMain.handle("permission:get-all", async () => {
    const cache = getPermissionCache();
    return cache.getAllGates();
  });

  ipcMain.handle("permission:refresh", async () => {
    const cache = getPermissionCache();
    return { refreshed: true };
  });

  ipcMain.handle("license:activate", async (_event, licenseKey: string, serverUrl?: string) => {
    const result = await licenseManager.activate(licenseKey, serverUrl);
    if (result.success && result.license) {
      const cache = getPermissionCache();
      cache.updateFromLicense(result.license);
    }
    return result;
  });

  ipcMain.handle("license:get-current", async () => {
    return licenseManager.getCurrentLicense();
  });

  ipcMain.handle("license:get-plan", async () => {
    return {
      plan: licenseManager.getPlan(),
      features: licenseManager.getFeatures(),
      quotas: licenseManager.getQuotas(),
    };
  });

  ipcMain.handle("license:check-feature", async (_event, gateKey: string) => {
    return licenseManager.checkFeature(gateKey);
  });

  ipcMain.handle("license:check-quota", async (_event, quotaKey: string, currentUsage: number) => {
    const quotas = licenseManager.getQuotas();
    const limit = quotas[quotaKey];
    if (limit === undefined) return { allowed: true, limit: -1, remaining: -1 };
    if (limit === -1) return { allowed: true, limit: -1, remaining: -1 };
    const remaining = Math.max(0, limit - currentUsage);
    return { allowed: currentUsage < limit, limit, remaining };
  });

  ipcMain.handle("license:deactivate", async () => {
    return licenseManager.deactivate();
  });

  ipcMain.handle("license:get-device-id", async () => {
    return {
      deviceId: licenseManager.generateDeviceId(),
      fingerprint: licenseManager.getMachineFingerprint(),
    };
  });

  ipcMain.handle("license:is-expired", async () => {
    return licenseManager.isExpired();
  });

  ipcMain.handle("sync:configure", async (_event, serverUrl: string, token: string) => {
    cloudSync.configure(serverUrl, token);
    return true;
  });

  ipcMain.handle("sync:start", async () => {
    cloudSync.startAutoSync();
    return true;
  });

  ipcMain.handle("sync:stop", async () => {
    cloudSync.stopAutoSync();
    return true;
  });

  ipcMain.handle("sync:now", async () => {
    return await cloudSync.syncAll();
  });

  ipcMain.handle("sync:status", async () => {
    return cloudSync.getStatus();
  });

  ipcMain.handle("sync:enqueue-product", async (_event, product: Record<string, unknown>, action: "create" | "update" | "delete") => {
    cloudSync.enqueueProduct(product, action);
    return true;
  });

  ipcMain.handle("sync:enqueue-feature", async (_event, productId: string, feature: Record<string, unknown>) => {
    cloudSync.enqueueFeature(productId, feature);
    return true;
  });

  ipcMain.handle("sync:ai-analyze", async (_event, productId: string, analysisType: string) => {
    const gateKeyMap: Record<string, string> = {
      basic_analysis: "gate:ai:basic_analysis",
      trend_score: "gate:ai:trend_score",
      prediction: "gate:ai:prediction",
      risk_warning: "gate:ai:risk_warning",
      report: "gate:ai:report",
      product_optimization: "gate:ai:trend_score",
    };
    const gateKey = gateKeyMap[analysisType];
    if (gateKey) {
      const cache = getPermissionCache();
      const allowed = cache.checkGate(gateKey);
      if (!allowed) {
        throw new Error(`permission: 当前套餐不支持「${analysisType}」分析，请升级套餐`);
      }
    }
    return await cloudSync.requestAIAnalysis(productId, analysisType);
  });

  ipcMain.handle("sync:clear-pending", async () => {
    return cloudSync.clearPending();
  });

  ipcMain.handle("sync:get-conflicts", async () => {
    return cloudSync.getConflicts();
  });

  ipcMain.handle("sync:get-all-conflicts", async () => {
    return cloudSync.getAllConflicts();
  });

  ipcMain.handle("sync:resolve-conflict", async (_event, conflictId: string, resolution: "local_wins" | "server_wins" | "merged") => {
    return cloudSync.resolveConflict(conflictId, resolution);
  });

  ipcMain.handle("sync:load-persisted-conflicts", async () => {
    cloudSync.loadPersistedConflicts();
    cloudSync.loadLastSyncAt();
    return cloudSync.getConflicts();
  });

  ipcMain.handle("sync:full-sync", async () => {
    return await cloudSync.fullSync();
  });

  ipcMain.handle("sync:server-status", async () => {
    return await cloudSync.getServerSyncStatus();
  });

  ipcMain.handle("sync:enqueue-category", async (_event, category: Record<string, unknown>, action: "create" | "update" | "delete") => {
    cloudSync.enqueueCategory(category, action);
    return true;
  });
}
