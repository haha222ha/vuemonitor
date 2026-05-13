<template>
  <span :class="['trend-badge', `trend-badge--${type}`]">
    <el-icon :size="12"><component :is="icon" /></el-icon>
    {{ value }}
  </span>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { Top, Bottom, Minus } from "@element-plus/icons-vue";

const props = defineProps<{
  value: string | number;
  type: "up" | "down" | "neutral";
}>();

const icon = computed(() => {
  if (props.type === "up") return Top;
  if (props.type === "down") return Bottom;
  return Minus;
});
</script>

<style scoped>
.trend-badge {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: var(--text-xs);
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 20px;
}

.trend-badge--up {
  color: var(--color-success);
  background: var(--color-success-bg);
}

.trend-badge--down {
  color: var(--color-danger);
  background: var(--color-danger-bg);
}

.trend-badge--neutral {
  color: var(--color-info);
  background: var(--color-bg-page);
}
</style>
