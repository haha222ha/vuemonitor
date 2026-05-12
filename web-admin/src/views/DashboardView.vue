<template>
  <div>
    <h2>管理仪表盘</h2>
    <el-row :gutter="16" style="margin-bottom: 20px">
      <el-col :span="6">
        <el-card shadow="hover"><el-statistic title="总用户数" :value="store.stats.totalUsers" /></el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover"><el-statistic title="活跃用户" :value="store.stats.activeUsers" /></el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover"><el-statistic title="今日采集任务" :value="store.stats.todayTasks" /></el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover"><el-statistic title="可用代理" :value="store.stats.availableProxies" /></el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-bottom: 20px">
      <el-col :span="6">
        <el-card shadow="hover"><el-statistic title="监控商品总数" :value="store.stats.monitoredProducts" /></el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover"><el-statistic title="今日API请求" :value="store.stats.todayApiRequests" /></el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover"><el-statistic title="系统健康度(%)" :value="store.stats.healthScore" :precision="1" /></el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover"><el-statistic title="告警待处理" :value="store.stats.pendingAlerts" /></el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-bottom: 24px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>7日采集趋势</span></template>
          <div class="bar-chart">
            <div v-for="(day, idx) in store.weeklyTrend" :key="idx" class="bar-row">
              <span class="bar-label">{{ day.label }}</span>
              <div class="bar-track">
                <div class="bar-fill" :style="{ width: day.percentage + '%' }"></div>
              </div>
              <span class="bar-value">{{ day.value }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header><span>平台分布</span></template>
          <div class="bar-chart">
            <div v-for="(plat, idx) in store.platformDist" :key="idx" class="bar-row">
              <span class="bar-label">{{ plat.label }}</span>
              <div class="bar-track">
                <div class="bar-fill" :style="{ width: plat.percentage + '%', background: platColor(idx) }"></div>
              </div>
              <span class="bar-value">{{ plat.count }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <h3>最近操作</h3>
    <el-table :data="recentActions" stripe v-loading="actionsLoading" max-height="320">
      <el-table-column prop="operator" label="操作人" width="120" />
      <el-table-column prop="action" label="操作" width="160" />
      <el-table-column prop="target" label="对象" min-width="200" show-overflow-tooltip />
      <el-table-column prop="ip" label="IP" width="140" />
      <el-table-column prop="created_at" label="时间" width="180" />
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { useDashboardStore } from "../stores/dashboard";
import { useAuditLogsStore } from "../stores/auditLogs";

const store = useDashboardStore();
const auditLogsStore = useAuditLogsStore();

const recentActions = ref<any[]>([]);
const actionsLoading = ref(false);

function platColor(idx: number): string {
  const colors = ["#f56c6c", "#409eff", "#e6a23c", "#67c23a", "#909399"];
  return colors[idx % colors.length];
}

async function fetchRecentActions() {
  actionsLoading.value = true;
  try {
    await auditLogsStore.fetchLogs(1, 10);
    recentActions.value = auditLogsStore.logs;
  } catch { /* non-critical */ }
  finally { actionsLoading.value = false; }
}

onMounted(() => {
  store.fetchStats();
  store.fetchWeeklyTrend();
  store.fetchPlatformDist();
  fetchRecentActions();
});
</script>

<style scoped>
.bar-chart {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.bar-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.bar-label {
  width: 60px;
  font-size: 13px;
  color: #606266;
  text-align: right;
  flex-shrink: 0;
}
.bar-track {
  flex: 1;
  height: 18px;
  background: #f0f2f5;
  border-radius: 3px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  background: #409eff;
  border-radius: 3px;
  transition: width 0.5s ease;
}
.bar-value {
  width: 60px;
  font-size: 13px;
  color: #909399;
  flex-shrink: 0;
}
</style>
