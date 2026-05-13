<template>
  <div class="empty-state">
    <div class="empty-state__icon">
      <el-icon :size="48"><component :is="icon" /></el-icon>
    </div>
    <h3 class="empty-state__title">{{ title }}</h3>
    <p v-if="description" class="empty-state__desc">{{ description }}</p>
    <el-button v-if="actionLabel" type="primary" @click="$emit('action')" class="empty-state__action">
      <el-icon v-if="actionIcon"><component :is="actionIcon" /></el-icon>
      {{ actionLabel }}
    </el-button>
  </div>
</template>

<script setup lang="ts">
import type { Component } from "vue";

defineProps<{
  icon: Component;
  title: string;
  description?: string;
  actionLabel?: string;
  actionIcon?: Component;
}>();

defineEmits<{
  action: [];
}>();
</script>

<style scoped>
.empty-state {
  text-align: center;
  padding: 48px 24px;
}

.empty-state__icon {
  color: var(--color-text-tertiary);
  margin-bottom: 16px;
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
}

.empty-state__action {
  border-radius: var(--radius-base);
}
</style>
