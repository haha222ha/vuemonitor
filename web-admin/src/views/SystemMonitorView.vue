<template>
  <div>
    <h2>系统监控</h2>
    <el-row :gutter="16" style="margin-bottom: 20px">
      <el-col :span="6">
        <el-card shadow="hover">
          <div style="text-align: center">
            <div style="font-size: 13px; color: #909399; margin-bottom: 8px">CPU使用率</div>
            <el-progress type="circle" :percentage="store.metrics.cpuUsage" :width="80" :color="progressColor(store.metrics.cpuUsage)" />
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div style="text-align: center">
            <div style="font-size: 13px; color: #909399; margin-bottom: 8px">内存使用率</div>
            <el-progress type="circle" :percentage="store.metrics.memoryUsage" :width="80" :color="progressColor(store.metrics.memoryUsage)" />
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div style="text-align: center">
            <div style="font-size: 13px; color: #909399; margin-bottom: 8px">磁盘使用率</div>
            <el-progress type="circle" :percentage="store.metrics.diskUsage" :width="80" :color="progressColor(store.metrics.diskUsage)" />
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="活跃WebSocket连接" :value="store.metrics.activeWsConnections" />
        </el-card>
      </el-col>
    </el-row>
    <el-row :gutter="16" style="margin-bottom: 24px">
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="今日API请求数" :value="store.metrics.todayApiRequests" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="今日采集任务数" :value="store.metrics.todayCollectTasks" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="平均响应时间(ms)" :value="store.metrics.avgResponseTimeMs" :precision="1" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="错误率(%)" :value="store.metrics.errorRate" :precision="2" />
        </el-card>
      </el-col>
    </el-row>

    <h3>最近系统事件</h3>
    <el-table :data="store.events" stripe v-loading="store.eventsLoading">
      <el-table-column prop="type" label="类型" width="140" />
      <el-table-column prop="message" label="消息" min-width="250" show-overflow-tooltip />
      <el-table-column prop="severity" label="严重程度" width="100">
        <template #default="{ row }">
          <el-tag :type="severityType(row.severity)">{{ row.severity }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="时间" width="180" />
    </el-table>
    <el-pagination
      v-model:current-page="eventsPage"
      :page-size="20"
      :total="store.eventsTotal"
      layout="prev, pager, next"
      style="margin-top: 16px; justify-content: flex-end"
      @current-change="fetchEvents"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { ElMessage } from "element-plus";
import { useSystemMonitorStore } from "../stores/systemMonitor";

const store = useSystemMonitorStore();

const eventsPage = ref(1);
let refreshTimer: ReturnType<typeof setInterval> | null = null;

function progressColor(value: number): string {
  if (value > 90) return "#f56c6c";
  if (value > 70) return "#e6a23c";
  return "#67c23a";
}

function severityType(s: string): string {
  const map: Record<string, string> = { critical: "danger", high: "danger", medium: "warning", low: "info", info: "info" };
  return map[s] || "info";
}

async function fetchMetrics() {
  try {
    await store.fetchMetrics();
  } catch {
    ElMessage.error("获取系统指标失败");
  }
}

async function fetchEvents() {
  try {
    await store.fetchEvents(eventsPage.value);
  } catch {
    ElMessage.error("获取系统事件失败");
  }
}

onMounted(() => {
  fetchMetrics();
  fetchEvents();
  refreshTimer = setInterval(fetchMetrics, 30000);
});

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer);
});
</script>
