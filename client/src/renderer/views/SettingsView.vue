<template>
  <div class="settings-page">
    <div class="settings-header">
      <h1 class="page-title">设置</h1>
      <p class="page-subtitle">管理您的账户、应用和系统配置</p>
    </div>

    <div class="settings-container">
      <aside class="settings-sidebar">
        <nav class="settings-nav">
          <div 
            v-for="section in sections" 
            :key="section.key"
            :class="['nav-item', { active: activeSection === section.key }]"
            @click="activeSection = section.key"
          >
            <el-icon class="nav-icon"><component :is="section.icon" /></el-icon>
            <span class="nav-label">{{ section.label }}</span>
          </div>
        </nav>
      </aside>

      <main class="settings-content">
        <div v-show="activeSection === 'account'" class="settings-section">
          <h2 class="section-title">账户信息</h2>
          <div class="settings-card">
            <div class="account-info" v-if="authStore.user">
              <div class="account-avatar">
                <div class="avatar-circle">{{ (authStore.user.nickname || authStore.user.email || 'U')[0].toUpperCase() }}</div>
              </div>
              <div class="account-details">
                <div class="detail-row">
                  <span class="detail-label">邮箱</span>
                  <span class="detail-value">{{ authStore.user.email || '未设置' }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">昵称</span>
                  <span class="detail-value">{{ authStore.user.nickname }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">套餐</span>
                  <el-tag class="plan-tag" effect="plain">{{ authStore.user.plan }}</el-tag>
                </div>
                <div class="detail-row">
                  <span class="detail-label">套餐到期</span>
                  <span class="detail-value">{{ authStore.user.plan_expires_at || "永久" }}</span>
                </div>
              </div>
            </div>
          </div>

          <h2 class="section-title" style="margin-top: 32px">授权信息</h2>
          <div class="settings-card">
            <div v-if="licenseStore.isActivated" class="license-info">
              <div class="license-grid">
                <div class="license-item">
                  <span class="license-label">当前套餐</span>
                  <el-tag type="success" effect="plain">{{ licenseStore.planLabel }}</el-tag>
                </div>
                <div class="license-item">
                  <span class="license-label">到期时间</span>
                  <span class="license-value">{{ licenseStore.expiresAtFormatted }}</span>
                </div>
                <div class="license-item">
                  <span class="license-label">设备ID</span>
                  <code class="device-id">{{ licenseStore.license?.deviceId }}</code>
                </div>
                <div class="license-item">
                  <span class="license-label">最后验证</span>
                  <span class="license-value">{{ licenseStore.license?.lastVerified }}</span>
                </div>
              </div>
            </div>
            <div v-else class="license-empty">
              <el-icon class="empty-icon"><Key /></el-icon>
              <p>未激活授权码</p>
              <el-button type="primary" @click="$router.push('/license')">前往激活</el-button>
            </div>
            <div class="card-actions">
              <el-button @click="$router.push('/license')">管理授权</el-button>
            </div>
          </div>
        </div>

        <div v-show="activeSection === 'notifications'" class="settings-section">
          <h2 class="section-title">通知偏好</h2>
          <div class="settings-card">
            <div class="setting-item">
              <div class="setting-info">
                <h3 class="setting-title">桌面通知</h3>
                <p class="setting-desc">监控规则触发时弹出系统通知</p>
              </div>
              <el-switch v-model="notifySettings.desktop" @change="saveNotifySettings" />
            </div>
            <div class="setting-divider"></div>
            <div class="setting-item">
              <div class="setting-info">
                <h3 class="setting-title">邮件通知</h3>
                <p class="setting-desc">重要事件发送邮件提醒</p>
              </div>
              <el-switch v-model="notifySettings.email" @change="saveNotifySettings" />
            </div>
            <div class="setting-divider"></div>
            <div class="setting-item">
              <div class="setting-info">
                <h3 class="setting-title">声音提醒</h3>
                <p class="setting-desc">收到通知时播放提示音</p>
              </div>
              <el-switch v-model="notifySettings.sound" @change="saveNotifySettings" />
            </div>
            <div class="setting-divider"></div>
            <div class="setting-item">
              <div class="setting-info">
                <h3 class="setting-title">免打扰时段</h3>
                <p class="setting-desc">在指定时间内静音所有通知</p>
              </div>
              <el-switch v-model="notifySettings.quietHours" @change="saveNotifySettings" />
            </div>
            <div v-if="notifySettings.quietHours" class="quiet-hours-config">
              <el-time-picker 
                v-model="quietHoursRange" 
                is-range 
                range-separator="至" 
                start-placeholder="开始" 
                end-placeholder="结束" 
                format="HH:mm" 
                @change="saveNotifySettings"
                class="modern-time-picker"
              />
            </div>
          </div>
        </div>

        <div v-show="activeSection === 'sync'" class="settings-section">
          <h2 class="section-title">数据同步</h2>
          <div class="settings-card">
            <div class="sync-status-header">
              <div class="sync-status">
                <el-tag :type="syncStatus.isSyncing ? 'warning' : 'success'" effect="dark">
                  <el-icon v-if="syncStatus.isSyncing" class="sync-pulse"><Loading /></el-icon>
                  {{ syncStatus.isSyncing ? "同步中..." : "空闲" }}
                </el-tag>
              </div>
              <el-button type="primary" :loading="syncing" @click="handleSyncNow">立即同步</el-button>
            </div>
            
            <div class="sync-stats">
              <div class="stat-item">
                <span class="stat-label">服务器</span>
                <span class="stat-value">{{ syncStatus.serverUrl || "未配置" }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">上次同步</span>
                <span class="stat-value">{{ syncStatus.lastSyncAt || "从未同步" }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">待同步</span>
                <el-badge :value="syncStatus.pendingCount" :type="syncStatus.pendingCount > 0 ? 'danger' : 'info'" />
              </div>
              <div class="stat-item">
                <span class="stat-label">已同步</span>
                <span class="stat-value">{{ syncStatus.syncedCount }}</span>
              </div>
            </div>

            <div v-if="!syncStatus.serverUrl" class="server-config">
              <el-input v-model="serverUrl" placeholder="https://api.xhs365.com" class="modern-input" />
              <el-button type="primary" @click="handleConnect">连接</el-button>
            </div>

            <div class="auto-sync-config">
              <div class="setting-item">
                <div class="setting-info">
                  <h3 class="setting-title">自动同步</h3>
                  <p class="setting-desc">定期自动同步数据到服务器</p>
                </div>
                <el-switch v-model="autoSyncEnabled" @change="handleAutoSyncToggle" />
              </div>
              <div v-if="autoSyncEnabled" class="sync-frequency">
                <span class="frequency-label">同步频率</span>
                <el-select v-model="syncInterval" class="modern-select" @change="handleSyncIntervalChange">
                  <el-option :value="3" label="每3分钟" />
                  <el-option :value="5" label="每5分钟" />
                  <el-option :value="10" label="每10分钟" />
                  <el-option :value="30" label="每30分钟" />
                </el-select>
              </div>
            </div>
          </div>

          <div v-if="conflictCount > 0" class="settings-card conflict-card">
            <el-alert type="warning" :closable="false" show-icon>
              <template #title>
                检测到 {{ conflictCount }} 条数据同步冲突
              </template>
            </el-alert>
            <div class="conflict-list">
              <div v-for="conflict in conflicts.slice(0, 3)" :key="conflict.id" class="conflict-item">
                <el-tag size="small" :type="conflict.type === 'product' ? 'primary' : 'success'">
                  {{ conflict.type === 'product' ? '商品' : '特征' }}
                </el-tag>
                <div class="conflict-actions">
                  <el-button size="small" @click="handleResolveConflict(conflict.id, 'local_wins')">保留本地</el-button>
                  <el-button size="small" type="success" @click="handleResolveConflict(conflict.id, 'server_wins')">采用服务器</el-button>
                </div>
              </div>
            </div>
            <div class="conflict-footer">
              <el-button size="small" @click="handleResolveAllConflicts('server_wins')">全部采用服务器</el-button>
              <el-button size="small" @click="loadConflicts">刷新</el-button>
            </div>
          </div>
        </div>

        <div v-show="activeSection === 'collection'" class="settings-section">
          <h2 class="section-title">采集配置</h2>
          <div class="settings-card">
            <div class="setting-item">
              <div class="setting-info">
                <h3 class="setting-title">最大并发数</h3>
                <p class="setting-desc">同时采集的任务数量</p>
              </div>
              <el-input-number v-model="concurrency" :min="1" :max="10" @change="handleConcurrencyChange" class="modern-input-number" />
            </div>
            <div class="setting-divider"></div>
            <div class="setting-item">
              <div class="setting-info">
                <h3 class="setting-title">自动最小化</h3>
                <p class="setting-desc">采集开始时自动最小化窗口</p>
              </div>
              <el-switch v-model="autoMinimize" />
            </div>
            <div class="setting-divider"></div>
            <div class="setting-item">
              <div class="setting-info">
                <h3 class="setting-title">采集间隔</h3>
                <p class="setting-desc">每次采集之间的等待时间（秒）</p>
              </div>
              <el-input-number v-model="collectInterval" :min="10" :max="300" :step="10" @change="handleCollectIntervalChange" class="modern-input-number" />
            </div>
          </div>
        </div>

        <div v-show="activeSection === 'updates'" class="settings-section">
          <h2 class="section-title">自动更新</h2>
          <div class="settings-card">
            <div class="setting-item">
              <div class="setting-info">
                <h3 class="setting-title">自动检查更新</h3>
                <p class="setting-desc">启动时自动检查新版本</p>
              </div>
              <el-switch v-model="autoUpdateEnabled" @change="handleAutoUpdateToggle" />
            </div>
            <div class="update-actions">
              <el-button @click="handleCheckUpdate" :loading="checkingUpdate">检查更新</el-button>
              <span v-if="updateStatus.version" class="update-status">
                <template v-if="updateStatus.updateAvailable">
                  新版本 <el-tag size="small" type="success">v{{ updateStatus.version }}</el-tag> 可用
                  <el-button type="primary" @click="handleDownloadUpdate" :loading="updateStatus.downloading">
                    {{ updateStatus.downloading ? `下载中 ${updateStatus.downloadProgress}%` : '下载并安装' }}
                  </el-button>
                </template>
                <template v-else>
                  <el-tag size="small" type="info">已是最新版本</el-tag>
                </template>
              </span>
              <span v-if="updateStatus.error" class="update-error">{{ updateStatus.error }}</span>
            </div>
          </div>
        </div>

        <div v-show="activeSection === 'data'" class="settings-section">
          <h2 class="section-title">数据管理</h2>
          <div class="settings-card">
            <div class="setting-item">
              <div class="setting-info">
                <h3 class="setting-title">导出全部数据</h3>
                <p class="setting-desc">导出本地SQLite数据库为JSON格式</p>
              </div>
              <el-button @click="handleExportLocalData">导出</el-button>
            </div>
            <div class="setting-divider"></div>
            <div class="setting-item">
              <div class="setting-info">
                <h3 class="setting-title">清理旧数据</h3>
                <p class="setting-desc">删除指定天数之前的采集数据</p>
              </div>
              <div class="cleanup-controls">
                <el-select v-model="cleanupDays" class="modern-select">
                  <el-option :value="30" label="30天前" />
                  <el-option :value="60" label="60天前" />
                  <el-option :value="90" label="90天前" />
                  <el-option :value="180" label="180天前" />
                </el-select>
                <el-button type="danger" @click="handleCleanup">清理</el-button>
              </div>
            </div>
            <div class="setting-divider"></div>
            <div class="setting-item">
              <div class="setting-info">
                <h3 class="setting-title">存储占用</h3>
              </div>
              <div class="storage-info">
                <span class="storage-size">{{ storageInfo.sizeText || '计算中...' }}</span>
                <el-button link type="primary" @click="refreshStorage">刷新</el-button>
              </div>
            </div>
          </div>
        </div>

        <div v-show="activeSection === 'logs'" class="settings-section">
          <h2 class="section-title">日志管理</h2>
          <div class="settings-card">
            <div class="setting-item">
              <div class="setting-info">
                <h3 class="setting-title">日志级别</h3>
                <p class="setting-desc">设置日志记录的详细程度</p>
              </div>
              <el-select v-model="logLevel" class="modern-select" @change="handleLogLevelChange">
                <el-option value="debug" label="Debug" />
                <el-option value="info" label="Info" />
                <el-option value="warn" label="Warn" />
                <el-option value="error" label="Error" />
              </el-select>
            </div>
            <div class="setting-divider"></div>
            <div class="log-stats">
              <div class="stat-item">
                <span class="stat-label">日志文件</span>
                <span class="stat-value">{{ logStats.logFiles || 0 }} 个</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">会话ID</span>
                <code class="session-id">{{ logStats.sessionId || '-' }}</code>
              </div>
            </div>
            <div class="log-actions">
              <el-button @click="handleViewLogs">查看日志</el-button>
              <el-button @click="handleExportLogs('json')">导出JSON</el-button>
              <el-button @click="handleExportLogs('text')">导出文本</el-button>
              <el-button type="danger" @click="handleClearLogs">清除日志</el-button>
            </div>
          </div>
        </div>

        <div v-show="activeSection === 'shortcuts'" class="settings-section">
          <h2 class="section-title">键盘快捷键</h2>
          <div class="settings-card">
            <div class="shortcuts-header">
              <span>快捷键</span>
              <span>功能</span>
              <span>启用</span>
              <span>操作</span>
            </div>
            <div class="shortcuts-list">
              <div v-for="row in shortcuts" :key="row.action" class="shortcut-item">
                <div class="shortcut-key">
                  <el-tag v-if="!row.editing" size="small" type="info">{{ row.key }}</el-tag>
                  <el-input
                    v-else
                    v-model="row.key"
                    size="small"
                    placeholder="按下新快捷键..."
                    @keydown="captureKey($event, row)"
                    class="shortcut-input"
                    readonly
                  />
                </div>
                <span class="shortcut-label">{{ row.label }}</span>
                <el-switch v-model="row.enabled" size="small" @change="handleShortcutToggle(row)" />
                <div class="shortcut-actions">
                  <el-button v-if="!row.editing" size="small" text @click="row.editing = true">修改</el-button>
                  <el-button v-else size="small" text type="primary" @click="saveShortcutKey(row)">保存</el-button>
                </div>
              </div>
            </div>
            <div class="shortcuts-footer">
              <el-button @click="resetShortcuts">重置默认</el-button>
            </div>
          </div>
        </div>
      </main>
    </div>

    <el-dialog 
      v-model="logDialogVisible" 
      title="最近日志" 
      width="80%" 
      top="5vh"
      class="modern-dialog log-dialog"
      :close-on-click-modal="true"
      :close-on-press-escape="true"
      :show-close="true"
    >
      <div class="log-filters">
        <el-select v-model="logFilterLevel" placeholder="级别筛选" clearable class="modern-select" @change="loadRecentLogs">
          <el-option value="debug" label="Debug" />
          <el-option value="info" label="Info" />
          <el-option value="warn" label="Warn" />
          <el-option value="error" label="Error" />
        </el-select>
        <el-select v-model="logFilterModule" placeholder="模块筛选" clearable class="modern-select" @change="loadRecentLogs">
          <el-option v-for="m in logModules" :key="m" :value="m" :label="m" />
        </el-select>
        <el-button @click="loadRecentLogs">刷新</el-button>
      </div>
      <el-table :data="logEntries" class="modern-table log-table" stripe>
        <el-table-column label="时间" width="170" prop="timestamp">
          <template #default="{ row }">
            {{ row.timestamp.replace('T', ' ').substring(0, 19) }}
          </template>
        </el-table-column>
        <el-table-column label="级别" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="row.level === 'error' || row.level === 'fatal' ? 'danger' : row.level === 'warn' ? 'warning' : row.level === 'info' ? 'success' : 'info'">
              {{ row.level.toUpperCase() }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="模块" width="140" prop="module" />
        <el-table-column label="消息" min-width="250" prop="message" />
        <el-table-column label="详情" width="200">
          <template #default="{ row }">
            <span v-if="row.error" class="log-error">{{ row.error }}</span>
            <span v-else-if="row.data" class="log-data">{{ JSON.stringify(row.data).substring(0, 80) }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from "vue";
import { useAuthStore } from "../stores/auth";
import { useLicenseStore } from "../stores/license";
import { ElMessage, ElMessageBox } from "element-plus";
import { shortcutManager, type ShortcutBinding } from "../composables/shortcuts";
import { 
  User, Bell, Refresh, Cpu, Download, Folder, Document, Connection, 
  Key, Loading 
} from "@element-plus/icons-vue";

const authStore = useAuthStore();
const licenseStore = useLicenseStore();

const activeSection = ref("account");

const sections = [
  { key: "account", label: "账户与授权", icon: User },
  { key: "notifications", label: "通知偏好", icon: Bell },
  { key: "sync", label: "数据同步", icon: Refresh },
  { key: "collection", label: "采集配置", icon: Cpu },
  { key: "updates", label: "自动更新", icon: Download },
  { key: "data", label: "数据管理", icon: Folder },
  { key: "logs", label: "日志管理", icon: Document },
  { key: "shortcuts", label: "快捷键", icon: Connection },
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

const storageInfo = reactive({
  sizeText: "",
});

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
const logModules = ref(["Main", "ChromiumWorker", "CloudSync", "DataMart", "FeatureEngine", "LocalEvaluator", "PlaywrightCollector", "CrashRecovery", "LicenseManager"]);

let statusTimer: ReturnType<typeof setInterval> | null = null;

const shortcuts = ref<(ShortcutBinding & { editing?: boolean })[]>(
  shortcutManager.getShortcuts().map((s) => ({ ...s, editing: false }))
);

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

onMounted(async () => {
  await licenseStore.fetchLicense();
  await refreshSyncStatus();
  loadSettings();
  refreshStorage();
  loadConflicts();
  loadLogStats();

  statusTimer = setInterval(refreshSyncStatus, 10000);

  window.electronAPI.on("sync:conflict:detected", () => {
    loadConflicts();
  });
  window.electronAPI.on("sync:conflict:resolved", () => {
    loadConflicts();
  });
});

onUnmounted(() => {
  if (statusTimer) {
    clearInterval(statusTimer);
  }
});

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
  } catch {
    ElMessage.error("同步失败");
  } finally {
    syncing.value = false;
  }
}

async function handleConnect() {
  if (!serverUrl.value) {
    ElMessage.warning("请输入服务器地址");
    return;
  }
  try {
    const token = localStorage.getItem("access_token") || "";
    await window.electronAPI.invoke("sync:configure", serverUrl.value, token);
    ElMessage.success("服务器连接配置成功");
    await refreshSyncStatus();
  } catch {
    ElMessage.error("连接配置失败");
  }
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
  } catch {
    ElMessage.error("操作失败");
  }
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
  try {
    await window.electronAPI.invoke("concurrency:set", val);
  } catch {}
}

async function handleCollectIntervalChange() {
  saveSettings();
}

async function handleAutoUpdateToggle() {
  saveSettings();
}

async function handleCheckUpdate() {
  checkingUpdate.value = true;
  updateStatus.error = null;
  try {
    const result = await window.electronAPI.invoke("update:check") as { updateAvailable: boolean; version: string };
    updateStatus.updateAvailable = result.updateAvailable;
    updateStatus.version = result.version;
    if (!result.updateAvailable) {
      ElMessage.success("当前已是最新版本");
    }
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

    const unsub = window.electronAPI.on("update:download-progress", (data: unknown) => {
      const d = data as { progress: number };
      updateStatus.downloadProgress = Math.round(d.progress);
    });

    window.electronAPI.on("update:downloaded", () => {
      updateStatus.downloading = false;
      ElMessageBox.confirm("更新已下载完成，是否立即重启安装？", "安装更新", {
        confirmButtonText: "重启安装",
        cancelButtonText: "稍后",
        type: "success",
      }).then(() => {
        window.electronAPI.invoke("update:install");
      }).catch(() => {});
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
  } catch {
    ElMessage.error("导出失败");
  }
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
  } catch {
    storageInfo.sizeText = "未知";
  }
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
  } catch {
    ElMessage.error("设置日志级别失败");
  }
}

async function handleViewLogs() {
  logDialogVisible.value = true;
  await loadRecentLogs();
}

async function loadRecentLogs() {
  try {
    const result = await window.electronAPI.invoke("log:get-recent", 200, logFilterLevel.value || undefined, logFilterModule.value || undefined) as Array<Record<string, unknown>>;
    logEntries.value = (result || []).reverse();
  } catch {
    logEntries.value = [];
  }
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
  } catch {
    ElMessage.error("日志导出失败");
  }
}

async function handleClearLogs() {
  try {
    await ElMessageBox.confirm("确定要清除所有日志文件吗？此操作不可恢复。", "确认清除日志", {
      confirmButtonText: "清除",
      cancelButtonText: "取消",
      type: "warning",
    });
    const result = await window.electronAPI.invoke("log:clear") as { deleted: number };
    ElMessage.success(`已清除 ${result.deleted} 个日志文件`);
    await loadLogStats();
  } catch {}
}
</script>

<style scoped>
.settings-page {
  padding: 24px;
  background: #f5f7fa;
  min-height: 100vh;
}

.settings-header {
  margin-bottom: 24px;
}

.page-title {
  margin: 0 0 8px;
  font-size: 28px;
  font-weight: 700;
  color: #1a1a2e;
  letter-spacing: -0.5px;
}

.page-subtitle {
  margin: 0;
  font-size: 14px;
  color: #6b7280;
}

.settings-container {
  display: flex;
  gap: 24px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  border: 1px solid #f3f4f6;
  overflow: hidden;
  min-height: calc(100vh - 140px);
}

.settings-sidebar {
  width: 220px;
  background: #f9fafb;
  border-right: 1px solid #f3f4f6;
  padding: 16px 0;
  flex-shrink: 0;
}

.settings-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  cursor: pointer;
  transition: all 0.2s;
  color: #6b7280;
  font-size: 14px;
}

.nav-item:hover {
  background: #f3f4f6;
  color: #374151;
}

.nav-item.active {
  background: #fff;
  color: #6366f1;
  font-weight: 500;
  border-right: 3px solid #6366f1;
}

.nav-icon {
  font-size: 18px;
}

.nav-label {
  flex: 1;
}

.settings-content {
  flex: 1;
  padding: 32px;
  overflow-y: auto;
}

.settings-section {
  max-width: 800px;
}

.section-title {
  margin: 0 0 16px;
  font-size: 20px;
  font-weight: 600;
  color: #1a1a2e;
}

.settings-card {
  background: #fff;
  border: 1px solid #f3f4f6;
  border-radius: 12px;
  padding: 20px;
}

.account-info {
  display: flex;
  gap: 20px;
}

.account-avatar {
  flex-shrink: 0;
}

.avatar-circle {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 24px;
  font-weight: 600;
}

.account-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.detail-label {
  font-size: 14px;
  color: #6b7280;
  min-width: 80px;
}

.detail-value {
  font-size: 14px;
  color: #1a1a2e;
}

.plan-tag {
  padding: 4px 10px;
  border-radius: 6px;
}

.license-info {
  margin-bottom: 16px;
}

.license-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.license-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.license-label {
  font-size: 12px;
  color: #6b7280;
}

.license-value {
  font-size: 14px;
  color: #1a1a2e;
}

.device-id {
  font-family: monospace;
  font-size: 12px;
  background: #f9fafb;
  padding: 4px 8px;
  border-radius: 6px;
  color: #374151;
}

.license-empty {
  text-align: center;
  padding: 32px 0;
  color: #6b7280;
}

.empty-icon {
  font-size: 48px;
  color: #d1d5db;
  margin-bottom: 12px;
}

.card-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 16px;
  border-top: 1px solid #f3f4f6;
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
}

.setting-info {
  flex: 1;
}

.setting-title {
  margin: 0 0 4px;
  font-size: 14px;
  font-weight: 500;
  color: #1a1a2e;
}

.setting-desc {
  margin: 0;
  font-size: 13px;
  color: #6b7280;
}

.setting-divider {
  height: 1px;
  background: #f3f4f6;
}

.quiet-hours-config {
  padding: 16px 0 0;
}

.modern-time-picker {
  width: 100%;
}

.sync-status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.sync-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.sync-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 20px;
  padding: 16px;
  background: #f9fafb;
  border-radius: 10px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 12px;
  color: #6b7280;
}

.stat-value {
  font-size: 14px;
  color: #1a1a2e;
}

.server-config {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.modern-input {
  flex: 1;
  border-radius: 10px;
}

.modern-select {
  border-radius: 10px;
}

.auto-sync-config {
  padding-top: 16px;
  border-top: 1px solid #f3f4f6;
}

.sync-frequency {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-top: 12px;
}

.frequency-label {
  font-size: 14px;
  color: #6b7280;
}

.modern-input-number {
  border-radius: 10px;
}

.conflict-card {
  margin-top: 20px;
  border-color: #fecaca;
}

.conflict-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 16px;
}

.conflict-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: #fef2f2;
  border-radius: 8px;
}

.conflict-actions {
  display: flex;
  gap: 8px;
}

.conflict-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f3f4f6;
}

.update-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f3f4f6;
}

.update-status {
  font-size: 14px;
  color: #6b7280;
}

.update-error {
  font-size: 13px;
  color: #ef4444;
}

.cleanup-controls {
  display: flex;
  gap: 12px;
  align-items: center;
}

.storage-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.storage-size {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
}

.log-stats {
  display: flex;
  gap: 24px;
  padding: 16px;
  background: #f9fafb;
  border-radius: 10px;
  margin-bottom: 16px;
}

.session-id {
  font-family: monospace;
  font-size: 12px;
  background: #fff;
  padding: 4px 8px;
  border-radius: 6px;
}

.log-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.shortcuts-header {
  display: grid;
  grid-template-columns: 160px 1fr 80px 100px;
  gap: 16px;
  padding: 12px 0;
  border-bottom: 1px solid #f3f4f6;
  font-size: 13px;
  font-weight: 500;
  color: #6b7280;
}

.shortcuts-list {
  display: flex;
  flex-direction: column;
}

.shortcut-item {
  display: grid;
  grid-template-columns: 160px 1fr 80px 100px;
  gap: 16px;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #f9fafb;
}

.shortcut-item:last-child {
  border-bottom: none;
}

.shortcut-key {
  display: flex;
  align-items: center;
}

.shortcut-input {
  width: 140px;
}

.shortcut-label {
  font-size: 14px;
  color: #1a1a2e;
}

.shortcut-actions {
  display: flex;
  justify-content: flex-end;
}

.shortcuts-footer {
  display: flex;
  justify-content: flex-end;
  padding-top: 16px;
  border-top: 1px solid #f3f4f6;
}

.modern-dialog :deep(.el-dialog__header) {
  padding: 20px 24px;
  border-bottom: 1px solid #f3f4f6;
  margin-right: 0;
}

.modern-dialog :deep(.el-dialog__title) {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a2e;
}

.modern-dialog :deep(.el-dialog__body) {
  padding: 24px;
}

.modern-dialog :deep(.el-dialog__footer) {
  padding: 16px 24px;
  border-top: 1px solid #f3f4f6;
}

.log-filters {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.log-table {
  border-radius: 8px;
}

.log-error {
  color: #ef4444;
  font-size: 12px;
}

.log-data {
  color: #6b7280;
  font-size: 11px;
}

@media (max-width: 1024px) {
  .settings-container {
    flex-direction: column;
  }
  
  .settings-sidebar {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid #f3f4f6;
  }
  
  .settings-nav {
    flex-direction: row;
    overflow-x: auto;
  }
  
  .nav-item.active {
    border-right: none;
    border-bottom: 3px solid #6366f1;
  }
  
  .license-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .settings-page {
    padding: 16px;
  }
  
  .settings-content {
    padding: 20px;
  }
  
  .account-info {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }
  
  .shortcuts-header,
  .shortcut-item {
    grid-template-columns: 120px 1fr 60px 80px;
    gap: 12px;
  }
}
</style>
