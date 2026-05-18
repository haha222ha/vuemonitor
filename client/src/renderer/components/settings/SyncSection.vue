<template>
  <div class="settings-section">
    <h2 class="section-title">数据同步</h2>
    <div class="settings-card">
      <div class="sync-status-header">
        <div class="sync-status">
          <el-tag :type="syncStatus.isSyncing ? 'warning' : 'success'" effect="dark">
            <el-icon v-if="syncStatus.isSyncing" class="sync-pulse"><Loading /></el-icon>
            {{ syncStatus.isSyncing ? "同步中..." : "空闲" }}
          </el-tag>
        </div>
        <el-button type="primary" :loading="syncing" @click="$emit('sync-now')">立即同步</el-button>
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
        <el-input v-model="serverUrlModel" placeholder="https://api.xhs365.com" class="modern-input" />
        <el-button type="primary" @click="$emit('connect')">连接</el-button>
      </div>

      <div class="auto-sync-config">
        <div class="setting-item">
          <div class="setting-info">
            <h3 class="setting-title">自动同步</h3>
            <p class="setting-desc">定期自动同步数据到服务器</p>
          </div>
          <el-switch v-model="autoSyncEnabledModel" @change="$emit('auto-sync-toggle')" />
        </div>
        <div v-if="autoSyncEnabledModel" class="sync-frequency">
          <span class="frequency-label">同步频率</span>
          <el-select v-model="syncIntervalModel" class="modern-select" @change="$emit('sync-interval-change')">
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
        <template #title>检测到 {{ conflictCount }} 条数据同步冲突</template>
      </el-alert>
      <div class="conflict-list">
        <div v-for="conflict in conflicts.slice(0, 3)" :key="conflict.id" class="conflict-item">
          <el-tag size="small" :type="conflict.type === 'product' ? 'primary' : 'success'">
            {{ conflict.type === 'product' ? '商品' : '特征' }}
          </el-tag>
          <div class="conflict-actions">
            <el-button size="small" @click="$emit('resolve-conflict', conflict.id, 'local_wins')">保留本地</el-button>
            <el-button size="small" type="success" @click="$emit('resolve-conflict', conflict.id, 'server_wins')">采用服务器</el-button>
          </div>
        </div>
      </div>
      <div class="conflict-footer">
        <el-button size="small" @click="$emit('resolve-all-conflicts', 'server_wins')">全部采用服务器</el-button>
        <el-button size="small" @click="$emit('load-conflicts')">刷新</el-button>
      </div>
    </div>

    <div class="settings-card" style="margin-top: 20px">
      <div class="sync-history-header">
        <h3 class="section-subtitle">同步历史</h3>
        <el-button text size="small" @click="$emit('load-sync-history')">刷新</el-button>
      </div>
      <div v-if="syncHistory.length > 0" class="sync-timeline">
        <div v-for="record in syncHistory" :key="record.id" class="sync-timeline__item">
          <div class="sync-timeline__dot" :class="`sync-timeline__dot--${record.status}`"></div>
          <div class="sync-timeline__content">
            <div class="sync-timeline__row">
              <span class="sync-timeline__action">{{ record.action === 'push' ? '推送' : record.action === 'pull' ? '拉取' : '同步' }}</span>
              <el-tag size="small" :type="record.status === 'success' ? 'success' : record.status === 'failed' ? 'danger' : 'warning'">
                {{ record.status === 'success' ? '成功' : record.status === 'failed' ? '失败' : '冲突' }}
              </el-tag>
            </div>
            <div class="sync-timeline__detail">
              <span v-if="record.pushed > 0">推送 {{ record.pushed }} 条</span>
              <span v-if="record.pulled > 0">拉取 {{ record.pulled }} 条</span>
              <span v-if="record.errors > 0" class="sync-timeline__error">{{ record.errors }} 错误</span>
            </div>
            <div class="sync-timeline__time">{{ formatSyncTime(record.timestamp) }}</div>
          </div>
        </div>
      </div>
      <div v-else class="sync-history-empty">暂无同步记录</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Loading } from "@element-plus/icons-vue";

const props = defineProps<{
  syncStatus: any;
  syncing: boolean;
  serverUrl: string;
  autoSyncEnabled: boolean;
  syncInterval: number;
  conflicts: any[];
  conflictCount: number;
  syncHistory: any[];
}>();

const emit = defineEmits<{
  'sync-now': [];
  'connect': [];
  'auto-sync-toggle': [];
  'sync-interval-change': [];
  'resolve-conflict': [id: string, resolution: string];
  'resolve-all-conflicts': [resolution: string];
  'load-conflicts': [];
  'load-sync-history': [];
  'update:serverUrl': [value: string];
  'update:autoSyncEnabled': [value: boolean];
  'update:syncInterval': [value: number];
}>();

const serverUrlModel = computed({
  get: () => props.serverUrl,
  set: (v: string) => emit('update:serverUrl', v),
});
const autoSyncEnabledModel = computed({
  get: () => props.autoSyncEnabled,
  set: (v: boolean) => emit('update:autoSyncEnabled', v),
});
const syncIntervalModel = computed({
  get: () => props.syncInterval,
  set: (v: number) => emit('update:syncInterval', v),
});

import { computed } from "vue";

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
  } catch { return ts; }
}
</script>

<style scoped>
.settings-section { max-width: 800px; }
.section-title { margin: 0 0 16px; font-size: var(--text-xl); font-weight: 600; color: var(--color-text-primary); }
.section-subtitle { margin: 0 0 16px; font-size: var(--text-base); font-weight: 600; color: var(--color-text-primary); }
.settings-card { background: var(--color-bg-card); border: 1px solid var(--color-border-light); border-radius: var(--radius-lg); padding: 20px; }
.sync-status-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.sync-pulse { animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
.sync-stats { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 20px; padding: 16px; background: var(--color-bg-page); border-radius: var(--radius-lg); }
.stat-item { display: flex; flex-direction: column; gap: 4px; }
.stat-label { font-size: var(--text-xs); color: var(--color-text-secondary); }
.stat-value { font-size: var(--text-sm); color: var(--color-text-primary); }
.server-config { display: flex; gap: 12px; margin-bottom: 20px; }
.modern-input { flex: 1; border-radius: var(--radius-base); }
.modern-select { border-radius: var(--radius-base); }
.auto-sync-config { padding-top: 16px; border-top: 1px solid var(--color-border-light); }
.setting-item { display: flex; justify-content: space-between; align-items: center; padding: 16px 0; }
.setting-info { flex: 1; }
.setting-title { margin: 0 0 4px; font-size: var(--text-sm); font-weight: 500; color: var(--color-text-primary); }
.setting-desc { margin: 0; font-size: var(--text-xs); color: var(--color-text-secondary); }
.sync-frequency { display: flex; align-items: center; gap: 12px; padding-top: 12px; }
.frequency-label { font-size: var(--text-sm); color: var(--color-text-secondary); }
.conflict-card { margin-top: 20px; border-color: var(--color-danger-light); }
.conflict-list { display: flex; flex-direction: column; gap: 12px; margin-top: 16px; }
.conflict-item { display: flex; justify-content: space-between; align-items: center; padding: 12px; background: var(--color-danger-bg); border-radius: var(--radius-base); }
.conflict-actions { display: flex; gap: 8px; }
.conflict-footer { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--color-border-light); }
.sync-history-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.sync-timeline { display: flex; flex-direction: column; gap: 0; position: relative; padding-left: 20px; }
.sync-timeline::before { content: ""; position: absolute; left: 6px; top: 8px; bottom: 8px; width: 2px; background: var(--color-border-light); }
.sync-timeline__item { display: flex; gap: 12px; padding: 10px 0; position: relative; }
.sync-timeline__dot { width: 12px; height: 12px; border-radius: 50%; position: absolute; left: -20px; top: 14px; border: 2px solid var(--color-bg-card); z-index: 1; }
.sync-timeline__dot--success { background: var(--color-success); }
.sync-timeline__dot--failed { background: var(--color-danger); }
.sync-timeline__dot--conflict { background: var(--color-warning); }
.sync-timeline__content { flex: 1; }
.sync-timeline__row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.sync-timeline__action { font-size: var(--text-sm); font-weight: 600; color: var(--color-text-primary); }
.sync-timeline__detail { display: flex; gap: 12px; font-size: var(--text-xs); color: var(--color-text-secondary); margin-bottom: 2px; }
.sync-timeline__error { color: var(--color-danger); }
.sync-timeline__time { font-size: var(--text-xs); color: var(--color-text-tertiary); }
.sync-history-empty { text-align: center; padding: 24px 0; color: var(--color-text-secondary); font-size: var(--text-sm); }
</style>
