<template>
  <el-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)" title="分析结果" width="720px" class="ai-dialog">
    <div v-if="result" class="analysis-result">
      <div class="analysis-result__tags">
        <el-tag size="small" :type="analysisTypeTag(result.analysis_type)" effect="light">
          {{ analysisTypeLabel(result.analysis_type) }}
        </el-tag>
        <el-tag v-if="result.confidence" size="small" type="info" effect="light">
          置信度 {{ (result.confidence * 100).toFixed(0) }}%
        </el-tag>
        <el-tag size="small" effect="light">
          {{ result.provider }} / {{ result.model }}
        </el-tag>
      </div>
      <div v-if="result.confidence" class="analysis-result__gauge-row">
        <div class="gauge-card">
          <div class="gauge-card__ring" :style="confidenceGaugeStyle(result.confidence)">
            <span class="gauge-card__value">{{ (result.confidence * 100).toFixed(0) }}</span>
          </div>
          <div class="gauge-card__label">置信度</div>
          <div :class="['gauge-card__badge', confidenceLevel(result.confidence)]">
            {{ confidenceLevel(result.confidence) === 'high' ? '高可信' : confidenceLevel(result.confidence) === 'medium' ? '中等' : '待验证' }}
          </div>
        </div>
        <div class="analysis-result__tri-cards">
          <div :class="['tri-card', result.confidence >= 0.8 ? 'tri-card--success' : result.confidence >= 0.5 ? 'tri-card--warning' : 'tri-card--danger']">
            <div class="tri-card__value">{{ result.confidence >= 0.8 ? '✓' : result.confidence >= 0.5 ? '!' : '✗' }}</div>
            <div class="tri-card__label">可信度</div>
          </div>
          <div class="tri-card tri-card--primary">
            <div class="tri-card__value">{{ analysisTypeLabel(result.analysis_type).substring(0, 2) }}</div>
            <div class="tri-card__label">类型</div>
          </div>
          <div class="tri-card tri-card--info">
            <div class="tri-card__value">{{ result.provider?.substring(0, 3) || 'AI' }}</div>
            <div class="tri-card__label">模型</div>
          </div>
        </div>
      </div>
      <div class="analysis-result__content">
        <template v-if="isStructuredResult(result.result)">
          <div v-if="result.result.summary" class="result-block result-block--highlight">
            <div class="result-block__label">摘要</div>
            <div class="result-block__text">{{ result.result.summary }}</div>
          </div>
          <div v-if="result.result.score != null" class="result-block">
            <div class="result-block__label">评分</div>
            <div class="result-score-bar">
              <div class="result-score-fill" :style="{ width: `${Math.min(result.result.score, 100)}%` }" />
              <span class="result-score-value">{{ result.result.score }}/100</span>
            </div>
          </div>
          <div v-if="result.result.recommendations?.length" class="result-block">
            <div class="result-block__label">建议</div>
            <ul class="result-list result-list--recommend">
              <li v-for="(rec, idx) in result.result.recommendations" :key="idx">{{ rec }}</li>
            </ul>
          </div>
          <div v-if="result.result.risks?.length" class="result-block">
            <div class="result-block__label">风险</div>
            <ul class="result-list result-list--risk">
              <li v-for="(risk, idx) in result.result.risks" :key="idx">{{ risk }}</li>
            </ul>
          </div>
          <div v-if="result.result.key_findings?.length" class="result-block">
            <div class="result-block__label">关键发现</div>
            <ul class="result-list">
              <li v-for="(finding, idx) in result.result.key_findings" :key="idx">{{ finding }}</li>
            </ul>
          </div>
        </template>
        <template v-else>{{ formatResult(result.result) }}</template>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: boolean;
  result: any;
  analysisTypeLabel: (t: string) => string;
  analysisTypeTag: (t: string) => string;
  formatResult: (r: any) => string;
  isStructuredResult: (r: any) => boolean;
  confidenceGaugeStyle: (c: number) => Record<string, string>;
  confidenceLevel: (c: number) => string;
}>();

defineEmits<{ (e: "update:modelValue", value: boolean): void }>();
</script>

<style scoped>
.ai-dialog :deep(.el-dialog__header) { padding: 20px 24px; border-bottom: 1px solid var(--color-border-light); margin-right: 0; }
.ai-dialog :deep(.el-dialog__title) { font-size: var(--text-lg); font-weight: 600; color: var(--color-text-primary); }
.ai-dialog :deep(.el-dialog__body) { padding: 24px; }
.analysis-result__tags { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
.analysis-result__gauge-row { display: flex; gap: 20px; margin-bottom: 20px; align-items: center; }
.gauge-card { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.gauge-card__ring { width: 80px; height: 80px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 20px; font-weight: 700; }
.gauge-card__value { color: var(--color-text-primary); }
.gauge-card__label { font-size: var(--text-xs); color: var(--color-text-tertiary); }
.gauge-card__badge { font-size: var(--text-xs); padding: 2px 8px; border-radius: 10px; }
.gauge-card__badge.high { background: #D1FAE5; color: #065F46; }
.gauge-card__badge.medium { background: #FEF3C7; color: #92400E; }
.gauge-card__badge.low { background: #FEE2E2; color: #991B1B; }
.analysis-result__tri-cards { display: flex; gap: 12px; flex: 1; }
.tri-card { flex: 1; padding: 12px; border-radius: var(--radius-lg); text-align: center; }
.tri-card--success { background: #D1FAE5; }
.tri-card--warning { background: #FEF3C7; }
.tri-card--danger { background: #FEE2E2; }
.tri-card--primary { background: #DBEAFE; }
.tri-card--info { background: #E0E7FF; }
.tri-card__value { font-size: 20px; font-weight: 700; }
.tri-card__label { font-size: var(--text-xs); color: var(--color-text-tertiary); margin-top: 4px; }
.analysis-result__content { font-size: var(--text-sm); color: var(--color-text-secondary); line-height: 1.6; }
.result-block { margin-bottom: 16px; }
.result-block--highlight { background: #F0F9FF; border-radius: var(--radius-base); padding: 12px 16px; border-left: 3px solid var(--color-primary); }
.result-block__label { font-size: var(--text-xs); font-weight: 600; color: var(--color-text-tertiary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }
.result-block__text { color: var(--color-text-primary); }
.result-score-bar { display: flex; align-items: center; gap: 12px; }
.result-score-fill { height: 8px; border-radius: 4px; background: linear-gradient(90deg, var(--color-primary), #818CF8); flex: 1; }
.result-score-value { font-size: var(--text-sm); font-weight: 600; color: var(--color-text-primary); }
.result-list { padding-left: 20px; margin: 0; }
.result-list li { margin-bottom: 4px; }
.result-list--recommend li { color: #065F46; }
.result-list--risk li { color: #991B1B; }
</style>
