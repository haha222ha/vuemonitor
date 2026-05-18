<template>
  <el-dialog :model-value="modelValue" @update:model-value="$emit('update:modelValue', $event)" :title="report?.title || '报告'" width="760px" class="ai-dialog">
    <div v-if="report" class="report-view">
      <div class="report-view__header">
        <div class="report-view__tags">
          <el-tag size="small" effect="light">{{ reportTypeLabel(report.report_type) }}</el-tag>
          <el-tag size="small" type="info" effect="light">{{ formatDate(report.created_at) }}</el-tag>
          <el-tag v-if="report.status" size="small" :type="report.status === 'completed' ? 'success' : 'warning'" effect="light">
            {{ report.status === 'completed' ? '已完成' : '生成中' }}
          </el-tag>
        </div>
      </div>

      <div v-if="isStructuredReport(report.content)" class="report-view__structured">
        <div v-if="report.content.executive_summary" class="report-section report-section--highlight">
          <h4>执行摘要</h4>
          <p>{{ report.content.executive_summary }}</p>
        </div>

        <div v-if="report.content.trend_score != null" class="report-section report-section--visual">
          <h4>趋势评分</h4>
          <div class="report-trend-mini">
            <div class="report-trend-gauge">
              <svg viewBox="0 0 100 100" class="report-trend-gauge__svg">
                <circle cx="50" cy="50" r="42" fill="none" stroke="var(--color-border-light)" stroke-width="6" />
                <circle cx="50" cy="50" r="42" fill="none" :stroke="trendScoreColor(report.content.trend_score)" stroke-width="6" stroke-linecap="round" :stroke-dasharray="2 * Math.PI * 42" :stroke-dashoffset="2 * Math.PI * 42 * (1 - Math.min(report.content.trend_score, 100) / 100)" class="report-trend-gauge__arc" />
              </svg>
              <div class="report-trend-gauge__center">
                <span class="report-trend-gauge__value" :style="{ color: trendScoreColor(report.content.trend_score) }">{{ report.content.trend_score }}</span>
                <span class="report-trend-gauge__unit">/100</span>
              </div>
            </div>
            <div class="report-trend-info">
              <span :class="['report-trend-badge', `report-trend-badge--${trendScoreLevel(report.content.trend_score)}`]">
                {{ trendScoreLevelLabel(report.content.trend_score) }}
              </span>
              <span class="report-trend-desc">{{ trendScoreDesc(report.content.trend_score) }}</span>
            </div>
          </div>
        </div>

        <div v-if="report.content.overall_risk_level" class="report-section report-section--visual">
          <h4>整体风险等级</h4>
          <div :class="['report-risk-banner', `report-risk-banner--${riskClass(report.content.overall_risk_level)}`]">
            <span class="report-risk-banner__icon">{{ riskIcon(report.content.overall_risk_level) }}</span>
            <div class="report-risk-banner__info">
              <span class="report-risk-banner__level">{{ riskLabel(report.content.overall_risk_level) }}</span>
              <span class="report-risk-banner__desc">{{ riskDesc(report.content.overall_risk_level) }}</span>
            </div>
          </div>
        </div>

        <div v-if="report.content.product_analysis" class="report-section">
          <h4>商品竞争力分析</h4>
          <div class="report-kv-grid">
            <template v-for="(val, key) in report.content.product_analysis" :key="key">
              <span class="report-kv-key">{{ formatKey(String(key)) }}</span>
              <span class="report-kv-val">
                <template v-if="typeof val === 'number'">
                  <span :class="['report-metric', numericClass(val, String(key))]">{{ formatNumeric(val, String(key)) }}</span>
                </template>
                <template v-else>{{ typeof val === 'object' ? JSON.stringify(val) : val }}</template>
              </span>
            </template>
          </div>
        </div>

        <div v-if="report.content.market_analysis" class="report-section">
          <h4>市场趋势分析</h4>
          <div class="report-text-block">{{ formatTextBlock(report.content.market_analysis) }}</div>
        </div>

        <div v-if="report.content.pricing_analysis" class="report-section">
          <h4>定价策略分析</h4>
          <div class="report-text-block">{{ formatTextBlock(report.content.pricing_analysis) }}</div>
        </div>

        <div v-if="report.content.competitive_position" class="report-section">
          <h4>竞争定位</h4>
          <div class="report-text-block">{{ formatTextBlock(report.content.competitive_position) }}</div>
        </div>

        <div v-if="report.content.trend_overview" class="report-section">
          <h4>趋势总览</h4>
          <div class="report-text-block">{{ formatTextBlock(report.content.trend_overview) }}</div>
        </div>

        <div v-if="report.content.recommendations?.length" class="report-section">
          <h4>选品建议</h4>
          <div class="report-list">
            <div v-for="(rec, i) in report.content.recommendations" :key="i" class="report-list-item report-list-item--recommend">
              <span class="report-list-index report-list-index--recommend">{{ i + 1 }}</span>
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
            <div v-for="(step, i) in report.content.next_steps" :key="i" class="report-list-item report-list-item--action">
              <span class="report-list-index report-list-index--action">{{ i + 1 }}</span>
              <span>{{ typeof step === 'string' ? step : step.action || JSON.stringify(step) }}</span>
            </div>
          </div>
        </div>

        <div v-if="report.content.mitigation_strategies?.length" class="report-section">
          <h4>风险缓解策略</h4>
          <div class="report-list">
            <div v-for="(s, i) in report.content.mitigation_strategies" :key="i" class="report-list-item report-list-item--mitigate">
              <span class="report-list-index report-list-index--mitigate">{{ i + 1 }}</span>
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
        <div class="report-plaintext">{{ typeof report.content === 'string' ? report.content : JSON.stringify(report.content, null, 2) }}</div>
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

function trendScoreColor(score: number): string {
  if (score >= 70) return '#10B981';
  if (score >= 40) return '#F59E0B';
  return '#EF4444';
}

function trendScoreLevel(score: number): string {
  if (score >= 80) return 'excellent';
  if (score >= 60) return 'good';
  if (score >= 40) return 'fair';
  return 'poor';
}

function trendScoreLevelLabel(score: number): string {
  const map: Record<string, string> = { excellent: '优秀', good: '良好', fair: '一般', poor: '较差' };
  return map[trendScoreLevel(score)] || '-';
}

function trendScoreDesc(score: number): string {
  if (score >= 80) return '趋势强劲，建议加大投入';
  if (score >= 60) return '趋势良好，持续关注';
  if (score >= 40) return '趋势一般，谨慎操作';
  return '趋势较弱，建议观望';
}

function riskClass(level: string): string {
  const map: Record<string, string> = { high: 'danger', critical: 'danger', medium: 'warning', low: 'safe', safe: 'safe' };
  return map[level.toLowerCase()] || 'warning';
}

function riskIcon(level: string): string {
  const cls = riskClass(level);
  const map: Record<string, string> = { danger: '⚠', warning: '⚡', safe: '✓' };
  return map[cls] || '?';
}

function riskLabel(level: string): string {
  const cls = riskClass(level);
  const map: Record<string, string> = { danger: '高风险', warning: '中等风险', safe: '低风险' };
  return map[cls] || level;
}

function riskDesc(level: string): string {
  const cls = riskClass(level);
  const map: Record<string, string> = { danger: '存在重大风险因素，建议立即处理', warning: '存在一定风险，需关注变化', safe: '风险可控，状态良好' };
  return map[cls] || '';
}

function formatTextBlock(content: any): string {
  if (typeof content === 'string') return content;
  if (typeof content === 'object' && content !== null) {
    return Object.entries(content)
      .map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : v}`)
      .join('\n');
  }
  return String(content);
}

function formatNumeric(val: number, key: string): string {
  if (key.includes('rate') || key.includes('growth') || key.includes('percentile')) return `${val.toFixed(1)}%`;
  if (key.includes('index') || key.includes('score')) return val.toFixed(2);
  return String(val);
}

function numericClass(val: number, key: string): string {
  if (key.includes('growth') || key.includes('rate')) return val >= 0 ? 'report-metric--up' : 'report-metric--down';
  if (key.includes('competition') || key.includes('risk')) return val > 0.7 ? 'report-metric--danger' : val > 0.4 ? 'report-metric--warning' : 'report-metric--safe';
  return '';
}
</script>

<style scoped>
.ai-dialog :deep(.el-dialog__header) { padding: 20px 24px; border-bottom: 1px solid var(--color-border-light); margin-right: 0; }
.ai-dialog :deep(.el-dialog__title) { font-size: var(--text-lg); font-weight: 600; color: var(--color-text-primary); }
.ai-dialog :deep(.el-dialog__body) { padding: 24px; max-height: 70vh; overflow-y: auto; }
.report-view__header { margin-bottom: 16px; }
.report-view__tags { display: flex; gap: 8px; flex-wrap: wrap; }
.report-view__structured { display: flex; flex-direction: column; gap: 16px; }
.report-section { padding: 12px 0; border-bottom: 1px solid var(--color-border-lighter); }
.report-section:last-child { border-bottom: none; }
.report-section--highlight { background: var(--color-primary-lightest); border-radius: var(--radius-base); padding: 12px 16px; border-left: 3px solid var(--color-primary); }
.report-section--visual { background: var(--color-bg-page); border-radius: var(--radius-base); padding: 16px; }
.report-section h4 { font-size: var(--text-sm); font-weight: 600; color: var(--color-text-primary); margin: 0 0 8px; }
.report-section p { font-size: var(--text-sm); color: var(--color-text-secondary); line-height: 1.6; margin: 0; white-space: pre-wrap; }
.report-trend-mini { display: flex; align-items: center; gap: 20px; }
.report-trend-gauge { position: relative; width: 80px; height: 80px; flex-shrink: 0; }
.report-trend-gauge__svg { width: 100%; height: 100%; transform: rotate(-90deg); }
.report-trend-gauge__arc { transition: stroke-dashoffset 0.8s ease-out; }
.report-trend-gauge__center { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.report-trend-gauge__value { font-size: 22px; font-weight: 700; line-height: 1; }
.report-trend-gauge__unit { font-size: 11px; color: var(--color-text-tertiary); }
.report-trend-info { display: flex; flex-direction: column; gap: 4px; }
.report-trend-badge { display: inline-block; padding: 3px 12px; border-radius: 10px; font-size: 13px; font-weight: 600; width: fit-content; }
.report-trend-badge--excellent { background: var(--color-success-bg); color: var(--color-success); }
.report-trend-badge--good { background: var(--color-primary-lightest); color: var(--color-primary-light); }
.report-trend-badge--fair { background: var(--color-warning-bg); color: var(--color-warning); }
.report-trend-badge--poor { background: var(--color-danger-bg); color: var(--color-danger); }
.report-trend-desc { font-size: 13px; color: var(--color-text-tertiary); }
.report-risk-banner { display: flex; align-items: center; gap: 14px; padding: 14px 18px; border-radius: var(--radius-lg); }
.report-risk-banner--danger { background: linear-gradient(135deg, var(--color-danger-bg), var(--color-bg-card)); border: 1px solid var(--color-danger-light); }
.report-risk-banner--warning { background: linear-gradient(135deg, var(--color-warning-bg), var(--color-bg-card)); border: 1px solid var(--color-warning-light); }
.report-risk-banner--safe { background: linear-gradient(135deg, var(--color-success-bg), var(--color-bg-card)); border: 1px solid var(--color-success-light); }
.report-risk-banner__icon { font-size: 28px; }
.report-risk-banner__info { display: flex; flex-direction: column; gap: 2px; }
.report-risk-banner__level { font-size: 16px; font-weight: 700; }
.report-risk-banner--danger .report-risk-banner__level { color: var(--color-danger-light); }
.report-risk-banner--warning .report-risk-banner__level { color: var(--color-warning-light); }
.report-risk-banner--safe .report-risk-banner__level { color: var(--color-success-light); }
.report-risk-banner__desc { font-size: 13px; }
.report-risk-banner--danger .report-risk-banner__desc { color: var(--color-danger-light); }
.report-risk-banner--warning .report-risk-banner__desc { color: var(--color-warning-light); }
.report-risk-banner--safe .report-risk-banner__desc { color: var(--color-success-light); }
.report-kv-grid { display: grid; grid-template-columns: auto 1fr; gap: 6px 16px; }
.report-kv-key { font-size: var(--text-xs); color: var(--color-text-tertiary); font-weight: 500; }
.report-kv-val { font-size: var(--text-sm); color: var(--color-text-primary); }
.report-metric { font-weight: 600; }
.report-metric--up { color: var(--color-success); }
.report-metric--down { color: var(--color-danger); }
.report-metric--safe { color: var(--color-success); }
.report-metric--warning { color: var(--color-warning); }
.report-metric--danger { color: var(--color-danger); }
.report-text-block { font-size: var(--text-sm); color: var(--color-text-secondary); line-height: 1.6; white-space: pre-wrap; }
.report-list { display: flex; flex-direction: column; gap: 8px; }
.report-list-item { display: flex; align-items: flex-start; gap: 10px; }
.report-list-index { flex-shrink: 0; width: 22px; height: 22px; border-radius: 50%; font-size: 12px; display: flex; align-items: center; justify-content: center; font-weight: 600; color: #fff; }
.report-list-index--recommend { background: var(--color-success); }
.report-list-index--action { background: var(--color-primary-light); }
.report-list-index--mitigate { background: var(--color-warning); }
.report-list-content { flex: 1; }
.report-list-reason { display: block; font-size: var(--text-xs); color: var(--color-text-tertiary); margin-top: 2px; }
.report-plaintext { white-space: pre-wrap; word-break: break-word; font-size: var(--text-sm); color: var(--color-text-secondary); line-height: 1.6; }
.report-view__footer { display: flex; justify-content: flex-end; gap: 8px; }
</style>
