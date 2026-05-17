<template>
  <div class="risk-warning-visual">
    <div class="risk-warning-visual__overall">
      <div :class="['risk-overall-card', `risk-overall-card--${overallClass}`]">
        <div class="risk-overall-card__icon">{{ overallIcon }}</div>
        <div class="risk-overall-card__info">
          <div class="risk-overall-card__level">{{ overallLabel }}</div>
          <div class="risk-overall-card__desc">{{ overallDesc }}</div>
        </div>
        <div v-if="score != null" class="risk-overall-card__score">
          <span class="risk-overall-card__score-value">{{ score }}</span>
          <span class="risk-overall-card__score-unit">/100</span>
        </div>
      </div>
    </div>
    <div v-if="riskItems.length > 0" class="risk-warning-visual__cards">
      <div
        v-for="(risk, idx) in riskItems"
        :key="idx"
        :class="['risk-card', `risk-card--${riskSeverity(risk)}`]"
      >
        <div class="risk-card__indicator" />
        <div class="risk-card__body">
          <div class="risk-card__title">{{ riskTitle(risk) }}</div>
          <div v-if="riskDetail(risk)" class="risk-card__detail">{{ riskDetail(risk) }}</div>
        </div>
        <div :class="['risk-card__badge', `risk-card__badge--${riskSeverity(risk)}`]">
          {{ severityLabel(riskSeverity(risk)) }}
        </div>
      </div>
    </div>
    <div v-else class="risk-warning-visual__empty">
      <span>暂无具体风险项</span>
    </div>
    <div class="risk-warning-visual__legend">
      <div class="risk-legend">
        <div class="risk-legend__item">
          <div class="risk-legend__dot risk-legend__dot--danger" />
          <span>高风险</span>
        </div>
        <div class="risk-legend__item">
          <div class="risk-legend__dot risk-legend__dot--warning" />
          <span>中风险</span>
        </div>
        <div class="risk-legend__item">
          <div class="risk-legend__dot risk-legend__dot--success" />
          <span>低风险</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  risks?: string[] | any[];
  overallRisk?: string;
  confidence?: number;
  score?: number | null;
}>();

const overallClass = computed(() => {
  if (props.overallRisk) {
    const map: Record<string, string> = { high: 'danger', critical: 'danger', medium: 'warning', low: 'success', safe: 'success' };
    return map[props.overallRisk.toLowerCase()] || 'warning';
  }
  const s = props.score ?? 50;
  if (s < 30) return 'danger';
  if (s < 60) return 'warning';
  return 'success';
});

const overallLabel = computed(() => {
  const map: Record<string, string> = { danger: '高风险', warning: '中风险', success: '低风险' };
  return map[overallClass.value] || '评估中';
});

const overallIcon = computed(() => {
  const map: Record<string, string> = { danger: '⚠', warning: '⚡', success: '✓' };
  return map[overallClass.value] || '?';
});

const overallDesc = computed(() => {
  const map: Record<string, string> = {
    danger: '存在重大风险，建议立即处理',
    warning: '存在一定风险，需关注变化',
    success: '风险可控，状态良好',
  };
  return map[overallClass.value] || '';
});

const riskItems = computed(() => {
  if (!props.risks?.length) return [];
  return props.risks.map((r: any) => {
    if (typeof r === 'string') return { text: r, level: 'warning' };
    return { text: r.description || r.text || r.name || '', level: r.level || r.severity || 'warning', detail: r.detail || r.impact || '' };
  });
});

function riskSeverity(risk: any): string {
  const level = (risk.level || '').toLowerCase();
  if (['high', 'critical', 'danger'].includes(level)) return 'danger';
  if (['medium', 'moderate'].includes(level)) return 'warning';
  if (['low', 'safe', 'info'].includes(level)) return 'success';
  return 'warning';
}

function riskTitle(risk: any): string {
  return typeof risk === 'string' ? risk : risk.text || risk.description || risk.name || '未知风险';
}

function riskDetail(risk: any): string {
  if (typeof risk === 'string') return '';
  return risk.detail || risk.impact || '';
}

function severityLabel(severity: string): string {
  const map: Record<string, string> = { danger: '高', warning: '中', success: '低' };
  return map[severity] || '中';
}
</script>

<style scoped>
.risk-warning-visual { background: var(--color-bg-card); border: 1px solid var(--color-border-light); border-radius: var(--radius-xl); padding: 24px; }
.risk-warning-visual__overall { margin-bottom: 20px; }
.risk-overall-card { display: flex; align-items: center; gap: 16px; padding: 16px 20px; border-radius: var(--radius-lg); }
.risk-overall-card--danger { background: linear-gradient(135deg, #FEE2E2, #FECACA); border: 1px solid #FCA5A5; }
.risk-overall-card--warning { background: linear-gradient(135deg, #FEF3C7, #FDE68A); border: 1px solid #FCD34D; }
.risk-overall-card--success { background: linear-gradient(135deg, #D1FAE5, #A7F3D0); border: 1px solid #6EE7B7; }
.risk-overall-card__icon { font-size: 32px; line-height: 1; }
.risk-overall-card__info { flex: 1; }
.risk-overall-card__level { font-size: 18px; font-weight: 700; }
.risk-overall-card--danger .risk-overall-card__level { color: #991B1B; }
.risk-overall-card--warning .risk-overall-card__level { color: #92400E; }
.risk-overall-card--success .risk-overall-card__level { color: #065F46; }
.risk-overall-card__desc { font-size: 13px; margin-top: 2px; }
.risk-overall-card--danger .risk-overall-card__desc { color: #B91C1C; }
.risk-overall-card--warning .risk-overall-card__desc { color: #B45309; }
.risk-overall-card--success .risk-overall-card__desc { color: #047857; }
.risk-overall-card__score { text-align: right; }
.risk-overall-card__score-value { font-size: 28px; font-weight: 700; }
.risk-overall-card--danger .risk-overall-card__score-value { color: #991B1B; }
.risk-overall-card--warning .risk-overall-card__score-value { color: #92400E; }
.risk-overall-card--success .risk-overall-card__score-value { color: #065F46; }
.risk-overall-card__score-unit { font-size: 13px; color: var(--color-text-tertiary); }
.risk-warning-visual__cards { display: flex; flex-direction: column; gap: 10px; margin-bottom: 16px; }
.risk-card { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border-radius: var(--radius-base); border: 1px solid var(--color-border-light); background: var(--color-bg-page); }
.risk-card--danger { border-left: 4px solid #EF4444; background: #FEF2F2; }
.risk-card--warning { border-left: 4px solid #F59E0B; background: #FFFBEB; }
.risk-card--success { border-left: 4px solid #10B981; background: #ECFDF5; }
.risk-card__indicator { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.risk-card--danger .risk-card__indicator { background: #EF4444; }
.risk-card--warning .risk-card__indicator { background: #F59E0B; }
.risk-card--success .risk-card__indicator { background: #10B981; }
.risk-card__body { flex: 1; min-width: 0; }
.risk-card__title { font-size: 13px; font-weight: 500; color: var(--color-text-primary); }
.risk-card__detail { font-size: 12px; color: var(--color-text-tertiary); margin-top: 2px; }
.risk-card__badge { padding: 2px 10px; border-radius: 10px; font-size: 12px; font-weight: 600; flex-shrink: 0; }
.risk-card__badge--danger { background: #FEE2E2; color: #991B1B; }
.risk-card__badge--warning { background: #FEF3C7; color: #92400E; }
.risk-card__badge--success { background: #D1FAE5; color: #065F46; }
.risk-warning-visual__empty { text-align: center; padding: 20px; color: var(--color-text-tertiary); font-size: 13px; }
.risk-warning-visual__legend { border-top: 1px solid var(--color-border-light); padding-top: 12px; }
.risk-legend { display: flex; justify-content: center; gap: 20px; }
.risk-legend__item { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--color-text-tertiary); }
.risk-legend__dot { width: 8px; height: 8px; border-radius: 50%; }
.risk-legend__dot--danger { background: #EF4444; }
.risk-legend__dot--warning { background: #F59E0B; }
.risk-legend__dot--success { background: #10B981; }
</style>
