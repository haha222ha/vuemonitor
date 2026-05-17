<template>
  <div class="prediction-visual">
    <div class="prediction-visual__hero">
      <div :class="['potential-ring', `potential-ring--${potentialClass}`]">
        <div class="potential-ring__inner">
          <div class="potential-ring__icon">{{ potentialIcon }}</div>
          <div class="potential-ring__level">{{ potentialLabel }}</div>
        </div>
      </div>
      <div class="prediction-visual__stats">
        <div v-if="score != null" class="prediction-stat">
          <span class="prediction-stat__label">潜力评分</span>
          <div class="prediction-stat__bar-row">
            <div class="prediction-stat__bar">
              <div class="prediction-stat__fill" :style="{ width: `${Math.min(score, 100)}%`, background: barColor }" />
            </div>
            <span class="prediction-stat__value">{{ score }}/100</span>
          </div>
        </div>
        <div v-if="growthRate != null" class="prediction-stat">
          <span class="prediction-stat__label">7日增长率</span>
          <span :class="['prediction-stat__metric', growthRate >= 0 ? 'prediction-stat__metric--up' : 'prediction-stat__metric--down']">
            {{ growthRate >= 0 ? '+' : '' }}{{ growthRate.toFixed(1) }}%
          </span>
        </div>
        <div v-if="competitionIndex != null" class="prediction-stat">
          <span class="prediction-stat__label">竞争指数</span>
          <span :class="['prediction-stat__metric', competitionIndex > 0.7 ? 'prediction-stat__metric--danger' : competitionIndex > 0.4 ? 'prediction-stat__metric--warning' : 'prediction-stat__metric--safe']">
            {{ competitionIndex.toFixed(2) }}
          </span>
        </div>
        <div v-if="confidence != null" class="prediction-stat">
          <span class="prediction-stat__label">置信度</span>
          <span class="prediction-stat__metric">{{ (confidence * 100).toFixed(0) }}%</span>
        </div>
      </div>
    </div>
    <div class="prediction-visual__scale">
      <div class="potential-scale">
        <div class="potential-scale__item potential-scale__item--low">
          <div class="potential-scale__dot" />
          <span>低潜力</span>
        </div>
        <div class="potential-scale__item potential-scale__item--medium">
          <div class="potential-scale__dot" />
          <span>中潜力</span>
        </div>
        <div class="potential-scale__item potential-scale__item--high">
          <div class="potential-scale__dot" />
          <span>高潜力</span>
        </div>
        <div class="potential-scale__item potential-scale__item--star">
          <div class="potential-scale__dot" />
          <span>爆款</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  score?: number | null;
  confidence?: number;
  potentialLevel?: string;
  growthRate?: number | null;
  competitionIndex?: number | null;
}>();

const potentialClass = computed(() => {
  if (props.potentialLevel) {
    const map: Record<string, string> = { low: 'low', medium: 'medium', high: 'high', star: 'star' };
    return map[props.potentialLevel] || 'medium';
  }
  const s = props.score ?? 0;
  if (s >= 80) return 'star';
  if (s >= 60) return 'high';
  if (s >= 35) return 'medium';
  return 'low';
});

const potentialLabel = computed(() => {
  const map: Record<string, string> = { low: '低潜力', medium: '中潜力', high: '高潜力', star: '爆款' };
  return map[potentialClass.value] || '评估中';
});

const potentialIcon = computed(() => {
  const map: Record<string, string> = { low: '○', medium: '◐', high: '●', star: '★' };
  return map[potentialClass.value] || '○';
});

const barColor = computed(() => {
  const s = props.score ?? 0;
  if (s >= 80) return 'linear-gradient(90deg, #F59E0B, #F97316)';
  if (s >= 60) return 'linear-gradient(90deg, #10B981, #34D399)';
  if (s >= 35) return 'linear-gradient(90deg, #6366F1, #818CF8)';
  return 'linear-gradient(90deg, #94A3B8, #CBD5E1)';
});
</script>

<style scoped>
.prediction-visual { background: var(--color-bg-card); border: 1px solid var(--color-border-light); border-radius: var(--radius-xl); padding: 24px; }
.prediction-visual__hero { display: flex; gap: 24px; align-items: center; margin-bottom: 20px; }
.potential-ring { width: 100px; height: 100px; border-radius: 50%; display: flex; align-items: center; justify-content: center; flex-shrink: 0; border: 3px solid; }
.potential-ring--low { border-color: #94A3B8; background: #F1F5F9; }
.potential-ring--medium { border-color: #6366F1; background: #EEF2FF; }
.potential-ring--high { border-color: #10B981; background: #ECFDF5; }
.potential-ring--star { border-color: #F59E0B; background: linear-gradient(135deg, #FFFBEB, #FEF3C7); box-shadow: 0 0 20px rgba(245, 158, 11, 0.3); }
.potential-ring__inner { text-align: center; }
.potential-ring__icon { font-size: 28px; line-height: 1; }
.potential-ring--star .potential-ring__icon { color: #F59E0B; }
.potential-ring--high .potential-ring__icon { color: #10B981; }
.potential-ring--medium .potential-ring__icon { color: #6366F1; }
.potential-ring--low .potential-ring__icon { color: #94A3B8; }
.potential-ring__level { font-size: 12px; font-weight: 600; margin-top: 4px; }
.potential-ring--star .potential-ring__level { color: #92400E; }
.potential-ring--high .potential-ring__level { color: #065F46; }
.potential-ring--medium .potential-ring__level { color: #3730A3; }
.potential-ring--low .potential-ring__level { color: #475569; }
.prediction-visual__stats { flex: 1; display: flex; flex-direction: column; gap: 12px; }
.prediction-stat { display: flex; flex-direction: column; gap: 4px; }
.prediction-stat__label { font-size: 12px; color: var(--color-text-tertiary); }
.prediction-stat__bar-row { display: flex; align-items: center; gap: 8px; }
.prediction-stat__bar { flex: 1; height: 6px; background: var(--color-border-light); border-radius: 3px; overflow: hidden; }
.prediction-stat__fill { height: 100%; border-radius: 3px; transition: width 0.6s ease-out; }
.prediction-stat__value { font-size: 13px; font-weight: 600; color: var(--color-text-primary); min-width: 48px; text-align: right; }
.prediction-stat__metric { font-size: 14px; font-weight: 600; }
.prediction-stat__metric--up { color: #10B981; }
.prediction-stat__metric--down { color: #EF4444; }
.prediction-stat__metric--safe { color: #10B981; }
.prediction-stat__metric--warning { color: #F59E0B; }
.prediction-stat__metric--danger { color: #EF4444; }
.prediction-visual__scale { border-top: 1px solid var(--color-border-light); padding-top: 16px; }
.potential-scale { display: flex; justify-content: space-between; }
.potential-scale__item { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--color-text-tertiary); }
.potential-scale__dot { width: 8px; height: 8px; border-radius: 50%; }
.potential-scale__item--low .potential-scale__dot { background: #94A3B8; }
.potential-scale__item--medium .potential-scale__dot { background: #6366F1; }
.potential-scale__item--high .potential-scale__dot { background: #10B981; }
.potential-scale__item--star .potential-scale__dot { background: #F59E0B; }
</style>
