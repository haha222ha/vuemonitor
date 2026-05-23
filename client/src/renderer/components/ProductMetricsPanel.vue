<template>
  <div class="metrics-panel">
    <div class="metrics-panel__grid">
      <div
        v-for="metric in metrics"
        :key="metric.key"
        :class="['metrics-panel__card', `metrics-panel__card--${metric.variant}`]"
      >
        <div class="metrics-panel__card-header">
          <el-icon :size="18" class="metrics-panel__card-icon">
            <component :is="metric.icon" />
          </el-icon>
          <span class="metrics-panel__card-label">{{ metric.label }}</span>
        </div>
        <div class="metrics-panel__card-value">{{ metric.value }}</div>
        <div v-if="metric.trend" :class="['metrics-panel__card-trend', `metrics-panel__card-trend--${metric.trendType}`]">
          <el-icon :size="14">
            <component :is="metric.trendType === 'up' ? ArrowUp : ArrowDown" />
          </el-icon>
          <span>{{ metric.trend }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { ArrowUp, ArrowDown, Money, Sell, Star, Trophy } from "@element-plus/icons-vue";

const props = defineProps<{
  price: string;
  priceChange?: string;
  priceChangeType?: 'up' | 'down' | 'neutral';
  sales: string;
  salesChange?: string;
  salesChangeType?: 'up' | 'down' | 'neutral';
  rating: string;
  competitionIndex?: number;
}>();

const metrics = computed(() => [
  {
    key: "price",
    icon: Money,
    label: "当前价格",
    value: props.price,
    variant: "danger",
    trend: props.priceChange,
    trendType: props.priceChangeType || "neutral",
  },
  {
    key: "sales",
    icon: Sell,
    label: "总销量",
    value: props.sales,
    variant: "primary",
    trend: props.salesChange,
    trendType: props.salesChangeType || "neutral",
  },
  {
    key: "rating",
    icon: Star,
    label: "评分",
    value: props.rating,
    variant: "warning",
  },
  {
    key: "competition",
    icon: Trophy,
    label: "竞争力",
    value: props.competitionIndex != null ? props.competitionIndex.toFixed(2) : "-",
    variant: "success",
  },
]);
</script>

<style scoped>
.metrics-panel {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  padding: var(--space-lg);
  border: 1px solid var(--color-border-light);
  box-shadow: var(--shadow-sm);
}

.metrics-panel__grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-base);
}

.metrics-panel__card {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
  padding: var(--space-base);
  background: var(--color-bg-page);
  border-radius: var(--radius-base);
  transition: all var(--duration-fast) var(--ease-out);
}

.metrics-panel__card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.metrics-panel__card-header {
  display: flex;
  align-items: center;
  gap: var(--space-xs);
}

.metrics-panel__card-icon {
  color: var(--color-text-tertiary);
}

.metrics-panel__card-label {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.metrics-panel__card-value {
  font-size: var(--text-xl);
  font-weight: 700;
  color: var(--color-text-primary);
}

.metrics-panel__card-trend {
  display: flex;
  align-items: center;
  gap: var(--space-2xs);
  font-size: var(--text-xs);
  font-weight: 500;
}

.metrics-panel__card-trend--up {
  color: var(--color-danger);
}

.metrics-panel__card-trend--down {
  color: var(--color-success);
}

.metrics-panel__card-trend--neutral {
  color: var(--color-text-tertiary);
}

@media (max-width: 1024px) {
  .metrics-panel__grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .metrics-panel__grid {
    grid-template-columns: 1fr;
  }
}
</style>
