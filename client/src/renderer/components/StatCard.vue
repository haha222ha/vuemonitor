<template>
  <div :class="['stat-card', `stat-card--${variant}`]">
    <div :class="['stat-card__icon', `stat-card__icon--${variant}`]">
      <el-icon :size="22"><component :is="icon" /></el-icon>
    </div>
    <div class="stat-card__content">
      <div class="stat-card__label">{{ label }}</div>
      <div class="stat-card__value">{{ value }}</div>
      <div v-if="trend" class="stat-card__trend">
        <el-icon :size="14"><component :is="trendIcon" /></el-icon>
        <span>{{ trend }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { Component } from "vue";

const props = defineProps<{
  label: string;
  value: string | number;
  icon: Component;
  variant?: "primary" | "success" | "warning" | "info" | "danger";
  trend?: string;
  trendType?: "up" | "down" | "neutral";
}>();

const trendIcon = computed(() => {
  const { TrendCharts, Bottom, Minus } = require("@element-plus/icons-vue");
  if (props.trendType === "up") return TrendCharts;
  if (props.trendType === "down") return Bottom;
  return Minus;
});
</script>

<style scoped>
.stat-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  padding: 24px;
  display: flex;
  align-items: flex-start;
  gap: 16px;
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-border-light);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.stat-card__icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: var(--color-text-inverse);
}

.stat-card__icon--primary { background: var(--gradient-hero); }
.stat-card__icon--success { background: var(--gradient-success); }
.stat-card__icon--warning { background: linear-gradient(135deg, #F59E0B, #FBBF24); }
.stat-card__icon--info { background: linear-gradient(135deg, #3B82F6, #60A5FA); }
.stat-card__icon--danger { background: linear-gradient(135deg, #EF4444, #F87171); }

.stat-card__content {
  flex: 1;
  min-width: 0;
}

.stat-card__label {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  margin-bottom: 8px;
}

.stat-card__value {
  font-size: var(--text-3xl);
  font-weight: 700;
  color: var(--color-text-primary);
  line-height: 1;
  margin-bottom: 8px;
}

.stat-card__trend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}
</style>
