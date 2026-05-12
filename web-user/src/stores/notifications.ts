import { defineStore } from "pinia";
import { ref, computed } from "vue";
import api from "../utils/api";
import { ElMessage } from "element-plus";

export interface Notification {
  id: string;
  type: 'price_change' | 'sales_change' | 'risk_alert' | 'system' | 'ai_analysis';
  title: string;
  content: string;
  is_read: boolean;
  product_id?: string;
  created_at: string;
}

export const useNotificationsStore = defineStore("notifications", () => {
  const items = ref<Notification[]>([]);
  const unreadCount = ref<number>(0);
  const loading = ref<boolean>(false);
  const total = ref<number>(0);

  const hasUnread = computed(() => unreadCount.value > 0);

  async function fetchNotifications(params?: { page?: number; page_size?: number; type?: string; is_read?: boolean }) {
    loading.value = true;
    try {
      const { data } = await api.get("/notifications", { params });
      items.value = data.items || [];
      total.value = data.total || 0;
      // Update unread count from response or calculate locally
      if (data.unread_count !== undefined) {
        unreadCount.value = data.unread_count;
      } else {
        unreadCount.value = items.value.filter(item => !item.is_read).length;
      }
    } catch (error) {
      ElMessage.error("Failed to fetch notifications");
    } finally {
      loading.value = false;
    }
  }

  async function markAsRead(id: string) {
    try {
      await api.put(`/notifications/${id}/read`);
      // Update local state
      const notification = items.value.find(n => n.id === id);
      if (notification) {
        notification.is_read = true;
        if (unreadCount.value > 0) {
          unreadCount.value--;
        }
      }
    } catch (error) {
      ElMessage.error("Failed to mark notification as read");
    }
  }

  async function markAllAsRead() {
    try {
      await api.put("/notifications/read-all");
      // Update local state
      items.value.forEach(notification => {
        notification.is_read = true;
      });
      unreadCount.value = 0;
    } catch (error) {
      ElMessage.error("Failed to mark all notifications as read");
    }
  }

  async function deleteNotification(id: string) {
    try {
      await api.delete(`/notifications/${id}`);
      // Remove from local state
      const index = items.value.findIndex(n => n.id === id);
      if (index !== -1) {
        const deleted = items.value.splice(index, 1)[0];
        if (!deleted.is_read && unreadCount.value > 0) {
          unreadCount.value--;
        }
        total.value--;
      }
    } catch (error) {
      ElMessage.error("Failed to delete notification");
    }
  }

  async function deleteAllRead() {
    try {
      await api.delete("/notifications/read");
      // Remove read notifications from local state
      const readCountBefore = items.value.filter(n => n.is_read).length;
      items.value = items.value.filter(n => !n.is_read);
      total.value = items.value.length;
      // unreadCount remains the same since we only deleted read notifications
    } catch (error) {
      ElMessage.error("Failed to delete read notifications");
    }
  }

  async function fetchUnreadCount() {
    try {
      const { data } = await api.get("/notifications/unread-count");
      unreadCount.value = data.count || 0;
    } catch (error) {
      ElMessage.error("Failed to fetch unread count");
    }
  }

  return { items, unreadCount, loading, total, hasUnread, fetchNotifications, markAsRead, markAllAsRead, deleteNotification, deleteAllRead, fetchUnreadCount };
});