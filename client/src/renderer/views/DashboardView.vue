<template>
  <div>
    <h2>仪表盘</h2>
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="监控商品" :value="productStore.productCount" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="活跃采集" :value="collectStore.status.activeCount" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="队列任务" :value="collectStore.status.queueLength" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="定时任务" :value="schedulerStore.state.activeTasks" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card>
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span>采集状态</span>
              <el-tag :type="collectStore.isCollecting ? 'success' : 'info'" size="small">
                {{ collectStore.isCollecting ? '采集中' : '空闲' }}
              </el-tag>
            </div>
          </template>
          <div style="display: flex; flex-direction: column; gap: 12px">
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span style="color: #909399; font-size: 13px">并发数</span>
              <div style="display: flex; align-items: center; gap: 8px">
                <el-slider v-model="concurrency" :min="1" :max="10" style="width: 150px" @change="handleConcurrencyChange" />
                <span style="font-size: 14px; font-weight: 500">{{ concurrency }}</span>
              </div>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span style="color: #909399; font-size: 13px">内存使用</span>
              <span style="font-size: 14px; font-weight: 500">{{ collectStore.status.resourceUsage.memoryMB }} MB</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span style="color: #909399; font-size: 13px">当前套餐</span>
              <el-tag size="small">{{ planLabels[permissionStore.plan] || permissionStore.plan }}</el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header><span>风控警报</span></template>
          <div v-if="collectStore.riskAlerts.length === 0" style="text-align: center; color: #909399; padding: 20px">
            暂无风控警报
          </div>
          <div v-else>
            <div v-for="alert in collectStore.riskAlerts.slice(0, 5)" :key="alert.taskId" style="padding: 8px 0; border-bottom: 1px solid #ebeef5">
              <div style="display: flex; justify-content: space-between">
                <span style="font-size: 13px">{{ alert.targetId }}</span>
                <span style="color: #f56c6c; font-size: 12px">{{ alert.error }}</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center">
              <span>最近采集结果</span>
              <el-button size="small" @click="collectStore.clearResults()">清空</el-button>
            </div>
          </template>
          <el-table :data="collectStore.results.slice(0, 10)" stripe max-height="300">
            <el-table-column prop="targetId" label="商品ID" width="200" />
            <el-table-column prop="status" label="状态" width="120">
              <template #default="{ row }">
                <el-tag :type="statusTagType(row.status)" size="small">{{ statusLabels[row.status] || row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="collectedAt" label="时间" width="180">
              <template #default="{ row }">{{ formatDate(row.collectedAt) }}</template>
            </el-table-column>
            <el-table-column prop="error" label="错误" min-width="200" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { useProductStore } from "../stores/product";
import { useCollectStore } from "../stores/collect";
import { useSchedulerStore } from "../stores/scheduler";
import { usePermissionStore } from "../stores/permission";

const productStore = useProductStore();
const collectStore = useCollectStore();
const schedulerStore = useSchedulerStore();
const permissionStore = usePermissionStore();

const concurrency = ref(collectStore.status.concurrency);

const planLabels: Record<string, string> = { free: "免费版", pro: "专业版", premium: "高级版", enterprise: "企业版" };
const statusLabels: Record<string, string> = { success: "成功", failed: "失败", risk_detected: "风控" };
const statusTagType: Record<string, string> = { success: "success", failed: "danger", risk_detected: "warning" };

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")}`;
}

async function handleConcurrencyChange(val: number) {
  await collectStore.setConcurrency(val);
}

let refreshTimer: ReturnType<typeof setInterval> | null = null;

onMounted(() => {
  productStore.fetchProducts();
  collectStore.setupListeners();
  collectStore.fetchStatus();
  schedulerStore.fetchState();
  permissionStore.fetchPermissions();

  refreshTimer = setInterval(() => {
    collectStore.fetchStatus();
    schedulerStore.fetchState();
  }, 5000);
});

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer);
  }
});
</script>
