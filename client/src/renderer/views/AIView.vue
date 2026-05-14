<template>
  <div class="ai fade-in">
    <PageHeader title="AI 决策" subtitle="智能分析商品数据，生成决策洞察报告">
      <el-button type="primary" @click="showReportDialog = true">
        <el-icon><Document /></el-icon>
        生成报告
      </el-button>
    </PageHeader>

    <div v-if="products.length > 0" class="ai__quick-actions">
      <div class="quick-actions__title">
        <el-icon :size="16"><MagicStick /></el-icon>
        <span>快捷分析</span>
      </div>
      <div class="quick-actions__grid">
        <div
          v-for="action in quickActions"
          :key="action.type"
          class="quick-action-card"
          @click="startQuickAnalysis(action.type)"
        >
          <div :class="['quick-action-card__icon', `quick-action-card__icon--${action.color}`]">
            <el-icon :size="20"><component :is="action.icon" /></el-icon>
          </div>
          <div class="quick-action-card__info">
            <div class="quick-action-card__label">{{ action.label }}</div>
            <div class="quick-action-card__desc">{{ action.desc }}</div>
          </div>
        </div>
      </div>
    </div>

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
          :icon="DataAnalysis"
          title="暂无分析记录"
          description="对商品执行 AI 分析后，记录将显示在这里"
        />

        <EmptyState
          v-else-if="!loading && filteredAnalyses.length === 0"
          :icon="Search"
          title="未找到匹配记录"
          description="尝试调整筛选条件"
        />

        <div v-else class="ai__grid">
          <div
            v-for="item in filteredAnalyses"
            :key="item.id"
            class="analysis-card"
            @click="viewAnalysis(item)"
          >
            <div class="analysis-card__header">
              <div :class="['analysis-card__type-icon', `analysis-card__type-icon--${analysisTypeTag(item.analysis_type)}`]">
                <el-icon :size="18"><component :is="analysisTypeIcon(item.analysis_type)" /></el-icon>
              </div>
              <div class="analysis-card__meta">
                <div class="analysis-card__type">{{ analysisTypeLabel(item.analysis_type) }}</div>
                <div class="analysis-card__model">{{ item.provider }} / {{ item.model }}</div>
              </div>
              <el-tag
                :type="item.status === 'completed' ? 'success' : item.status === 'failed' ? 'danger' : 'warning'"
                size="small"
                effect="light"
                class="analysis-card__status"
              >
                {{ statusLabel(item.status) }}
              </el-tag>
            </div>

            <div class="analysis-card__body">
              <div v-if="item.confidence" class="analysis-card__confidence">
                <span class="analysis-card__confidence-label">置信度</span>
                <div class="analysis-card__confidence-bar">
                  <div
                    class="analysis-card__confidence-fill"
                    :style="{ width: `${(item.confidence * 100).toFixed(0)}%` }"
                    :class="item.confidence >= 0.8 ? 'high' : item.confidence >= 0.5 ? 'medium' : 'low'"
                  />
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

        <div v-if="loading" class="ai__loading">
          <el-skeleton :rows="3" animated />
        </div>
      </el-tab-pane>

      <el-tab-pane name="reports">
        <template #label>
          <span class="ai__tab-label">
            <el-icon :size="16"><Document /></el-icon>
            分析报告
          </span>
        </template>

        <EmptyState
          v-if="!reportsLoading && reports.length === 0"
          :icon="Document"
          title="暂无分析报告"
          description="点击右上角「生成报告」创建您的第一份报告"
        />

        <div v-else class="ai__reports">
          <div
            v-for="report in reports"
            :key="report.id"
            class="report-card"
            @click="viewReport(report)"
          >
            <div class="report-card__header">
              <div class="report-card__icon">
                <el-icon :size="20"><Document /></el-icon>
              </div>
              <div class="report-card__info">
                <div class="report-card__title">{{ report.title }}</div>
                <div class="report-card__meta">
                  <el-tag size="small" effect="light">{{ reportTypeLabel(report.report_type) }}</el-tag>
                  <span class="report-card__time">{{ formatDate(report.created_at) }}</span>
                </div>
              </div>
              <el-tag
                :type="report.status === 'completed' ? 'success' : 'warning'"
                size="small"
                effect="light"
              >
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

        <div v-if="reportsLoading" class="ai__loading">
          <el-skeleton :rows="3" animated />
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="showResult" title="分析结果" width="720px" class="ai-dialog">
      <div v-if="currentResult" class="analysis-result">
        <div class="analysis-result__tags">
          <el-tag size="small" :type="analysisTypeTag(currentResult.analysis_type)" effect="light">
            {{ analysisTypeLabel(currentResult.analysis_type) }}
          </el-tag>
          <el-tag v-if="currentResult.confidence" size="small" type="info" effect="light">
            置信度 {{ (currentResult.confidence * 100).toFixed(0) }}%
          </el-tag>
          <el-tag size="small" effect="light">
            {{ currentResult.provider }} / {{ currentResult.model }}
          </el-tag>
        </div>
        <div v-if="currentResult.confidence" class="analysis-result__gauge-row">
          <div class="gauge-card">
            <div class="gauge-card__ring" :style="confidenceGaugeStyle(currentResult.confidence)">
              <span class="gauge-card__value">{{ (currentResult.confidence * 100).toFixed(0) }}</span>
            </div>
            <div class="gauge-card__label">置信度</div>
            <div :class="['gauge-card__badge', confidenceLevel(currentResult.confidence)]">
              {{ confidenceLevel(currentResult.confidence) === 'high' ? '高可信' : confidenceLevel(currentResult.confidence) === 'medium' ? '中等' : '待验证' }}
            </div>
          </div>
          <div class="analysis-result__tri-cards">
            <div :class="['tri-card', currentResult.confidence >= 0.8 ? 'tri-card--success' : currentResult.confidence >= 0.5 ? 'tri-card--warning' : 'tri-card--danger']">
              <div class="tri-card__value">{{ currentResult.confidence >= 0.8 ? '✓' : currentResult.confidence >= 0.5 ? '!' : '✗' }}</div>
              <div class="tri-card__label">可信度</div>
            </div>
            <div class="tri-card tri-card--primary">
              <div class="tri-card__value">{{ analysisTypeLabel(currentResult.analysis_type).substring(0, 2) }}</div>
              <div class="tri-card__label">类型</div>
            </div>
            <div class="tri-card tri-card--info">
              <div class="tri-card__value">{{ currentResult.provider?.substring(0, 3) || 'AI' }}</div>
              <div class="tri-card__label">模型</div>
            </div>
          </div>
        </div>
        <div class="analysis-result__content">
          {{ formatResult(currentResult.result) }}
        </div>
      </div>
    </el-dialog>

    <el-dialog v-model="showReportView" :title="currentReport?.title || '报告'" width="760px" class="ai-dialog">
      <div v-if="currentReport" class="report-view">
        <div class="report-view__tags">
          <el-tag size="small" effect="light">{{ reportTypeLabel(currentReport.report_type) }}</el-tag>
          <el-tag size="small" type="info" effect="light">{{ formatDate(currentReport.created_at) }}</el-tag>
        </div>
        <div v-if="isStructuredReport(currentReport.content)" class="report-view__structured">
          <div v-if="currentReport.content.executive_summary" class="report-section report-section--highlight">
            <h4>执行摘要</h4>
            <p>{{ currentReport.content.executive_summary }}</p>
          </div>
          <div v-if="currentReport.content.product_analysis" class="report-section">
            <h4>商品竞争力分析</h4>
            <div class="report-kv-grid">
              <template v-for="(val, key) in currentReport.content.product_analysis" :key="key">
                <span class="report-kv-key">{{ formatKey(String(key)) }}</span>
                <span class="report-kv-val">{{ typeof val === 'object' ? JSON.stringify(val) : val }}</span>
              </template>
            </div>
          </div>
          <div v-if="currentReport.content.market_analysis" class="report-section">
            <h4>市场趋势分析</h4>
            <p>{{ typeof currentReport.content.market_analysis === 'string' ? currentReport.content.market_analysis : JSON.stringify(currentReport.content.market_analysis, null, 2) }}</p>
          </div>
          <div v-if="currentReport.content.pricing_analysis" class="report-section">
            <h4>定价策略分析</h4>
            <p>{{ typeof currentReport.content.pricing_analysis === 'string' ? currentReport.content.pricing_analysis : JSON.stringify(currentReport.content.pricing_analysis, null, 2) }}</p>
          </div>
          <div v-if="currentReport.content.competitive_position" class="report-section">
            <h4>竞争定位</h4>
            <p>{{ typeof currentReport.content.competitive_position === 'string' ? currentReport.content.competitive_position : JSON.stringify(currentReport.content.competitive_position, null, 2) }}</p>
          </div>
          <div v-if="currentReport.content.trend_overview" class="report-section">
            <h4>趋势总览</h4>
            <p>{{ typeof currentReport.content.trend_overview === 'string' ? currentReport.content.trend_overview : JSON.stringify(currentReport.content.trend_overview, null, 2) }}</p>
          </div>
          <div v-if="currentReport.content.trend_score != null" class="report-section">
            <h4>趋势评分</h4>
            <div class="report-score-bar">
              <div class="report-score-fill" :style="{ width: `${currentReport.content.trend_score}%` }" :class="currentReport.content.trend_score >= 70 ? 'high' : currentReport.content.trend_score >= 40 ? 'medium' : 'low'" />
              <span class="report-score-value">{{ currentReport.content.trend_score }}/100</span>
            </div>
          </div>
          <div v-if="currentReport.content.overall_risk_level" class="report-section">
            <h4>整体风险等级</h4>
            <el-tag :type="currentReport.content.overall_risk_level === 'high' ? 'danger' : currentReport.content.overall_risk_level === 'medium' ? 'warning' : 'success'" size="large" effect="dark">
              {{ currentReport.content.overall_risk_level === 'high' ? '高风险' : currentReport.content.overall_risk_level === 'medium' ? '中等风险' : '低风险' }}
            </el-tag>
          </div>
          <div v-if="currentReport.content.recommendations?.length" class="report-section">
            <h4>选品建议</h4>
            <div class="report-list">
              <div v-for="(rec, i) in currentReport.content.recommendations" :key="i" class="report-list-item">
                <span class="report-list-index">{{ i + 1 }}</span>
                <div class="report-list-content">
                  <strong>{{ rec.action || rec }}</strong>
                  <span v-if="rec.reason" class="report-list-reason">{{ rec.reason }}</span>
                </div>
              </div>
            </div>
          </div>
          <div v-if="currentReport.content.next_steps?.length" class="report-section">
            <h4>下一步行动</h4>
            <div class="report-list">
              <div v-for="(step, i) in currentReport.content.next_steps" :key="i" class="report-list-item">
                <span class="report-list-index">{{ i + 1 }}</span>
                <span>{{ typeof step === 'string' ? step : step.action || JSON.stringify(step) }}</span>
              </div>
            </div>
          </div>
          <div v-if="currentReport.content.mitigation_strategies?.length" class="report-section">
            <h4>风险缓解策略</h4>
            <div class="report-list">
              <div v-for="(s, i) in currentReport.content.mitigation_strategies" :key="i" class="report-list-item">
                <span class="report-list-index">{{ i + 1 }}</span>
                <span>{{ typeof s === 'string' ? s : s.action || JSON.stringify(s) }}</span>
              </div>
            </div>
          </div>
          <div v-if="currentReport.content.conclusion" class="report-section report-section--highlight">
            <h4>结论</h4>
            <p>{{ currentReport.content.conclusion }}</p>
          </div>
        </div>
        <div v-else class="report-view__content">
          {{ typeof currentReport.content === 'string' ? currentReport.content : JSON.stringify(currentReport.content, null, 2) }}
        </div>
      </div>
      <template #footer>
        <div class="report-view__footer">
          <el-button size="default" @click="exportReport(currentReport, 'markdown')">导出 Markdown</el-button>
          <el-button size="default" type="primary" @click="exportReport(currentReport, 'html')">导出 HTML</el-button>
          <el-button size="default" type="success" @click="exportReport(currentReport, 'pdf')">导出 PDF</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="showReportDialog" title="生成分析报告" width="540px" class="ai-dialog">
      <el-form :model="reportForm" label-width="100px" :rules="reportFormRules" ref="reportFormRef">
        <el-form-item label="报告标题" prop="title">
          <el-input v-model="reportForm.title" placeholder="如：本周商品分析报告" />
        </el-form-item>
        <el-form-item label="报告类型" prop="report_type">
          <el-select v-model="reportForm.report_type" style="width: 100%">
            <el-option label="商品分析" value="product" />
            <el-option label="品类分析" value="category" />
            <el-option label="趋势分析" value="trend" />
            <el-option label="风险分析" value="risk" />
          </el-select>
        </el-form-item>
        <el-form-item label="选择商品" prop="product_ids">
          <el-select v-model="reportForm.product_ids" multiple filterable placeholder="选择商品" style="width: 100%">
            <el-option
              v-for="p in products"
              :key="p.id"
              :label="p.product_name || p.platform_product_id"
              :value="p.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showReportDialog = false">取消</el-button>
        <el-button type="primary" :loading="generating" @click="handleGenerateReport">生成报告</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";
import { jsPDF } from "jspdf";
import PageHeader from "../components/PageHeader.vue";
import SearchInput from "../components/SearchInput.vue";
import EmptyState from "../components/EmptyState.vue";
import {
  DataAnalysis,
  Document,
  Search,
  TrendCharts,
  Warning,
  PriceTag,
  Star,
  Cpu,
  MagicStick,
  Opportunity,
  ArrowRight,
  ShoppingCart,
} from "@element-plus/icons-vue";
import api from "../utils/api";

const router = useRouter();
const activeTab = ref("analyses");
const analyses = ref<any[]>([]);
const reports = ref<any[]>([]);
const products = ref<any[]>([]);
const recommendations = ref<any[]>([]);
const loading = ref(false);
const reportsLoading = ref(false);
const generating = ref(false);
const showResult = ref(false);
const showReportView = ref(false);
const showReportDialog = ref(false);
const currentResult = ref<any>(null);
const currentReport = ref<any>(null);
const reportFormRef = ref<FormInstance>();
const searchQuery = ref("");
const typeFilter = ref("");
const statusFilter = ref("");

const reportForm = reactive({
  title: "",
  report_type: "product",
  product_ids: [] as string[],
});

const reportFormRules: FormRules = {
  title: [{ required: true, message: "请输入报告标题", trigger: "blur" }],
  report_type: [{ required: true, message: "请选择报告类型", trigger: "change" }],
  product_ids: [{ required: true, message: "请选择商品", trigger: "change", type: "array", min: 1 }],
};

const quickActions = [
  { type: "trend_score", label: "趋势评分", desc: "评估商品趋势走向", icon: TrendCharts, color: "success" },
  { type: "prediction", label: "爆品预测", desc: "预测爆款潜力", icon: Opportunity, color: "amber" },
  { type: "risk_warning", label: "风险预警", desc: "识别潜在风险信号", icon: Warning, color: "danger" },
  { type: "basic_analysis", label: "基础分析", desc: "全面商品数据分析", icon: DataAnalysis, color: "primary" },
];

const ANALYSIS_TYPE_MAP: Record<string, { label: string; tagType: string; icon: typeof DataAnalysis }> = {
  basic_analysis: { label: "基础分析", tagType: "", icon: DataAnalysis },
  trend_score: { label: "趋势评分", tagType: "success", icon: TrendCharts },
  prediction: { label: "爆品预测", tagType: "warning", icon: Star },
  risk_warning: { label: "风险预警", tagType: "danger", icon: Warning },
  report: { label: "综合报告", tagType: "info", icon: Document },
  product_optimization: { label: "优化建议", tagType: "success", icon: Cpu },
};

const REPORT_TYPE_MAP: Record<string, string> = {
  product: "商品分析",
  category: "品类分析",
  trend: "趋势分析",
  risk: "风险分析",
};

const filteredAnalyses = computed(() => {
  let result = analyses.value;
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase();
    result = result.filter(
      (a) =>
        analysisTypeLabel(a.analysis_type).toLowerCase().includes(q) ||
        a.provider?.toLowerCase().includes(q) ||
        a.model?.toLowerCase().includes(q)
    );
  }
  if (typeFilter.value) {
    result = result.filter((a) => a.analysis_type === typeFilter.value);
  }
  if (statusFilter.value) {
    result = result.filter((a) => a.status === statusFilter.value);
  }
  return result;
});

function analysisTypeLabel(type: string) {
  return ANALYSIS_TYPE_MAP[type]?.label || type;
}

function analysisTypeTag(type: string) {
  return ANALYSIS_TYPE_MAP[type]?.tagType || "info";
}

function analysisTypeIcon(type: string) {
  return ANALYSIS_TYPE_MAP[type]?.icon || DataAnalysis;
}

function reportTypeLabel(type: string) {
  return REPORT_TYPE_MAP[type] || type;
}

function statusLabel(status: string) {
  const map: Record<string, string> = { completed: "完成", failed: "失败", pending: "处理中", processing: "处理中" };
  return map[status] || status;
}

function formatDate(dateStr: string): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function formatResult(result: any): string {
  if (!result) return "";
  if (typeof result === "string") return result;
  if (result.result) return String(result.result);
  if (result.analysis) return String(result.analysis);
  if (result.content) return String(result.content);
  return JSON.stringify(result, null, 2);
}

function confidenceGaugeStyle(confidence: number) {
  const deg = confidence * 360;
  const color = confidence >= 0.8 ? '#10B981' : confidence >= 0.5 ? '#F59E0B' : '#EF4444';
  return { background: `conic-gradient(${color} ${deg}deg, var(--color-border-light) ${deg}deg)` };
}

function confidenceLevel(confidence: number): string {
  if (confidence >= 0.8) return 'high';
  if (confidence >= 0.5) return 'medium';
  return 'low';
}

async function startQuickAnalysis(type: string) {
  if (products.value.length === 0) {
    ElMessage.warning("请先添加商品");
    return;
  }
  const productIds = products.value.slice(0, 5).map((p: any) => p.id);
  try {
    await window.electronAPI.invoke("ai:create-report", {
      title: `${analysisTypeLabel(type)} - ${new Date().toLocaleDateString('zh-CN')}`,
      report_type: type === "basic_analysis" ? "product" : type === "risk_warning" ? "risk" : "trend",
      product_ids: productIds,
    });
    ElMessage.success("AI分析已提交，请稍后查看结果");
    fetchAnalyses();
    fetchReports();
  } catch {
    ElMessage.error("AI分析提交失败");
  }
}

function isStructuredReport(content: any): boolean {
  return content && typeof content === "object" && !Array.isArray(content) && (content.executive_summary || content.product_analysis || content.recommendations || content.conclusion || content.trend_overview || content.overall_risk_level);
}

function formatKey(key: string): string {
  const map: Record<string, string> = {
    price_position: "价格定位",
    sales_performance: "销量表现",
    user_rating: "用户评价",
    price_percentile: "价格百分位",
    sales_percentile: "销量百分位",
    rating_percentile: "评分百分位",
    lifecycle_stage: "生命周期阶段",
    trend_short: "短期趋势",
    trend_long: "长期趋势",
    sales_velocity: "销售速度",
    growth_rate_7d: "7日增长率",
    growth_rate_30d: "30日增长率",
    volatility: "波动率",
    competition_index: "竞争指数",
  };
  return map[key] || key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatObjToMd(obj: any): string {
  if (typeof obj === "string") return obj;
  if (Array.isArray(obj)) return obj.map((item: any) => `- ${typeof item === "string" ? item : JSON.stringify(item)}`).join("\n");
  if (typeof obj === "object" && obj !== null) return Object.entries(obj).map(([k, v]) => `- **${formatKey(k)}**: ${typeof v === "object" ? JSON.stringify(v) : v}`).join("\n");
  return String(obj);
}

async function fetchAnalyses() {
  loading.value = true;
  try {
    const result = await window.electronAPI.invoke("ai:get-analyses");
    analyses.value = result?.items || [];
  } finally {
    loading.value = false;
  }
}

async function fetchReports() {
  reportsLoading.value = true;
  try {
    const result = await window.electronAPI.invoke("ai:get-reports");
    reports.value = result || [];
  } finally {
    reportsLoading.value = false;
  }
}

async function fetchProducts() {
  try {
    const result = await window.electronAPI.invoke("storage:get-products");
    products.value = result || [];
  } catch {}
}

function viewAnalysis(row: any) {
  currentResult.value = row;
  showResult.value = true;
}

async function viewReport(row: any) {
  currentReport.value = row;
  showReportView.value = true;
}

function exportReport(report: any, format: string) {
  if (!report?.content) {
    ElMessage.warning("报告内容为空");
    return;
  }

  const contentObj = typeof report.content === "string" ? null : report.content;
  const contentStr = contentObj ? JSON.stringify(contentObj, null, 2) : report.content;

  let content: string;
  let mimeType: string;
  let extension: string;

  if (format === "markdown") {
    let md = `# ${report.title}\n\n`;
    if (contentObj?.executive_summary) md += `## 执行摘要\n\n${contentObj.executive_summary}\n\n`;
    if (contentObj?.product_analysis) md += `## 商品竞争力分析\n\n${formatObjToMd(contentObj.product_analysis)}\n\n`;
    if (contentObj?.market_analysis) md += `## 市场趋势分析\n\n${formatObjToMd(contentObj.market_analysis)}\n\n`;
    if (contentObj?.pricing_analysis) md += `## 定价策略分析\n\n${formatObjToMd(contentObj.pricing_analysis)}\n\n`;
    if (contentObj?.competitive_position) md += `## 竞争定位\n\n${formatObjToMd(contentObj.competitive_position)}\n\n`;
    if (contentObj?.trend_overview) md += `## 趋势总览\n\n${formatObjToMd(contentObj.trend_overview)}\n\n`;
    if (contentObj?.trend_score != null) md += `## 趋势评分\n\n**${contentObj.trend_score}/100**\n\n`;
    if (contentObj?.overall_risk_level) md += `## 风险等级\n\n**${contentObj.overall_risk_level}**\n\n`;
    if (contentObj?.recommendations?.length) {
      md += `## 选品建议\n\n`;
      contentObj.recommendations.forEach((r: any, i: number) => { md += `${i + 1}. ${typeof r === 'string' ? r : r.action || ''}${r.reason ? ` - ${r.reason}` : ''}\n`; });
      md += `\n`;
    }
    if (contentObj?.next_steps?.length) {
      md += `## 下一步行动\n\n`;
      contentObj.next_steps.forEach((s: any, i: number) => { md += `${i + 1}. ${typeof s === 'string' ? s : s.action || JSON.stringify(s)}\n`; });
      md += `\n`;
    }
    if (contentObj?.mitigation_strategies?.length) {
      md += `## 风险缓解策略\n\n`;
      contentObj.mitigation_strategies.forEach((s: any, i: number) => { md += `${i + 1}. ${typeof s === 'string' ? s : s.action || JSON.stringify(s)}\n`; });
      md += `\n`;
    }
    if (contentObj?.conclusion) md += `## 结论\n\n${contentObj.conclusion}\n\n`;
    if (!contentObj) md += contentStr + `\n\n`;
    md += `---\n*生成时间：${formatDate(report.created_at)}*`;
    content = md;
    mimeType = "text/markdown;charset=utf-8";
    extension = "md";
  } else if (format === "html") {
    content = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>${report.title}</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; max-width: 800px; margin: 0 auto; padding: 48px 32px; color: #0F172A; line-height: 1.8; background: #fff; }
    .header { border-bottom: 3px solid #4F46E5; padding-bottom: 20px; margin-bottom: 32px; }
    h1 { color: #0F172A; font-size: 28px; font-weight: 700; margin-bottom: 8px; }
    .subtitle { color: #4F46E5; font-size: 14px; font-weight: 500; }
    .meta { color: #94A3B8; font-size: 13px; margin-top: 12px; display: flex; gap: 16px; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; background: #EEF2FF; color: #4F46E5; }
    .content { background: #F8FAFC; padding: 24px; border-radius: 8px; white-space: pre-wrap; font-size: 14px; line-height: 2; }
    .footer { margin-top: 48px; color: #94A3B8; font-size: 12px; border-top: 1px solid #E2E8F0; padding-top: 16px; display: flex; justify-content: space-between; }
  </style>
</head>
<body>
  <div class="header">
    <div class="subtitle">XHS365 智能分析报告</div>
    <h1>${report.title}</h1>
    <div class="meta">
      <span class="badge">${reportTypeLabel(report.report_type)}</span>
      <span>生成时间：${formatDate(report.created_at)}</span>
    </div>
  </div>
  <div class="content">${report.content}</div>
  <div class="footer">
    <span>XHS365 AI-Powered E-commerce Intelligence</span>
    <span>Confidential</span>
  </div>
</body>
</html>`;
    mimeType = "text/html;charset=utf-8";
    extension = "html";
  } else if (format === "pdf") {
    try {
      const doc = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
      const pageWidth = doc.internal.pageSize.getWidth();
      const margin = 20;
      const contentWidth = pageWidth - margin * 2;

      doc.setFontSize(20);
      doc.setTextColor(79, 70, 229);
      doc.text(report.title || "AI Analysis Report", margin, 30);

      doc.setDrawColor(79, 70, 229);
      doc.setLineWidth(0.5);
      doc.line(margin, 34, pageWidth - margin, 34);

      doc.setFontSize(10);
      doc.setTextColor(148, 163, 184);
      doc.text(`Type: ${reportTypeLabel(report.report_type)} | Date: ${formatDate(report.created_at)}`, margin, 42);

      doc.setFontSize(11);
      doc.setTextColor(15, 23, 42);

      const pdfContent = typeof report.content === "string" ? report.content : JSON.stringify(report.content, null, 2);
      const lines = doc.splitTextToSize(pdfContent, contentWidth);

      let y = 52;
      const lineHeight = 5.5;
      const pageHeight = doc.internal.pageSize.getHeight();

      for (const line of lines) {
        if (y + lineHeight > pageHeight - 20) {
          doc.addPage();
          y = 20;
        }
        doc.text(line, margin, y);
        y += lineHeight;
      }

      const totalPages = doc.getNumberOfPages();
      for (let i = 1; i <= totalPages; i++) {
        doc.setPage(i);
        doc.setFontSize(8);
        doc.setTextColor(148, 163, 184);
        doc.text(`XHS365 AI Report - Page ${i} / ${totalPages}`, margin, pageHeight - 10);
      }

      doc.save(`report_${report.id?.slice(0, 8) || "export"}.pdf`);
      ElMessage.success("PDF 已导出");
      return;
    } catch {
      ElMessage.error("PDF 导出失败，请尝试其他格式");
      return;
    }
  } else {
    content = JSON.stringify(report, null, 2);
    mimeType = "application/json;charset=utf-8";
    extension = "json";
  }

  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `report_${report.id?.slice(0, 8) || "export"}.${extension}`;
  a.click();
  URL.revokeObjectURL(url);
  ElMessage.success(`已导出 ${extension.toUpperCase()} 格式`);
}

async function handleGenerateReport() {
  if (!reportFormRef.value) return;
  await reportFormRef.value.validate();

  generating.value = true;
  try {
    await window.electronAPI.invoke("ai:create-report", {
      title: reportForm.title,
      report_type: reportForm.report_type,
      product_ids: reportForm.product_ids,
    });
    ElMessage.success("报告生成请求已提交");
    showReportDialog.value = false;
    reportForm.title = "";
    reportForm.report_type = "product";
    reportForm.product_ids = [];
    fetchReports();
  } catch {
    ElMessage.error("报告生成失败");
  } finally {
    generating.value = false;
  }
}

onMounted(() => {
  fetchAnalyses();
  fetchReports();
  fetchProducts();
  fetchRecommendations();
});

async function fetchRecommendations() {
  try {
    const { data } = await api.get("/ai/recommendations", { params: { limit: 5 } });
    if (data?.code === 0 && data.data?.items) {
      recommendations.value = data.data.items;
    }
  } catch {}
}

function recIcon(type: string) {
  const map: Record<string, typeof TrendCharts> = {
    trending: TrendCharts, alert: Warning, category_insight: Opportunity, risk: PriceTag,
  };
  return map[type] || Opportunity;
}

function recTagType(type: string): string {
  const map: Record<string, string> = {
    trending: "success", alert: "danger", category_insight: "warning", risk: "danger",
  };
  return map[type] || "info";
}

function recLabel(type: string): string {
  const map: Record<string, string> = {
    trending: "趋势上升", alert: "异动告警", category_insight: "品类洞察", risk: "竞争风险",
  };
  return map[type] || "推荐";
}

function handleRecommendationClick(rec: any) {
  if (rec.type === "alert" && rec.event_id) {
    router.push("/notifications");
  } else if (rec.product_id) {
    router.push(`/products/${rec.product_id}`);
  } else if (rec.type === "category_insight" && rec.category) {
    router.push("/dashboard");
  }
}
</script>

<style scoped>
.ai {
  padding: 0;
}

.ai__quick-actions {
  padding: 20px 24px;
  background: var(--color-bg-card);
  border-bottom: 1px solid var(--color-border-light);
}

.quick-actions__title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: 12px;
}

.quick-actions__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.quick-action-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: var(--color-bg-page);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all 0.2s;
}

.quick-action-card:hover {
  border-color: var(--color-primary-light);
  box-shadow: var(--shadow-sm);
  transform: translateY(-1px);
}

.quick-action-card__icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-base);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}

.quick-action-card__icon--primary { background: linear-gradient(135deg, #4F46E5, #7C3AED); }
.quick-action-card__icon--success { background: linear-gradient(135deg, #10B981, #34D399); }
.quick-action-card__icon--amber { background: linear-gradient(135deg, #F59E0B, #D97706); }
.quick-action-card__icon--danger { background: linear-gradient(135deg, #EF4444, #F87171); }

.quick-action-card__info {
  flex: 1;
  min-width: 0;
}

.quick-action-card__label {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-primary);
}

.quick-action-card__desc {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-top: 2px;
}

.ai__recommendations {
  padding: 20px 24px;
  background: linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 100%);
  border-bottom: 1px solid #FDE68A;
}

.recommendations__title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--text-sm);
  font-weight: 600;
  color: #92400E;
  margin-bottom: 12px;
}

.recommendations__badge {
  margin-left: 4px;
}

.recommendations__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 10px;
}

.recommendation-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid #FDE68A;
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all 0.2s;
  backdrop-filter: blur(4px);
}

.recommendation-card:hover {
  border-color: #D97706;
  box-shadow: 0 4px 12px rgba(217, 119, 6, 0.15);
  transform: translateY(-1px);
}

.recommendation-card--alert {
  border-color: #FCA5A5;
  background: rgba(255, 255, 255, 0.9);
}

.recommendation-card--alert:hover {
  border-color: #EF4444;
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.15);
}

.recommendation-card--risk {
  border-color: #FED7AA;
  background: rgba(255, 255, 255, 0.9);
}

.recommendation-card--risk:hover {
  border-color: #F97316;
  box-shadow: 0 4px 12px rgba(249, 115, 22, 0.15);
}

.recommendation-card--trending {
  border-color: #BBF7D0;
  background: rgba(255, 255, 255, 0.9);
}

.recommendation-card--trending:hover {
  border-color: #22C55E;
  box-shadow: 0 4px 12px rgba(34, 197, 94, 0.15);
}

.recommendation-card__header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.recommendation-card__icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-base);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}

.recommendation-card__icon--trending { background: linear-gradient(135deg, #22C55E, #16A34A); }
.recommendation-card__icon--alert { background: linear-gradient(135deg, #EF4444, #DC2626); }
.recommendation-card__icon--category_insight { background: linear-gradient(135deg, #F59E0B, #D97706); }
.recommendation-card__icon--risk { background: linear-gradient(135deg, #F97316, #EA580C); }

.recommendation-card__body {
  flex: 1;
  min-width: 0;
}

.recommendation-card__name {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recommendation-card__reason {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recommendation-card__action {
  flex-shrink: 0;
  color: var(--color-text-tertiary);
  transition: color 0.2s;
}

.recommendation-card:hover .recommendation-card__action {
  color: var(--color-primary);
}

.analysis-result__gauge-row {
  display: flex;
  gap: 20px;
  margin-bottom: 16px;
  align-items: center;
}

.gauge-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.gauge-card__ring {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.gauge-card__ring::before {
  content: "";
  position: absolute;
  inset: 8px;
  border-radius: 50%;
  background: var(--color-bg-card);
}

.gauge-card__value {
  position: relative;
  z-index: 1;
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.gauge-card__label {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}

.gauge-card__badge {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
}

.gauge-card__badge.high { background: #D1FAE5; color: #065F46; }
.gauge-card__badge.medium { background: #FEF3C7; color: #92400E; }
.gauge-card__badge.low { background: #FEE2E2; color: #991B1B; }

.analysis-result__tri-cards {
  display: flex;
  gap: 10px;
  flex: 1;
}

.tri-card {
  flex: 1;
  padding: 12px;
  border-radius: var(--radius-base);
  text-align: center;
}

.tri-card--success { background: #D1FAE5; color: #065F46; }
.tri-card--warning { background: #FEF3C7; color: #92400E; }
.tri-card--danger { background: #FEE2E2; color: #991B1B; }
.tri-card--primary { background: #EEF2FF; color: #3730A3; }
.tri-card--info { background: #E0F2FE; color: #075985; }

.tri-card__value {
  font-size: 18px;
  font-weight: 700;
}

.tri-card__label {
  font-size: 11px;
  margin-top: 4px;
  opacity: 0.8;
}

.ai__tabs {
  margin-top: 0;
}

.ai__tabs :deep(.el-tabs__header) {
  margin-bottom: 20px;
}

.ai__tabs :deep(.el-tabs__nav-wrap::after) {
  height: 1px;
  background: var(--color-border-light);
}

.ai__tabs :deep(.el-tabs__active-bar) {
  background-color: var(--color-primary);
}

.ai__tabs :deep(.el-tabs__item.is-active) {
  color: var(--color-primary);
  font-weight: 600;
}

.ai__tab-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.ai__toolbar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.ai__toolbar :deep(.search-input) {
  flex: 1;
  min-width: 200px;
}

.ai__filter-group {
  display: flex;
  gap: 8px;
}

.ai__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.analysis-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.analysis-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  border-color: var(--color-primary-light);
}

.analysis-card__header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.analysis-card__type-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-base);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #fff;
}

.analysis-card__type-icon----,
.analysis-card__type-icon--primary {
  background: var(--gradient-hero);
}

.analysis-card__type-icon--success {
  background: linear-gradient(135deg, #10B981, #34D399);
}

.analysis-card__type-icon--warning {
  background: linear-gradient(135deg, #F59E0B, #FBBF24);
}

.analysis-card__type-icon--danger {
  background: linear-gradient(135deg, #EF4444, #F87171);
}

.analysis-card__type-icon--info {
  background: linear-gradient(135deg, #3B82F6, #60A5FA);
}

.analysis-card__meta {
  flex: 1;
  min-width: 0;
}

.analysis-card__type {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--color-text-primary);
  line-height: 1.4;
}

.analysis-card__model {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-top: 2px;
}

.analysis-card__status {
  flex-shrink: 0;
}

.analysis-card__body {
  flex: 1;
}

.analysis-card__confidence {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.analysis-card__confidence-label {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  flex-shrink: 0;
}

.analysis-card__confidence-bar {
  flex: 1;
  height: 6px;
  background: var(--color-bg-page);
  border-radius: 3px;
  overflow: hidden;
}

.analysis-card__confidence-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.6s ease;
}

.analysis-card__confidence-fill.high {
  background: var(--color-success);
}

.analysis-card__confidence-fill.medium {
  background: var(--color-warning);
}

.analysis-card__confidence-fill.low {
  background: var(--color-danger);
}

.analysis-card__confidence-value {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--color-text-secondary);
  flex-shrink: 0;
  min-width: 32px;
  text-align: right;
}

.analysis-card__preview {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.analysis-card__footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid var(--color-border-light);
}

.analysis-card__time {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.ai__reports {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.report-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.report-card:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
  border-color: var(--color-primary-light);
}

.report-card__header {
  display: flex;
  align-items: center;
  gap: 12px;
}

.report-card__icon {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-base);
  background: linear-gradient(135deg, #4F46E5, #7C3AED);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}

.report-card__info {
  flex: 1;
  min-width: 0;
}

.report-card__title {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--color-text-primary);
  line-height: 1.4;
}

.report-card__meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.report-card__time {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.report-card__preview {
  margin-top: 12px;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  line-height: 1.6;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.report-card__actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border-light);
}

.report-card__actions .el-button {
  font-weight: 500;
  font-size: 13px;
}

.report-card__actions .el-button--primary {
  color: var(--color-primary);
}

.report-card__actions .el-button--success {
  color: var(--color-success);
}

.ai__loading {
  margin-top: 20px;
}

.analysis-result__tags {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.analysis-result__content {
  white-space: pre-wrap;
  line-height: 1.8;
  max-height: 400px;
  overflow: auto;
  padding: 20px;
  background: var(--color-bg-page);
  border-radius: var(--radius-lg);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  border: 1px solid var(--color-border-light);
}

.report-view__tags {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.report-view__content {
  white-space: pre-wrap;
  line-height: 1.8;
  padding: 20px;
  background: var(--color-bg-page);
  border-radius: var(--radius-lg);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  max-height: 500px;
  overflow: auto;
  border: 1px solid var(--color-border-light);
}

.report-view__structured {
  max-height: 500px;
  overflow: auto;
}

.report-section {
  padding: 16px 0;
  border-bottom: 1px solid var(--color-border-lighter);
}

.report-section:last-child {
  border-bottom: none;
}

.report-section--highlight {
  background: var(--color-primary-light-9, #f0f2ff);
  border-radius: var(--radius-lg);
  padding: 16px;
  margin-bottom: 8px;
}

.report-section h4 {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 8px;
}

.report-section p {
  font-size: 13px;
  line-height: 1.8;
  color: var(--color-text-regular);
  margin: 0;
  white-space: pre-wrap;
}

.report-kv-grid {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 6px 16px;
  font-size: 13px;
}

.report-kv-key {
  color: var(--color-text-secondary);
  font-weight: 500;
  white-space: nowrap;
}

.report-kv-val {
  color: var(--color-text-primary);
}

.report-score-bar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.report-score-fill {
  flex: 1;
  height: 8px;
  border-radius: 4px;
  background: var(--color-bg-page);
  overflow: hidden;
  position: relative;
}

.report-score-fill::after {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  border-radius: 4px;
  width: inherit;
}

.report-score-fill.high::after {
  background: var(--el-color-success);
}

.report-score-fill.medium::after {
  background: var(--el-color-warning);
}

.report-score-fill.low::after {
  background: var(--el-color-danger);
}

.report-score-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  min-width: 60px;
}

.report-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.report-list-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 13px;
}

.report-list-index {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--color-primary, #4f46e5);
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
}

.report-list-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.report-list-reason {
  color: var(--color-text-secondary);
  font-size: 12px;
}

.report-view__footer {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

@media (max-width: 768px) {
  .ai__grid {
    grid-template-columns: 1fr;
  }

  .ai__toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .ai__filter-group {
    width: 100%;
  }

  .ai__filter-group .el-select {
    flex: 1;
  }
}
</style>
