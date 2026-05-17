<template>
  <div class="card">
    <div class="card__header">
      <div class="card__title-group">
        <el-icon class="card__icon" :size="20"><MagicStick /></el-icon>
        <h3 class="card__title">AI分析结果</h3>
      </div>
      <div class="card__actions">
        <el-tag v-if="analysis.analysis_type" size="small" effect="plain">
          {{ analysisTypeLabel(analysis.analysis_type) }}
        </el-tag>
      </div>
    </div>
    <div class="ai-result-section" v-if="analysis.summary">
      <div class="ai-result-section__label">摘要</div>
      <div class="ai-result-section__content ai-result-section__content--highlight">{{ analysis.summary }}</div>
    </div>
    <div class="ai-result-section" v-if="analysis.score != null">
      <div class="ai-result-section__label">评分</div>
      <div class="ai-score-bar">
        <div class="ai-score-bar__fill" :style="{ width: `${Math.min(analysis.score, 100)}%` }" />
        <span class="ai-score-bar__value">{{ analysis.score }}/100</span>
      </div>
    </div>
    <div class="ai-result-section" v-if="analysis.recommendations?.length">
      <div class="ai-result-section__label">建议</div>
      <ul class="ai-recommendations">
        <li v-for="(rec, idx) in analysis.recommendations" :key="idx">{{ rec }}</li>
      </ul>
    </div>
    <div class="ai-result-section" v-if="analysis.risks?.length">
      <div class="ai-result-section__label">风险</div>
      <ul class="ai-risks">
        <li v-for="(risk, idx) in analysis.risks" :key="idx">{{ risk }}</li>
      </ul>
    </div>
    <div class="ai-result" v-if="!analysis.summary && !analysis.recommendations?.length">
      {{ formatAIResult(analysis) }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { MagicStick } from "@element-plus/icons-vue";

defineProps<{
  analysis: Record<string, any>;
  analysisTypeLabel: (type: string) => string;
  formatAIResult: (result: Record<string, unknown>) => string;
}>();
</script>

<style scoped>
.card { background: var(--color-bg-card); border: 1px solid var(--color-border-light); border-radius: var(--radius-lg); padding: 20px; }
.card__header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.card__title-group { display: flex; align-items: center; gap: 8px; }
.card__icon { color: var(--color-primary); }
.card__title { margin: 0; font-size: var(--text-base); font-weight: 600; color: var(--color-text-primary); }
.card__actions { display: flex; gap: 8px; }
.ai-result { white-space: pre-wrap; line-height: 1.8; font-size: var(--text-base); color: var(--color-text-primary); padding: 4px 0; }
.ai-result-section { margin-bottom: 16px; }
.ai-result-section__label { font-size: var(--text-xs); font-weight: 600; color: var(--color-text-tertiary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }
.ai-result-section__content { font-size: var(--text-base); color: var(--color-text-primary); line-height: 1.7; }
.ai-result-section__content--highlight { padding: 12px 16px; background: var(--color-bg-page); border-radius: var(--radius-base); border-left: 3px solid var(--color-primary); }
.ai-score-bar { height: 28px; background: var(--color-bg-page); border-radius: var(--radius-base); position: relative; overflow: hidden; }
.ai-score-bar__fill { height: 100%; background: linear-gradient(90deg, var(--color-primary), #818CF8); border-radius: var(--radius-base); transition: width 0.6s ease; }
.ai-score-bar__value { position: absolute; right: 12px; top: 50%; transform: translateY(-50%); font-size: var(--text-sm); font-weight: 700; color: var(--color-text-primary); }
.ai-recommendations, .ai-risks { margin: 0; padding-left: 20px; display: flex; flex-direction: column; gap: 6px; }
.ai-recommendations li { font-size: var(--text-sm); color: var(--color-text-primary); line-height: 1.6; }
.ai-risks li { font-size: var(--text-sm); color: var(--color-danger, #EF4444); line-height: 1.6; }
</style>
