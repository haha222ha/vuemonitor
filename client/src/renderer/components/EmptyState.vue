<template>
  <div :class="['empty-state', { 'empty-state--compact': compact, 'empty-state--with-illustration': illustration }]">
    <div v-if="illustration" class="empty-state__illustration">
      <div class="empty-state__illustration-icon">
        <el-icon :size="64"><component :is="icon" /></el-icon>
      </div>
    </div>
    <div v-else class="empty-state__icon" :style="iconBgStyle">
      <el-icon :size="compact ? 32 : 48"><component :is="icon" /></el-icon>
    </div>
    <h3 class="empty-state__title">{{ title }}</h3>
    <p v-if="description" class="empty-state__desc">{{ description }}</p>
    <div v-if="tips && tips.length > 0" class="empty-state__tips">
      <div v-for="(tip, i) in tips" :key="i" class="empty-state__tip">
        <el-icon :size="16"><InfoFilled /></el-icon>
        <span>{{ tip }}</span>
      </div>
    </div>
    <div v-if="actionLabel || $slots.actions" class="empty-state__actions">
      <el-button v-if="actionLabel" type="primary" size="large" class="empty-state__action" @click="$emit('action')">
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
import { InfoFilled } from "@element-plus/icons-vue";

const props = withDefaults(defineProps<{
  icon: Component;
  title: string;
  description?: string;
  actionLabel?: string;
  actionIcon?: Component;
  compact?: boolean;
  iconBg?: string;
  illustration?: boolean;
  tips?: string[];
}>(), {
  compact: false,
  illustration: false,
  tips: () => [],
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
  padding: var(--space-3xl) var(--space-xl);
}

.empty-state--compact {
  padding: var(--space-xl) var(--space-base);
}

.empty-state--with-illustration {
  padding: var(--space-2xl) var(--space-xl);
}

.empty-state__illustration {
  margin-bottom: var(--space-xl);
}

.empty-state__illustration-icon {
  width: 120px;
  height: 120px;
  margin: 0 auto;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light));
  border-radius: var(--radius-2xl);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: var(--shadow-lg);
}

.empty-state__icon {
  width: 80px;
  height: 80px;
  border-radius: var(--radius-full);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-tertiary);
  background: var(--color-bg-card);
  margin-bottom: var(--space-base);
}

.empty-state--compact .empty-state__icon {
  width: 56px;
  height: 56px;
  margin-bottom: var(--space-sm);
}

.empty-state__title {
  font-size: var(--text-xl);
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: var(--space-sm);
}

.empty-state__desc {
  font-size: var(--text-base);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-lg);
  max-width: 400px;
  margin-left: auto;
  margin-right: auto;
  line-height: 1.6;
}

.empty-state__tips {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  margin-bottom: var(--space-lg);
  max-width: 360px;
  margin-left: auto;
  margin-right: auto;
}

.empty-state__tip {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  padding: var(--space-sm) var(--space-base);
  background: var(--color-bg-page);
  border-radius: var(--radius-base);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.empty-state__tip .el-icon {
  color: var(--color-primary);
  flex-shrink: 0;
}

.empty-state__actions {
  display: flex;
  justify-content: center;
  gap: var(--space-base);
  flex-wrap: wrap;
}

.empty-state__action {
  border-radius: var(--radius-base);
  min-width: 120px;
}

@media (max-width: 640px) {
  .empty-state {
    padding: var(--space-xl) var(--space-base);
  }

  .empty-state__illustration-icon {
    width: 96px;
    height: 96px;
  }

  .empty-state__title {
    font-size: var(--text-lg);
  }
}
</style>
