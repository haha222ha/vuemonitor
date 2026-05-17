<template>
  <div class="license__plans">
    <h4 class="license__section-title">套餐对比</h4>
    <div class="license__plans-grid">
      <div v-for="plan in planCards" :key="plan.name" :class="['plan-card', { 'plan-card--active': currentPlan === plan.key }]">
        <div class="plan-card__name">{{ plan.name }}</div>
        <div class="plan-card__price">{{ plan.price }}</div>
        <div class="plan-card__features">
          <div v-for="f in plan.features" :key="f" class="plan-card__feature">
            <el-icon :size="12" color="#67c23a"><CircleCheckFilled /></el-icon>
            <span>{{ f }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { CircleCheckFilled } from "@element-plus/icons-vue";

defineProps<{
  planCards: any[];
  currentPlan: string;
}>();
</script>

<style scoped>
.license__plans { margin-top: 32px; }
.license__section-title { font-size: var(--text-base); font-weight: 600; color: var(--color-text-primary); margin: 0 0 16px; }
.license__plans-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.plan-card { background: var(--color-bg-card); border: 1px solid var(--color-border-light); border-radius: var(--radius-lg); padding: 20px; transition: all 0.2s; }
.plan-card:hover { border-color: var(--color-primary); box-shadow: 0 4px 12px rgba(79, 70, 229, 0.1); }
.plan-card--active { border-color: var(--color-primary); box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.2); }
.plan-card__name { font-size: var(--text-base); font-weight: 600; color: var(--color-text-primary); margin-bottom: 4px; }
.plan-card__price { font-size: var(--text-lg); font-weight: 700; color: var(--color-primary); margin-bottom: 16px; }
.plan-card__features { display: flex; flex-direction: column; gap: 8px; }
.plan-card__feature { display: flex; align-items: center; gap: 6px; font-size: var(--text-xs); color: var(--color-text-secondary); }
@media (max-width: 768px) { .license__plans-grid { grid-template-columns: repeat(2, 1fr); } }
</style>
