import { ref, reactive, computed } from "vue";
import { ElMessage } from "element-plus";
import { jsPDF } from "jspdf";
import {
  DataAnalysis, Document, TrendCharts, Warning, PriceTag, Star, Cpu,
} from "@element-plus/icons-vue";
import api from "../utils/api";

export const ANALYSIS_TYPE_MAP: Record<string, { label: string; tagType: string; icon: typeof DataAnalysis }> = {
  basic_analysis: { label: "基础分析", tagType: "", icon: DataAnalysis },
  trend_score: { label: "趋势评分", tagType: "success", icon: TrendCharts },
  prediction: { label: "爆品预测", tagType: "warning", icon: Star },
  risk_warning: { label: "风险预警", tagType: "danger", icon: Warning },
  report: { label: "综合报告", tagType: "info", icon: Document },
  product_optimization: { label: "优化建议", tagType: "success", icon: Cpu },
};

export const REPORT_TYPE_MAP: Record<string, string> = {
  product: "商品分析", category: "品类分析", trend: "趋势分析", risk: "风险分析",
};

export function useAIData() {
  const analyses = ref<any[]>([]);
  const reports = ref<any[]>([]);
  const products = ref<any[]>([]);
  const recommendations = ref<any[]>([]);
  const loading = ref(false);
  const reportsLoading = ref(false);
  const generating = ref(false);
  const searchQuery = ref("");
  const typeFilter = ref("");
  const statusFilter = ref("");

  const reportForm = reactive({
    title: "",
    report_type: "product",
    product_ids: [] as string[],
  });

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

  function analysisTypeLabel(type: string) { return ANALYSIS_TYPE_MAP[type]?.label || type; }
  function analysisTypeTag(type: string) { return ANALYSIS_TYPE_MAP[type]?.tagType || "info"; }
  function analysisTypeIcon(type: string) { return ANALYSIS_TYPE_MAP[type]?.icon || DataAnalysis; }
  function reportTypeLabel(type: string) { return REPORT_TYPE_MAP[type] || type; }

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

  function isStructuredResult(result: any): boolean {
    if (!result || typeof result === "string") return false;
    return !!(result.summary || result.recommendations?.length || result.risks?.length || result.key_findings?.length || result.score != null);
  }

  function isStructuredReport(content: any): boolean {
    return content && typeof content === "object" && !Array.isArray(content) && (content.executive_summary || content.product_analysis || content.recommendations || content.conclusion || content.trend_overview || content.overall_risk_level);
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

  function formatKey(key: string): string {
    const map: Record<string, string> = {
      price_position: "价格定位", sales_performance: "销量表现", user_rating: "用户评价",
      price_percentile: "价格百分位", sales_percentile: "销量百分位", rating_percentile: "评分百分位",
      lifecycle_stage: "生命周期阶段", trend_short: "短期趋势", trend_long: "长期趋势",
      sales_velocity: "销售速度", growth_rate_7d: "7日增长率", growth_rate_30d: "30日增长率",
      volatility: "波动率", competition_index: "竞争指数",
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

  async function fetchRecommendations() {
    try {
      const { data } = await api.get("/ai/recommendations", { params: { limit: 5 } });
      if (data?.code === 0 && data.data?.items) {
        recommendations.value = data.data.items;
      }
    } catch {}
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

  async function handleGenerateReport() {
    generating.value = true;
    try {
      await window.electronAPI.invoke("ai:create-report", {
        title: reportForm.title,
        report_type: reportForm.report_type,
        product_ids: reportForm.product_ids,
      });
      ElMessage.success("报告生成请求已提交");
      reportForm.title = "";
      reportForm.report_type = "product";
      reportForm.product_ids = [];
      fetchReports();
      return true;
    } catch {
      ElMessage.error("报告生成失败");
      return false;
    } finally {
      generating.value = false;
    }
  }

  function exportReport(report: any, format: string) {
    if (!report?.content) {
      ElMessage.warning("报告内容为空");
      return;
    }

    const contentObj = typeof report.content === "string" ? null : report.content;
    const contentStr = contentObj ? JSON.stringify(contentObj, null, 2) : report.content;

    if (format === "pdf") {
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
    }

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

  function recIcon(type: string) {
    const map: Record<string, typeof TrendCharts> = {
      trending: TrendCharts, alert: Warning, category_insight: PriceTag, risk: PriceTag,
    };
    return map[type] || PriceTag;
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

  return {
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
  };
}
