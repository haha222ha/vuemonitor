<template>
  <div class="notifications fade-in">
    <PageHeader title="通知中心" subtitle="异动预警、AI分析、系统通知统一管理">
      <el-badge :value="notificationStore.unreadCount" :hidden="!notificationStore.hasUnread" :max="99">
        <el-button size="small" :disabled="!notificationStore.hasUnread" @click="handleMarkAllRead">
          全部已读
        </el-button>
      </el-badge>
      <el-button size="small" type="danger" plain :disabled="readCount === 0" @click="handleDeleteRead">
        清除已读
      </el-button>
    </PageHeader>

    <div class="notifications__toolbar">
      <el-radio-group v-model="filterRead" size="small" @change="handleFilterChange">
        <el-radio-button :value="undefined">全部</el-radio-button>
        <el-radio-button :value="false">未读</el-radio-button>
        <el-radio-button :value="true">已读</el-radio-button>
      </el-radio-group>

      <el-radio-group v-model="categoryFilter" size="small" @change="handleCategoryChange">
        <el-radio-button value="all">全部</el-radio-button>
        <el-radio-button value="alert">异动预警</el-radio-button>
        <el-radio-button value="ai">AI分析</el-radio-button>
        <el-radio-button value="system">系统</el-radio-button>
      </el-radio-group>

      <el-select v-model="typeFilter" size="small" placeholder="通知类型" clearable style="width: 140px" @change="handleTypeChange">
        <el-option label="全部类型" value="all" />
        <el-option v-for="t in allTypes" :key="t" :label="typeLabel(t)" :value="t" />
      </el-select>

      <div style="flex: 1" />
      <span class="notifications__count">共 {{ displayNotifications.length }} 条</span>
    </div>

    <div v-loading="notificationStore.loading || alertLoading" class="notifications__body">
      <EmptyState
        v-if="displayNotifications.length === 0 && !notificationStore.loading && !alertLoading"
        :icon="Bell"
        title="暂无通知"
        description="异动预警、AI分析完成等事件会在此提醒"
      />

      <div v-else class="notification-list">
        <div
          v-for="item in displayNotifications"
          :key="item.source + '-' + item.id"
          class="notification-item"
          :class="{ unread: !item.is_read, [`severity-${item.severity}`]: item.severity }"
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
              <div class="notification-tags">
                <el-tag size="small" :type="typeTagType(item.type)" effect="plain">{{ typeLabel(item.type) }}</el-tag>
                <el-tag v-if="item.severity" size="small" :type="severityTagType(item.severity)" effect="dark">{{ severityLabel(item.severity) }}</el-tag>
                <el-tag size="small" :type="categoryTagType(item.type)" effect="plain" class="category-tag">
                  {{ categoryLabel(item.type) }}
                </el-tag>
              </div>
            </div>
            <div class="notification-content">{{ item.content }}</div>
            <div class="notification-footer">
              <span class="notification-time">{{ formatTime(item.created_at) }}</span>
              <div class="notification-actions">
                <el-button
                  v-if="item.source === 'alert_event' && !item.is_acknowledged"
                  link
                  size="small"
                  type="warning"
                  @click.stop="handleAcknowledgeAlert(item)"
                >确认告警</el-button>
                <el-button
                  v-if="!item.is_read && item.source !== 'alert_event'"
                  link
                  size="small"
                  type="primary"
                  @click.stop="handleMarkRead(item.id, item.source === 'alert_event' ? 'cloud' : item.source)"
                >标为已读</el-button>
                <el-button
                  link
                  size="small"
                  type="danger"
                  @click.stop="handleDelete(item.id, item.source === 'alert_event' ? 'cloud' : item.source)"
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
import PageHeader from "../components/PageHeader.vue";
import EmptyState from "../components/EmptyState.vue";
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
import api from "../utils/api";

interface AlertEventItem extends NotificationItem {
  severity?: string;
  is_acknowledged?: boolean;
  rule_id?: string;
  metric_value?: number;
  threshold_value?: number;
}

const router = useRouter();
const notificationStore = useNotificationStore();

const filterRead = ref<boolean | undefined>(undefined);
const categoryFilter = ref<"all" | "alert" | "ai" | "system">("all");
const typeFilter = ref<string>("all");
const alertEvents = ref<AlertEventItem[]>([]);
const alertLoading = ref(false);

const allTypes = [
  "price_drop",
  "sales_surge",
  "stock_change",
  "rating_drop",
  "risk_warning",
  "ai_analysis",
  "monitor_triggered",
  "alert_event",
  "system",
];

const ALERT_TYPES = new Set(["price_drop", "sales_surge", "stock_change", "rating_drop", "risk_warning", "monitor_triggered", "alert_event"]);
const AI_TYPES = new Set(["ai_analysis"]);
const SYSTEM_TYPES = new Set(["system"]);

const CATEGORY_MAP: Record<string, "alert" | "ai" | "system"> = {
  price_drop: "alert", sales_surge: "alert", stock_change: "alert", rating_drop: "alert",
  risk_warning: "alert", monitor_triggered: "alert", alert_event: "alert",
  ai_analysis: "ai",
  system: "system",
};

const readCount = computed(() => notificationStore.notifications.filter((n) => n.is_read).length);

const TYPE_CONFIG: Record<string, { label: string; icon: typeof Warning; color: string; tagType: string; bg: string }> = {
  price_drop: { label: "降价", icon: PriceTag, color: "#F56C6C", tagType: "danger", bg: "#FEF0F0" },
  sales_surge: { label: "销量飙升", icon: TrendCharts, color: "#67C23A", tagType: "success", bg: "#F0F9EB" },
  stock_change: { label: "库存变化", icon: ShoppingCart, color: "#E6A23C", tagType: "warning", bg: "#FDF6EC" },
  rating_drop: { label: "评分下降", icon: Star, color: "#F56C6C", tagType: "danger", bg: "#FEF0F0" },
  risk_warning: { label: "风险预警", icon: Warning, color: "#F56C6C", tagType: "danger", bg: "#FEF0F0" },
  ai_analysis: { label: "AI分析", icon: InfoFilled, color: "#409EFF", tagType: "", bg: "#ECF5FF" },
  monitor_triggered: { label: "监控触发", icon: Monitor, color: "#E6A23C", tagType: "warning", bg: "#FDF6EC" },
  alert_event: { label: "异动告警", icon: Warning, color: "#F56C6C", tagType: "danger", bg: "#FEF0F0" },
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

function severityTagType(severity: string): string {
  const map: Record<string, string> = { critical: "danger", high: "danger", warning: "warning", info: "info", low: "info" };
  return map[severity] || "info";
}

function severityLabel(severity: string): string {
  const map: Record<string, string> = { critical: "紧急", high: "高", warning: "中", info: "低", low: "低" };
  return map[severity] || severity;
}

function categoryTagType(type: string): string {
  const cat = CATEGORY_MAP[type];
  if (cat === "alert") return "danger";
  if (cat === "ai") return "";
  return "info";
}

function categoryLabel(type: string): string {
  const cat = CATEGORY_MAP[type];
  if (cat === "alert") return "异动预警";
  if (cat === "ai") return "AI分析";
  return "系统";
}

const displayNotifications = computed(() => {
  let list: (NotificationItem | AlertEventItem)[] = [
    ...notificationStore.filteredNotifications,
    ...alertEvents.value,
  ];

  list.sort((a, b) => {
    const ta = a.created_at ? new Date(a.created_at).getTime() : 0;
    const tb = b.created_at ? new Date(b.created_at).getTime() : 0;
    return tb - ta;
  });

  if (categoryFilter.value !== "all") {
    list = list.filter((n) => CATEGORY_MAP[n.type] === categoryFilter.value);
  }

  return list;
});

async function fetchAlertEvents() {
  alertLoading.value = true;
  try {
    const { data } = await api.get("/alert-rules/events/all", { params: { limit: 50 } });
    if (data?.code === 0 && Array.isArray(data.data)) {
      alertEvents.value = data.data.map((e: any) => ({
        id: e.id,
        type: "alert_event",
        title: e.title || "异动告警",
        content: e.detail || "",
        is_read: e.is_acknowledged || false,
        is_acknowledged: e.is_acknowledged || false,
        related_id: e.rule_id || null,
        related_type: "monitor_rule" as const,
        created_at: e.created_at,
        source: "alert_event" as const,
        severity: e.severity,
        rule_id: e.rule_id,
        metric_value: e.metric_value,
        threshold_value: e.threshold_value,
      }));
    }
  } catch {
    alertEvents.value = [];
  } finally {
    alertLoading.value = false;
  }
}

async function handleAcknowledgeAlert(item: AlertEventItem) {
  try {
    await api.post(`/alert-rules/events/${item.id}/acknowledge`);
    item.is_acknowledged = true;
    item.is_read = true;
    ElMessage.success("告警已确认");
  } catch {
    ElMessage.error("确认失败");
  }
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

function handleCategoryChange() {}

function handleTypeChange(val: string) {
  notificationStore.setTypeFilter(val || "all");
}

let refreshTimer: ReturnType<typeof setInterval> | null = null;
let unsubscribeLocal: (() => void) | null = null;
let unsubscribeWs: (() => void) | null = null;

onMounted(() => {
  notificationStore.fetchNotifications(1);
  notificationStore.fetchUnreadCount();
  fetchAlertEvents();

  refreshTimer = setInterval(() => {
    notificationStore.fetchUnreadCount();
    fetchAlertEvents();
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
  if (refreshTimer) clearInterval(refreshTimer);
  if (unsubscribeLocal) unsubscribeLocal();
  if (unsubscribeWs) unsubscribeWs();
});
</script>

<style scoped>
.notifications {
  padding: 0;
}

.notifications__toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
  margin-bottom: 20px;
}

.notifications__count {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.notifications__body {
  min-height: 200px;
}

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
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border-light);
  background: var(--color-bg-card);
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.notification-item:hover {
  border-color: var(--color-primary);
  box-shadow: 0 2px 8px rgba(79, 70, 229, 0.1);
}

.notification-item.unread {
  background: #f0f4ff;
  border-color: #d0dfff;
}

.notification-dot {
  position: absolute;
  top: 16px;
  left: 6px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-primary);
}

.notification-icon {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  border-radius: var(--radius-base);
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
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-text-primary);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.notification-tags {
  display: flex;
  gap: 4px;
  align-items: center;
  flex-shrink: 0;
}

.notification-content {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
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
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
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

.category-tag {
  font-size: 11px;
  padding: 0 4px;
  height: 20px;
  line-height: 18px;
}

.notification-item.severity-critical {
  border-left: 3px solid #F56C6C;
}

.notification-item.severity-high {
  border-left: 3px solid #E6A23C;
}

.notification-item.severity-warning {
  border-left: 3px solid #E6A23C;
}

.notification-item.severity-info {
  border-left: 3px solid #909399;
}
</style>
