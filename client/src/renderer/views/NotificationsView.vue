<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center">
      <h2>通知中心</h2>
      <div style="display: flex; gap: 8px; align-items: center">
        <el-badge :value="notificationStore.unreadCount" :hidden="!notificationStore.hasUnread" :max="99">
          <el-button size="small" :disabled="!notificationStore.hasUnread" @click="handleMarkAllRead">
            全部已读
          </el-button>
        </el-badge>
        <el-button size="small" type="danger" plain :disabled="readCount === 0" @click="handleDeleteRead">
          清除已读
        </el-button>
      </div>
    </div>

    <div style="display: flex; gap: 12px; align-items: center; margin-top: 16px; flex-wrap: wrap">
      <el-radio-group v-model="filterRead" size="small" @change="handleFilterChange">
        <el-radio-button :value="undefined">全部</el-radio-button>
        <el-radio-button :value="false">未读</el-radio-button>
        <el-radio-button :value="true">已读</el-radio-button>
      </el-radio-group>

      <el-radio-group v-model="sourceFilter" size="small" @change="handleSourceChange">
        <el-radio-button value="all">全部来源</el-radio-button>
        <el-radio-button value="local">本地</el-radio-button>
        <el-radio-button value="cloud">云端</el-radio-button>
      </el-radio-group>

      <el-select v-model="typeFilter" size="small" placeholder="通知类型" clearable style="width: 140px" @change="handleTypeChange">
        <el-option label="全部类型" value="all" />
        <el-option v-for="t in allTypes" :key="t" :label="typeLabel(t)" :value="t" />
      </el-select>

      <div style="flex: 1" />
      <span style="font-size: 12px; color: #909399">共 {{ notificationStore.filteredNotifications.length }} 条</span>
    </div>

    <div v-loading="notificationStore.loading" style="margin-top: 12px">
      <div v-if="notificationStore.filteredNotifications.length === 0 && !notificationStore.loading" style="text-align: center; padding: 60px 0">
        <el-empty description="暂无通知" />
      </div>

      <div v-else class="notification-list">
        <div
          v-for="item in notificationStore.filteredNotifications"
          :key="item.id"
          class="notification-item"
          :class="{ unread: !item.is_read }"
          @click="handleClick(item)"
        >
          <div class="notification-dot" v-if="!item.is_read" />
          <div class="notification-icon" :style="{ background: iconBg(item.type) }">
            <el-icon :size="20" :color="typeIconColor(item.type)">
              <component :is="typeIcon(item.type)" />
            </el-icon>
          </div>
          <div class="notification-body">
            <div class="notification-header">
              <span class="notification-title">{{ item.title }}</span>
              <div style="display: flex; gap: 4px; align-items: center; flex-shrink: 0">
                <el-tag size="small" :type="typeTagType(item.type)" effect="plain">{{ typeLabel(item.type) }}</el-tag>
                <el-tag size="small" :type="item.source === 'local' ? 'warning' : 'primary'" effect="plain" class="source-tag">
                  {{ item.source === 'local' ? '本地' : '云端' }}
                </el-tag>
              </div>
            </div>
            <div class="notification-content">{{ item.content }}</div>
            <div class="notification-footer">
              <span class="notification-time">{{ formatTime(item.created_at) }}</span>
              <div class="notification-actions">
                <el-button
                  v-if="!item.is_read"
                  link
                  size="small"
                  type="primary"
                  @click.stop="handleMarkRead(item.id, item.source)"
                >标为已读</el-button>
                <el-button
                  link
                  size="small"
                  type="danger"
                  @click.stop="handleDelete(item.id, item.source)"
                >删除</el-button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { useNotificationStore, type NotificationItem } from "../stores/notification";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  Warning,
  TrendCharts,
  PriceTag,
  ShoppingCart,
  Star,
  InfoFilled,
  Bell,
  Monitor,
} from "@element-plus/icons-vue";

const router = useRouter();
const notificationStore = useNotificationStore();

const filterRead = ref<boolean | undefined>(undefined);
const sourceFilter = ref<"all" | "cloud" | "local">("all");
const typeFilter = ref<string>("all");

const allTypes = [
  "price_drop",
  "sales_surge",
  "stock_change",
  "rating_drop",
  "risk_warning",
  "ai_analysis",
  "monitor_triggered",
  "system",
];

const readCount = computed(() => notificationStore.notifications.filter((n) => n.is_read).length);

const TYPE_CONFIG: Record<string, { label: string; icon: typeof Warning; color: string; tagType: string; bg: string }> = {
  price_drop: { label: "降价", icon: PriceTag, color: "#F56C6C", tagType: "danger", bg: "#FEF0F0" },
  sales_surge: { label: "销量飙升", icon: TrendCharts, color: "#67C23A", tagType: "success", bg: "#F0F9EB" },
  stock_change: { label: "库存变化", icon: ShoppingCart, color: "#E6A23C", tagType: "warning", bg: "#FDF6EC" },
  rating_drop: { label: "评分下降", icon: Star, color: "#F56C6C", tagType: "danger", bg: "#FEF0F0" },
  risk_warning: { label: "风险预警", icon: Warning, color: "#F56C6C", tagType: "danger", bg: "#FEF0F0" },
  ai_analysis: { label: "AI分析", icon: InfoFilled, color: "#409EFF", tagType: "", bg: "#ECF5FF" },
  monitor_triggered: { label: "监控触发", icon: Monitor, color: "#E6A23C", tagType: "warning", bg: "#FDF6EC" },
  system: { label: "系统通知", icon: Bell, color: "#909399", tagType: "info", bg: "#F4F4F5" },
};

function typeIcon(type: string) {
  return TYPE_CONFIG[type]?.icon || Bell;
}

function typeIconColor(type: string) {
  return TYPE_CONFIG[type]?.color || "#909399";
}

function iconBg(type: string) {
  return TYPE_CONFIG[type]?.bg || "#F5F7FA";
}

function typeLabel(type: string) {
  return TYPE_CONFIG[type]?.label || type;
}

function typeTagType(type: string) {
  return TYPE_CONFIG[type]?.tagType || "info";
}

function formatTime(dateStr: string | null): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  if (diff < 60000) return "刚刚";
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`;
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`;
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")}`;
}

async function handleClick(item: NotificationItem) {
  if (!item.is_read) {
    await notificationStore.markAsRead(item.id, item.source);
  }
  if (item.related_id && item.related_type === "product") {
    router.push(`/products/${item.related_id}`);
  } else if (item.related_id && item.related_type === "monitor_rule") {
    router.push("/monitor");
  }
}

async function handleMarkRead(id: string, source: "cloud" | "local") {
  await notificationStore.markAsRead(id, source);
}

async function handleMarkAllRead() {
  await notificationStore.markAllAsRead();
  ElMessage.success("已全部标为已读");
}

async function handleDelete(id: string, source: "cloud" | "local") {
  await notificationStore.deleteNotification(id, source);
  ElMessage.success("已删除");
}

async function handleDeleteRead() {
  try {
    await ElMessageBox.confirm("确定清除所有已读通知？此操作不可恢复。", "清除已读", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
    });
    await notificationStore.deleteReadNotifications();
    ElMessage.success("已清除所有已读通知");
  } catch {}
}

function handleFilterChange() {
  notificationStore.fetchNotifications(1, filterRead.value);
}

function handleSourceChange(val: "all" | "cloud" | "local") {
  notificationStore.setSourceFilter(val);
}

function handleTypeChange(val: string) {
  notificationStore.setTypeFilter(val || "all");
}

let refreshTimer: ReturnType<typeof setInterval> | null = null;
let unsubscribeLocal: (() => void) | null = null;
let unsubscribeWs: (() => void) | null = null;

onMounted(() => {
  notificationStore.fetchNotifications(1);
  notificationStore.fetchUnreadCount();

  refreshTimer = setInterval(() => {
    notificationStore.fetchUnreadCount();
  }, 30000);

  try {
    unsubscribeLocal = window.electronAPI.on("notification:local", (data: unknown) => {
      const notif = data as NotificationItem;
      notificationStore.handleNewNotification(notif);
    });
  } catch {}

  try {
    unsubscribeWs = window.electronAPI.on("notification", (data: unknown) => {
      const msg = data as { type: string; data: NotificationItem };
      if (msg.type === "notification:new" && msg.data) {
        notificationStore.handleNewNotification({ ...msg.data, source: "cloud" });
      }
    });
  } catch {}
});

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer);
  }
  if (unsubscribeLocal) {
    unsubscribeLocal();
  }
  if (unsubscribeWs) {
    unsubscribeWs();
  }
});
</script>

<style scoped>
.notification-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.notification-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 8px;
  border: 1px solid #ebeef5;
  background: #fff;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.notification-item:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.1);
}

.notification-item.unread {
  background: #f0f7ff;
  border-color: #d0e3ff;
}

.notification-dot {
  position: absolute;
  top: 16px;
  left: 6px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #409eff;
}

.notification-icon {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.notification-body {
  flex: 1;
  min-width: 0;
}

.notification-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.notification-title {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.notification-content {
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.notification-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 6px;
}

.notification-time {
  font-size: 12px;
  color: #909399;
}

.notification-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.notification-item:hover .notification-actions {
  opacity: 1;
}

.source-tag {
  font-size: 11px;
  padding: 0 4px;
  height: 20px;
  line-height: 18px;
}
</style>
