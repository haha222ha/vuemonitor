<template>
  <div class="settings-section">
    <h2 class="section-title">日志管理</h2>
    <div class="settings-card">
      <div class="setting-item">
        <div class="setting-info">
          <h3 class="setting-title">日志级别</h3>
          <p class="setting-desc">设置应用日志记录的详细程度</p>
        </div>
        <el-select v-model="logLevelModel" class="modern-select" @change="$emit('log-level-change')">
          <el-option value="debug" label="Debug (调试)" />
          <el-option value="info" label="Info (信息)" />
          <el-option value="warn" label="Warn (警告)" />
          <el-option value="error" label="Error (错误)" />
        </el-select>
      </div>

      <div class="log-stats-grid">
        <div class="log-stat-item">
          <span class="log-stat-label">会话ID</span>
          <code class="log-stat-value audit-id">{{ logStats.sessionId || '-' }}</code>
        </div>
        <div class="log-stat-item">
          <span class="log-stat-label">日志文件数</span>
          <span class="log-stat-value">{{ logStats.logFiles }}</span>
        </div>
        <div class="log-stat-item">
          <span class="log-stat-label">缓冲区</span>
          <span class="log-stat-value">{{ logStats.bufferSize }}</span>
        </div>
        <div class="log-stat-item">
          <span class="log-stat-label">上传队列</span>
          <span class="log-stat-value">{{ logStats.uploadQueueSize }}</span>
        </div>
      </div>

      <div class="log-actions">
        <el-button @click="$emit('view-logs')">查看日志</el-button>
        <el-button @click="$emit('export-logs', 'json')">导出 JSON</el-button>
        <el-button @click="$emit('export-logs', 'text')">导出文本</el-button>
        <el-button @click="$emit('upload-logs')" :loading="logUploading">上传日志</el-button>
        <el-button type="danger" @click="$emit('clear-logs')">清除日志</el-button>
      </div>
    </div>

    <el-dialog v-model="logDialogVisibleModel" title="应用日志" width="80%" top="5vh" class="modern-dialog">
      <div class="log-dialog-toolbar">
        <el-select v-model="logFilterLevelModel" placeholder="级别" clearable style="width: 100px" @change="$emit('filter-log-entries')">
          <el-option value="debug" label="Debug" />
          <el-option value="info" label="Info" />
          <el-option value="warn" label="Warn" />
          <el-option value="error" label="Error" />
        </el-select>
        <el-select v-model="logFilterModuleModel" placeholder="模块" clearable style="width: 160px" @change="$emit('filter-log-entries')">
          <el-option v-for="mod in logModules" :key="mod" :value="mod" :label="mod" />
        </el-select>
        <el-input v-model="logSearchQueryModel" placeholder="搜索日志..." clearable style="width: 200px" />
        <el-switch v-model="logAutoRefreshModel" active-text="自动刷新" @change="$emit('toggle-log-auto-refresh', $event)" />
        <el-button @click="$emit('load-recent-logs')">刷新</el-button>
      </div>

      <div class="log-level-bars">
        <div class="log-level-bar">
          <span class="bar-label">Debug</span>
          <div class="bar-track"><div class="bar-fill bar-fill--debug" :style="{ width: logLevelBarWidth(logLevelCounts.debug) }"></div></div>
          <span class="bar-count">{{ logLevelCounts.debug }}</span>
        </div>
        <div class="log-level-bar">
          <span class="bar-label">Info</span>
          <div class="bar-track"><div class="bar-fill bar-fill--info" :style="{ width: logLevelBarWidth(logLevelCounts.info) }"></div></div>
          <span class="bar-count">{{ logLevelCounts.info }}</span>
        </div>
        <div class="log-level-bar">
          <span class="bar-label">Warn</span>
          <div class="bar-track"><div class="bar-fill bar-fill--warn" :style="{ width: logLevelBarWidth(logLevelCounts.warn) }"></div></div>
          <span class="bar-count">{{ logLevelCounts.warn }}</span>
        </div>
        <div class="log-level-bar">
          <span class="bar-label">Error</span>
          <div class="bar-track"><div class="bar-fill bar-fill--error" :style="{ width: logLevelBarWidth(logLevelCounts.error) }"></div></div>
          <span class="bar-count">{{ logLevelCounts.error }}</span>
        </div>
      </div>

      <div class="log-entries-container">
        <div v-for="(entry, idx) in filteredLogEntries" :key="idx" class="log-entry" :class="`log-entry--${(entry as any).level}`">
          <span class="log-entry__time">{{ (entry as any).timestamp }}</span>
          <el-tag size="small" :type="logEntryTagType((entry as any).level)">{{ (entry as any).level }}</el-tag>
          <span class="log-entry__module">{{ (entry as any).module }}</span>
          <span class="log-entry__message">{{ (entry as any).message }}</span>
          <span v-if="(entry as any).error" class="log-entry__error">{{ (entry as any).error }}</span>
        </div>
        <div v-if="filteredLogEntries.length === 0" class="log-empty">暂无日志记录</div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  logLevel: string;
  logStats: any;
  logDialogVisible: boolean;
  logEntries: any[];
  logFilterLevel: string;
  logFilterModule: string;
  logSearchQuery: string;
  logAutoRefresh: boolean;
  logUploading: boolean;
  logModules: string[];
  logLevelCounts: { debug: number; info: number; warn: number; error: number; total: number };
  filteredLogEntries: any[];
  logLevelBarWidth: (count: number) => string;
}>();

const emit = defineEmits<{
  'log-level-change': [];
  'view-logs': [];
  'export-logs': [format: string];
  'upload-logs': [];
  'clear-logs': [];
  'filter-log-entries': [];
  'load-recent-logs': [];
  'toggle-log-auto-refresh': [on: boolean];
  'update:logLevel': [value: string];
  'update:logDialogVisible': [value: boolean];
  'update:logFilterLevel': [value: string];
  'update:logFilterModule': [value: string];
  'update:logSearchQuery': [value: string];
  'update:logAutoRefresh': [value: boolean];
}>();

const logLevelModel = computed({
  get: () => props.logLevel,
  set: (v: string) => emit('update:logLevel', v),
});
const logDialogVisibleModel = computed({
  get: () => props.logDialogVisible,
  set: (v: boolean) => emit('update:logDialogVisible', v),
});
const logFilterLevelModel = computed({
  get: () => props.logFilterLevel,
  set: (v: string) => emit('update:logFilterLevel', v),
});
const logFilterModuleModel = computed({
  get: () => props.logFilterModule,
  set: (v: string) => emit('update:logFilterModule', v),
});
const logSearchQueryModel = computed({
  get: () => props.logSearchQuery,
  set: (v: string) => emit('update:logSearchQuery', v),
});
const logAutoRefreshModel = computed({
  get: () => props.logAutoRefresh,
  set: (v: boolean) => emit('update:logAutoRefresh', v),
});

function logEntryTagType(level: string): "" | "success" | "warning" | "danger" | "info" {
  const map: Record<string, "" | "success" | "warning" | "danger" | "info"> = {
    debug: "info", info: "success", warn: "warning", error: "danger", fatal: "danger",
  };
  return map[level] || "info";
}
</script>

<style scoped>
.settings-section { max-width: 800px; }
.section-title { margin: 0 0 16px; font-size: var(--text-xl); font-weight: 600; color: var(--color-text-primary); }
.settings-card { background: var(--color-bg-card); border: 1px solid var(--color-border-light); border-radius: var(--radius-lg); padding: 20px; }
.setting-item { display: flex; justify-content: space-between; align-items: center; padding: 16px 0; }
.setting-info { flex: 1; }
.setting-title { margin: 0 0 4px; font-size: var(--text-sm); font-weight: 500; color: var(--color-text-primary); }
.setting-desc { margin: 0; font-size: var(--text-xs); color: var(--color-text-secondary); }
.modern-select { border-radius: var(--radius-base); }
.log-stats-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; padding: 16px; background: var(--color-bg-page); border-radius: var(--radius-lg); margin: 16px 0; }
.log-stat-item { display: flex; flex-direction: column; gap: 4px; }
.log-stat-label { font-size: var(--text-xs); color: var(--color-text-secondary); }
.log-stat-value { font-size: var(--text-sm); color: var(--color-text-primary); }
.audit-id { font-family: monospace; font-size: var(--text-xs); background: var(--color-bg-page); padding: 2px 6px; border-radius: var(--radius-sm); color: var(--color-text-secondary); }
.log-actions { display: flex; gap: 8px; flex-wrap: wrap; padding-top: 16px; border-top: 1px solid var(--color-border-light); }
.log-dialog-toolbar { display: flex; gap: 8px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }
.log-level-bars { display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px; padding: 12px; background: var(--color-bg-page); border-radius: var(--radius-base); }
.log-level-bar { display: flex; align-items: center; gap: 8px; }
.bar-label { font-size: 11px; color: var(--color-text-secondary); min-width: 40px; }
.bar-track { flex: 1; height: 6px; background: var(--color-bg-card); border-radius: 3px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 3px; transition: width 0.3s; }
.bar-fill--debug { background: #909399; }
.bar-fill--info { background: var(--color-primary); }
.bar-fill--warn { background: var(--color-warning); }
.bar-fill--error { background: var(--color-danger); }
.bar-count { font-size: 11px; color: var(--color-text-secondary); min-width: 30px; text-align: right; }
.log-entries-container { max-height: 500px; overflow-y: auto; font-family: monospace; font-size: 12px; }
.log-entry { display: flex; align-items: flex-start; gap: 8px; padding: 6px 8px; border-bottom: 1px solid var(--color-border-light); }
.log-entry--error { background: rgba(245, 108, 108, 0.05); }
.log-entry--warn { background: rgba(230, 162, 60, 0.05); }
.log-entry__time { color: var(--color-text-tertiary); font-size: 11px; white-space: nowrap; }
.log-entry__module { color: var(--color-primary); font-size: 11px; min-width: 80px; }
.log-entry__message { flex: 1; color: var(--color-text-primary); word-break: break-all; }
.log-entry__error { color: var(--color-danger); font-size: 11px; }
.log-empty { text-align: center; padding: 32px 0; color: var(--color-text-secondary); }
.modern-dialog :deep(.el-dialog__header) { padding: 20px 24px; border-bottom: 1px solid var(--color-border-light); margin-right: 0; }
.modern-dialog :deep(.el-dialog__title) { font-size: var(--text-lg); font-weight: 600; color: var(--color-text-primary); }
.modern-dialog :deep(.el-dialog__body) { padding: 24px; }
</style>
