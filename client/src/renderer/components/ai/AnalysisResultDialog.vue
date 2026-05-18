<template>
  <el-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)" title="分析结果" width="760px" class="ai-dialog">
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

      <div v-if="result.analysis_type === 'trend_score'" class="analysis-result__visual">
        <TrendScoreVisual
          :score="result.result?.score"
          :confidence="result.confidence"
          :trend="result.result?.trend_short"
          :growth-rate="result.result?.growth_rate_7d"
          :lifecycle="result.result?.lifecycle_stage"
        />
      </div>

      <div v-else-if="result.analysis_type === 'prediction'" class="analysis-result__visual">
        <PredictionVisual
          :score="result.result?.score"
          :confidence="result.confidence"
          :potential-level="result.result?.potential_level"
          :growth-rate="result.result?.growth_rate_7d"
          :competition-index="result.result?.competition_index"
        />
      </div>

      <div v-else-if="result.analysis_type === 'risk_warning'" class="analysis-result__visual">
        <RiskWarningVisual
          :risks="result.result?.risks"
          :overall-risk="result.result?.overall_risk_level"
          :confidence="result.confidence"
          :score="result.result?.score"
        />
      </div>

      <div v-else class="analysis-result__gauge-row">
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
          <div v-if="result.analysis_type !== 'trend_score' && result.result.score != null" class="result-block">
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
          <div v-if="result.analysis_type !== 'risk_warning' && result.result.risks?.length" class="result-block">
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
          <div v-if="result.result.next_steps?.length" class="result-block">
            <div class="result-block__label">下一步行动</div>
            <ul class="result-list result-list--action">
              <li v-for="(step, idx) in result.result.next_steps" :key="idx">{{ step }}</li>
            </ul>
          </div>
        </template>
        <template v-else>
          <div class="result-plaintext">{{ formatResult(result.result) }}</div>
        </template>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import TrendScoreVisual from "./TrendScoreVisual.vue";
import PredictionVisual from "./PredictionVisual.vue";
import RiskWarningVisual from "./RiskWarningVisual.vue";

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
.ai-dialog :deep(.el-dialog__body) { padding: 24px; max-height: 70vh; overflow-y: auto; }
.analysis-result__tags { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
.analysis-result__visual { margin-bottom: 20px; }
.analysis-result__gauge-row { display: flex; gap: 20px; margin-bottom: 20px; align-items: center; }
.gauge-card { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.gauge-card__ring { width: 80px; height: 80px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 20px; font-weight: 700; }
.gauge-card__value { color: var(--color-text-primary); }
.gauge-card__label { font-size: var(--text-xs); color: var(--color-text-tertiary); }
.gauge-card__badge { font-size: var(--text-xs); padding: 2px 8px; border-radius: 10px; }
.gauge-card__badge.high { background: var(--color-success-bg); color: var(--color-success); }
.gauge-card__badge.medium { background: var(--color-warning-bg); color: var(--color-warning); }
.gauge-card__badge.low { background: var(--color-danger-bg); color: var(--color-danger); }
.analysis-result__tri-cards { display: flex; gap: 12px; flex: 1; }
.tri-card { flex: 1; padding: 12px; border-radius: var(--radius-lg); text-align: center; }
.tri-card--success { background: var(--color-success-bg); }
.tri-card--warning { background: var(--color-warning-bg); }
.tri-card--danger { background: var(--color-danger-bg); }
.tri-card--primary { background: var(--color-primary-lightest); }
.tri-card--info { background: var(--color-primary-lightest); }
.tri-card__value { font-size: 20px; font-weight: 700; }
.tri-card__label { font-size: var(--text-xs); color: var(--color-text-tertiary); margin-top: 4px; }
.analysis-result__content { font-size: var(--text-sm); color: var(--color-text-secondary); line-height: 1.6; }
.result-block { margin-bottom: 16px; }
.result-block--highlight { background: var(--color-primary-lightest); border-radius: var(--radius-base); padding: 12px 16px; border-left: 3px solid var(--color-primary); }
.result-block__label { font-size: var(--text-xs); font-weight: 600; color: var(--color-text-tertiary); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }
.result-block__text { color: var(--color-text-primary); }
.result-score-bar { display: flex; align-items: center; gap: 12px; }
.result-score-fill { height: 8px; border-radius: 4px; background: linear-gradient(90deg, var(--color-primary), #818CF8); flex: 1; }
.result-score-value { font-size: var(--text-sm); font-weight: 600; color: var(--color-text-primary); }
.result-list { padding-left: 20px; margin: 0; }
.result-list li { margin-bottom: 4px; }
.result-list--recommend li { color: var(--color-success); }
.result-list--risk li { color: var(--color-danger); }
.result-list--action li { color: var(--color-primary-light); }
.result-plaintext { white-space: pre-wrap; word-break: break-word; }
</style>
