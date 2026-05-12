<template>
  <div class="notifications-page">
    <div class="page-header">
      <h2>通知中心</h2>
      <div class="header-actions">
        <el-radio-group v-model="sourceFilter" size="small">
          <el-radio-button value="all">全部</el-radio-button>
          <el-radio-button value="cloud">云端</el-radio-button>
          <el-radio-button value="local">本地</el-radio-button>
        </el-radio-group>
        <el-button size="small" @click="markAllRead" :disabled="unreadCount === 0">全部已读</el-button>
        <el-button size="small" type="danger" plain @click="deleteRead" :disabled="readCount === 0">删除已读</el-button>
      </div>
    </div>

    <el-card shadow="never" class="notifications-card">
      <div class="filter-bar">
        <el-input v-model="searchQuery" placeholder="搜索通知..." prefix-icon="Search" clearable size="small" style="width: 240px" />
        <el-select v-model="typeFilter" size="small" clearable placeholder="类型筛选" style="width: 140px">
          <el-option label="价格变动" value="price_change" />
          <el-option label="销量变动" value="sales_change" />
          <el-option label="风控警报" value="risk_alert" />
          <el-option label="系统通知" value="system" />
          <el-option label="AI分析" value="ai_analysis" />
        </el-select>
      </div>

      <div v-if="loading" class="loading-state">
        <el-skeleton :rows="5" animated />
      </div>

      <div v-else-if="filteredNotifications.length === 0" class="empty-state">
        <el-empty description="暂无通知" />
      </div>

      <div v-else class="notification-list">
        <div
          v-for="n in filteredNotifications"
          :key="n.id"
          :class="['notification-item', { 'is-unread': !n.is_read }]"
        >
          <div class="notification-icon" :style="{ background: getTypeColor(n.type) }">
            <el-icon :size="16"><component :is="getTypeIcon(n.type)" /></el-icon>
          </div>
          <div class="notification-body" @click="handleClick(n)">
            <div class="notification-header">
              <span class="notification-title">{{ n.title }}</span>
              <el-tag v-if="n.source === 'local'" size="small" type="info">本地</el-tag>
              <el-tag v-else size="small" type="success">云端</el-tag>
            </div>
            <div class="notification-content">{{ n.content }}</div>
            <div class="notification-footer">
              <span class="notification-time">{{ timeAgo(n.created_at) }}</span>
              <div class="notification-actions">
                <el-button v-if="!n.is_read" link type="primary" size="small" @click.stop="markRead(n)">标为已读</el-button>
                <el-button link type="danger" size="small" @click.stop="deleteOne(n)">删除</el-button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="hasMore" class="load-more">
        <el-button link type="primary" @click="loadMore" :loading="loadingMore">加载更多</el-button>
      </div>

      <div class="pagination-bar">
        <span class="total-text">共 {{ total }} 条通知，{{ unreadCount }} 条未读</span>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { ElMessage } from "element-plus";
import { Bell, TrendCharts, Warning, InfoFilled, MagicStick } from "@element-plus/icons-vue";
import api from "../../utils/api";
import { useWebSocket } from "../../composables/useWebSocket";

interface Notification {
  id: string;
  title: string;
  content: string;
  type: string;
  source: string;
  is_read: boolean;
  related_type?: string;
  related_id?: string;
  created_at: string;
}

const notifications = ref<Notification[]>([]);
const loading = ref(false);
const loadingMore = ref(false);
const total = ref(0);
const unreadCount = ref(0);
const page = ref(1);
const pageSize = 30;
const searchQuery = ref("");
const sourceFilter = ref("all");
const typeFilter = ref("");
let pollTimer: ReturnType<typeof setInterval> | null = null;

const { on: wsOn, off: wsOff, connect: wsConnect } = useWebSocket();

const readCount = computed(() => notifications.value.filter((n) => n.is_read).length);

const hasMore = computed(() => notifications.value.length < total.value);

const filteredNotifications = computed(() => {
  let result = notifications.value;
  if (sourceFilter.value !== "all") {
    result = result.filter((n) => n.source === sourceFilter.value);
  }
  if (typeFilter.value) {
    result = result.filter((n) => n.type === typeFilter.value);
  }
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase();
    result = result.filter(
      (n) => n.title.toLowerCase().includes(q) || n.content.toLowerCase().includes(q)
    );
  }
  return result;
});

function getTypeColor(type: string) {
  const map: Record<string, string> = {
    price_change: "#f97316",
    sales_change: "#6366f1",
    risk_alert: "#ef4444",
    system: "#22c55e",
    ai_analysis: "#8b5cf6",
  };
  return map[type] || "#6366f1";
}

function getTypeIcon(type: string) {
  const map: Record<string, any> = {
    price_change: TrendCharts,
    sales_change: TrendCharts,
    risk_alert: Warning,
    system: InfoFilled,
    ai_analysis: MagicStick,
  };
  return map[type] || Bell;
}

function timeAgo(dateStr: string) {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes}分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}小时前`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}天前`;
  return new Date(dateStr).toLocaleDateString();
}

async function fetchNotifications(append = false) {
  if (append) {
    loadingMore.value = true;
  } else {
    loading.value = true;
  }
  try {
    const { data } = await api.get("/notifications", {
      params: { page: page.value, page_size: pageSize },
    });
    const items = data?.data?.items || [];
    if (append) {
      notifications.value = [...notifications.value, ...items];
    } else {
      notifications.value = items;
    }
    total.value = data?.data?.total || 0;
  } catch {
    if (!append) notifications.value = [];
  } finally {
    loading.value = false;
    loadingMore.value = false;
  }
}

async function fetchUnreadCount() {
  try {
    const { data } = await api.get("/notifications/unread-count");
    unreadCount.value = data?.data?.unread_count || 0;
  } catch {}
}

async function markRead(n: Notification) {
  try {
    await api.put(`/notifications/${n.id}/read`);
    n.is_read = true;
    unreadCount.value = Math.max(0, unreadCount.value - 1);
  } catch {
    ElMessage.error("操作失败");
  }
}

async function markAllRead() {
  try {
    await api.put("/notifications/read-all");
    notifications.value.forEach((n) => (n.is_read = true));
    unreadCount.value = 0;
    ElMessage.success("已全部标为已读");
  } catch {
    ElMessage.error("操作失败");
  }
}

async function deleteOne(n: Notification) {
  try {
    await api.delete(`/notifications/${n.id}`);
    notifications.value = notifications.value.filter((item) => item.id !== n.id);
    total.value = Math.max(0, total.value - 1);
    if (!n.is_read) unreadCount.value = Math.max(0, unreadCount.value - 1);
  } catch {
    ElMessage.error("删除失败");
  }
}

async function deleteRead() {
  try {
    const readIds = notifications.value.filter((n) => n.is_read).map((n) => n.id);
    for (const id of readIds) {
      await api.delete(`/notifications/${id}`);
    }
    notifications.value = notifications.value.filter((n) => !n.is_read);
    total.value = notifications.value.length;
    ElMessage.success("已删除已读通知");
  } catch {
    ElMessage.error("操作失败");
  }
}

function handleClick(n: Notification) {
  if (!n.is_read) markRead(n);
}

function loadMore() {
  page.value++;
  fetchNotifications(true);
}

function onWsNotification() {
  fetchNotifications();
  fetchUnreadCount();
}

onMounted(() => {
  fetchNotifications();
  fetchUnreadCount();
  wsConnect();
  wsOn("monitor:triggered", onWsNotification);
  wsOn("notification:new", onWsNotification);
  pollTimer = setInterval(() => {
    fetchUnreadCount();
  }, 60000);
});

onUnmounted(() => {
  wsOff("monitor:triggered", onWsNotification);
  wsOff("notification:new", onWsNotification);
  if (pollTimer) clearInterval(pollTimer);
});
</script>

<style scoped>
.notifications-page {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  color: #e0e0e6;
  font-size: 20px;
  margin: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.notifications-card {
  background: #1a1a24;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.notifications-card :deep(.el-card__body) {
  padding: 16px;
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.loading-state,
.empty-state {
  padding: 40px 0;
}

.notification-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.notification-item {
  display: flex;
  gap: 12px;
  padding: 12px;
  border-radius: 8px;
  transition: background 0.15s;
}

.notification-item:hover {
  background: rgba(255, 255, 255, 0.03);
}

.notification-item.is-unread {
  background: rgba(99, 102, 241, 0.06);
}

.notification-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}

.notification-body {
  flex: 1;
  min-width: 0;
  cursor: pointer;
}

.notification-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.notification-title {
  color: #e0e0e6;
  font-size: 14px;
  font-weight: 500;
}

.notification-content {
  color: #8a8a9a;
  font-size: 13px;
  line-height: 1.5;
  word-break: break-all;
}

.notification-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 6px;
}

.notification-time {
  font-size: 12px;
  color: #5a5a6a;
}

.notification-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.15s;
}

.notification-item:hover .notification-actions {
  opacity: 1;
}

.load-more {
  text-align: center;
  padding: 12px 0;
}

.pagination-bar {
  text-align: center;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.04);
  margin-top: 12px;
}

.total-text {
  color: #6a6a7a;
  font-size: 12px;
}
</style>
