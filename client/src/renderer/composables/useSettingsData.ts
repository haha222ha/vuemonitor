import { ref, reactive, computed, onMounted, onUnmounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useAuthStore } from "../stores/auth";
import { useLicenseStore } from "../stores/license";
import { shortcutManager, type ShortcutBinding } from "../utils/shortcuts";

export function useSettingsData() {
  const authStore = useAuthStore();
  const licenseStore = useLicenseStore();

  const activeSection = ref("account");

  const sections = [
    { key: "account", label: "账户与授权", icon: "User" },
    { key: "notifications", label: "通知偏好", icon: "Bell" },
    { key: "sync", label: "数据同步", icon: "Refresh" },
    { key: "collection", label: "采集配置", icon: "Cpu" },
    { key: "updates", label: "自动更新", icon: "Download" },
    { key: "data", label: "数据管理", icon: "Folder" },
    { key: "privacy", label: "隐私管理", icon: "Lock" },
    { key: "team", label: "团队管理", icon: "UserFilled" },
    { key: "audit", label: "操作审计", icon: "List" },
    { key: "security", label: "安全审计", icon: "WarningFilled" },
    { key: "logs", label: "日志管理", icon: "Document" },
    { key: "shortcuts", label: "快捷键", icon: "Connection" },
  ];

  const serverUrl = ref("");
  const syncing = ref(false);
  const autoSyncEnabled = ref(false);
  const syncInterval = ref(5);
  const concurrency = ref(3);
  const autoMinimize = ref(true);
  const collectInterval = ref(30);
  const autoUpdateEnabled = ref(true);
  const checkingUpdate = ref(false);
  const cleanupDays = ref(90);

  const notifySettings = reactive({
    desktop: true,
    email: false,
    sound: true,
    quietHours: false,
  });

  const quietHoursRange = ref<[Date, Date] | null>(null);

  const updateStatus = reactive({
    checking: false,
    downloading: false,
    downloadProgress: 0,
    updateAvailable: false,
    version: null as string | null,
    error: null as string | null,
  });

  const syncStatus = reactive({
    lastSyncAt: null as string | null,
    pendingCount: 0,
    syncedCount: 0,
    failedCount: 0,
    conflictCount: 0,
    isSyncing: false,
    serverUrl: null as string | null,
  });

  const conflicts = ref<Array<{
    id: string;
    type: "product" | "feature";
    localId: string;
    localData: Record<string, unknown>;
    localVersion: number;
    localUpdatedAt: string;
    serverData: Record<string, unknown>;
    serverVersion: number;
    serverUpdatedAt: string;
    resolution: string;
    createdAt: string;
  }>>([]);

  const conflictCount = computed(() => conflicts.value.length);

  const storageInfo = reactive({ sizeText: "" });

  const logLevel = ref("info");
  const logStats = reactive({
    sessionId: "",
    logFiles: 0,
    bufferSize: 0,
    uploadQueueSize: 0,
  });
  const logDialogVisible = ref(false);
  const logEntries = ref<Array<Record<string, unknown>>>([]);
  const logFilterLevel = ref("");
  const logFilterModule = ref("");
  const logSearchQuery = ref("");
  const logAutoRefresh = ref(false);
  const logUploading = ref(false);
  let logAutoRefreshTimer: ReturnType<typeof setInterval> | null = null;
  const logModules = ref(["Main", "ChromiumWorker", "CloudSync", "DataMart", "FeatureEngine", "LocalEvaluator", "PlaywrightCollector", "CrashRecovery", "LicenseManager"]);

  const logLevelCounts = reactive({ debug: 0, info: 0, warn: 0, error: 0, total: 0 });

  const clientPrivacy = reactive({
    dataCollection: true,
    anonymousAggregation: true,
    aiDataUsage: true,
    autoErrorReport: false,
  });

  const cloudDataSummary = ref<any>(null);
  const cloudDataLoading = ref(false);
  const cloudExportLoading = ref(false);
  const cloudDeleteLoading = ref(false);

  const showCreateTeamDialog = ref(false);
  const creatingTeam = ref(false);
  const createTeamForm = ref({ name: "", description: "" });
  const teams = ref<any[]>([]);
  const teamsLoading = ref(false);
  const currentTeam = ref<any>(null);
  const teamMembers = ref<any[]>([]);
  const inviteEmail = ref("");
  const inviteRole = ref("member");
  const inviting = ref(false);

  const auditLogs = ref<any[]>([]);
  const auditLoading = ref(false);
  const auditPage = ref(1);
  const auditPageSize = ref(20);
  const auditTotal = ref(0);
  const auditFilter = ref({ action: "", resource_type: "" });

  const securityLogs = ref<any[]>([]);
  const securityLoading = ref(false);
  const securityPage = ref(1);
  const securityPageSize = ref(20);
  const securityTotal = ref(0);
  const securityFilter = ref<{ path: string; client_ip: string; method: string; min_risk: number | null }>({ path: "", client_ip: "", method: "", min_risk: null });
  const securitySummary = ref<any>(null);

  const CLOUD_TABLE_LABELS: Record<string, string> = {
    products: "商品数据", product_features: "商品特征", monitor_rules: "监控规则",
    ai_analyses: "AI分析", ai_reports: "AI报告", notifications: "通知",
    sync_records: "同步记录", alert_rules: "告警规则", alert_events: "告警事件",
    team_members: "团队成员", scheduled_tasks: "定时任务",
  };

  function cloudTableLabel(table: string): string {
    return CLOUD_TABLE_LABELS[table] || table;
  }

  const shortcuts = ref<(ShortcutBinding & { editing?: boolean })[]>(
    shortcutManager.getShortcuts().map((s) => ({ ...s, editing: false }))
  );

  const filteredLogEntries = computed(() => {
    if (!logSearchQuery.value) return logEntries.value;
    const q = logSearchQuery.value.toLowerCase();
    return logEntries.value.filter((e: any) => {
      const msg = (e.message || "").toLowerCase();
      const mod = (e.module || "").toLowerCase();
      const err = (e.error || "").toLowerCase();
      return msg.includes(q) || mod.includes(q) || err.includes(q);
    });
  });

  function logLevelBarWidth(count: number): string {
    if (logLevelCounts.total === 0) return "0%";
    return `${Math.min((count / logLevelCounts.total) * 100, 100)}%`;
  }

  function captureKey(e: KeyboardEvent, row: ShortcutBinding & { editing?: boolean }) {
    e.preventDefault();
    const parts: string[] = [];
    if (e.ctrlKey || e.metaKey) parts.push("Ctrl");
    if (e.shiftKey) parts.push("Shift");
    if (e.altKey) parts.push("Alt");
    if (!["Control", "Shift", "Alt", "Meta"].includes(e.key)) {
      parts.push(e.key.length === 1 ? e.key.toUpperCase() : e.key);
    }
    if (parts.length > 1 || (parts.length === 1 && !["Ctrl", "Shift", "Alt", "Meta"].includes(parts[0]))) {
      row.key = parts.join("+");
    }
  }

  function saveShortcutKey(row: ShortcutBinding & { editing?: boolean }) {
    shortcutManager.updateShortcut(row.action, row.key);
    row.editing = false;
    ElMessage.success("快捷键已更新");
  }

  function handleShortcutToggle(row: ShortcutBinding & { editing?: boolean }) {
    shortcutManager.toggleShortcut(row.action, row.enabled);
  }

  function resetShortcuts() {
    const reset = shortcutManager.reset();
    shortcuts.value = reset.map((s) => ({ ...s, editing: false }));
    ElMessage.success("快捷键已重置为默认");
  }

  function loadSettings() {
    try {
      const saved = localStorage.getItem("xhs365_settings");
      if (saved) {
        const s = JSON.parse(saved);
        if (s.notifySettings) Object.assign(notifySettings, s.notifySettings);
        if (s.autoSyncEnabled !== undefined) autoSyncEnabled.value = s.autoSyncEnabled;
        if (s.syncInterval) syncInterval.value = s.syncInterval;
        if (s.concurrency) concurrency.value = s.concurrency;
        if (s.collectInterval) collectInterval.value = s.collectInterval;
        if (s.autoUpdateEnabled !== undefined) autoUpdateEnabled.value = s.autoUpdateEnabled;
        if (s.cleanupDays) cleanupDays.value = s.cleanupDays;
      }
    } catch {}
  }

  function saveSettings() {
    const settings = {
      notifySettings: { ...notifySettings },
      autoSyncEnabled: autoSyncEnabled.value,
      syncInterval: syncInterval.value,
      concurrency: concurrency.value,
      collectInterval: collectInterval.value,
      autoUpdateEnabled: autoUpdateEnabled.value,
      cleanupDays: cleanupDays.value,
    };
    localStorage.setItem("xhs365_settings", JSON.stringify(settings));
  }

  function saveNotifySettings() {
    saveSettings();
    if (notifySettings.email) {
      updateEmailNotifyPreference(true);
    }
  }

  async function updateEmailNotifyPreference(enabled: boolean) {
    try {
      const api = (await import("../utils/api")).default;
      await api.put("/users/me", { email_notify_enabled: enabled });
    } catch {}
  }

  async function refreshSyncStatus() {
    try {
      const status = await window.electronAPI.invoke("sync:status") as typeof syncStatus;
      Object.assign(syncStatus, status);
    } catch {}
  }

  async function loadConflicts() {
    try {
      const result = await window.electronAPI.invoke("sync:get-conflicts") as typeof conflicts.value;
      conflicts.value = result || [];
    } catch {
      conflicts.value = [];
    }
  }

  async function handleResolveConflict(conflictId: string, resolution: "local_wins" | "server_wins" | "merged") {
    try {
      const success = await window.electronAPI.invoke("sync:resolve-conflict", conflictId, resolution) as boolean;
      if (success) {
        const labels: Record<string, string> = { local_wins: "保留本地", server_wins: "采用服务器", merged: "合并" };
        ElMessage.success(`冲突已解决（${labels[resolution]}）`);
        await loadConflicts();
        await refreshSyncStatus();
      } else {
        ElMessage.warning("冲突解决失败，可能已被处理");
      }
    } catch {
      ElMessage.error("解决冲突时出错");
    }
  }

  async function handleResolveAllConflicts(resolution: "local_wins" | "server_wins" | "merged") {
    try {
      await ElMessageBox.confirm(
        `确定要将所有冲突全部采用"${resolution === 'server_wins' ? '服务器' : resolution === 'local_wins' ? '本地' : '合并'}"方式解决吗？`,
        "批量解决冲突",
        { confirmButtonText: "确定", cancelButtonText: "取消", type: "warning" }
      );
      const allConflicts = await window.electronAPI.invoke("sync:get-conflicts") as Array<{ id: string }>;
      let resolved = 0;
      for (const c of allConflicts) {
        const success = await window.electronAPI.invoke("sync:resolve-conflict", c.id, resolution) as boolean;
        if (success) resolved++;
      }
      ElMessage.success(`已解决 ${resolved} 条冲突`);
      await loadConflicts();
      await refreshSyncStatus();
    } catch {}
  }

  async function handleSyncNow() {
    syncing.value = true;
    try {
      const result = await window.electronAPI.invoke("sync:now") as { pushed: number; pulled: number; errors: number };
      ElMessage.success(`同步完成：推送${result.pushed}条，拉取${result.pulled}条`);
      await refreshSyncStatus();
      loadSyncHistory();
    } catch {
      ElMessage.error("同步失败");
    } finally {
      syncing.value = false;
    }
  }

  const syncHistory = ref<Array<{ id: string; action: string; status: string; pushed: number; pulled: number; errors: number; timestamp: string }>>([]);

  async function loadSyncHistory() {
    try {
      const result = await window.electronAPI.invoke("sync:get-history") as typeof syncHistory.value;
      syncHistory.value = result || [];
    } catch {
      syncHistory.value = [];
    }
  }

  function formatSyncTime(ts: string): string {
    if (!ts) return "-";
    try {
      const d = new Date(ts);
      const now = new Date();
      const diffMs = now.getTime() - d.getTime();
      const diffMin = Math.floor(diffMs / 60000);
      if (diffMin < 1) return "刚刚";
      if (diffMin < 60) return `${diffMin}分钟前`;
      const diffHr = Math.floor(diffMin / 60);
      if (diffHr < 24) return `${diffHr}小时前`;
      return d.toLocaleDateString("zh-CN", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
    } catch {
      return ts;
    }
  }

  async function handleConnect() {
    if (!serverUrl.value) { ElMessage.warning("请输入服务器地址"); return; }
    try {
      const token = localStorage.getItem("access_token") || "";
      await window.electronAPI.invoke("sync:configure", serverUrl.value, token);
      ElMessage.success("服务器连接配置成功");
      await refreshSyncStatus();
    } catch { ElMessage.error("连接配置失败"); }
  }

  async function handleAutoSyncToggle() {
    saveSettings();
    try {
      if (autoSyncEnabled.value) {
        await window.electronAPI.invoke("sync:start", syncInterval.value);
        ElMessage.success(`已开启自动同步（每${syncInterval.value}分钟）`);
      } else {
        await window.electronAPI.invoke("sync:stop");
        ElMessage.info("已停止自动同步");
      }
    } catch { ElMessage.error("操作失败"); }
  }

  async function handleSyncIntervalChange() {
    saveSettings();
    if (autoSyncEnabled.value) {
      try {
        await window.electronAPI.invoke("sync:stop");
        await window.electronAPI.invoke("sync:start", syncInterval.value);
        ElMessage.success(`同步频率已调整为每${syncInterval.value}分钟`);
      } catch {}
    }
  }

  async function handleConcurrencyChange(val: number) {
    saveSettings();
    try { await window.electronAPI.invoke("concurrency:set", val); } catch {}
  }

  async function handleCollectIntervalChange() { saveSettings(); }

  async function handleAutoUpdateToggle() { saveSettings(); }

  async function handleCheckUpdate() {
    checkingUpdate.value = true;
    updateStatus.error = null;
    try {
      const result = await window.electronAPI.invoke("update:check") as { updateAvailable: boolean; version: string };
      updateStatus.updateAvailable = result.updateAvailable;
      updateStatus.version = result.version;
      if (!result.updateAvailable) ElMessage.success("当前已是最新版本");
    } catch (err) {
      updateStatus.error = (err as Error).message || "检查更新失败";
    } finally {
      checkingUpdate.value = false;
    }
  }

  async function handleDownloadUpdate() {
    try {
      await window.electronAPI.invoke("update:download");
      updateStatus.downloading = true;
      window.electronAPI.on("update:download-progress", (data: unknown) => {
        const d = data as { progress: number };
        updateStatus.downloadProgress = Math.round(d.progress);
      });
      window.electronAPI.on("update:downloaded", () => {
        updateStatus.downloading = false;
        ElMessageBox.confirm("更新已下载完成，是否立即重启安装？", "安装更新", {
          confirmButtonText: "重启安装", cancelButtonText: "稍后", type: "success",
        }).then(() => { window.electronAPI.invoke("update:install"); }).catch(() => {});
      });
    } catch {
      updateStatus.downloading = false;
      ElMessage.error("下载更新失败");
    }
  }

  async function handleExportLocalData() {
    try {
      const result = await window.electronAPI.invoke("storage:export-all") as Record<string, unknown[]>;
      const json = JSON.stringify(result, null, 2);
      const blob = new Blob([json], { type: "application/json;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `xhs365_data_${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      ElMessage.success("数据导出成功");
    } catch { ElMessage.error("导出失败"); }
  }

  async function handleCleanup() {
    try {
      await ElMessageBox.confirm(
        `确定要清理 ${cleanupDays.value} 天前的采集数据吗？此操作不可恢复。`,
        "确认清理",
        { confirmButtonText: "清理", cancelButtonText: "取消", type: "warning" }
      );
      const result = await window.electronAPI.invoke("storage:cleanup", cleanupDays.value) as { deleted: number };
      ElMessage.success(`已清理 ${result.deleted} 条旧数据`);
      refreshStorage();
    } catch {}
  }

  async function refreshStorage() {
    try {
      const result = await window.electronAPI.invoke("storage:size") as { sizeBytes: number };
      const sizeMB = (result.sizeBytes / (1024 * 1024)).toFixed(2);
      storageInfo.sizeText = `${sizeMB} MB`;
    } catch { storageInfo.sizeText = "未知"; }
  }

  async function loadLogStats() {
    try {
      const stats = await window.electronAPI.invoke("log:get-stats") as typeof logStats;
      Object.assign(logStats, stats);
      if (stats.config?.level) logLevel.value = stats.config.level;
    } catch {}
  }

  async function handleLogLevelChange() {
    try {
      await window.electronAPI.invoke("log:set-level", logLevel.value);
      ElMessage.success(`日志级别已设为 ${logLevel.value.toUpperCase()}`);
    } catch { ElMessage.error("设置日志级别失败"); }
  }

  async function handleViewLogs() {
    logDialogVisible.value = true;
    await loadRecentLogs();
  }

  async function loadRecentLogs() {
    try {
      const result = await window.electronAPI.invoke("log:get-recent", 200, logFilterLevel.value || undefined, logFilterModule.value || undefined) as Array<Record<string, unknown>>;
      logEntries.value = (result || []).reverse();
      logLevelCounts.debug = 0;
      logLevelCounts.info = 0;
      logLevelCounts.warn = 0;
      logLevelCounts.error = 0;
      logLevelCounts.total = logEntries.value.length;
      for (const e of logEntries.value) {
        const lvl = (e as any).level as string;
        if (lvl === "debug") logLevelCounts.debug++;
        else if (lvl === "info") logLevelCounts.info++;
        else if (lvl === "warn") logLevelCounts.warn++;
        else if (lvl === "error" || lvl === "fatal") logLevelCounts.error++;
      }
    } catch { logEntries.value = []; }
  }

  async function handleExportLogs(format: string) {
    try {
      const content = await window.electronAPI.invoke("log:export", format) as string;
      const ext = format === "json" ? "json" : "txt";
      const mimeType = format === "json" ? "application/json" : "text/plain";
      const blob = new Blob([content], { type: `${mimeType};charset=utf-8` });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `xhs365_logs_${new Date().toISOString().slice(0, 10)}.${ext}`;
      a.click();
      URL.revokeObjectURL(url);
      ElMessage.success("日志导出成功");
    } catch { ElMessage.error("日志导出失败"); }
  }

  async function handleClearLogs() {
    try {
      await ElMessageBox.confirm("确定要清除所有日志文件吗？此操作不可恢复。", "确认清除日志", {
        confirmButtonText: "清除", cancelButtonText: "取消", type: "warning",
      });
      const result = await window.electronAPI.invoke("log:clear") as { deleted: number };
      ElMessage.success(`已清除 ${result.deleted} 个日志文件`);
      await loadLogStats();
    } catch {}
  }

  function filterLogEntries() {}

  function toggleLogAutoRefresh(on: boolean) {
    if (logAutoRefreshTimer) { clearInterval(logAutoRefreshTimer); logAutoRefreshTimer = null; }
    if (on) { logAutoRefreshTimer = setInterval(loadRecentLogs, 3000); }
  }

  async function handleUploadLogs() {
    logUploading.value = true;
    try {
      const result = await window.electronAPI.invoke("log:upload") as { success: boolean; uploaded: number };
      if (result.success) { ElMessage.success(`已上传 ${result.uploaded} 条日志`); }
      else { ElMessage.warning("日志上传失败，请检查上传端点配置"); }
    } catch { ElMessage.error("日志上传失败"); }
    finally { logUploading.value = false; }
  }

  async function fetchTeams() {
    teamsLoading.value = true;
    try {
      const api = (await import("../utils/api")).default;
      const { data } = await api.get("/teams");
      teams.value = data?.data || data || [];
    } catch { teams.value = []; }
    finally { teamsLoading.value = false; }
  }

  async function handleCreateTeam() {
    if (!createTeamForm.value.name) { ElMessage.warning("请输入团队名称"); return; }
    creatingTeam.value = true;
    try {
      const api = (await import("../utils/api")).default;
      await api.post("/teams", createTeamForm.value);
      ElMessage.success("团队创建成功");
      showCreateTeamDialog.value = false;
      createTeamForm.value = { name: "", description: "" };
      fetchTeams();
    } catch { ElMessage.error("创建团队失败"); }
    finally { creatingTeam.value = false; }
  }

  async function selectTeam(teamId: string) {
    currentTeam.value = teams.value.find((t: any) => t.id === teamId);
    if (currentTeam.value) {
      try {
        const api = (await import("../utils/api")).default;
        const { data } = await api.get(`/teams/${teamId}`);
        teamMembers.value = data?.data?.members || data?.members || [];
      } catch { teamMembers.value = []; }
    }
  }

  async function handleDeleteTeam(teamId: string) {
    try {
      await ElMessageBox.confirm("确定要删除该团队吗？此操作不可恢复。", "确认删除团队", {
        confirmButtonText: "删除", cancelButtonText: "取消", type: "warning",
      });
      const api = (await import("../utils/api")).default;
      await api.delete(`/teams/${teamId}`);
      ElMessage.success("团队已删除");
      if (currentTeam.value?.id === teamId) { currentTeam.value = null; teamMembers.value = []; }
      fetchTeams();
    } catch {}
  }

  async function handleInviteMember() {
    if (!inviteEmail.value || !currentTeam.value?.id) return;
    inviting.value = true;
    try {
      const api = (await import("../utils/api")).default;
      await api.post(`/teams/${currentTeam.value.id}/invite`, { email: inviteEmail.value, role: inviteRole.value });
      ElMessage.success("邀请已发送");
      inviteEmail.value = "";
      selectTeam(currentTeam.value.id);
    } catch (err: any) {
      ElMessage.error(err?.response?.data?.message || "邀请失败");
    } finally { inviting.value = false; }
  }

  async function handleRemoveMember(teamId: string, memberId: string) {
    try {
      await ElMessageBox.confirm("确定要移除该成员吗？", "确认移除", {
        confirmButtonText: "移除", cancelButtonText: "取消", type: "warning",
      });
      const api = (await import("../utils/api")).default;
      await api.delete(`/teams/${teamId}/members/${memberId}`);
      ElMessage.success("成员已移除");
      selectTeam(teamId);
    } catch {}
  }

  function teamRoleLabel(role: string): string {
    const map: Record<string, string> = { owner: "所有者", admin: "管理员", member: "成员", viewer: "查看者" };
    return map[role] || role;
  }

  async function fetchAuditLogs() {
    auditLoading.value = true;
    try {
      const api = (await import("../utils/api")).default;
      const params: Record<string, any> = { page: auditPage.value, page_size: auditPageSize.value };
      if (auditFilter.value.action) params.action = auditFilter.value.action;
      if (auditFilter.value.resource_type) params.resource_type = auditFilter.value.resource_type;
      const { data } = await api.get("/audit/operations", { params });
      auditLogs.value = data?.data?.items || [];
      auditTotal.value = data?.data?.total || 0;
    } catch { auditLogs.value = []; auditTotal.value = 0; }
    finally { auditLoading.value = false; }
  }

  function auditActionTagType(action: string): "" | "success" | "warning" | "danger" | "info" {
    const map: Record<string, "" | "success" | "warning" | "danger" | "info"> = {
      create: "success", update: "warning", delete: "danger", login: "info", export: "info",
    };
    return map[action] || "info";
  }

  async function fetchSecuritySummary() {
    try {
      const api = (await import("../utils/api")).default;
      const { data } = await api.get("/admin/security/audit-summary");
      securitySummary.value = data?.data || data;
    } catch { securitySummary.value = null; }
  }

  async function fetchSecurityLogs() {
    securityLoading.value = true;
    try {
      const api = (await import("../utils/api")).default;
      const params: Record<string, any> = { page: securityPage.value, page_size: securityPageSize.value };
      if (securityFilter.value.path) params.path = securityFilter.value.path;
      if (securityFilter.value.client_ip) params.client_ip = securityFilter.value.client_ip;
      if (securityFilter.value.method) params.method = securityFilter.value.method;
      if (securityFilter.value.min_risk != null) params.min_risk = securityFilter.value.min_risk;
      const { data } = await api.get("/admin/security/audit-logs", { params });
      securityLogs.value = data?.data?.items || [];
      securityTotal.value = data?.data?.total || 0;
    } catch { securityLogs.value = []; securityTotal.value = 0; }
    finally { securityLoading.value = false; }
  }

  async function handleCloudDataSummary() {
    cloudDataLoading.value = true;
    try {
      const api = (await import("../utils/api")).default;
      const { data } = await api.get("/gdpr/data-summary");
      cloudDataSummary.value = data?.data || data;
    } catch { ElMessage.error("获取数据摘要失败"); }
    finally { cloudDataLoading.value = false; }
  }

  async function handleCloudDataExport() {
    cloudExportLoading.value = true;
    try {
      const api = (await import("../utils/api")).default;
      const { data } = await api.post("/gdpr/export", null, { params: { format: "json" } });
      const exportData = data?.data || data;
      const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: "application/json;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `vuemonitor_cloud_export_${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      ElMessage.success("云端数据导出成功");
    } catch { ElMessage.error("云端数据导出失败"); }
    finally { cloudExportLoading.value = false; }
  }

  async function handleShowPrivacyPolicy() {
    try {
      const api = (await import("../utils/api")).default;
      const { data } = await api.get("/gdpr/privacy-policy");
      const policy = data?.data || data;
      ElMessageBox.alert(
        `<div style="max-height: 400px; overflow-y: auto; text-align: left; font-size: 13px; line-height: 1.6;">
          <p><strong>数据控制者:</strong> ${policy.policy?.data_controller || "-"}</p>
          <p><strong>生效日期:</strong> ${policy.effective_date || "-"}</p>
          <p><strong>收集的数据类型:</strong></p>
          <ul>${(policy.policy?.data_types_collected || []).map((i: string) => `<li>${i}</li>`).join("")}</ul>
          <p><strong>数据处理目的:</strong></p>
          <ul>${(policy.policy?.data_purposes || []).map((i: string) => `<li>${i}</li>`).join("")}</ul>
          <p><strong>您的权利:</strong></p>
          <ul>${(policy.policy?.user_rights || []).map((i: string) => `<li>${i}</li>`).join("")}</ul>
          <p><strong>数据保留:</strong> ${policy.policy?.data_retention || "-"}</p>
          <p><strong>联系方式:</strong> ${policy.policy?.contact || "-"}</p>
        </div>`,
        "隐私政策",
        { dangerouslyUseHTMLString: true, confirmButtonText: "我已了解" }
      );
    } catch { ElMessage.error("获取隐私政策失败"); }
  }

  async function handleCloudDataDeletion() {
    try {
      await ElMessageBox.confirm(
        "此操作将永久删除您的所有云端个人数据，账户将被匿名化且无法恢复。请确认您了解此操作的后果。",
        "确认删除所有云端数据",
        { confirmButtonText: "确认删除", cancelButtonText: "取消", type: "warning" }
      );
      const email = authStore.user?.email;
      if (!email) { ElMessage.error("无法获取邮箱信息"); return; }
      await ElMessageBox.prompt("请输入您的邮箱地址以确认删除操作", "邮箱确认", {
        confirmButtonText: "确认", cancelButtonText: "取消",
        inputPattern: new RegExp(`^${email.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}$`),
        inputErrorMessage: "邮箱地址不匹配",
      });
      cloudDeleteLoading.value = true;
      const api = (await import("../utils/api")).default;
      const { data } = await api.post("/gdpr/deletion-request", null, { params: { confirm_email: email } });
      const result = data?.data || data;
      ElMessage.success(`数据删除成功，共删除 ${result.total_deleted} 条记录`);
      authStore.logout();
    } catch (e: any) {
      if (e !== "cancel" && e?.message !== "cancel") { ElMessage.error("数据删除失败"); }
    } finally { cloudDeleteLoading.value = false; }
  }

  let statusTimer: ReturnType<typeof setInterval> | null = null;

  function init() {
    licenseStore.fetchLicense();
    refreshSyncStatus();
    loadSettings();
    refreshStorage();
    loadConflicts();
    loadLogStats();
    loadSyncHistory();
    fetchTeams();
    fetchAuditLogs();
    fetchSecuritySummary();
    fetchSecurityLogs();
    statusTimer = setInterval(refreshSyncStatus, 10000);
    window.electronAPI.on("sync:conflict:detected", () => { loadConflicts(); });
    window.electronAPI.on("sync:conflict:resolved", () => { loadConflicts(); });
  }

  function cleanup() {
    if (statusTimer) { clearInterval(statusTimer); }
    if (logAutoRefreshTimer) { clearInterval(logAutoRefreshTimer); }
  }

  return {
    authStore, licenseStore,
    activeSection, sections,
    serverUrl, syncing, autoSyncEnabled, syncInterval,
    concurrency, autoMinimize, collectInterval,
    autoUpdateEnabled, checkingUpdate, cleanupDays,
    notifySettings, quietHoursRange,
    updateStatus, syncStatus,
    conflicts, conflictCount,
    storageInfo,
    logLevel, logStats, logDialogVisible, logEntries,
    logFilterLevel, logFilterModule, logSearchQuery,
    logAutoRefresh, logUploading, logModules, logLevelCounts,
    filteredLogEntries,
    clientPrivacy, cloudDataSummary, cloudDataLoading, cloudExportLoading, cloudDeleteLoading,
    showCreateTeamDialog, creatingTeam, createTeamForm,
    teams, teamsLoading, currentTeam, teamMembers,
    inviteEmail, inviteRole, inviting,
    auditLogs, auditLoading, auditPage, auditPageSize, auditTotal, auditFilter,
    securityLogs, securityLoading, securityPage, securityPageSize, securityTotal, securityFilter, securitySummary,
    shortcuts,
    cloudTableLabel, logLevelBarWidth, captureKey,
    saveShortcutKey, handleShortcutToggle, resetShortcuts,
    saveNotifySettings, saveSettings,
    refreshSyncStatus, loadConflicts,
    handleResolveConflict, handleResolveAllConflicts,
    handleSyncNow, loadSyncHistory, formatSyncTime,
    handleConnect, handleAutoSyncToggle, handleSyncIntervalChange,
    handleConcurrencyChange, handleCollectIntervalChange, handleAutoUpdateToggle,
    handleCheckUpdate, handleDownloadUpdate,
    handleExportLocalData, handleCleanup, refreshStorage,
    handleLogLevelChange, handleViewLogs, loadRecentLogs,
    handleExportLogs, handleClearLogs, filterLogEntries,
    toggleLogAutoRefresh, handleUploadLogs,
    fetchTeams, handleCreateTeam, selectTeam, handleDeleteTeam,
    handleInviteMember, handleRemoveMember, teamRoleLabel,
    fetchAuditLogs, auditActionTagType,
    fetchSecuritySummary, fetchSecurityLogs,
    handleCloudDataSummary, handleCloudDataExport, handleShowPrivacyPolicy, handleCloudDataDeletion,
    init, cleanup,
  };
}
