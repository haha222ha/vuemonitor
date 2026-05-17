<template>
  <div class="license__activated">
    <div class="license__status-icon">
      <el-icon :size="56" color="#67c23a"><CircleCheckFilled /></el-icon>
    </div>
    <h3 class="license__status-title">已激活</h3>

    <div class="license__info-card">
      <div class="license__info-grid">
        <div class="license__info-item">
          <span class="license__info-label">当前套餐</span>
          <el-tag :type="planTagType" size="large">{{ licenseStore.planLabel }}</el-tag>
        </div>
        <div class="license__info-item">
          <span class="license__info-label">到期时间</span>
          <span :class="['license__info-value', { expired: licenseStore.isExpired }]">{{ licenseStore.expiresAtFormatted }}</span>
        </div>
        <div class="license__info-item">
          <span class="license__info-label">设备ID</span>
          <span class="license__device-id">{{ licenseStore.license?.deviceId }}</span>
        </div>
        <div class="license__info-item">
          <span class="license__info-label">激活时间</span>
          <span class="license__info-value">{{ licenseStore.license?.activatedAt ? new Date(licenseStore.license.activatedAt).toLocaleString("zh-CN") : '-' }}</span>
        </div>
      </div>
    </div>

    <div v-if="quotaItems.length" class="license__quotas">
      <h4 class="license__section-title">配额使用</h4>
      <div v-for="item in quotaItems" :key="item.key" class="quota-item">
        <div class="quota-item__header">
          <span class="quota-item__label">{{ item.label }}</span>
          <span class="quota-item__value">{{ item.limit === -1 ? '无限' : `${item.current}/${item.limit}` }}</span>
        </div>
        <el-progress
          v-if="item.limit !== -1"
          :percentage="Math.min(100, Math.round((item.current / item.limit) * 100))"
          :color="item.current / item.limit > 0.9 ? '#f56c6c' : item.current / item.limit > 0.7 ? '#e6a23c' : '#67c23a'"
          :stroke-width="6"
          :show-text="false"
        />
      </div>
    </div>

    <div class="license__actions">
      <el-button @click="$emit('refresh')">刷新状态</el-button>
      <el-button type="danger" @click="$emit('deactivate')">解除绑定</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { CircleCheckFilled } from "@element-plus/icons-vue";

defineProps<{
  licenseStore: any;
  planTagType: string;
  quotaItems: any[];
}>();

defineEmits<{
  (e: "refresh"): void;
  (e: "deactivate"): void;
}>();
</script>

<style scoped>
.license__activated { text-align: center; padding: 40px 0; }
.license__status-icon { margin-bottom: 12px; }
.license__status-title { font-size: var(--text-xl); font-weight: 600; color: var(--color-text-primary); margin: 0 0 24px; }
.license__info-card { background: var(--color-bg-card); border: 1px solid var(--color-border-light); border-radius: var(--radius-lg); padding: 24px; margin-bottom: 24px; }
.license__info-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
.license__info-item { display: flex; flex-direction: column; gap: 6px; }
.license__info-label { font-size: var(--text-xs); color: var(--color-text-secondary); }
.license__info-value { font-size: var(--text-sm); color: var(--color-text-primary); }
.license__info-value.expired { color: var(--color-danger); }
.license__device-id { font-family: monospace; font-size: var(--text-xs); background: var(--color-bg-page); padding: 4px 8px; border-radius: var(--radius-sm); color: var(--color-text-primary); }
.license__quotas { text-align: left; background: var(--color-bg-card); border: 1px solid var(--color-border-light); border-radius: var(--radius-lg); padding: 24px; margin-bottom: 24px; }
.license__section-title { font-size: var(--text-base); font-weight: 600; color: var(--color-text-primary); margin: 0 0 16px; }
.quota-item { margin-bottom: 14px; }
.quota-item:last-child { margin-bottom: 0; }
.quota-item__header { display: flex; justify-content: space-between; font-size: var(--text-xs); margin-bottom: 6px; }
.quota-item__label { color: var(--color-text-secondary); }
.quota-item__value { color: var(--color-text-primary); font-weight: 500; }
.license__actions { display: flex; gap: 10px; justify-content: center; }
@media (max-width: 768px) { .license__info-grid { grid-template-columns: 1fr; } }
</style>
