<template>
  <div class="trend-score-visual">
    <div class="trend-score-visual__main">
      <div class="trend-gauge">
        <svg viewBox="0 0 120 120" class="trend-gauge__svg">
          <circle cx="60" cy="60" r="52" fill="none" stroke="var(--color-border-light)" stroke-width="8" />
          <circle
            cx="60" cy="60" r="52" fill="none"
            :stroke="scoreColor"
            stroke-width="8"
            stroke-linecap="round"
            :stroke-dasharray="circumference"
            :stroke-dashoffset="dashOffset"
            class="trend-gauge__arc"
          />
        </svg>
        <div class="trend-gauge__center">
          <div class="trend-gauge__score" :style="{ color: scoreColor }">{{ score ?? '-' }}</div>
          <div class="trend-gauge__unit">/100</div>
        </div>
      </div>
      <div class="trend-score-visual__info">
        <div class="trend-score-visual__level">
          <span :class="['level-badge', `level-badge--${scoreLevel}`]">{{ levelLabel }}</span>
        </div>
        <div v-if="trend" class="trend-score-visual__trend">
          <span class="trend-label">趋势方向</span>
          <span :class="['trend-value', `trend-value--${trendDir}`]">
            {{ trend === 'rising' ? '↑ 上升' : trend === 'falling' ? '↓ 下降' : '→ 平稳' }}
          </span>
        </div>
        <div v-if="growthRate != null" class="trend-score-visual__growth">
          <span class="trend-label">7日增长率</span>
          <span :class="['trend-value', growthRate >= 0 ? 'trend-value--up' : 'trend-value--down']">
            {{ growthRate >= 0 ? '+' : '' }}{{ growthRate.toFixed(1) }}%
          </span>
        </div>
        <div v-if="lifecycle" class="trend-score-visual__lifecycle">
          <span class="trend-label">生命周期</span>
          <span :class="['lifecycle-badge', `lifecycle-badge--${lifecycleKey}`]">{{ lifecycleLabel }}</span>
        </div>
      </div>
    </div>
    <div class="trend-score-visual__scale">
      <span class="scale-label scale-label--low">0</span>
      <div class="scale-bar">
        <div class="scale-segment scale-segment--danger" style="width: 30%" />
        <div class="scale-segment scale-segment--warning" style="width: 30%" />
        <div class="scale-segment scale-segment--success" style="width: 40%" />
        <div class="scale-marker" :style="{ left: `${Math.min(score ?? 0, 100)}%` }" />
      </div>
      <span class="scale-label scale-label--high">100</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  score?: number | null;
  confidence?: number;
  trend?: string;
  growthRate?: number | null;
  lifecycle?: string;
}>();

const circumference = 2 * Math.PI * 52;

const dashOffset = computed(() => {
  const pct = Math.min(props.score ?? 0, 100) / 100;
  return circumference * (1 - pct);
});

const scoreColor = computed(() => {
  const s = props.score ?? 0;
  if (s >= 70) return '#10B981';
  if (s >= 40) return '#F59E0B';
  return '#EF4444';
});

const scoreLevel = computed(() => {
  const s = props.score ?? 0;
  if (s >= 80) return 'excellent';
  if (s >= 60) return 'good';
  if (s >= 40) return 'fair';
  return 'poor';
});

const levelLabel = computed(() => {
  const map: Record<string, string> = { excellent: '优秀', good: '良好', fair: '一般', poor: '较差' };
  return map[scoreLevel.value] || '-';
});

const trendDir = computed(() => {
  if (props.trend === 'rising') return 'up';
  if (props.trend === 'falling') return 'down';
  return 'neutral';
});

const lifecycleKey = computed(() => {
  const map: Record<string, string> = { '新品期': 'new', '成长期': 'growth', '稳定期': 'stable', '衰退期': 'decline' };
  return map[props.lifecycle || ''] || 'stable';
});

const lifecycleLabel = computed(() => props.lifecycle || '-');
</script>

<style scoped>
.trend-score-visual { background: var(--color-bg-card); border: 1px solid var(--color-border-light); border-radius: var(--radius-xl); padding: 24px; }
.trend-score-visual__main { display: flex; gap: 24px; align-items: center; margin-bottom: 20px; }
.trend-gauge { position: relative; width: 120px; height: 120px; flex-shrink: 0; }
.trend-gauge__svg { width: 100%; height: 100%; transform: rotate(-90deg); }
.trend-gauge__arc { transition: stroke-dashoffset 0.8s ease-out; }
.trend-gauge__center { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.trend-gauge__score { font-size: 32px; font-weight: 700; line-height: 1; }
.trend-gauge__unit { font-size: 12px; color: var(--color-text-tertiary); margin-top: 2px; }
.trend-score-visual__info { flex: 1; display: flex; flex-direction: column; gap: 10px; }
.trend-score-visual__level { margin-bottom: 4px; }
.level-badge { display: inline-block; padding: 4px 14px; border-radius: 12px; font-size: 13px; font-weight: 600; }
.level-badge--excellent { background: var(--color-success-bg); color: var(--color-success); }
.level-badge--good { background: var(--color-primary-lightest); color: var(--color-primary-light); }
.level-badge--fair { background: var(--color-warning-bg); color: var(--color-warning); }
.level-badge--poor { background: var(--color-danger-bg); color: var(--color-danger); }
.trend-score-visual__trend,
.trend-score-visual__growth,
.trend-score-visual__lifecycle { display: flex; align-items: center; justify-content: space-between; }
.trend-label { font-size: 13px; color: var(--color-text-tertiary); }
.trend-value { font-size: 14px; font-weight: 600; }
.trend-value--up { color: #10B981; }
.trend-value--down { color: #EF4444; }
.trend-value--neutral { color: #94A3B8; }
.lifecycle-badge { padding: 2px 10px; border-radius: 10px; font-size: 12px; font-weight: 500; }
.lifecycle-badge--new { background: var(--color-primary-lightest); color: var(--color-primary-light); }
.lifecycle-badge--growth { background: var(--color-success-bg); color: var(--color-success); }
.lifecycle-badge--stable { background: var(--color-bg-hover); color: var(--color-text-secondary); }
.lifecycle-badge--decline { background: var(--color-danger-bg); color: var(--color-danger); }
.trend-score-visual__scale { display: flex; align-items: center; gap: 8px; }
.scale-label { font-size: 11px; color: var(--color-text-tertiary); min-width: 20px; }
.scale-bar { flex: 1; height: 6px; border-radius: 3px; display: flex; overflow: hidden; position: relative; }
.scale-segment { height: 100%; }
.scale-segment--danger { background: #FCA5A5; }
.scale-segment--warning { background: #FCD34D; }
.scale-segment--success { background: #6EE7B7; }
.scale-marker { position: absolute; top: -4px; width: 3px; height: 14px; background: var(--color-text-primary); border-radius: 2px; transform: translateX(-50%); transition: left 0.5s ease-out; }
</style>
