import { ipcMain, BrowserWindow } from "electron";
import { getStorage } from "../storage/sqlite";
import { getCommunication } from "../communication/ws-client";
import { featureEngine } from "../feature/feature-engine";
import { crashRecovery } from "../recovery/crash-recovery";
import { localRuleEvaluator } from "../monitor/local-evaluator";
import { autoUpdateManager } from "../update/auto-updater";
import { logger } from "../logger/logger";
import { offlineMode } from "../services/offline-mode";
import { trayManager } from "../services/tray-manager";
import { performanceMonitor } from "../services/performance-monitor";
import { CollectTask } from "../collect/chromium-worker";
import { PlaywrightTask } from "../collect/playwright-collector";
import { getWorker, getPlaywrightCollector } from "./worker-registry";

export function registerServiceHandlers(): void {
  ipcMain.handle("app:minimize-to-tray", async () => {
    const mainWindow = BrowserWindow.getAllWindows()[0];
    if (mainWindow) {
      mainWindow.hide();
    }
    return true;
  });

  ipcMain.handle("app:get-platform", async () => {
    return process.platform;
  });

  ipcMain.handle("feature:compute", async (_event, productId: string) => {
    return featureEngine.computeForProduct(productId);
  });

  ipcMain.handle("feature:compute-all", async () => {
    return { computed: featureEngine.computeAll() };
  });

  ipcMain.handle("feature:get", async (_event, productId: string) => {
    return featureEngine.getFeaturesForProduct(productId);
  });

  ipcMain.handle("feature:stats", async () => {
    return featureEngine.getStats();
  });

  ipcMain.handle("recovery:get-active", async () => {
    return crashRecovery.getActiveSnapshots();
  });

  ipcMain.handle("recovery:get-all", async (_event, limit?: number) => {
    return crashRecovery.getAllSnapshots(limit);
  });

  ipcMain.handle("recovery:clear-completed", async () => {
    return { cleared: crashRecovery.clearCompleted() };
  });

  ipcMain.handle("recovery:clear-all", async () => {
    crashRecovery.clearAll();
    return { cleared: true };
  });

  ipcMain.handle("recovery:stats", async () => {
    return crashRecovery.getRecoveryStats();
  });

  ipcMain.handle("recovery:retry-task", async (_event, taskId: string) => {
    const snapshots = crashRecovery.getAllSnapshots();
    const task = snapshots.find((s) => s.id === taskId);
    if (!task) return { success: false, error: "Task not found" };

    crashRecovery.incrementRetry(task.id);
    crashRecovery.updateSnapshotStatus(task.id, "pending", 0, null);

    try {
      if (task.taskType === "chromium") {
        const worker = getWorker();
        const collectTask: CollectTask = {
          id: task.id,
          targetId: task.targetId,
          targetType: task.targetType as CollectTask["targetType"],
          targetUrl: task.targetUrl || undefined,
        };
        worker.enqueueBatchSharded([collectTask]);
      } else if (task.taskType === "playwright") {
        const collector = getPlaywrightCollector();
        await collector.launch();
        const pwTask: PlaywrightTask = {
          id: task.id,
          targetId: task.targetId,
          targetType: task.targetType as PlaywrightTask["targetType"],
          targetUrl: task.targetUrl || "",
        };
        collector.enqueue(pwTask);
      }
      return { success: true };
    } catch (err) {
      return { success: false, error: String(err) };
    }
  });

  ipcMain.handle("recovery:discard-task", async (_event, taskId: string) => {
    crashRecovery.updateSnapshotStatus(taskId, "failed", undefined, "Manually discarded");
    crashRecovery.removeSnapshot(taskId);
    return { success: true };
  });

  ipcMain.handle("notifications:get", async (_event, limit?: number) => {
    return localRuleEvaluator.getNotifications(limit);
  });

  ipcMain.handle("notifications:unread-count", async () => {
    return { count: localRuleEvaluator.getUnreadCount() };
  });

  ipcMain.handle("notifications:mark-read", async (_event, notificationId: string) => {
    localRuleEvaluator.markAsRead(notificationId);
    return { read: true };
  });

  ipcMain.handle("notifications:mark-all-read", async () => {
    return { count: localRuleEvaluator.markAllAsRead() };
  });

  ipcMain.handle("notifications:delete", async (_event, notificationId: string) => {
    return { deleted: localRuleEvaluator.deleteNotification(notificationId) };
  });

  localRuleEvaluator.on("notification:created", (notification: { id: string; type: string; title: string; content: string; related_id: string | null }) => {
    const mainWindow = BrowserWindow.getAllWindows()[0];
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send("notification:local", {
        id: notification.id,
        type: notification.type,
        title: notification.title,
        content: notification.content,
        is_read: false,
        related_id: notification.related_id,
        related_type: "product",
        created_at: new Date().toISOString(),
        source: "local",
      });
    }
  });

  ipcMain.handle("monitor:get-rules", async () => {
    const storage = getStorage();
    const rules = storage.query("SELECT * FROM monitor_rules ORDER BY created_at DESC") as Record<string, unknown>[];
    return rules.map((r) => ({
      ...r,
      conditions: typeof r.conditions === "string" ? JSON.parse(r.conditions) : r.conditions,
      is_active: !!r.is_active,
      trigger_count: r.trigger_count || 0,
    }));
  });

  ipcMain.handle("monitor:create-rule", async (_event, rule: { product_id: string; rule_name: string; rule_type: string; conditions: Record<string, unknown>; notify_channels?: string[]; is_active?: boolean }) => {
    const storage = getStorage();
    const id = crypto.randomUUID();
    const now = new Date().toISOString();
    storage.run(
      "INSERT INTO monitor_rules (id, product_id, rule_name, rule_type, conditions, is_active, trigger_count, created_at) VALUES (?, ?, ?, ?, ?, ?, 0, ?)",
      [id, rule.product_id, rule.rule_name, rule.rule_type, JSON.stringify(rule.conditions || {}), rule.is_active !== false ? 1 : 0, now]
    );
    return { id, ...rule, is_active: rule.is_active !== false, trigger_count: 0, created_at: now };
  });

  ipcMain.handle("monitor:update-rule", async (_event, ruleId: string, updates: Record<string, unknown>) => {
    const storage = getStorage();
    const sets: string[] = [];
    const params: unknown[] = [];
    if (updates.rule_name !== undefined) { sets.push("rule_name = ?"); params.push(updates.rule_name); }
    if (updates.conditions !== undefined) { sets.push("conditions = ?"); params.push(JSON.stringify(updates.conditions)); }
    if (updates.is_active !== undefined) { sets.push("is_active = ?"); params.push(updates.is_active ? 1 : 0); }
    if (updates.notify_channels !== undefined) { sets.push("conditions = ?"); params.push(JSON.stringify({ ...(typeof updates.conditions === "object" ? updates.conditions as Record<string, unknown> : {}), _notify_channels: updates.notify_channels })); }
    if (sets.length === 0) return { updated: false };
    params.push(ruleId);
    storage.run(`UPDATE monitor_rules SET ${sets.join(", ")} WHERE id = ?`, params);
    return { updated: true };
  });

  ipcMain.handle("monitor:delete-rule", async (_event, ruleId: string) => {
    const storage = getStorage();
    storage.run("DELETE FROM monitor_rules WHERE id = ?", [ruleId]);
    return { deleted: true };
  });

  ipcMain.handle("monitor:toggle-rule", async (_event, ruleId: string, active: boolean) => {
    const storage = getStorage();
    storage.run("UPDATE monitor_rules SET is_active = ? WHERE id = ?", [active ? 1 : 0, ruleId]);
    return { updated: true };
  });

  ipcMain.handle("monitor:evaluate", async (_event, productId?: string) => {
    if (!offlineMode.getStatus().isOnline) {
      if (productId) {
        return { triggered: localRuleEvaluator.evaluateForProduct(productId) };
      }
      return { triggered: localRuleEvaluator.evaluateAll() };
    }
    return { triggered: 0, skipped: true, reason: "online_mode" };
  });

  ipcMain.handle("ai:get-analyses", async (_event, params?: { page?: number; pageSize?: number }) => {
    const storage = getStorage();
    const page = params?.page || 1;
    const pageSize = params?.pageSize || 50;
    const offset = (page - 1) * pageSize;
    const items = storage.query("SELECT * FROM ai_analysis ORDER BY analyzed_at DESC LIMIT ? OFFSET ?", [pageSize, offset]) as Record<string, unknown>[];
    return {
      items: items.map((a) => ({
        ...a,
        result: typeof a.result === "string" ? JSON.parse(a.result) : a.result,
      })),
      total: items.length,
    };
  });

  ipcMain.handle("ai:get-reports", async () => {
    const storage = getStorage();
    const items = storage.query("SELECT * FROM ai_analysis WHERE analysis_type = 'report' ORDER BY analyzed_at DESC") as Record<string, unknown>[];
    return items.map((a) => ({
      id: a.id,
      title: (typeof a.result === "string" ? JSON.parse(a.result as string) : a.result)?.title || "分析报告",
      report_type: (typeof a.result === "string" ? JSON.parse(a.result as string) : a.result)?.report_type || "product",
      status: "completed",
      content: typeof a.result === "string" ? JSON.parse(a.result as string) : a.result,
      created_at: a.analyzed_at,
    }));
  });

  ipcMain.handle("ai:create-report", async (_event, params: { title: string; report_type: string; product_ids: string[] }) => {
    const storage = getStorage();
    const id = crypto.randomUUID();
    const now = new Date().toISOString();
    const content = {
      title: params.title,
      report_type: params.report_type,
      executive_summary: "报告正在生成中，请稍后查看",
      product_analysis: null,
      recommendations: [],
      conclusion: "数据采集中，分析报告将在数据充足后自动生成",
    };
    storage.run(
      "INSERT INTO ai_analysis (id, product_id, analysis_type, result, confidence, analyzed_at) VALUES (?, ?, ?, ?, ?, ?)",
      [id, params.product_ids[0] || "", "report", JSON.stringify(content), 0, now]
    );
    return { id, status: "processing" };
  });

  ipcMain.handle("update:check", async (_event, silent?: boolean) => {
    await autoUpdateManager.checkForUpdate(silent !== false);
    return autoUpdateManager.getStatus();
  });

  ipcMain.handle("update:download", async () => {
    await autoUpdateManager.downloadUpdate();
    return { downloading: true };
  });

  ipcMain.handle("update:install", async () => {
    await autoUpdateManager.installUpdate();
    return { installing: true };
  });

  ipcMain.handle("update:status", async () => {
    return autoUpdateManager.getStatus();
  });

  ipcMain.handle("log:get-recent", async (_event, count?: number, level?: string, module?: string) => {
    return logger.getRecentLogs(count || 100, level as any, module);
  });

  ipcMain.handle("log:get-files", async () => {
    return logger.getLogFiles();
  });

  ipcMain.handle("log:export", async (_event, format?: string) => {
    return logger.exportLogs((format as "json" | "text") || "json");
  });

  ipcMain.handle("log:upload", async () => {
    return logger.uploadLogs();
  });

  ipcMain.handle("log:clear", async () => {
    return { deleted: logger.clearLogs() };
  });

  ipcMain.handle("log:get-stats", async () => {
    return logger.getStats();
  });

  ipcMain.handle("log:set-level", async (_event, level: string) => {
    logger.setLevel(level as any);
    return true;
  });

  ipcMain.handle("log:set-upload-endpoint", async (_event, endpoint: string | null) => {
    logger.setUploadEndpoint(endpoint);
    return true;
  });

  ipcMain.handle("offline:status", async () => {
    return offlineMode.getStatus();
  });

  ipcMain.handle("offline:pending-operations", async () => {
    return offlineMode.getPendingOperations();
  });

  ipcMain.handle("offline:clear-pending", async () => {
    return offlineMode.clearPendingOperations();
  });

  ipcMain.handle("offline:check", async () => {
    return await offlineMode.checkConnectivity();
  });

  ipcMain.handle("offline:enqueue", async (_event, type: string, payload: unknown) => {
    return await offlineMode.enqueueOperation(type, payload);
  });

  ipcMain.handle("window:open", async (_event, id: string, title: string, route: string) => {
    trayManager.openSecondaryWindow(id, title, route);
    return true;
  });

  ipcMain.handle("window:close", async (_event, id: string) => {
    trayManager.closeSecondaryWindow(id);
    return true;
  });

  ipcMain.handle("window:list", async () => {
    return trayManager.getSecondaryWindows();
  });

  ipcMain.handle("tray:update-status", async (_event, status: string) => {
    trayManager.updateCollectStatus(status);
    return true;
  });

  ipcMain.handle("perf:latest", async () => {
    return performanceMonitor.getLatest();
  });

  ipcMain.handle("perf:history", async (_event, limit?: number) => {
    return performanceMonitor.getHistory(limit);
  });

  ipcMain.handle("perf:alerts", async (_event, limit?: number) => {
    return performanceMonitor.getAlerts(limit);
  });

  ipcMain.handle("perf:summary", async () => {
    return performanceMonitor.getSummary();
  });

  ipcMain.handle("perf:clear", async () => {
    performanceMonitor.clearHistory();
    return true;
  });

  ipcMain.handle("products:list", async (_event, params?: { page?: number; pageSize?: number; platform?: string }) => {
    const comm = getCommunication();
    if (!comm.hasApiSession()) return { data: { items: [], total: 0 } };
    const page = params?.page || 1;
    const pageSize = params?.pageSize || 20;
    const platform = params?.platform;
    let url = `/api/v1/products?page=${page}&page_size=${pageSize}`;
    if (platform) url += `&platform=${platform}`;
    return comm.request("GET", url);
  });

  ipcMain.handle("products:compare", async (_event, params: { productIds: string[] }) => {
    const comm = getCommunication();
    if (!comm.hasApiSession()) return { data: null };
    const ids = params.productIds.join("&product_ids=");
    return comm.request("POST", `/api/v1/products/compare?product_ids=${ids}`);
  });

  ipcMain.handle("discovery:search", async (_event, params: { keyword: string; page?: number; page_size?: number; min_price?: number; max_price?: number; min_sold?: number; sort_by?: string; sort_order?: string }) => {
    const comm = getCommunication();
    if (comm.hasApiSession()) {
      return comm.request("POST", "/api/v1/discovery/search", params);
    }
    return { code: 0, data: { items: [], total: 0, page: params.page || 1, page_size: params.page_size || 20 } };
  });

  ipcMain.handle("discovery:stores", async (_event, params: { keyword: string; page?: number; page_size?: number }) => {
    const comm = getCommunication();
    if (comm.hasApiSession()) {
      return comm.request("POST", "/api/v1/discovery/stores", params);
    }
    return { code: 0, data: { items: [], total: 0, page: params.page || 1, page_size: params.page_size || 20 } };
  });

  ipcMain.handle("discovery:store-goods", async (_event, storeId: string, page?: number, pageSize?: number) => {
    const comm = getCommunication();
    if (comm.hasApiSession()) {
      return comm.request("GET", `/api/v1/discovery/stores/${storeId}/goods?page=${page || 1}&page_size=${pageSize || 50}`);
    }
    return { code: 0, data: { items: [], total: 0 } };
  });

  ipcMain.handle("discovery:hot-goods", async (_event, params?: { page?: number; page_size?: number; category?: string }) => {
    const comm = getCommunication();
    if (comm.hasApiSession()) {
      const query: string[] = [];
      if (params?.page) query.push(`page=${params.page}`);
      if (params?.page_size) query.push(`page_size=${params.page_size}`);
      if (params?.category) query.push(`category=${params.category}`);
      const qs = query.length > 0 ? `?${query.join("&")}` : "";
      return comm.request("GET", `/api/v1/discovery/hot-goods${qs}`);
    }
    return { code: 0, data: { items: [], total: 0 } };
  });

  ipcMain.handle("discovery:keywords", async (_event, params?: { page?: number; page_size?: number }) => {
    const comm = getCommunication();
    if (comm.hasApiSession()) {
      const query: string[] = [];
      if (params?.page) query.push(`page=${params.page}`);
      if (params?.page_size) query.push(`page_size=${params.page_size}`);
      const qs = query.length > 0 ? `?${query.join("&")}` : "";
      return comm.request("GET", `/api/v1/discovery/keywords${qs}`);
    }
    return { code: 0, data: { items: [], total: 0 } };
  });

  ipcMain.handle("discovery:quota", async () => {
    const comm = getCommunication();
    if (comm.hasApiSession()) {
      return comm.request("GET", "/api/v1/discovery/quota");
    }
    return { code: 0, data: { used_today: 0, remaining: 50, db_stats: { total_goods: 0, total_stores: 0, total_keywords: 0 } } };
  });

  ipcMain.handle("discovery:add-to-monitor", async (_event, params: { ref_id: string; product_name?: string; mode?: string }) => {
    const comm = getCommunication();
    if (comm.hasApiSession()) {
      const response = await comm.request("POST", "/api/v1/discovery/add-to-monitor", params) as {
        code?: number;
        message?: string;
        data?: {
          platform_product_id?: string;
          platform_product_ids?: string[];
          product_name?: string;
          product_id?: string;
        };
      };
      if ((response?.code ?? 1) === 0 && response.data) {
        const storage = getStorage();
        const ids =
          response.data.mode === "store" && response.data.platform_product_ids?.length
            ? response.data.platform_product_ids
            : response.data.platform_product_id
              ? [response.data.platform_product_id]
              : [];
        for (const goodsId of ids) {
          const existing = storage.query(
            "SELECT id FROM products WHERE platform = ? AND platform_product_id = ? AND is_active = 1",
            ["xhs", goodsId],
          ) as Record<string, unknown>[];
          if (existing.length > 0) continue;
          storage.insertProduct({
            platform: "xhs",
            platform_product_id: goodsId,
            product_name: params.product_name || response.data.product_name || `XHS商品 ${goodsId.slice(0, 8)}`,
          });
        }
        if (ids.length > 0) {
          const { dataMart } = require("../collect/data-mart");
          dataMart.invalidateCache();
        }
      }
      return response;
    }
    const storage = getStorage();
    const id = crypto.randomUUID();
    const now = new Date().toISOString();
    const goodsId = String(params.ref_id || "").replace(/^goods:/, "").trim();
    if (!goodsId) {
      return { code: 1, message: "无效的商品引用" };
    }
    storage.run(
      "INSERT OR IGNORE INTO products (id, platform, platform_product_id, product_name, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, 1, ?, ?)",
      [id, "xhs", goodsId, params.product_name || `XHS商品 ${goodsId.slice(0, 8)}`, now, now]
    );
    return { code: 0, data: { added: true, id, product_id: id } };
  });

  ipcMain.handle("discovery:rising-goods", async (_event, params?: { page?: number; page_size?: number; category?: string }) => {
    const comm = getCommunication();
    if (comm.hasApiSession()) {
      const query: string[] = [];
      if (params?.page) query.push(`page=${params.page}`);
      if (params?.page_size) query.push(`page_size=${params.page_size}`);
      if (params?.category) query.push(`category=${params.category}`);
      const qs = query.length > 0 ? `?${query.join("&")}` : "";
      return comm.request("GET", `/api/v1/discovery/rising-goods${qs}`);
    }
    return { code: 0, data: { items: [], total: 0 } };
  });

  ipcMain.handle("discovery:new-goods", async (_event, params?: { page?: number; page_size?: number; category?: string }) => {
    const comm = getCommunication();
    if (comm.hasApiSession()) {
      const query: string[] = [];
      if (params?.page) query.push(`page=${params.page}`);
      if (params?.page_size) query.push(`page_size=${params.page_size}`);
      if (params?.category) query.push(`category=${params.category}`);
      const qs = query.length > 0 ? `?${query.join("&")}` : "";
      return comm.request("GET", `/api/v1/discovery/new-goods${qs}`);
    }
    return { code: 0, data: { items: [], total: 0 } };
  });

  ipcMain.handle("discovery:top-sold-goods", async (_event, params?: { page?: number; page_size?: number; min_sold?: number }) => {
    const comm = getCommunication();
    if (comm.hasApiSession()) {
      const query: string[] = [];
      if (params?.page) query.push(`page=${params.page}`);
      if (params?.page_size) query.push(`page_size=${params.page_size}`);
      if (params?.min_sold) query.push(`min_sold=${params.min_sold}`);
      const qs = query.length > 0 ? `?${query.join("&")}` : "";
      return comm.request("GET", `/api/v1/discovery/top-sold${qs}`);
    }
    return { code: 0, data: { items: [], total: 0 } };
  });

  ipcMain.handle("category:list", async () => {
    const comm = getCommunication();
    if (comm.hasApiSession()) {
      try {
        return await comm.request("GET", "/api/v1/categories");
      } catch { /* fallback to local */ }
    }
    const storage = getStorage();
    const rows = storage.query("SELECT id, name, icon, color, sort_order, parent_id, is_active, created_at FROM categories WHERE is_active = 1 ORDER BY sort_order, created_at") as Record<string, unknown>[];
    const productCounts = storage.query("SELECT category_id, COUNT(*) as cnt FROM products WHERE is_active = 1 AND category_id IS NOT NULL GROUP BY category_id") as Record<string, unknown>[];
    const countMap = new Map<string, number>();
    for (const row of productCounts) {
      countMap.set(String(row.category_id), Number(row.cnt));
    }
    const items = rows.map((row) => ({
      id: String(row.id),
      name: String(row.name),
      icon: row.icon ? String(row.icon) : null,
      color: row.color ? String(row.color) : null,
      sort_order: Number(row.sort_order || 0),
      parent_id: row.parent_id ? String(row.parent_id) : null,
      product_count: countMap.get(String(row.id)) || 0,
      created_at: row.created_at ? String(row.created_at) : null,
    }));
    return { code: 0, data: { categories: items } };
  });

  ipcMain.handle("category:create", async (_event, params: { name: string; icon?: string; color?: string; sort_order?: number; parent_id?: string }) => {
    const comm = getCommunication();
    if (comm.hasApiSession()) {
      try {
        return await comm.request("POST", "/api/v1/categories", params);
      } catch { /* fallback to local */ }
    }
    const storage = getStorage();
    const id = crypto.randomUUID();
    const now = new Date().toISOString();
    storage.run(
      "INSERT INTO categories (id, name, icon, color, sort_order, parent_id, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)",
      [id, params.name, params.icon || null, params.color || null, params.sort_order || 0, params.parent_id || null, now, now]
    );
    return { code: 0, data: { id, name: params.name } };
  });

  ipcMain.handle("category:update", async (_event, params: { id: string; name?: string; icon?: string; color?: string; sort_order?: number; parent_id?: string; is_active?: boolean }) => {
    const comm = getCommunication();
    if (comm.hasApiSession()) {
      try {
        return await comm.request("PUT", `/api/v1/categories/${params.id}`, params);
      } catch { /* fallback to local */ }
    }
    const storage = getStorage();
    const sets: string[] = [];
    const values: unknown[] = [];
    if (params.name !== undefined) { sets.push("name = ?"); values.push(params.name); }
    if (params.icon !== undefined) { sets.push("icon = ?"); values.push(params.icon); }
    if (params.color !== undefined) { sets.push("color = ?"); values.push(params.color); }
    if (params.sort_order !== undefined) { sets.push("sort_order = ?"); values.push(params.sort_order); }
    if (params.parent_id !== undefined) { sets.push("parent_id = ?"); values.push(params.parent_id || null); }
    if (params.is_active !== undefined) { sets.push("is_active = ?"); values.push(params.is_active ? 1 : 0); }
    if (sets.length === 0) return { code: 0, data: { id: params.id } };
    sets.push("updated_at = ?");
    values.push(new Date().toISOString());
    values.push(params.id);
    storage.run(`UPDATE categories SET ${sets.join(", ")} WHERE id = ?`, values);
    return { code: 0, data: { id: params.id } };
  });

  ipcMain.handle("category:delete", async (_event, params: { id: string }) => {
    const comm = getCommunication();
    if (comm.hasApiSession()) {
      try {
        return await comm.request("DELETE", `/api/v1/categories/${params.id}`);
      } catch { /* fallback to local */ }
    }
    const storage = getStorage();
    storage.run("UPDATE products SET category_id = NULL WHERE category_id = ?", [params.id]);
    storage.run("DELETE FROM categories WHERE id = ?", [params.id]);
    return { code: 0, data: { deleted: true } };
  });

  ipcMain.handle("category:reorder", async (_event, params: { order: string[] }) => {
    const comm = getCommunication();
    if (comm.hasApiSession()) {
      try {
        return await comm.request("POST", "/api/v1/categories/reorder", params.order);
      } catch { /* fallback to local */ }
    }
    const storage = getStorage();
    for (let idx = 0; idx < params.order.length; idx++) {
      storage.run("UPDATE categories SET sort_order = ?, updated_at = ? WHERE id = ?", [idx, new Date().toISOString(), params.order[idx]]);
    }
    return { code: 0, data: { reordered: params.order.length } };
  });

  ipcMain.handle("category:assign-product", async (_event, params: { product_id: string; category_id: string | null }) => {
    const comm = getCommunication();
    if (comm.hasApiSession()) {
      try {
        return await comm.request("PATCH", `/api/v1/products/${params.product_id}`, { category_id: params.category_id });
      } catch { /* fallback to local */ }
    }
    const storage = getStorage();
    storage.run("UPDATE products SET category_id = ?, updated_at = ? WHERE id = ?", [params.category_id, new Date().toISOString(), params.product_id]);
    return { code: 0, data: { updated: true } };
  });
}
