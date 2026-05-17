<template>
  <div v-if="actions.length > 0" class="ai__quick-actions">
    <div class="quick-actions__title">
      <el-icon :size="16"><MagicStick /></el-icon>
      <span>快捷分析</span>
    </div>
    <div class="quick-actions__grid">
      <div
        v-for="action in actions"
        :key="action.type"
        class="quick-action-card"
        @click="$emit('action', action.type)"
      >
        <div :class="['quick-action-card__icon', `quick-action-card__icon--${action.color}`]">
          <el-icon :size="20"><component :is="action.icon" /></el-icon>
        </div>
        <div class="quick-action-card__info">
          <div class="quick-action-card__label">{{ action.label }}</div>
          <div class="quick-action-card__desc">{{ action.desc }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { MagicStick } from "@element-plus/icons-vue";
import type { Component } from "vue";

export interface QuickAction {
  type: string;
  label: string;
  desc: string;
  icon: Component;
  color: string;
}

defineProps<{ actions: QuickAction[] }>();
defineEmits<{ action: [type: string] }>();
</script>

<style scoped>
.ai__quick-actions {
  padding: 20px 24px;
  background: var(--color-bg-card);
  border-bottom: 1px solid var(--color-border-light);
}

.quick-actions__title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: 12px;
}

.quick-actions__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.quick-action-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: var(--color-bg-page);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all 0.2s;
}

.quick-action-card:hover {
  border-color: var(--color-primary-light);
  box-shadow: var(--shadow-sm);
  transform: translateY(-1px);
}

.quick-action-card__icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-base);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}

.quick-action-card__icon--primary { background: linear-gradient(135deg, #4F46E5, #7C3AED); }
.quick-action-card__icon--success { background: linear-gradient(135deg, #10B981, #34D399); }
.quick-action-card__icon--amber { background: linear-gradient(135deg, #F59E0B, #D97706); }
.quick-action-card__icon--danger { background: linear-gradient(135deg, #EF4444, #F87171); }

.quick-action-card__info {
  flex: 1;
  min-width: 0;
}

.quick-action-card__label {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-primary);
}

.quick-action-card__desc {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-top: 2px;
}
</style>
