<template>
  <div class="notifications fade-in">
    <PageHeader title="通知中心" subtitle="异动预警、AI分析、系统通知统一管理">
      <el-badge :value="notificationStore.unreadCount" :hidden="!notificationStore.hasUnread" :max="99">
        <el-button size="small" :disabled="!notificationStore.hasUnread" @click="markAllRead">
          全部已读
        </el-button>
      </el-badge>
      <el-button size="small" type="danger" plain :disabled="readCount === 0" @click="deleteReadNotifications">
        清除已读
      </el-button>
    </PageHeader>

    <div class="notifications__toolbar">
      <el-radio-group v-model="filterRead" size="small" @change="handleFilterChange">
        <el-radio-button :value="undefined">全部</el-radio-button>
        <el-radio-button :value="false">未读</el-radio-button>
        <el-radio-button :value="true">已读</el-radio-button>
      </el-radio-group>

      <el-radio-group v-model="categoryFilter" size="small">
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
        <NotificationItemCard
          v-for="item in displayNotifications"
          :key="item.source + '-' + item.id"
          :item="item"
          @click="handleClick"
          @acknowledge-alert="acknowledgeAlert"
          @mark-read="markRead"
          @delete="deleteNotification"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import type { NotificationItem } from "../stores/notification";
import PageHeader from "../components/PageHeader.vue";
import EmptyState from "../components/EmptyState.vue";
import NotificationItemCard from "../components/NotificationItem.vue";
import { useNotificationData } from "../composables/useNotificationData";
import { Bell } from "@element-plus/icons-vue";

const router = useRouter();

const {
  notificationStore,
  filterRead,
  categoryFilter,
  typeFilter,
  alertLoading,
  readCount,
  displayNotifications,
  acknowledgeAlert,
  markRead,
  markAllRead,
  deleteNotification,
  deleteReadNotifications,
  handleFilterChange,
  handleTypeChange,
  startListeners,
  stopListeners,
} = useNotificationData();

const allTypes = [
  "price_drop", "sales_surge", "stock_change", "rating_drop",
  "risk_warning", "ai_analysis", "monitor_triggered", "alert_event", "system",
];

const TYPE_LABEL_MAP: Record<string, string> = {
  price_drop: "降价", sales_surge: "销量飙升", stock_change: "库存变化", rating_drop: "评分下降",
  risk_warning: "风险预警", ai_analysis: "AI分析", monitor_triggered: "监控触发",
  alert_event: "异动告警", system: "系统通知",
};

function typeLabel(type: string) { return TYPE_LABEL_MAP[type] || type; }

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

onMounted(() => { startListeners(); });
onUnmounted(() => { stopListeners(); });
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
</style>
