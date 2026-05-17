<template>
  <div class="ai fade-in">
    <PageHeader title="AI 决策" subtitle="智能分析商品数据，生成决策洞察报告">
      <el-button type="primary" @click="showReportDialog = true">
        <el-icon><Document /></el-icon>
        生成报告
      </el-button>
    </PageHeader>

    <QuickActionGrid :actions="quickActions" @action="startQuickAnalysis" />

    <div v-if="recommendations.length > 0" class="ai__recommendations">
      <div class="recommendations__title">
        <el-icon :size="16"><Opportunity /></el-icon>
        <span>智能推荐</span>
        <el-tag size="small" effect="light" type="warning" class="recommendations__badge">基于您的数据</el-tag>
      </div>
      <div class="recommendations__grid">
        <div
          v-for="rec in recommendations"
          :key="rec.type + '-' + (rec.product_id || rec.event_id || rec.category)"
          class="recommendation-card"
          :class="[`recommendation-card--${rec.type}`]"
          @click="handleRecommendationClick(rec)"
        >
          <div class="recommendation-card__header">
            <div :class="['recommendation-card__icon', `recommendation-card__icon--${rec.type}`]">
              <el-icon :size="16"><component :is="recIcon(rec.type)" /></el-icon>
            </div>
            <el-tag size="small" :type="recTagType(rec.type)" effect="dark">{{ recLabel(rec.type) }}</el-tag>
          </div>
          <div class="recommendation-card__body">
            <div class="recommendation-card__name">{{ rec.product_name || rec.title || rec.category }}</div>
            <div class="recommendation-card__reason">{{ rec.reason }}</div>
          </div>
          <div class="recommendation-card__action">
            <el-icon :size="14"><ArrowRight /></el-icon>
          </div>
        </div>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="ai__tabs">
      <el-tab-pane name="analyses">
        <template #label>
          <span class="ai__tab-label">
            <el-icon :size="16"><DataAnalysis /></el-icon>
            分析记录
          </span>
        </template>

        <div class="ai__toolbar">
          <SearchInput placeholder="搜索分析记录..." @search="searchQuery = $event" />
          <div class="ai__filter-group">
            <el-select v-model="typeFilter" placeholder="分析类型" clearable size="default" style="width: 140px">
              <el-option v-for="(v, k) in ANALYSIS_TYPE_MAP" :key="k" :label="v.label" :value="k" />
            </el-select>
            <el-select v-model="statusFilter" placeholder="状态" clearable size="default" style="width: 120px">
              <el-option label="完成" value="completed" />
              <el-option label="处理中" value="processing" />
              <el-option label="失败" value="failed" />
            </el-select>
          </div>
        </div>

        <EmptyState
          v-if="!loading && filteredAnalyses.length === 0 && !searchQuery && !typeFilter && !statusFilter"
          :icon="DataAnalysis" title="暂无分析记录" description="对商品执行 AI 分析后，记录将显示在这里"
          action-label="前往商品页" :action-icon="DataAnalysis" @action="router.push('/products')"
        />
        <EmptyState v-else-if="!loading && filteredAnalyses.length === 0" :icon="Search" title="未找到匹配记录" description="尝试调整筛选条件" />

        <div v-else class="ai__grid">
          <div v-for="item in filteredAnalyses" :key="item.id" class="analysis-card" @click="viewAnalysis(item)">
            <div class="analysis-card__header">
              <div :class="['analysis-card__type-icon', `analysis-card__type-icon--${analysisTypeTag(item.analysis_type)}`]">
                <el-icon :size="18"><component :is="analysisTypeIcon(item.analysis_type)" /></el-icon>
              </div>
              <div class="analysis-card__meta">
                <div class="analysis-card__type">{{ analysisTypeLabel(item.analysis_type) }}</div>
                <div class="analysis-card__model">{{ item.provider }} / {{ item.model }}</div>
              </div>
              <el-tag :type="item.status === 'completed' ? 'success' : item.status === 'failed' ? 'danger' : 'warning'" size="small" effect="light" class="analysis-card__status">
                {{ statusLabel(item.status) }}
              </el-tag>
            </div>
            <div class="analysis-card__body">
              <div v-if="item.confidence" class="analysis-card__confidence">
                <span class="analysis-card__confidence-label">置信度</span>
                <div class="analysis-card__confidence-bar">
                  <div class="analysis-card__confidence-fill" :style="{ width: `${(item.confidence * 100).toFixed(0)}%` }" :class="item.confidence >= 0.8 ? 'high' : item.confidence >= 0.5 ? 'medium' : 'low'" />
                </div>
                <span class="analysis-card__confidence-value">{{ (item.confidence * 100).toFixed(0) }}%</span>
              </div>
              <div v-if="item.result" class="analysis-card__preview">
                {{ formatResult(item.result).substring(0, 120) }}{{ formatResult(item.result).length > 120 ? '...' : '' }}
              </div>
            </div>
            <div class="analysis-card__footer">
              <span class="analysis-card__time">{{ formatDate(item.created_at) }}</span>
              <el-button size="small" type="primary" text @click="viewAnalysis(item)">查看详情</el-button>
            </div>
          </div>
        </div>

        <div v-if="loading" class="ai__loading"><el-skeleton :rows="3" animated /></div>
      </el-tab-pane>

      <el-tab-pane name="reports">
        <template #label>
          <span class="ai__tab-label">
            <el-icon :size="16"><Document /></el-icon>
            分析报告
          </span>
        </template>

        <EmptyState v-if="!reportsLoading && reports.length === 0" :icon="Document" title="暂无分析报告" description="点击右上角「生成报告」创建您的第一份报告" />

        <div v-else class="ai__reports">
          <div v-for="report in reports" :key="report.id" class="report-card" @click="viewReport(report)">
            <div class="report-card__header">
              <div class="report-card__icon"><el-icon :size="20"><Document /></el-icon></div>
              <div class="report-card__info">
                <div class="report-card__title">{{ report.title }}</div>
                <div class="report-card__meta">
                  <el-tag size="small" effect="light">{{ reportTypeLabel(report.report_type) }}</el-tag>
                  <span class="report-card__time">{{ formatDate(report.created_at) }}</span>
                </div>
              </div>
              <el-tag :type="report.status === 'completed' ? 'success' : 'warning'" size="small" effect="light">
                {{ report.status === 'completed' ? '完成' : '生成中' }}
              </el-tag>
            </div>
            <div v-if="report.content" class="report-card__preview">
              {{ typeof report.content === 'string' ? report.content.substring(0, 160) : report.content.executive_summary || JSON.stringify(report.content).substring(0, 160) }}{{ (typeof report.content === 'string' ? report.content : JSON.stringify(report.content)).length > 160 ? '...' : '' }}
            </div>
            <div class="report-card__actions">
              <el-button size="small" type="primary" text @click.stop="viewReport(report)">查看</el-button>
              <el-dropdown trigger="click" @command="(cmd: string) => exportReport(report, cmd)" @click.stop>
                <el-button size="small" text type="success" @click.stop>导出</el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="markdown">Markdown</el-dropdown-item>
                    <el-dropdown-item command="html">HTML</el-dropdown-item>
                    <el-dropdown-item command="pdf">PDF</el-dropdown-item>
                    <el-dropdown-item command="json">JSON</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
        </div>

        <div v-if="reportsLoading" class="ai__loading"><el-skeleton :rows="3" animated /></div>
      </el-tab-pane>
    </el-tabs>

    <AnalysisResultDialog
      v-model="showResult"
      :result="currentResult"
      :analysis-type-label="analysisTypeLabel"
      :analysis-type-tag="analysisTypeTag"
      :format-result="formatResult"
      :is-structured-result="isStructuredResult"
      :confidence-gauge-style="confidenceGaugeStyle"
      :confidence-level="confidenceLevel"
    />

    <ReportViewDialog
      v-model="showReportView"
      :report="currentReport"
      :report-type-label="reportTypeLabel"
      :format-date="formatDate"
      :format-key="formatKey"
      :is-structured-report="isStructuredReport"
      :export-report="exportReport"
    />

    <ReportGenerateDialog
      v-model="showReportDialog"
      :report-form="reportForm"
      :products="products"
      :generating="generating"
      :on-generate="handleGenerateReport"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import PageHeader from "../components/PageHeader.vue";
import SearchInput from "../components/SearchInput.vue";
import EmptyState from "../components/EmptyState.vue";
import QuickActionGrid from "../components/QuickActionGrid.vue";
import AnalysisResultDialog from "../components/ai/AnalysisResultDialog.vue";
import ReportViewDialog from "../components/ai/ReportViewDialog.vue";
import ReportGenerateDialog from "../components/ai/ReportGenerateDialog.vue";
import { useAIData, ANALYSIS_TYPE_MAP } from "../composables/useAIData";
import { DataAnalysis, Document, Search, TrendCharts, Warning, PriceTag, Star, Cpu, Opportunity, ArrowRight } from "@element-plus/icons-vue";

const router = useRouter();
const activeTab = ref("analyses");
const showResult = ref(false);
const showReportView = ref(false);
const showReportDialog = ref(false);
const currentResult = ref<any>(null);
const currentReport = ref<any>(null);

const {
  analyses, reports, products, recommendations,
  loading, reportsLoading, generating,
  searchQuery, typeFilter, statusFilter,
  reportForm, filteredAnalyses,
  analysisTypeLabel, analysisTypeTag, analysisTypeIcon, reportTypeLabel, statusLabel,
  formatDate, formatResult, isStructuredResult, isStructuredReport,
  confidenceGaugeStyle, confidenceLevel, formatKey,
  fetchAnalyses, fetchReports, fetchProducts, fetchRecommendations,
  startQuickAnalysis, handleGenerateReport, exportReport,
  recIcon, recTagType, recLabel,
} = useAIData();

const quickActions = [
  { type: "trend_score", label: "趋势评分", desc: "评估商品趋势走向", icon: TrendCharts, color: "success" },
  { type: "prediction", label: "爆品预测", desc: "预测爆款潜力", icon: Opportunity, color: "amber" },
  { type: "risk_warning", label: "风险预警", desc: "识别潜在风险信号", icon: Warning, color: "danger" },
  { type: "basic_analysis", label: "基础分析", desc: "全面商品数据分析", icon: DataAnalysis, color: "primary" },
];

function viewAnalysis(row: any) { currentResult.value = row; showResult.value = true; }
function viewReport(row: any) { currentReport.value = row; showReportView.value = true; }

function handleRecommendationClick(rec: any) {
  if (rec.type === "alert" && rec.event_id) router.push("/notifications");
  else if (rec.product_id) router.push(`/products/${rec.product_id}`);
  else if (rec.type === "category_insight" && rec.category) router.push("/dashboard");
}

onMounted(() => { fetchAnalyses(); fetchReports(); fetchProducts(); fetchRecommendations(); });
</script>

<style scoped>
.ai { padding: 0; }
.ai__recommendations { padding: 20px 24px; background: linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%); border-bottom: 1px solid #FDE68A; }
.recommendations__title { display: flex; align-items: center; gap: 8px; font-size: var(--text-sm); font-weight: 600; color: #92400E; margin-bottom: 12px; }
.recommendations__badge { margin-left: 4px; }
.recommendations__grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 10px; }
.recommendation-card { display: flex; align-items: center; gap: 12px; padding: 12px 16px; background: rgba(255, 255, 255, 0.85); border: 1px solid #FDE68A; border-radius: var(--radius-lg); cursor: pointer; transition: all 0.2s; backdrop-filter: blur(4px); }
.recommendation-card:hover { border-color: #D97706; box-shadow: 0 4px 12px rgba(217, 119, 6, 0.15); transform: translateY(-1px); }
.recommendation-card--alert { border-color: #FCA5A5; background: rgba(255, 255, 255, 0.9); }
.recommendation-card--alert:hover { border-color: #EF4444; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.15); }
.recommendation-card--risk { border-color: #FED7AA; background: rgba(255, 255, 255, 0.9); }
.recommendation-card--risk:hover { border-color: #F97316; box-shadow: 0 4px 12px rgba(249, 115, 22, 0.15); }
.recommendation-card--trending { border-color: #BBF7D0; background: rgba(255, 255, 255, 0.9); }
.recommendation-card--trending:hover { border-color: #22C55E; box-shadow: 0 4px 12px rgba(34, 197, 94, 0.15); }
.recommendation-card__header { display: flex; flex-direction: column; align-items: center; gap: 6px; flex-shrink: 0; }
.recommendation-card__icon { width: 36px; height: 36px; border-radius: var(--radius-base); display: flex; align-items: center; justify-content: center; color: #fff; }
.recommendation-card__icon--trending { background: linear-gradient(135deg, #22C55E, #16A34A); }
.recommendation-card__icon--alert { background: linear-gradient(135deg, #EF4444, #DC2626); }
.recommendation-card__icon--category_insight { background: linear-gradient(135deg, #F59E0B, #D97706); }
.recommendation-card__icon--risk { background: linear-gradient(135deg, #F97316, #EA580C); }
.recommendation-card__body { flex: 1; min-width: 0; }
.recommendation-card__name { font-size: var(--text-sm); font-weight: 600; color: var(--color-text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.recommendation-card__reason { font-size: var(--text-xs); color: var(--color-text-secondary); margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.recommendation-card__action { flex-shrink: 0; color: var(--color-text-tertiary); transition: color 0.2s; }
.ai__toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; gap: 12px; flex-wrap: wrap; }
.ai__filter-group { display: flex; gap: 8px; }
.ai__grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
.analysis-card { background: var(--color-bg-card); border: 1px solid var(--color-border-light); border-radius: var(--radius-lg); padding: 16px; cursor: pointer; transition: all 0.2s; }
.analysis-card:hover { border-color: var(--color-primary); box-shadow: 0 4px 12px rgba(79, 70, 229, 0.1); }
.analysis-card__header { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.analysis-card__type-icon { width: 40px; height: 40px; border-radius: var(--radius-base); display: flex; align-items: center; justify-content: center; color: #fff; }
.analysis-card__type-icon--success { background: linear-gradient(135deg, #10B981, #059669); }
.analysis-card__type-icon--warning { background: linear-gradient(135deg, #F59E0B, #D97706); }
.analysis-card__type-icon--danger { background: linear-gradient(135deg, #EF4444, #DC2626); }
.analysis-card__type-icon--primary { background: linear-gradient(135deg, #6366F1, #4F46E5); }
.analysis-card__meta { flex: 1; min-width: 0; }
.analysis-card__type { font-size: var(--text-sm); font-weight: 600; color: var(--color-text-primary); }
.analysis-card__model { font-size: var(--text-xs); color: var(--color-text-tertiary); }
.analysis-card__status { flex-shrink: 0; }
.analysis-card__body { margin-bottom: 12px; }
.analysis-card__confidence { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.analysis-card__confidence-label { font-size: var(--text-xs); color: var(--color-text-tertiary); min-width: 40px; }
.analysis-card__confidence-bar { flex: 1; height: 6px; background: var(--color-bg-muted); border-radius: 3px; overflow: hidden; }
.analysis-card__confidence-fill { height: 100%; border-radius: 3px; transition: width 0.3s; }
.analysis-card__confidence-fill.high { background: linear-gradient(90deg, #10B981, #059669); }
.analysis-card__confidence-fill.medium { background: linear-gradient(90deg, #F59E0B, #D97706); }
.analysis-card__confidence-fill.low { background: linear-gradient(90deg, #EF4444, #DC2626); }
.analysis-card__confidence-value { font-size: var(--text-xs); font-weight: 600; min-width: 36px; text-align: right; }
.analysis-card__preview { font-size: var(--text-xs); color: var(--color-text-secondary); line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.analysis-card__footer { display: flex; align-items: center; justify-content: space-between; padding-top: 12px; border-top: 1px solid var(--color-border-lighter); }
.analysis-card__time { font-size: var(--text-xs); color: var(--color-text-tertiary); }
.ai__reports { display: flex; flex-direction: column; gap: 12px; }
.report-card { background: var(--color-bg-card); border: 1px solid var(--color-border-light); border-radius: var(--radius-lg); padding: 16px; cursor: pointer; transition: all 0.2s; }
.report-card:hover { border-color: var(--color-primary); box-shadow: 0 4px 12px rgba(79, 70, 229, 0.1); }
.report-card__header { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.report-card__icon { width: 40px; height: 40px; border-radius: var(--radius-base); background: #DBEAFE; display: flex; align-items: center; justify-content: center; color: #3B82F6; }
.report-card__info { flex: 1; min-width: 0; }
.report-card__title { font-size: var(--text-sm); font-weight: 600; color: var(--color-text-primary); }
.report-card__meta { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
.report-card__time { font-size: var(--text-xs); color: var(--color-text-tertiary); }
.report-card__preview { font-size: var(--text-xs); color: var(--color-text-secondary); line-height: 1.5; margin-bottom: 8px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.report-card__actions { display: flex; gap: 8px; }
.ai__loading { padding: 20px 0; }
.ai__tabs :deep(.el-tabs__header) { margin-bottom: 16px; }
.ai__tab-label { display: flex; align-items: center; gap: 6px; }
</style>
