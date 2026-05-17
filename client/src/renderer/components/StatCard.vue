<template>
  <div :class="['stat-card', `stat-card--${variant}`]">
    <div :class="['stat-card__icon', `stat-card__icon--${variant}`]">
      <el-icon :size="22"><component :is="icon" /></el-icon>
    </div>
    <div class="stat-card__content">
      <div class="stat-card__label">{{ label }}</div>
      <div :class="['stat-card__value', `stat-card__value--${variant}`]">{{ value }}</div>
      <div v-if="trend" :class="['stat-card__trend', `stat-card__trend--${trendType}`]">
        <el-icon :size="14"><component :is="trendIcon" /></el-icon>
        <span>{{ trend }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { TrendCharts, Bottom, Minus } from "@element-plus/icons-vue";
import type { Component } from "vue";

const props = defineProps<{
  label: string;
  value: string | number;
  icon: Component;
  variant?: "primary" | "success" | "warning" | "info" | "danger" | "amber";
  trend?: string;
  trendType?: "up" | "down" | "neutral";
}>();

const trendIcon = computed(() => {
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
  position: relative;
  overflow: hidden;
}

.stat-card::before {
  content: "";
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  opacity: 0;
  transition: opacity 0.3s;
}

.stat-card--primary::before { background: var(--gradient-hero); }
.stat-card--success::before { background: var(--gradient-success); }
.stat-card--amber::before { background: linear-gradient(90deg, #F59E0B, #D97706); }
.stat-card--danger::before { background: linear-gradient(90deg, #EF4444, #DC2626); }
.stat-card--warning::before { background: linear-gradient(90deg, #F59E0B, #FBBF24); }
.stat-card--info::before { background: linear-gradient(90deg, #3B82F6, #60A5FA); }

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.stat-card:hover::before {
  opacity: 1;
}

.stat-card__icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #fff;
  transition: transform 0.3s;
}

.stat-card:hover .stat-card__icon {
  transform: scale(1.05);
}

.stat-card__icon--primary { background: var(--gradient-hero); }
.stat-card__icon--success { background: var(--gradient-success); }
.stat-card__icon--warning { background: linear-gradient(135deg, #F59E0B, #FBBF24); }
.stat-card__icon--info { background: linear-gradient(135deg, #3B82F6, #60A5FA); }
.stat-card__icon--danger { background: linear-gradient(135deg, #EF4444, #F87171); }
.stat-card__icon--amber { background: linear-gradient(135deg, #F59E0B, #D97706); }

.stat-card__content {
  flex: 1;
  min-width: 0;
}

.stat-card__label {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  margin-bottom: 8px;
  font-weight: 500;
}

.stat-card__value {
  font-size: var(--text-3xl);
  font-weight: 700;
  line-height: 1;
  margin-bottom: 8px;
  transition: color 0.3s;
}

.stat-card__value--primary { color: var(--color-primary); }
.stat-card__value--success { color: var(--color-success); }
.stat-card__value--amber { color: #D97706; }
.stat-card__value--danger { color: var(--color-danger); }
.stat-card__value--warning { color: #F59E0B; }
.stat-card__value--info { color: #3B82F6; }

.stat-card__trend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--text-xs);
  font-weight: 500;
  transition: color 0.3s;
}

.stat-card__trend--up {
  color: var(--color-success);
}

.stat-card__trend--down {
  color: var(--color-danger);
}

.stat-card__trend--neutral {
  color: var(--color-text-tertiary);
}
</style>
