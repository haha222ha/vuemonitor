<template>
  <div class="settings-page">
    <PageHeader title="设置" subtitle="管理您的账户、应用和系统配置" />

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
        <div v-show="activeSection === 'account'">
          <AccountSection :auth-store="authStore" :license-store="licenseStore" />
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

        <div v-show="activeSection === 'appearance'" class="settings-section">
          <h2 class="section-title">外观</h2>
          <div class="settings-card">
            <div class="setting-item">
              <div class="setting-info">
                <h3 class="setting-title">主题模式</h3>
                <p class="setting-desc">选择界面配色方案</p>
              </div>
              <div class="theme-switcher">
                <div
                  v-for="opt in themeOptions"
                  :key="opt.value"
                  :class="['theme-option', { 'theme-option--active': themeMode === opt.value }]"
                  @click="setThemeMode(opt.value)"
                >
                  <div :class="['theme-option__preview', `theme-option__preview--${opt.value}`]">
                    <div class="theme-option__preview-sidebar" />
                    <div class="theme-option__preview-body">
                      <div class="theme-option__preview-line" />
                      <div class="theme-option__preview-line theme-option__preview-line--short" />
                    </div>
                  </div>
                  <span class="theme-option__label">{{ opt.label }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-show="activeSection === 'sync'">
          <SyncSection
            v-model:server-url="serverUrl"
            v-model:auto-sync-enabled="autoSyncEnabled"
            v-model:sync-interval="syncInterval"
            :sync-status="syncStatus"
            :syncing="syncing"
            :conflicts="conflicts"
            :conflict-count="conflictCount"
            :sync-history="syncHistory"
            @sync-now="handleSyncNow"
            @connect="handleConnect"
            @auto-sync-toggle="handleAutoSyncToggle"
            @sync-interval-change="handleSyncIntervalChange"
            @resolve-conflict="handleResolveConflict"
            @resolve-all-conflicts="handleResolveAllConflicts"
            @load-conflicts="loadConflicts"
            @load-sync-history="loadSyncHistory"
          />
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

        <div v-show="activeSection === 'privacy'">
          <PrivacySection
            :client-privacy="clientPrivacy"
            :cloud-data-summary="cloudDataSummary"
            :cloud-data-loading="cloudDataLoading"
            :cloud-export-loading="cloudExportLoading"
            :cloud-delete-loading="cloudDeleteLoading"
            :cloud-table-label="cloudTableLabel"
            @cloud-data-summary="handleCloudDataSummary"
            @cloud-data-export="handleCloudDataExport"
            @show-privacy-policy="handleShowPrivacyPolicy"
            @cloud-data-deletion="handleCloudDataDeletion"
          />
        </div>

        <div v-show="activeSection === 'team'">
          <TeamSection
            v-model:invite-email="inviteEmail"
            v-model:invite-role="inviteRole"
            v-model:show-create-team-dialog="showCreateTeamDialog"
            :teams="teams"
            :teams-loading="teamsLoading"
            :current-team="currentTeam"
            :team-members="teamMembers"
            :inviting="inviting"
            :creating-team="creatingTeam"
            :create-team-form="createTeamForm"
            :team-role-label="teamRoleLabel"
            @fetch-teams="fetchTeams"
            @show-create-team="showCreateTeamDialog = true"
            @select-team="selectTeam"
            @delete-team="handleDeleteTeam"
            @remove-member="handleRemoveMember"
            @invite-member="handleInviteMember"
            @create-team="handleCreateTeam"
          />
        </div>

        <div v-show="activeSection === 'audit'">
          <AuditSection
            v-model:audit-page="auditPage"
            v-model:security-page="securityPage"
            v-model:audit-filter="auditFilter"
            v-model:security-filter="securityFilter"
            :audit-logs="auditLogs"
            :audit-loading="auditLoading"
            :audit-page-size="auditPageSize"
            :audit-total="auditTotal"
            :audit-action-tag-type="auditActionTagType"
            :security-logs="securityLogs"
            :security-loading="securityLoading"
            :security-page-size="securityPageSize"
            :security-total="securityTotal"
            :security-summary="securitySummary"
            @fetch-audit-logs="fetchAuditLogs"
            @fetch-security-logs="fetchSecurityLogs"
          />
        </div>

        <div v-show="activeSection === 'security'">
          <AuditSection
            v-model:audit-page="auditPage"
            v-model:security-page="securityPage"
            v-model:audit-filter="auditFilter"
            v-model:security-filter="securityFilter"
            :audit-logs="auditLogs"
            :audit-loading="auditLoading"
            :audit-page-size="auditPageSize"
            :audit-total="auditTotal"
            :audit-action-tag-type="auditActionTagType"
            :security-logs="securityLogs"
            :security-loading="securityLoading"
            :security-page-size="securityPageSize"
            :security-total="securityTotal"
            :security-summary="securitySummary"
            @fetch-audit-logs="fetchAuditLogs"
            @fetch-security-logs="fetchSecurityLogs"
          />
        </div>

        <div v-show="activeSection === 'logs'">
          <LogSection
            v-model:log-level="logLevel"
            v-model:log-dialog-visible="logDialogVisible"
            v-model:log-filter-level="logFilterLevel"
            v-model:log-filter-module="logFilterModule"
            v-model:log-search-query="logSearchQuery"
            v-model:log-auto-refresh="logAutoRefresh"
            :log-stats="logStats"
            :log-entries="logEntries"
            :log-uploading="logUploading"
            :log-modules="logModules"
            :log-level-counts="logLevelCounts"
            :filtered-log-entries="filteredLogEntries"
            :log-level-bar-width="logLevelBarWidth"
            @log-level-change="handleLogLevelChange"
            @view-logs="handleViewLogs"
            @export-logs="handleExportLogs"
            @upload-logs="handleUploadLogs"
            @clear-logs="handleClearLogs"
            @filter-log-entries="filterLogEntries"
            @load-recent-logs="loadRecentLogs"
            @toggle-log-auto-refresh="toggleLogAutoRefresh"
          />
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
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from "vue";
import { 
  User, Bell, Refresh, Cpu, Download, Folder, Document, Connection, 
  Lock, UserFilled, List, WarningFilled
} from "@element-plus/icons-vue";
import PageHeader from "../components/PageHeader.vue";
import AccountSection from "../components/settings/AccountSection.vue";
import SyncSection from "../components/settings/SyncSection.vue";
import PrivacySection from "../components/settings/PrivacySection.vue";
import TeamSection from "../components/settings/TeamSection.vue";
import AuditSection from "../components/settings/AuditSection.vue";
import LogSection from "../components/settings/LogSection.vue";
import { useSettingsData } from "../composables/useSettingsData";
import { useTheme, type ThemeMode } from "../composables/useTheme";

const { mode: themeMode, setMode: setThemeMode } = useTheme();

const themeOptions: { value: ThemeMode; label: string }[] = [
  { value: "light", label: "浅色" },
  { value: "dark", label: "深色" },
  { value: "system", label: "跟随系统" },
];

const {
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
  saveNotifySettings,
  refreshSyncStatus, loadConflicts,
  handleResolveConflict, handleResolveAllConflicts,
  handleSyncNow, loadSyncHistory, syncHistory,
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
  fetchSecurityLogs,
  handleCloudDataSummary, handleCloudDataExport, handleShowPrivacyPolicy, handleCloudDataDeletion,
  init, cleanup,
} = useSettingsData();

onMounted(() => { init(); });
onUnmounted(() => { cleanup(); });
</script>

<style scoped>
.settings-page { padding: 0; }
.settings-container { display: flex; gap: 0; background: var(--color-bg-card); border-radius: var(--radius-xl); box-shadow: var(--shadow-sm); border: 1px solid var(--color-border-light); overflow: hidden; min-height: calc(100vh - 140px); }
.settings-sidebar { width: 220px; background: var(--color-bg-page); border-right: 1px solid var(--color-border-light); padding: 16px 0; flex-shrink: 0; }
.settings-nav { display: flex; flex-direction: column; gap: 2px; }
.nav-item { display: flex; align-items: center; gap: 10px; padding: 10px 16px; cursor: pointer; transition: all 0.2s; color: var(--color-text-secondary); font-size: var(--text-sm); border-left: 3px solid transparent; }
.nav-item:hover { background: var(--color-bg-card); color: var(--color-text-primary); }
.nav-item.active { background: var(--color-bg-card); color: var(--color-primary); font-weight: 600; border-left-color: var(--color-primary); }
.nav-icon { font-size: 18px; }
.nav-label { flex: 1; }
.settings-content { flex: 1; padding: 32px; overflow-y: auto; }
.settings-section { max-width: 800px; }
.section-title { margin: 0 0 16px; font-size: var(--text-xl); font-weight: 600; color: var(--color-text-primary); }
.settings-card { background: var(--color-bg-card); border: 1px solid var(--color-border-light); border-radius: var(--radius-lg); padding: 20px; }
.setting-item { display: flex; justify-content: space-between; align-items: center; padding: 16px 0; }
.setting-info { flex: 1; }
.setting-title { margin: 0 0 4px; font-size: var(--text-sm); font-weight: 500; color: var(--color-text-primary); }
.setting-desc { margin: 0; font-size: var(--text-xs); color: var(--color-text-secondary); }
.setting-divider { height: 1px; background: var(--color-border-light); }
.modern-select { border-radius: var(--radius-base); }
.modern-input-number { border-radius: var(--radius-base); }
.modern-time-picker { border-radius: var(--radius-base); }
.quiet-hours-config { padding: 12px 0 0 0; }
.update-actions { display: flex; gap: 12px; align-items: center; padding-top: 16px; border-top: 1px solid var(--color-border-light); }
.update-status { display: flex; align-items: center; gap: 8px; }
.update-error { color: var(--color-danger); font-size: var(--text-xs); }
.cleanup-controls { display: flex; gap: 8px; align-items: center; }
.storage-info { display: flex; align-items: center; gap: 8px; }
.storage-size { font-size: var(--text-sm); font-weight: 600; color: var(--color-text-primary); }
.shortcuts-header, .shortcut-item { display: grid; grid-template-columns: 140px 1fr 60px 80px; gap: 16px; align-items: center; padding: 10px 0; border-bottom: 1px solid var(--color-border-light); }
.shortcuts-header { font-size: var(--text-xs); color: var(--color-text-secondary); font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
.shortcut-key { display: flex; align-items: center; }
.shortcut-input { width: 120px; }
.shortcut-label { font-size: var(--text-sm); color: var(--color-text-primary); }
.shortcut-actions { display: flex; gap: 4px; }
.shortcuts-footer { padding-top: 16px; display: flex; justify-content: flex-end; }
.theme-switcher { display: flex; gap: 12px; }
.theme-option { display: flex; flex-direction: column; align-items: center; gap: 8px; cursor: pointer; padding: 12px; border: 2px solid var(--color-border-light); border-radius: var(--radius-lg); transition: all 0.2s; }
.theme-option:hover { border-color: var(--color-primary-lighter); }
.theme-option--active { border-color: var(--color-primary); background: var(--color-primary-lightest); }
.theme-option__preview { width: 80px; height: 52px; border-radius: 6px; overflow: hidden; display: flex; }
.theme-option__preview--light { background: #F8FAFC; border: 1px solid #E2E8F0; }
.theme-option__preview--dark { background: #0F172A; border: 1px solid #334155; }
.theme-option__preview--system { background: linear-gradient(135deg, #F8FAFC 50%, #0F172A 50%); border: 1px solid #94A3B8; }
.theme-option__preview-sidebar { width: 20px; height: 100%; }
.theme-option__preview--light .theme-option__preview-sidebar { background: #1E1B4B; }
.theme-option__preview--dark .theme-option__preview-sidebar { background: #0F172A; border-right: 1px solid #334155; }
.theme-option__preview--system .theme-option__preview-sidebar { background: linear-gradient(180deg, #1E1B4B 50%, #0F172A 50%); }
.theme-option__preview-body { flex: 1; padding: 6px 4px; display: flex; flex-direction: column; gap: 4px; }
.theme-option__preview-line { height: 4px; border-radius: 2px; }
.theme-option__preview-line--short { width: 60%; }
.theme-option__preview--light .theme-option__preview-line { background: #CBD5E1; }
.theme-option__preview--dark .theme-option__preview-line { background: #475569; }
.theme-option__preview--system .theme-option__preview-line { background: linear-gradient(90deg, #CBD5E1 50%, #475569 50%); }
.theme-option__label { font-size: var(--text-xs); color: var(--color-text-secondary); font-weight: 500; }
.theme-option--active .theme-option__label { color: var(--color-primary); }
@media (max-width: 1024px) {
  .settings-container { flex-direction: column; }
  .settings-sidebar { width: 100%; border-right: none; border-bottom: 1px solid var(--color-border-light); }
  .settings-nav { flex-direction: row; overflow-x: auto; }
  .nav-item.active { border-left: none; border-bottom: 3px solid var(--color-primary); }
}
@media (max-width: 768px) {
  .settings-content { padding: 20px; }
  .shortcuts-header, .shortcut-item { grid-template-columns: 120px 1fr 60px 80px; gap: 12px; }
}
</style>
