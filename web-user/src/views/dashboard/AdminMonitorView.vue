<template>
  <div class="admin-monitor">
    <div class="monitor-header">
      <h2>系统监控</h2>
      <div class="monitor-actions">
        <el-select v-model="refreshInterval" size="small" style="width: 140px" @change="setupAutoRefresh">
          <el-option :value="0" label="手动刷新" />
          <el-option :value="5" label="5秒刷新" />
          <el-option :value="15" label="15秒刷新" />
          <el-option :value="30" label="30秒刷新" />
          <el-option :value="60" label="60秒刷新" />
        </el-select>
        <el-button size="small" :icon="Refresh" @click="refreshAll" :loading="refreshing">刷新</el-button>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="monitor-tabs">
      <el-tab-pane label="系统概览" name="system">
        <div class="metrics-grid" v-if="systemData">
          <div class="metric-card metric-card--cpu">
            <div class="metric-card__header">
              <span class="metric-card__label">CPU</span>
              <el-tag :type="systemData.cpu.percent > 80 ? 'danger' : systemData.cpu.percent > 60 ? 'warning' : 'success'" size="small" effect="dark">
                {{ systemData.cpu.percent }}%
              </el-tag>
            </div>
            <div class="metric-progress">
              <el-progress :percentage="systemData.cpu.percent" :color="progressColor(systemData.cpu.percent)" :stroke-width="12" :show-text="false" />
            </div>
            <div class="metric-details">
              <span>核心数: {{ systemData.cpu.count }}</span>
              <span v-if="systemData.cpu.load_avg">负载: {{ systemData.cpu.load_avg.map((v: number) => v.toFixed(2)).join(' / ') }}</span>
            </div>
          </div>

          <div class="metric-card metric-card--memory">
            <div class="metric-card__header">
              <span class="metric-card__label">内存</span>
              <el-tag :type="systemData.memory.percent > 85 ? 'danger' : systemData.memory.percent > 70 ? 'warning' : 'success'" size="small" effect="dark">
                {{ systemData.memory.percent }}%
              </el-tag>
            </div>
            <div class="metric-progress">
              <el-progress :percentage="systemData.memory.percent" :color="progressColor(systemData.memory.percent)" :stroke-width="12" :show-text="false" />
            </div>
            <div class="metric-details">
              <span>已用: {{ systemData.memory.used_gb }} GB</span>
              <span>可用: {{ systemData.memory.available_gb }} GB</span>
              <span>总计: {{ systemData.memory.total_gb }} GB</span>
            </div>
          </div>

          <div class="metric-card metric-card--disk">
            <div class="metric-card__header">
              <span class="metric-card__label">磁盘</span>
              <el-tag :type="systemData.disk.percent > 90 ? 'danger' : systemData.disk.percent > 75 ? 'warning' : 'success'" size="small" effect="dark">
                {{ systemData.disk.percent }}%
              </el-tag>
            </div>
            <div class="metric-progress">
              <el-progress :percentage="systemData.disk.percent" :color="progressColor(systemData.disk.percent)" :stroke-width="12" :show-text="false" />
            </div>
            <div class="metric-details">
              <span>已用: {{ systemData.disk.used_gb }} GB</span>
              <span>可用: {{ systemData.disk.free_gb }} GB</span>
              <span>总计: {{ systemData.disk.total_gb }} GB</span>
            </div>
          </div>

          <div class="metric-card metric-card--uptime">
            <div class="metric-card__header">
              <span class="metric-card__label">运行时间</span>
            </div>
            <div class="metric-big-value">{{ formatUptime(systemData.uptime_seconds) }}</div>
            <div class="metric-details">
              <span>进程数: {{ systemData.processes }}</span>
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无系统数据" />
      </el-tab-pane>

      <el-tab-pane label="采集性能" name="performance">
        <div class="perf-section" v-if="perfData">
          <el-row :gutter="16">
            <el-col :span="6">
              <div class="perf-stat-card">
                <div class="perf-stat-value">{{ perfData.last_hour.total_tasks }}</div>
                <div class="perf-stat-label">1小时任务数</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="perf-stat-card perf-stat-card--success">
                <div class="perf-stat-value">{{ perfData.last_hour.success_tasks }}</div>
                <div class="perf-stat-label">成功任务</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="perf-stat-card perf-stat-card--danger">
                <div class="perf-stat-value">{{ perfData.last_hour.failed_tasks }}</div>
                <div class="perf-stat-label">失败任务</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="perf-stat-card perf-stat-card--warning">
                <div class="perf-stat-value">{{ perfData.last_hour.error_rate }}%</div>
                <div class="perf-stat-label">错误率</div>
              </div>
            </el-col>
          </el-row>

          <el-row :gutter="16" style="margin-top: 16px">
            <el-col :span="6">
              <div class="perf-stat-card">
                <div class="perf-stat-value">{{ perfData.last_hour.qps }}</div>
                <div class="perf-stat-label">QPS</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="perf-stat-card">
                <div class="perf-stat-value">{{ perfData.last_24h.total_tasks }}</div>
                <div class="perf-stat-label">24小时任务数</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="perf-stat-card perf-stat-card--success">
                <div class="perf-stat-value">{{ perfData.last_24h.success_rate }}%</div>
                <div class="perf-stat-label">24h成功率</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="perf-stat-card">
                <div class="perf-stat-value">{{ perfData.active_tasks }}</div>
                <div class="perf-stat-label">运行中</div>
              </div>
            </el-col>
          </el-row>

          <div class="perf-chart-section">
            <h3 class="section-subtitle">任务状态分布</h3>
            <div class="task-status-bars">
              <div class="status-bar-item">
                <span class="status-bar-label">运行中</span>
                <div class="status-bar-track">
                  <div class="status-bar-fill status-bar-fill--running" :style="{ width: taskBarWidth(perfData.active_tasks) }" />
                </div>
                <span class="status-bar-value">{{ perfData.active_tasks }}</span>
              </div>
              <div class="status-bar-item">
                <span class="status-bar-label">等待中</span>
                <div class="status-bar-track">
                  <div class="status-bar-fill status-bar-fill--pending" :style="{ width: taskBarWidth(perfData.pending_tasks) }" />
                </div>
                <span class="status-bar-value">{{ perfData.pending_tasks }}</span>
              </div>
              <div class="status-bar-item">
                <span class="status-bar-label">1h成功</span>
                <div class="status-bar-track">
                  <div class="status-bar-fill status-bar-fill--success" :style="{ width: taskBarWidth(perfData.last_hour.success_tasks) }" />
                </div>
                <span class="status-bar-value">{{ perfData.last_hour.success_tasks }}</span>
              </div>
              <div class="status-bar-item">
                <span class="status-bar-label">1h失败</span>
                <div class="status-bar-track">
                  <div class="status-bar-fill status-bar-fill--failed" :style="{ width: taskBarWidth(perfData.last_hour.failed_tasks) }" />
                </div>
                <span class="status-bar-value">{{ perfData.last_hour.failed_tasks }}</span>
              </div>
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无性能数据" />
      </el-tab-pane>

      <el-tab-pane label="基础设施" name="infrastructure">
        <div class="infra-section" v-if="infraData">
          <el-row :gutter="16">
            <el-col :span="12">
              <div class="infra-card" :class="{ 'infra-card--healthy': infraData.database.status === 'healthy', 'infra-card--unhealthy': infraData.database.status !== 'healthy' }">
                <div class="infra-card__header">
                  <h3>PostgreSQL</h3>
                  <el-tag :type="infraData.database.status === 'healthy' ? 'success' : 'danger'" effect="dark" size="small">
                    {{ infraData.database.status === 'healthy' ? '正常' : '异常' }}
                  </el-tag>
                </div>
                <div class="infra-card__body">
                  <div class="infra-metric">
                    <span class="infra-metric__label">连接池大小</span>
                    <span class="infra-metric__value">{{ infraData.database.pool_size }}</span>
                  </div>
                  <div class="infra-metric">
                    <span class="infra-metric__label">已使用连接</span>
                    <span class="infra-metric__value">{{ infraData.database.checked_out }}</span>
                  </div>
                  <div class="infra-metric">
                    <span class="infra-metric__label">可用连接</span>
                    <span class="infra-metric__value">{{ infraData.database.available }}</span>
                  </div>
                  <div class="infra-pool-bar">
                    <el-progress
                      :percentage="infraData.database.pool_size > 0 ? Math.round(infraData.database.checked_out / infraData.database.pool_size * 100) : 0"
                      :color="infraData.database.pool_size > 0 && infraData.database.checked_out / infraData.database.pool_size > 0.8 ? '#F56C6C' : '#67C23A'"
                      :stroke-width="8"
                    />
                  </div>
                </div>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="infra-card" :class="{ 'infra-card--healthy': infraData.redis.status === 'healthy', 'infra-card--unhealthy': infraData.redis.status !== 'healthy' }">
                <div class="infra-card__header">
                  <h3>Redis</h3>
                  <el-tag :type="infraData.redis.status === 'healthy' ? 'success' : 'danger'" effect="dark" size="small">
                    {{ infraData.redis.status === 'healthy' ? '正常' : '异常' }}
                  </el-tag>
                </div>
                <div class="infra-card__body">
                  <div class="infra-metric" v-if="infraData.redis.used_memory_human">
                    <span class="infra-metric__label">内存使用</span>
                    <span class="infra-metric__value">{{ infraData.redis.used_memory_human }}</span>
                  </div>
                  <div class="infra-metric" v-if="infraData.redis.connected_clients !== undefined">
                    <span class="infra-metric__label">连接客户端</span>
                    <span class="infra-metric__value">{{ infraData.redis.connected_clients }}</span>
                  </div>
                  <div class="infra-metric" v-if="infraData.redis.uptime_in_seconds">
                    <span class="infra-metric__label">运行时间</span>
                    <span class="infra-metric__value">{{ formatUptime(infraData.redis.uptime_in_seconds) }}</span>
                  </div>
                  <div class="infra-metric" v-if="infraData.redis.total_commands_processed">
                    <span class="infra-metric__label">累计命令</span>
                    <span class="infra-metric__value">{{ Number(infraData.redis.total_commands_processed).toLocaleString() }}</span>
                  </div>
                </div>
              </div>
            </el-col>
          </el-row>
        </div>
        <el-empty v-else description="暂无基础设施数据" />
      </el-tab-pane>

      <el-tab-pane label="风控统计" name="risk">
        <div class="risk-section" v-if="riskData">
          <el-row :gutter="16">
            <el-col :span="8">
              <div class="risk-summary-card">
                <div class="risk-summary-value">{{ riskData.last_24h.total }}</div>
                <div class="risk-summary-label">24小时风控事件</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="risk-summary-card risk-summary-card--week">
                <div class="risk-summary-value">{{ riskData.last_7d.total }}</div>
                <div class="risk-summary-label">7天风控事件</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="risk-summary-card risk-summary-card--types">
                <div class="risk-summary-value">{{ Object.keys(riskData.last_24h.by_type).length }}</div>
                <div class="risk-summary-label">风控类型数</div>
              </div>
            </el-col>
          </el-row>

          <el-row :gutter="16" style="margin-top: 16px">
            <el-col :span="12">
              <div class="risk-detail-card">
                <h3 class="section-subtitle">按类型分布 (24h)</h3>
                <div class="risk-bars">
                  <div v-for="(count, type) in riskData.last_24h.by_type" :key="type" class="risk-bar-item">
                    <span class="risk-bar-label">{{ riskTypeLabel(type as string) }}</span>
                    <div class="risk-bar-track">
                      <div class="risk-bar-fill" :style="{ width: riskBarWidth(count as number) }" />
                    </div>
                    <span class="risk-bar-value">{{ count }}</span>
                  </div>
                  <el-empty v-if="Object.keys(riskData.last_24h.by_type).length === 0" :image-size="60" description="暂无数据" />
                </div>
              </div>
            </el-col>
            <el-col :span="12">
              <div class="risk-detail-card">
                <h3 class="section-subtitle">按级别分布 (7天)</h3>
                <div class="risk-bars">
                  <div v-for="(count, level) in riskData.last_7d.by_level" :key="level" class="risk-bar-item">
                    <span class="risk-bar-label">{{ riskLevelLabel(level as string) }}</span>
                    <div class="risk-bar-track">
                      <div class="risk-bar-fill" :class="'risk-bar-fill--' + level" :style="{ width: riskBarWidth(count as number) }" />
                    </div>
                    <span class="risk-bar-value">{{ count }}</span>
                  </div>
                  <el-empty v-if="Object.keys(riskData.last_7d.by_level).length === 0" :image-size="60" description="暂无数据" />
                </div>
              </div>
            </el-col>
          </el-row>

          <div class="risk-detail-card" style="margin-top: 16px" v-if="Object.keys(riskData.last_24h.by_platform).length > 0">
            <h3 class="section-subtitle">按平台分布 (24h)</h3>
            <div class="risk-platforms">
              <el-tag v-for="(count, platform) in riskData.last_24h.by_platform" :key="platform" :type="platformTagType(platform as string)" effect="light" size="large" class="risk-platform-tag">
                {{ platformLabel(platform as string) }}: {{ count }}
              </el-tag>
            </div>
          </div>
        </div>
        <el-empty v-else description="暂无风控数据" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { Refresh } from "@element-plus/icons-vue";
import api from "../../utils/api";

const activeTab = ref("system");
const refreshing = ref(false);
const refreshInterval = ref(15);
let refreshTimer: ReturnType<typeof setInterval> | null = null;

const systemData = ref<any>(null);
const perfData = ref<any>(null);
const infraData = ref<any>(null);
const riskData = ref<any>(null);

function progressColor(pct: number): string {
  if (pct > 85) return "#F56C6C";
  if (pct > 65) return "#E6A23C";
  return "#67C23A";
}

function formatUptime(seconds: number): string {
  if (!seconds) return "-";
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d > 0) return `${d}天 ${h}小时`;
  if (h > 0) return `${h}小时 ${m}分钟`;
  return `${m}分钟`;
}

function taskBarWidth(value: number): string {
  if (!perfData.value) return "0%";
  const max = Math.max(
    perfData.value.active_tasks || 0,
    perfData.value.pending_tasks || 0,
    perfData.value.last_hour?.success_tasks || 0,
    perfData.value.last_hour?.failed_tasks || 0,
    1
  );
  return `${Math.min((value / max) * 100, 100)}%`;
}

function riskTypeLabel(type: string): string {
  const map: Record<string, string> = {
    captcha: "验证码",
    rate_limit: "频率限制",
    ip_block: "IP封锁",
    account_ban: "账号封禁",
    fingerprint: "指纹检测",
    behavior: "行为检测",
    unknown: "未知",
  };
  return map[type] || type;
}

function riskLevelLabel(level: string): string {
  const map: Record<string, string> = { low: "低", medium: "中", high: "高", critical: "严重" };
  return map[level] || level;
}

function riskBarWidth(count: number): string {
  if (!riskData.value) return "0%";
  const allCounts = [
    ...Object.values(riskData.value.last_24h.by_type || {}),
    ...Object.values(riskData.value.last_7d.by_level || {}),
  ] as number[];
  const max = Math.max(...allCounts, 1);
  return `${Math.min((count / max) * 100, 100)}%`;
}

function platformLabel(p: string): string {
  const map: Record<string, string> = { xhs: "小红书", taobao: "淘宝", jd: "京东", pdd: "拼多多", douyin: "抖音" };
  return map[p] || p;
}

function platformTagType(p: string): string {
  const map: Record<string, string> = { xhs: "danger", taobao: "warning", jd: "primary", pdd: "success", douyin: "" };
  return map[p] || "info";
}

async function fetchSystem() {
  try {
    const { data } = await api.get("/admin/monitoring/system");
    systemData.value = data?.data || data;
  } catch {
    systemData.value = null;
  }
}

async function fetchPerformance() {
  try {
    const { data } = await api.get("/admin/monitoring/performance");
    perfData.value = data?.data || data;
  } catch {
    perfData.value = null;
  }
}

async function fetchInfrastructure() {
  try {
    const { data } = await api.get("/admin/monitoring/infrastructure");
    infraData.value = data?.data || data;
  } catch {
    infraData.value = null;
  }
}

async function fetchRisk() {
  try {
    const { data } = await api.get("/admin/monitoring/risk-stats");
    riskData.value = data?.data || data;
  } catch {
    riskData.value = null;
  }
}

async function refreshAll() {
  refreshing.value = true;
  await Promise.allSettled([fetchSystem(), fetchPerformance(), fetchInfrastructure(), fetchRisk()]);
  refreshing.value = false;
}

function setupAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
  if (refreshInterval.value > 0) {
    refreshTimer = setInterval(refreshAll, refreshInterval.value * 1000);
  }
}

onMounted(() => {
  refreshAll();
  setupAutoRefresh();
});

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
});
</script>

<style scoped>
.admin-monitor {
  padding: 0;
}

.monitor-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.monitor-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 0;
}

.monitor-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.monitor-tabs :deep(.el-tabs__item) {
  font-size: 14px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.metric-card {
  background: var(--el-bg-color-overlay);
  border-radius: 12px;
  padding: 20px;
  border: 1px solid var(--el-border-color-lighter);
  transition: box-shadow 0.2s;
}

.metric-card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.metric-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.metric-card__label {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-regular);
}

.metric-progress {
  margin-bottom: 12px;
}

.metric-details {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.metric-big-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  margin: 8px 0 12px;
}

.perf-section {
  padding: 4px 0;
}

.perf-stat-card {
  background: var(--el-bg-color-overlay);
  border-radius: 10px;
  padding: 20px;
  text-align: center;
  border: 1px solid var(--el-border-color-lighter);
}

.perf-stat-card--success .perf-stat-value { color: #67C23A; }
.perf-stat-card--danger .perf-stat-value { color: #F56C6C; }
.perf-stat-card--warning .perf-stat-value { color: #E6A23C; }

.perf-stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  line-height: 1.2;
}

.perf-stat-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}

.perf-chart-section {
  margin-top: 20px;
  background: var(--el-bg-color-overlay);
  border-radius: 10px;
  padding: 20px;
  border: 1px solid var(--el-border-color-lighter);
}

.section-subtitle {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 0 0 16px;
}

.task-status-bars,
.risk-bars {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.status-bar-item,
.risk-bar-item {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-bar-label,
.risk-bar-label {
  width: 60px;
  font-size: 13px;
  color: var(--el-text-color-regular);
  flex-shrink: 0;
}

.status-bar-track,
.risk-bar-track {
  flex: 1;
  height: 8px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
  overflow: hidden;
}

.status-bar-fill,
.risk-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.4s ease;
  background: var(--el-color-primary);
}

.status-bar-fill--running { background: #67C23A; }
.status-bar-fill--pending { background: #E6A23C; }
.status-bar-fill--success { background: #67C23A; }
.status-bar-fill--failed { background: #F56C6C; }

.risk-bar-fill--low { background: #67C23A; }
.risk-bar-fill--medium { background: #E6A23C; }
.risk-bar-fill--high { background: #F56C6C; }
.risk-bar-fill--critical { background: #F56C6C; }

.status-bar-value,
.risk-bar-value {
  width: 40px;
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  text-align: right;
}

.infra-section {
  padding: 4px 0;
}

.infra-card {
  background: var(--el-bg-color-overlay);
  border-radius: 12px;
  padding: 20px;
  border: 1px solid var(--el-border-color-lighter);
  border-left: 4px solid var(--el-border-color-lighter);
}

.infra-card--healthy { border-left-color: #67C23A; }
.infra-card--unhealthy { border-left-color: #F56C6C; }

.infra-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.infra-card__header h3 {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
  color: var(--el-text-color-primary);
}

.infra-card__body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.infra-metric {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.infra-metric__label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.infra-metric__value {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.infra-pool-bar {
  margin-top: 4px;
}

.risk-section {
  padding: 4px 0;
}

.risk-summary-card {
  background: var(--el-bg-color-overlay);
  border-radius: 10px;
  padding: 24px;
  text-align: center;
  border: 1px solid var(--el-border-color-lighter);
  border-top: 3px solid var(--el-color-primary);
}

.risk-summary-card--week { border-top-color: #E6A23C; }
.risk-summary-card--types { border-top-color: #67C23A; }

.risk-summary-value {
  font-size: 32px;
  font-weight: 700;
  color: var(--el-text-color-primary);
}

.risk-summary-label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}

.risk-detail-card {
  background: var(--el-bg-color-overlay);
  border-radius: 10px;
  padding: 20px;
  border: 1px solid var(--el-border-color-lighter);
}

.risk-platforms {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.risk-platform-tag {
  font-size: 14px;
}
</style>
