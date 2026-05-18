import { defineStore } from "pinia";
import { ref, computed } from "vue";
import api from "../utils/api";

export interface NotificationItem {
  id: string;
  type: string;
  title: string;
  content: string;
  is_read: boolean;
  related_id: string | null;
  related_type: string | null;
  created_at: string | null;
  source: "cloud" | "local" | "alert_event";
  severity?: string;
  is_acknowledged?: boolean;
}

export const useNotificationStore = defineStore("notification", () => {
  const notifications = ref<NotificationItem[]>([]);
  const unreadCount = ref(0);
  const loading = ref(false);
  const total = ref(0);
  const currentPage = ref(1);
  const pageSize = ref(20);
  const activeSource = ref<"all" | "cloud" | "local">("all");
  const activeType = ref<string>("all");

  const hasUnread = computed(() => unreadCount.value > 0);

  const notificationTypes = computed(() => {
    const types = new Set<string>();
    for (const n of notifications.value) {
      types.add(n.type);
    }
    return Array.from(types).sort();
  });

  const filteredNotifications = computed(() => {
    let list = notifications.value;
    if (activeSource.value !== "all") {
      list = list.filter((n) => n.source === activeSource.value);
    }
    if (activeType.value !== "all") {
      list = list.filter((n) => n.type === activeType.value);
    }
    return list;
  });

  async function fetchLocalNotifications(): Promise<NotificationItem[]> {
    try {
      if (!window.electronAPI) return [];
      const localNotifs = await window.electronAPI.invoke("notifications:get", 100) as Array<{
        id: string;
        type: string;
        title: string;
        content: string;
        is_read: number;
        related_id: string | null;
        related_type: string | null;
        created_at: string;
      }>;
      return (localNotifs || []).map((n) => ({
        id: n.id,
        type: n.type,
        title: n.title,
        content: n.content,
        is_read: n.is_read === 1,
        related_id: n.related_id,
        related_type: n.related_type,
        created_at: n.created_at,
        source: "local" as const,
      }));
    } catch {
      return [];
    }
  }

  async function fetchCloudNotifications(page = 1, isRead?: boolean): Promise<{ items: NotificationItem[]; total: number }> {
    try {
      const params: Record<string, unknown> = { page, page_size: pageSize.value };
      if (isRead !== undefined) params.is_read = isRead;
      const { data } = await api.get("/notifications", { params });
      const resp = data?.data || {};
      const items = (resp.items || []) as NotificationItem[];
      return {
        items: items.map((n: NotificationItem) => ({ ...n, source: "cloud" as const })),
        total: resp.total || 0,
      };
    } catch {
      return { items: [], total: 0 };
    }
  }

  async function fetchNotifications(page = 1, isRead?: boolean) {
    loading.value = true;
    try {
      const [localItems, cloudResult] = await Promise.all([
        fetchLocalNotifications(),
        fetchCloudNotifications(page, isRead),
      ]);

      const merged = [...localItems, ...cloudResult.items];
      merged.sort((a, b) => {
        const ta = a.created_at ? new Date(a.created_at).getTime() : 0;
        const tb = b.created_at ? new Date(b.created_at).getTime() : 0;
        return tb - ta;
      });

      notifications.value = merged;
      total.value = localItems.length + cloudResult.total;
      currentPage.value = page;
    } catch {
      notifications.value = [];
    } finally {
      loading.value = false;
    }
  }

  async function fetchUnreadCount() {
    try {
      let cloudCount = 0;
      try {
        const { data } = await api.get("/notifications/unread-count");
        cloudCount = data?.data?.unread_count || 0;
      } catch {}

      let localCount = 0;
      try {
        if (window.electronAPI) {
          const result = await window.electronAPI.invoke("notifications:unread-count") as { count: number };
          localCount = result?.count || 0;
        }
      } catch {}

      unreadCount.value = cloudCount + localCount;
    } catch {
      unreadCount.value = 0;
    }
  }

  async function markAsRead(notificationId: string, source?: string) {
    const n = notifications.value.find((item) => item.id === notificationId);
    const itemSource = source || n?.source;

    if (itemSource === "local") {
      try {
        if (window.electronAPI) await window.electronAPI.invoke("notifications:mark-read", notificationId);
      } catch {}
    } else {
      try {
        await api.put(`/notifications/${notificationId}/read`);
      } catch {}
    }

    if (n && !n.is_read) {
      n.is_read = true;
      unreadCount.value = Math.max(0, unreadCount.value - 1);
    }
  }

  async function markAllAsRead() {
    const localUnread = notifications.value.filter((n) => !n.is_read && n.source === "local");
    const cloudUnread = notifications.value.filter((n) => !n.is_read && n.source === "cloud");

    if (localUnread.length > 0) {
      try {
        if (window.electronAPI) await window.electronAPI.invoke("notifications:mark-all-read");
      } catch {}
    }

    if (cloudUnread.length > 0) {
      try {
        await api.put("/notifications/read-all");
      } catch {}
    }

    notifications.value.forEach((n) => {
      n.is_read = true;
    });
    unreadCount.value = 0;
  }

  async function deleteNotification(notificationId: string, source?: string) {
    const n = notifications.value.find((item) => item.id === notificationId);
    const itemSource = source || n?.source;

    if (itemSource === "local") {
      try {
        if (window.electronAPI) await window.electronAPI.invoke("notifications:delete", notificationId);
      } catch {}
    } else {
      try {
        await api.delete(`/notifications/${notificationId}`);
      } catch {}
    }

    const idx = notifications.value.findIndex((item) => item.id === notificationId);
    if (idx !== -1) {
      const removed = notifications.value.splice(idx, 1)[0];
      if (!removed.is_read) {
        unreadCount.value = Math.max(0, unreadCount.value - 1);
      }
      total.value = Math.max(0, total.value - 1);
    }
  }

  async function deleteReadNotifications() {
    const readItems = notifications.value.filter((n) => n.is_read);
    const localRead = readItems.filter((n) => n.source === "local");
    const cloudRead = readItems.filter((n) => n.source === "cloud");

    for (const item of localRead) {
      try {
        if (window.electronAPI) await window.electronAPI.invoke("notifications:delete", item.id);
      } catch {}
    }

    for (const item of cloudRead) {
      try {
        await api.delete(`/notifications/${item.id}`);
      } catch {}
    }

    notifications.value = notifications.value.filter((n) => !n.is_read);
    total.value = notifications.value.filter((n) => !n.is_read).length;
  }

  function handleNewNotification(notification: NotificationItem) {
    const exists = notifications.value.some((n) => n.id === notification.id);
    if (exists) return;

    notifications.value.unshift(notification);
    if (!notification.is_read) {
      unreadCount.value += 1;
    }
    total.value += 1;
  }

  function setSourceFilter(source: "all" | "cloud" | "local") {
    activeSource.value = source;
  }

  function setTypeFilter(type: string) {
    activeType.value = type;
  }

  return {
    notifications,
    filteredNotifications,
    notificationTypes,
    unreadCount,
    loading,
    total,
    currentPage,
    pageSize,
    hasUnread,
    activeSource,
    activeType,
    fetchNotifications,
    fetchUnreadCount,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    deleteReadNotifications,
    handleNewNotification,
    setSourceFilter,
    setTypeFilter,
  };
});
