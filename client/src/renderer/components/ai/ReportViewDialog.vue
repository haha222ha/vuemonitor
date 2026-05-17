<template>
  <el-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)" :title="report?.title || '报告'" width="760px" class="ai-dialog">
    <div v-if="report" class="report-view">
      <div class="report-view__tags">
        <el-tag size="small" effect="light">{{ reportTypeLabel(report.report_type) }}</el-tag>
        <el-tag size="small" type="info" effect="light">{{ formatDate(report.created_at) }}</el-tag>
      </div>
      <div v-if="isStructuredReport(report.content)" class="report-view__structured">
        <div v-if="report.content.executive_summary" class="report-section report-section--highlight">
          <h4>执行摘要</h4>
          <p>{{ report.content.executive_summary }}</p>
        </div>
        <div v-if="report.content.product_analysis" class="report-section">
          <h4>商品竞争力分析</h4>
          <div class="report-kv-grid">
            <template v-for="(val, key) in report.content.product_analysis" :key="key">
              <span class="report-kv-key">{{ formatKey(String(key)) }}</span>
              <span class="report-kv-val">{{ typeof val === 'object' ? JSON.stringify(val) : val }}</span>
            </template>
          </div>
        </div>
        <div v-if="report.content.market_analysis" class="report-section">
          <h4>市场趋势分析</h4>
          <p>{{ typeof report.content.market_analysis === 'string' ? report.content.market_analysis : JSON.stringify(report.content.market_analysis, null, 2) }}</p>
        </div>
        <div v-if="report.content.pricing_analysis" class="report-section">
          <h4>定价策略分析</h4>
          <p>{{ typeof report.content.pricing_analysis === 'string' ? report.content.pricing_analysis : JSON.stringify(report.content.pricing_analysis, null, 2) }}</p>
        </div>
        <div v-if="report.content.competitive_position" class="report-section">
          <h4>竞争定位</h4>
          <p>{{ typeof report.content.competitive_position === 'string' ? report.content.competitive_position : JSON.stringify(report.content.competitive_position, null, 2) }}</p>
        </div>
        <div v-if="report.content.trend_overview" class="report-section">
          <h4>趋势总览</h4>
          <p>{{ typeof report.content.trend_overview === 'string' ? report.content.trend_overview : JSON.stringify(report.content.trend_overview, null, 2) }}</p>
        </div>
        <div v-if="report.content.trend_score != null" class="report-section">
          <h4>趋势评分</h4>
          <div class="report-score-bar">
            <div class="report-score-fill" :style="{ width: `${report.content.trend_score}%` }" :class="report.content.trend_score >= 70 ? 'high' : report.content.trend_score >= 40 ? 'medium' : 'low'" />
            <span class="report-score-value">{{ report.content.trend_score }}/100</span>
          </div>
        </div>
        <div v-if="report.content.overall_risk_level" class="report-section">
          <h4>整体风险等级</h4>
          <el-tag :type="report.content.overall_risk_level === 'high' ? 'danger' : report.content.overall_risk_level === 'medium' ? 'warning' : 'success'" size="large" effect="dark">
            {{ report.content.overall_risk_level === 'high' ? '高风险' : report.content.overall_risk_level === 'medium' ? '中等风险' : '低风险' }}
          </el-tag>
        </div>
        <div v-if="report.content.recommendations?.length" class="report-section">
          <h4>选品建议</h4>
          <div class="report-list">
            <div v-for="(rec, i) in report.content.recommendations" :key="i" class="report-list-item">
              <span class="report-list-index">{{ i + 1 }}</span>
              <div class="report-list-content">
                <strong>{{ rec.action || rec }}</strong>
                <span v-if="rec.reason" class="report-list-reason">{{ rec.reason }}</span>
              </div>
            </div>
          </div>
        </div>
        <div v-if="report.content.next_steps?.length" class="report-section">
          <h4>下一步行动</h4>
          <div class="report-list">
            <div v-for="(step, i) in report.content.next_steps" :key="i" class="report-list-item">
              <span class="report-list-index">{{ i + 1 }}</span>
              <span>{{ typeof step === 'string' ? step : step.action || JSON.stringify(step) }}</span>
            </div>
          </div>
        </div>
        <div v-if="report.content.mitigation_strategies?.length" class="report-section">
          <h4>风险缓解策略</h4>
          <div class="report-list">
            <div v-for="(s, i) in report.content.mitigation_strategies" :key="i" class="report-list-item">
              <span class="report-list-index">{{ i + 1 }}</span>
              <span>{{ typeof s === 'string' ? s : s.action || JSON.stringify(s) }}</span>
            </div>
          </div>
        </div>
        <div v-if="report.content.conclusion" class="report-section report-section--highlight">
          <h4>结论</h4>
          <p>{{ report.content.conclusion }}</p>
        </div>
      </div>
      <div v-else class="report-view__content">
        {{ typeof report.content === 'string' ? report.content : JSON.stringify(report.content, null, 2) }}
      </div>
    </div>
    <template #footer>
      <div class="report-view__footer">
        <el-button size="default" @click="exportReport(report, 'markdown')">导出 Markdown</el-button>
        <el-button size="default" type="primary" @click="exportReport(report, 'html')">导出 HTML</el-button>
        <el-button size="default" type="success" @click="exportReport(report, 'pdf')">导出 PDF</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: boolean;
  report: any;
  reportTypeLabel: (t: string) => string;
  formatDate: (d: string) => string;
  formatKey: (k: string) => string;
  isStructuredReport: (c: any) => boolean;
  exportReport: (r: any, fmt: string) => void;
}>();

defineEmits<{ (e: "update:modelValue", value: boolean): void }>();
</script>

<style scoped>
.ai-dialog :deep(.el-dialog__header) { padding: 20px 24px; border-bottom: 1px solid var(--color-border-light); margin-right: 0; }
.ai-dialog :deep(.el-dialog__title) { font-size: var(--text-lg); font-weight: 600; color: var(--color-text-primary); }
.ai-dialog :deep(.el-dialog__body) { padding: 24px; }
.report-view__tags { display: flex; gap: 8px; margin-bottom: 16px; }
.report-view__structured { display: flex; flex-direction: column; gap: 16px; }
.report-section { padding: 12px 0; border-bottom: 1px solid var(--color-border-lighter); }
.report-section:last-child { border-bottom: none; }
.report-section--highlight { background: #F0F9FF; border-radius: var(--radius-base); padding: 12px 16px; border-left: 3px solid var(--color-primary); }
.report-section h4 { font-size: var(--text-sm); font-weight: 600; color: var(--color-text-primary); margin: 0 0 8px; }
.report-section p { font-size: var(--text-sm); color: var(--color-text-secondary); line-height: 1.6; margin: 0; white-space: pre-wrap; }
.report-kv-grid { display: grid; grid-template-columns: auto 1fr; gap: 6px 16px; }
.report-kv-key { font-size: var(--text-xs); color: var(--color-text-tertiary); font-weight: 500; }
.report-kv-val { font-size: var(--text-sm); color: var(--color-text-primary); }
.report-score-bar { display: flex; align-items: center; gap: 12px; }
.report-score-fill { height: 8px; border-radius: 4px; flex: 1; }
.report-score-fill.high { background: linear-gradient(90deg, #10B981, #059669); }
.report-score-fill.medium { background: linear-gradient(90deg, #F59E0B, #D97706); }
.report-score-fill.low { background: linear-gradient(90deg, #EF4444, #DC2626); }
.report-score-value { font-size: var(--text-sm); font-weight: 600; }
.report-list { display: flex; flex-direction: column; gap: 8px; }
.report-list-item { display: flex; align-items: flex-start; gap: 10px; }
.report-list-index { flex-shrink: 0; width: 22px; height: 22px; border-radius: 50%; background: var(--color-primary); color: #fff; font-size: 12px; display: flex; align-items: center; justify-content: center; font-weight: 600; }
.report-list-content { flex: 1; }
.report-list-reason { display: block; font-size: var(--text-xs); color: var(--color-text-tertiary); margin-top: 2px; }
.report-view__content { font-size: var(--text-sm); color: var(--color-text-secondary); line-height: 1.6; white-space: pre-wrap; }
.report-view__footer { display: flex; justify-content: flex-end; gap: 8px; }
</style>
