<template>
  <div class="collect-center">
    <div class="page-toolbar">
      <h3>采集中心</h3>
      <div class="toolbar-actions">
        <el-tag v-if="wsConnected" type="success" size="small" effect="dark">
          <span class="ws-dot"></span> 实时连接
        </el-tag>
        <el-tag v-else type="info" size="small" effect="dark">离线</el-tag>
      </div>
    </div>

    <div class="client-banner">
      <div class="banner-content">
        <span class="banner-icon">⚡</span>
        <div class="banner-text">
          <strong>采集功能需使用桌面客户端</strong>
          <span>下载 XHS365 客户端，使用本地浏览器资源采集，更快更安全</span>
        </div>
      </div>
      <el-button type="primary" size="small">下载客户端</el-button>
    </div>

    <el-row :gutter="16" class="collect-stats">
      <el-col :span="6">
        <div class="mini-stat">
          <div class="mini-value">{{ taskStats.total }}</div>
          <div class="mini-label">总任务</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="mini-stat">
          <div class="mini-value" style="color: #6366f1;">{{ taskStats.running }}</div>
          <div class="mini-label">运行中</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="mini-stat">
          <div class="mini-value" style="color: #22c55e;">{{ taskStats.completed }}</div>
          <div class="mini-label">已完成</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="mini-stat">
          <div class="mini-value" style="color: #ef4444;">{{ taskStats.failed }}</div>
          <div class="mini-label">失败/风控</div>
        </div>
      </el-col>
    </el-row>

    <div class="filter-bar">
      <el-select v-model="filterStatus" placeholder="全部状态" clearable style="width: 130px" @change="fetchTasks">
        <el-option label="等待中" value="pending" />
        <el-option label="运行中" value="running" />
        <el-option label="已完成" value="completed" />
        <el-option label="失败" value="failed" />
        <el-option label="已取消" value="cancelled" />
        <el-option label="风控拦截" value="risk_detected" />
      </el-select>
      <el-select v-model="filterPlatform" placeholder="全部平台" clearable style="width: 130px" @change="fetchTasks">
        <el-option label="小红书" value="xhs" />
        <el-option label="淘宝" value="taobao" />
        <el-option label="京东" value="jd" />
        <el-option label="拼多多" value="pdd" />
        <el-option label="抖音" value="douyin" />
      </el-select>
    </div>

    <el-table :data="tasks" stripe v-loading="loading" empty-text="暂无采集任务" @row-click="openTaskDetail">
      <el-table-column prop="task_type" label="类型" width="80">
        <template #default="{ row }">
          <el-tag size="small">{{ taskTypeLabel(row.task_type) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="platform" label="平台" width="90">
        <template #default="{ row }">
          <span class="platform-badge" :style="{ borderColor: platformColors[row.platform] || '#6366f1' }">
            {{ platformIcons[row.platform] || '' }} {{ platformLabel(row.platform) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="target_type" label="目标" width="90">
        <template #default="{ row }">
          {{ targetTypeLabel(row.target_type) }}
        </template>
      </el-table-column>
      <el-table-column label="目标ID" min-width="200">
        <template #default="{ row }">
          <div class="target-cell">
            <span v-for="(tid, idx) in (row.target_ids || []).slice(0, 3)" :key="idx" class="target-chip">
              {{ tid.length > 20 ? tid.slice(0, 20) + '...' : tid }}
            </span>
            <span v-if="(row.target_ids || []).length > 3" class="target-more">
              +{{ row.target_ids.length - 3 }}
            </span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small" effect="dark">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="progress" label="进度" width="140">
        <template #default="{ row }">
          <div class="progress-cell">
            <el-progress
              :percentage="row.progress || 0"
              :stroke-width="6"
              :status="progressStatus(row)"
              :show-text="false"
            />
            <span class="progress-text">{{ row.progress || 0 }}%</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="160">
        <template #default="{ row }">
          {{ formatTime(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="80" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click.stop="openTaskDetail(row)">详情</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-bar" v-if="total > pageSize">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        @current-change="fetchTasks"
      />
    </div>

    <el-dialog v-model="detailVisible" title="任务详情" width="720px" destroy-on-close>
      <div v-if="detailLoading" style="text-align: center; padding: 30px;">
        <el-icon class="is-loading" :size="24"><Loading /></el-icon>
      </div>
      <template v-else-if="taskDetail">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="任务ID">
            <span class="mono-text">{{ taskDetail.id }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="类型">{{ taskTypeLabel(taskDetail.task_type) }}</el-descriptions-item>
          <el-descriptions-item label="平台">
            <span :style="{ color: platformColors[taskDetail.platform] }">
              {{ platformIcons[taskDetail.platform] }} {{ platformLabel(taskDetail.platform) }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusType(taskDetail.status)" size="small" effect="dark">{{ statusLabel(taskDetail.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="目标类型">{{ targetTypeLabel(taskDetail.target_type) }}</el-descriptions-item>
          <el-descriptions-item label="进度">
            <div class="progress-cell">
              <el-progress :percentage="taskDetail.progress || 0" :stroke-width="6" :status="detailProgressStatus" :show-text="false" style="flex:1" />
              <span class="progress-text">{{ taskDetail.progress || 0 }}%</span>
            </div>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatTime(taskDetail.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="完成时间">{{ formatTime(taskDetail.completed_at) }}</el-descriptions-item>
        </el-descriptions>

        <div v-if="taskDetail.result_summary" class="result-summary">
          <h4>采集结果</h4>
          <el-row :gutter="12">
            <el-col :span="6">
              <div class="rs-item success">
                <div class="rs-val">{{ taskDetail.result_summary.success || 0 }}</div>
                <div class="rs-lbl">成功</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="rs-item fail">
                <div class="rs-val">{{ taskDetail.result_summary.failed || 0 }}</div>
                <div class="rs-lbl">失败</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="rs-item risk">
                <div class="rs-val">{{ taskDetail.result_summary.risk_detected || 0 }}</div>
                <div class="rs-lbl">风控</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="rs-item total">
                <div class="rs-val">{{ taskDetail.result_summary.products_created || 0 }}</div>
                <div class="rs-lbl">入库商品</div>
              </div>
            </el-col>
          </el-row>
        </div>

        <div v-if="taskDetail.error_message" class="error-box">
          <h4>错误信息</h4>
          <p>{{ taskDetail.error_message }}</p>
        </div>

        <div v-if="taskDetail.items && taskDetail.items.length" class="items-section">
          <h4>采集明细 ({{ taskDetail.items.length }})</h4>
          <div class="item-cards">
            <div v-for="item in taskDetail.items" :key="item.id" class="item-card" :class="`item-card--${item.status}`">
              <div class="item-card-header">
                <span class="item-target-id">{{ item.target_id }}</span>
                <el-tag :type="statusType(item.status)" size="small">{{ statusLabel(item.status) }}</el-tag>
              </div>
              <div v-if="item.result && item.result.product_name" class="item-card-body">
                <div class="product-preview">
                  <img v-if="item.result.image_url" :src="item.result.image_url" class="product-thumb" @error="onImgError" />
                  <div class="product-info">
                    <div class="product-name">{{ item.result.product_name }}</div>
                    <div class="product-meta">
                      <span v-if="item.result.price" class="product-price">¥{{ item.result.price }}</span>
                      <span v-if="item.result.shop_name" class="product-shop">{{ item.result.shop_name }}</span>
                    </div>
                    <div class="product-stats-row">
                      <span v-if="item.result.sales_count != null">销量 {{ item.result.sales_count }}</span>
                      <span v-if="item.result.review_count != null">评论 {{ item.result.review_count }}</span>
                      <span v-if="item.result.favorite_count != null">收藏 {{ item.result.favorite_count }}</span>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else-if="item.error_message" class="item-card-error">
                {{ item.error_message }}
              </div>
            </div>
          </div>
        </div>
      </template>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <transition-group name="notify-slide" tag="div" class="risk-notifications">
      <div v-for="alert in riskAlerts" :key="alert.id" class="risk-alert" :class="`risk-alert--${alert.level}`">
        <div class="risk-alert-icon">
          <el-icon :size="18"><WarningFilled /></el-icon>
        </div>
        <div class="risk-alert-body">
          <div class="risk-alert-title">{{ alert.title }}</div>
          <div class="risk-alert-desc">{{ alert.desc }}</div>
        </div>
        <el-button size="small" text @click="dismissAlert(alert.id)">
          <el-icon><Close /></el-icon>
        </el-button>
      </div>
    </transition-group>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import api from "../../utils/api";
import { ElMessage } from "element-plus";
import { Loading, WarningFilled, Close } from "@element-plus/icons-vue";
import { useWebSocket } from "../../composables/useWebSocket";
import { PLATFORM_ICONS, PLATFORM_COLORS } from "../../utils/urlParser";

const platformIcons = PLATFORM_ICONS;
const platformColors = PLATFORM_COLORS;

const loading = ref(false);
const tasks = ref<any[]>([]);
const total = ref(0);
const currentPage = ref(1);
const pageSize = ref(20);
const filterStatus = ref("");
const filterPlatform = ref("");

const detailVisible = ref(false);
const detailLoading = ref(false);
const taskDetail = ref<any>(null);

const riskAlerts = ref<any[]>([]);

const { connected: wsConnected, on: wsOn, off: wsOff, connect: wsConnect } = useWebSocket();

const taskStats = computed(() => {
  const t = tasks.value.length;
  return {
    total: t,
    running: tasks.value.filter((x) => x.status === "running" || x.status === "pending").length,
    completed: tasks.value.filter((x) => x.status === "completed").length,
    failed: tasks.value.filter((x) => x.status === "failed" || x.status === "cancelled" || x.status === "risk_detected").length,
  };
});

const detailProgressStatus = computed(() => {
  if (!taskDetail.value) return undefined;
  if (taskDetail.value.status === "completed") return "success" as const;
  if (taskDetail.value.status === "failed") return "exception" as const;
  return undefined;
});

function taskTypeLabel(t: string) {
  const map: Record<string, string> = { product: "商品", shop: "店铺", category: "分类" };
  return map[t] || t;
}

function platformLabel(p: string) {
  const map: Record<string, string> = { xhs: "小红书", taobao: "淘宝", jd: "京东", pdd: "拼多多", douyin: "抖音" };
  return map[p] || p;
}

function targetTypeLabel(t: string) {
  const map: Record<string, string> = { product_id: "商品ID", shop_id: "店铺ID", category_url: "分类URL" };
  return map[t] || t;
}

function statusType(s: string) {
  const map: Record<string, string> = {
    pending: "warning", running: "primary", completed: "success",
    failed: "danger", cancelled: "info", risk_detected: "warning",
  };
  return map[s] || "info";
}

function statusLabel(s: string) {
  const map: Record<string, string> = {
    pending: "等待中", running: "运行中", completed: "已完成",
    failed: "失败", cancelled: "已取消", risk_detected: "风控拦截",
  };
  return map[s] || s;
}

function progressStatus(row: any) {
  if (row.status === "completed") return "success" as const;
  if (row.status === "failed") return "exception" as const;
  return undefined;
}

function formatTime(t: string | null) {
  if (!t) return "—";
  const d = new Date(t);
  return d.toLocaleString("zh-CN", { hour12: false });
}

function onImgError(e: Event) {
  const img = e.target as HTMLImageElement;
  img.style.display = "none";
}

function addRiskAlert(title: string, desc: string, level: string = "high") {
  const id = Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  riskAlerts.value.push({ id, title, desc, level });
  if (riskAlerts.value.length > 5) {
    riskAlerts.value.shift();
  }
  setTimeout(() => {
    dismissAlert(id);
  }, 15000);
}

function dismissAlert(id: string) {
  riskAlerts.value = riskAlerts.value.filter((a) => a.id !== id);
}

function handleWSProgress(data: any) {
  if (!data?.task_id) return;
  const idx = tasks.value.findIndex((t) => t.id === data.task_id);
  if (idx >= 0) {
    tasks.value[idx] = { ...tasks.value[idx], ...data, progress: data.progress ?? tasks.value[idx].progress };
  }
}

function handleWSCompleted(data: any) {
  if (!data?.task_id) return;
  const idx = tasks.value.findIndex((t) => t.id === data.task_id);
  if (idx >= 0) {
    tasks.value[idx] = {
      ...tasks.value[idx],
      status: "completed",
      progress: 100,
      result_summary: data.summary,
    };
  }
  if (data.summary) {
    const s = data.summary;
    ElMessage.success(`采集完成：成功 ${s.success || 0}，失败 ${s.failed || 0}，入库 ${s.products_created || 0}`);
  }
}

function handleWSRiskAlert(data: any) {
  addRiskAlert(
    `风控告警 - ${platformLabel(data.platform || '')}`,
    `${data.risk_type || '未知风险'}：${data.detail?.message || '请检查采集策略'}`,
    data.risk_level === "critical" ? "critical" : "high"
  );
  fetchTasks();
}

let pollTimer: ReturnType<typeof setInterval> | null = null;

async function fetchTasks() {
  loading.value = true;
  try {
    const params: any = { page: currentPage.value, page_size: pageSize.value };
    if (filterStatus.value) params.status = filterStatus.value;
    if (filterPlatform.value) params.platform = filterPlatform.value;
    const { data } = await api.get("/collect/tasks", { params });
    tasks.value = data?.data?.items || [];
    total.value = data?.data?.total || 0;
  } catch {
    ElMessage.error("获取采集任务失败");
  } finally {
    loading.value = false;
  }
}

async function openTaskDetail(row: any) {
  detailVisible.value = true;
  detailLoading.value = true;
  taskDetail.value = null;
  try {
    const { data } = await api.get(`/collect/tasks/${row.id}`);
    taskDetail.value = data?.data || null;
  } catch {
    ElMessage.error("获取任务详情失败");
  } finally {
    detailLoading.value = false;
  }
}

function refreshRunningTasks() {
  const hasRunning = tasks.value.some((t) => t.status === "running" || t.status === "pending");
  if (hasRunning) {
    fetchTasks();
  }
}

onMounted(() => {
  fetchTasks();
  wsConnect();
  wsOn("collect:progress", handleWSProgress);
  wsOn("collect:completed", handleWSCompleted);
  wsOn("collect:risk_alert", handleWSRiskAlert);
  pollTimer = setInterval(refreshRunningTasks, 10000);
});

onUnmounted(() => {
  wsOff("collect:progress", handleWSProgress);
  wsOff("collect:completed", handleWSCompleted);
  wsOff("collect:risk_alert", handleWSRiskAlert);
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
});
</script>

<style scoped>
.collect-center {
  padding: 4px;
}

.client-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.12), rgba(139, 92, 246, 0.08));
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: 12px;
  padding: 14px 20px;
  margin-bottom: 20px;
}

.banner-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.banner-icon {
  font-size: 24px;
}

.banner-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.banner-text strong {
  color: #fff;
  font-size: 14px;
}

.banner-text span {
  color: #8a8a9a;
  font-size: 12px;
}

.page-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.page-toolbar h3 {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  margin: 0;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ws-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #22c55e;
  margin-right: 4px;
  animation: pulse-dot 2s infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.collect-stats {
  margin-bottom: 20px;
}

.mini-stat {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  padding: 16px;
  text-align: center;
}

.mini-value {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
}

.mini-label {
  font-size: 13px;
  color: #6a6a7a;
  margin-top: 4px;
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.platform-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid;
  border-left-width: 3px;
}

.target-cell {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
}

.target-chip {
  font-size: 11px;
  color: #b0b0c0;
  background: rgba(255, 255, 255, 0.04);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
}

.target-more {
  font-size: 11px;
  color: #6366f1;
  padding: 2px 4px;
}

.progress-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-text {
  font-size: 12px;
  color: #8a8a9a;
  min-width: 32px;
  text-align: right;
}

.pagination-bar {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.create-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.url-input-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.section-label {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #e0e0e6;
}

.section-hint {
  font-size: 12px;
  color: #6a6a7a;
  font-weight: 400;
}

.parsed-preview {
  background: rgba(99, 102, 241, 0.06);
  border: 1px solid rgba(99, 102, 241, 0.15);
  border-radius: 8px;
  padding: 12px;
  margin-top: 8px;
}

.parsed-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 13px;
  color: #a5b4fc;
}

.parsed-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 200px;
  overflow-y: auto;
}

.parsed-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  padding: 4px 8px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 4px;
}

.parsed-platform {
  font-weight: 600;
  min-width: 70px;
}

.parsed-type {
  color: #8a8a9a;
  min-width: 60px;
}

.parsed-id {
  color: #b0b0c0;
  font-family: monospace;
  font-size: 11px;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-item label {
  font-size: 13px;
  color: #8a8a9a;
}

.result-summary {
  margin-top: 20px;
}

.result-summary h4 {
  font-size: 14px;
  color: #e0e0e6;
  margin: 0 0 12px;
}

.rs-item {
  text-align: center;
  padding: 12px 8px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.03);
}

.rs-item.success { border-left: 3px solid #22c55e; }
.rs-item.fail { border-left: 3px solid #ef4444; }
.rs-item.risk { border-left: 3px solid #f59e0b; }
.rs-item.total { border-left: 3px solid #6366f1; }

.rs-val {
  font-size: 22px;
  font-weight: 700;
  color: #fff;
}

.rs-lbl {
  font-size: 12px;
  color: #6a6a7a;
  margin-top: 2px;
}

.error-box {
  margin-top: 16px;
  padding: 12px;
  background: rgba(239, 68, 68, 0.06);
  border: 1px solid rgba(239, 68, 68, 0.15);
  border-radius: 8px;
}

.error-box h4 {
  font-size: 14px;
  color: #fca5a5;
  margin: 0 0 8px;
}

.error-box p {
  font-size: 13px;
  color: #e0e0e6;
  margin: 0;
  word-break: break-all;
}

.items-section {
  margin-top: 20px;
}

.items-section h4 {
  font-size: 14px;
  color: #e0e0e6;
  margin: 0 0 12px;
}

.item-cards {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 400px;
  overflow-y: auto;
}

.item-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 12px;
  transition: border-color 0.2s;
}

.item-card--completed { border-left: 3px solid #22c55e; }
.item-card--failed { border-left: 3px solid #ef4444; }
.item-card--risk_detected { border-left: 3px solid #f59e0b; }
.item-card--pending { border-left: 3px solid #6366f1; }
.item-card--running { border-left: 3px solid #6366f1; }

.item-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.item-target-id {
  font-size: 12px;
  font-family: monospace;
  color: #8a8a9a;
}

.item-card-body {
  margin-top: 4px;
}

.product-preview {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.product-thumb {
  width: 56px;
  height: 56px;
  border-radius: 6px;
  object-fit: cover;
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.04);
}

.product-info {
  flex: 1;
  min-width: 0;
}

.product-name {
  font-size: 13px;
  color: #e0e0e6;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.product-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.product-price {
  font-size: 14px;
  font-weight: 700;
  color: #ef4444;
}

.product-shop {
  font-size: 12px;
  color: #8a8a9a;
}

.product-stats-row {
  display: flex;
  gap: 12px;
  margin-top: 4px;
  font-size: 11px;
  color: #6a6a7a;
}

.item-card-error {
  font-size: 12px;
  color: #fca5a5;
  margin-top: 4px;
}

.mono-text {
  font-family: monospace;
  font-size: 12px;
}

.risk-notifications {
  position: fixed;
  top: 80px;
  right: 24px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 380px;
}

.risk-alert {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 16px;
  border-radius: 10px;
  background: #1a1a24;
  border: 1px solid rgba(245, 158, 11, 0.3);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
  animation: slide-in 0.3s ease-out;
}

.risk-alert--critical {
  border-color: rgba(239, 68, 68, 0.5);
  background: rgba(239, 68, 68, 0.08);
}

.risk-alert--high {
  border-color: rgba(245, 158, 11, 0.4);
  background: rgba(245, 158, 11, 0.06);
}

.risk-alert-icon {
  color: #f59e0b;
  margin-top: 1px;
  flex-shrink: 0;
}

.risk-alert--critical .risk-alert-icon {
  color: #ef4444;
}

.risk-alert-body {
  flex: 1;
  min-width: 0;
}

.risk-alert-title {
  font-size: 13px;
  font-weight: 600;
  color: #e0e0e6;
}

.risk-alert-desc {
  font-size: 12px;
  color: #8a8a9a;
  margin-top: 2px;
}

.notify-slide-enter-active {
  animation: slide-in 0.3s ease-out;
}

.notify-slide-leave-active {
  animation: slide-out 0.2s ease-in;
}

@keyframes slide-in {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

@keyframes slide-out {
  from { transform: translateX(0); opacity: 1; }
  to { transform: translateX(100%); opacity: 0; }
}
</style>
