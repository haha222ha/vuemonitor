<template>
  <div :class="['empty-state', { 'empty-state--compact': compact }]">
    <div class="empty-state__icon" :style="iconBgStyle">
      <el-icon :size="compact ? 32 : 48"><component :is="icon" /></el-icon>
    </div>
    <h3 class="empty-state__title">{{ title }}</h3>
    <p v-if="description" class="empty-state__desc">{{ description }}</p>
    <div v-if="actionLabel || $slots.actions" class="empty-state__actions">
      <el-button v-if="actionLabel" type="primary" @click="$emit('action')" class="empty-state__action">
        <el-icon v-if="actionIcon"><component :is="actionIcon" /></el-icon>
        {{ actionLabel }}
      </el-button>
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Component } from "vue";
import { computed } from "vue";

const props = withDefaults(defineProps<{
  icon: Component;
  title: string;
  description?: string;
  actionLabel?: string;
  actionIcon?: Component;
  compact?: boolean;
  iconBg?: string;
}>(), {
  compact: false,
});

defineEmits<{
  action: [];
}>();

const iconBgStyle = computed(() => {
  if (props.iconBg) return { background: props.iconBg };
  return {};
});
</script>

<style scoped>
.empty-state {
  text-align: center;
  padding: 48px 24px;
}

.empty-state--compact {
  padding: 32px 16px;
}

.empty-state__icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-tertiary);
  background: var(--color-bg-card, #f5f7fa);
  margin-bottom: 16px;
}

.empty-state--compact .empty-state__icon {
  width: 56px;
  height: 56px;
  margin-bottom: 12px;
}

.empty-state__title {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 8px;
}

.empty-state__desc {
  font-size: var(--text-base);
  color: var(--color-text-secondary);
  margin-bottom: 24px;
  max-width: 360px;
  margin-left: auto;
  margin-right: auto;
  line-height: 1.6;
}

.empty-state__actions {
  display: flex;
  justify-content: center;
  gap: 12px;
}

.empty-state__action {
  border-radius: var(--radius-base);
}
</style>
