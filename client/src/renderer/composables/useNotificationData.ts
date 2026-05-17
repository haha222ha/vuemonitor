import { ref, computed, onMounted, onUnmounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useNotificationStore, type NotificationItem } from "../stores/notification";
import api from "../utils/api";

interface AlertEventItem extends NotificationItem {
  severity?: string;
  is_acknowledged?: boolean;
  rule_id?: string;
  metric_value?: number;
  threshold_value?: number;
}

export function useNotificationData() {
  const notificationStore = useNotificationStore();

  const filterRead = ref<boolean | undefined>(undefined);
  const categoryFilter = ref<"all" | "alert" | "ai" | "system">("all");
  const typeFilter = ref<string>("all");
  const alertEvents = ref<AlertEventItem[]>([]);
  const alertLoading = ref(false);

  const CATEGORY_MAP: Record<string, "alert" | "ai" | "system"> = {
    price_drop: "alert", sales_surge: "alert", stock_change: "alert", rating_drop: "alert",
    risk_warning: "alert", monitor_triggered: "alert", alert_event: "alert",
    ai_analysis: "ai", system: "system",
  };

  const readCount = computed(() => notificationStore.notifications.filter((n) => n.is_read).length);

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

  async function acknowledgeAlert(item: AlertEventItem) {
    try {
      await api.post(`/alert-rules/events/${item.id}/acknowledge`);
      item.is_acknowledged = true;
      item.is_read = true;
      ElMessage.success("告警已确认");
    } catch {
      ElMessage.error("确认失败");
    }
  }

  async function markRead(id: string, source: "cloud" | "local") {
    await notificationStore.markAsRead(id, source);
  }

  async function markAllRead() {
    await notificationStore.markAllAsRead();
    ElMessage.success("已全部标为已读");
  }

  async function deleteNotification(id: string, source: "cloud" | "local") {
    await notificationStore.deleteNotification(id, source);
    ElMessage.success("已删除");
  }

  async function deleteReadNotifications() {
    try {
      await ElMessageBox.confirm("确定清除所有已读通知？此操作不可恢复。", "清除已读", {
        confirmButtonText: "确定", cancelButtonText: "取消", type: "warning",
      });
      await notificationStore.deleteReadNotifications();
      ElMessage.success("已清除所有已读通知");
    } catch {}
  }

  function handleFilterChange() {
    notificationStore.fetchNotifications(1, filterRead.value);
  }

  function handleTypeChange(val: string) {
    notificationStore.setTypeFilter(val || "all");
  }

  let refreshTimer: ReturnType<typeof setInterval> | null = null;
  let unsubscribeLocal: (() => void) | null = null;
  let unsubscribeWs: (() => void) | null = null;

  function startListeners() {
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
  }

  function stopListeners() {
    if (refreshTimer) clearInterval(refreshTimer);
    if (unsubscribeLocal) unsubscribeLocal();
    if (unsubscribeWs) unsubscribeWs();
  }

  return {
    notificationStore,
    filterRead,
    categoryFilter,
    typeFilter,
    alertEvents,
    alertLoading,
    readCount,
    displayNotifications,
    fetchAlertEvents,
    acknowledgeAlert,
    markRead,
    markAllRead,
    deleteNotification,
    deleteReadNotifications,
    handleFilterChange,
    handleTypeChange,
    startListeners,
    stopListeners,
  };
}
