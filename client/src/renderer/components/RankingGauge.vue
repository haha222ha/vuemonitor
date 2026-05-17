<template>
  <div class="ranking-gauge">
    <div class="gauge-item" v-for="gauge in gauges" :key="gauge.label">
      <div class="gauge-ring" :style="ringStyle(gauge.value, gauge.color)">
        <span class="gauge-value">{{ gauge.value || 0 }}</span>
      </div>
      <div class="gauge-label">{{ gauge.label }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface GaugeItem {
  value: number | undefined;
  label: string;
  color: string;
}

defineProps<{
  gauges: GaugeItem[];
}>();

function ringStyle(percentile: number | undefined, color: string) {
  const pct = percentile || 0;
  const deg = (pct / 100) * 360;
  return {
    background: `conic-gradient(${color} ${deg}deg, var(--color-border-light) ${deg}deg)`,
  };
}
</script>

<style scoped>
.ranking-gauge {
  display: flex;
  justify-content: space-around;
  padding: 16px 0;
}

.gauge-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.gauge-ring {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.gauge-ring::before {
  content: "";
  position: absolute;
  inset: 6px;
  border-radius: 50%;
  background: var(--color-bg-card);
}

.gauge-value {
  position: relative;
  z-index: 1;
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--color-text-primary);
}

.gauge-label {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}
</style>
