<template>
  <div class="setting-item">
    <div class="setting-item__info">
      <h3 class="setting-item__title">{{ title }}</h3>
      <p v-if="description" class="setting-item__desc">{{ description }}</p>
    </div>
    <div class="setting-item__control">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string;
  description?: string;
}>();
</script>

<style scoped>
.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
  border-bottom: 1px solid var(--color-border-light);
}

.setting-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.setting-item:first-child {
  padding-top: 0;
}

.setting-item__info {
  flex: 1;
  min-width: 0;
  margin-right: 24px;
}

.setting-item__title {
  font-size: var(--text-base);
  font-weight: 500;
  color: var(--color-text-primary);
  margin-bottom: 4px;
}

.setting-item__desc {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  line-height: var(--leading-sm);
}

.setting-item__control {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 12px;
}
</style>
