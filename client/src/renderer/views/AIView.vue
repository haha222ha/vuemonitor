<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center">
      <h2>AI分析</h2>
      <el-button type="primary" size="small" @click="showReportDialog = true">生成报告</el-button>
    </div>

    <el-tabs v-model="activeTab" style="margin-top: 16px">
      <el-tab-pane label="分析记录" name="analyses">
        <el-table :data="analyses" stripe v-loading="loading" @row-click="viewAnalysis">
          <el-table-column prop="analysis_type" label="分析类型" width="120">
            <template #default="{ row }">
              <el-tag size="small" :type="analysisTypeTag(row.analysis_type)">{{ analysisTypeLabel(row.analysis_type) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="provider" label="Provider" width="100" />
          <el-table-column prop="model" label="模型" width="140" />
          <el-table-column prop="status" label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.status === 'completed' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'" size="small">
                {{ statusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="confidence" label="置信度" width="80">
            <template #default="{ row }">
              <span v-if="row.confidence">{{ (row.confidence * 100).toFixed(0) }}%</span>
              <span v-else>-</span>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="时间" width="160">
            <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button size="small" link type="primary" @click.stop="viewAnalysis(row)">查看</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="分析报告" name="reports">
        <el-table :data="reports" stripe v-loading="reportsLoading">
          <el-table-column prop="title" label="报告标题" min-width="200" />
          <el-table-column prop="report_type" label="类型" width="100">
            <template #default="{ row }">
              <el-tag size="small">{{ reportTypeLabel(row.report_type) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.status === 'completed' ? 'success' : 'warning'" size="small">
                {{ row.status === 'completed' ? '完成' : '生成中' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="生成时间" width="160">
            <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="160">
            <template #default="{ row }">
              <el-button size="small" link type="primary" @click="viewReport(row)">查看</el-button>
              <el-dropdown trigger="click" @command="(cmd: string) => exportReport(row, cmd)">
                <el-button size="small" link type="success">导出</el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="markdown">Markdown</el-dropdown-item>
                    <el-dropdown-item command="html">HTML</el-dropdown-item>
                    <el-dropdown-item command="pdf">PDF</el-dropdown-item>
                    <el-dropdown-item command="json">JSON</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="showResult" title="分析结果" width="640px">
      <div v-if="currentResult">
        <div style="display: flex; gap: 8px; margin-bottom: 12px">
          <el-tag size="small" :type="analysisTypeTag(currentResult.analysis_type)">
            {{ analysisTypeLabel(currentResult.analysis_type) }}
          </el-tag>
          <el-tag v-if="currentResult.confidence" size="small" type="info">
            置信度 {{ (currentResult.confidence * 100).toFixed(0) }}%
          </el-tag>
          <el-tag size="small" type="info">{{ currentResult.provider }} / {{ currentResult.model }}</el-tag>
        </div>
        <div style="white-space: pre-wrap; line-height: 1.8; max-height: 400px; overflow: auto; padding: 12px; background: #f5f7fa; border-radius: 8px">
          {{ formatResult(currentResult.result) }}
        </div>
      </div>
    </el-dialog>

    <el-dialog v-model="showReportView" :title="currentReport?.title || '报告'" width="720px">
      <div v-if="currentReport" style="max-height: 500px; overflow: auto">
        <div style="display: flex; gap: 8px; margin-bottom: 16px">
          <el-tag size="small">{{ reportTypeLabel(currentReport.report_type) }}</el-tag>
          <el-tag size="small" type="info">{{ formatDate(currentReport.created_at) }}</el-tag>
        </div>
        <div style="white-space: pre-wrap; line-height: 1.8; padding: 16px; background: #f5f7fa; border-radius: 8px">
          {{ currentReport.content }}
        </div>
      </div>
      <template #footer>
        <el-button @click="exportReport(currentReport, 'markdown')">导出 Markdown</el-button>
        <el-button type="primary" @click="exportReport(currentReport, 'html')">导出 HTML</el-button>
        <el-button type="success" @click="exportReport(currentReport, 'pdf')">导出 PDF</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showReportDialog" title="生成分析报告" width="520px">
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
import { ref, reactive, onMounted } from "vue";
import api from "../utils/api";
import { ElMessage } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";
import { jsPDF } from "jspdf";

const activeTab = ref("analyses");
const analyses = ref<any[]>([]);
const reports = ref<any[]>([]);
const products = ref<any[]>([]);
const loading = ref(false);
const reportsLoading = ref(false);
const generating = ref(false);
const showResult = ref(false);
const showReportView = ref(false);
const showReportDialog = ref(false);
const currentResult = ref<any>(null);
const currentReport = ref<any>(null);
const reportFormRef = ref<FormInstance>();

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

const ANALYSIS_TYPE_MAP: Record<string, { label: string; tagType: string }> = {
  basic_analysis: { label: "基础分析", tagType: "" },
  trend_score: { label: "趋势评分", tagType: "success" },
  prediction: { label: "爆品预测", tagType: "warning" },
  risk_warning: { label: "风险预警", tagType: "danger" },
  report: { label: "综合报告", tagType: "info" },
  product_optimization: { label: "优化建议", tagType: "success" },
};

const REPORT_TYPE_MAP: Record<string, string> = {
  product: "商品分析",
  category: "品类分析",
  trend: "趋势分析",
  risk: "风险分析",
};

function analysisTypeLabel(type: string) {
  return ANALYSIS_TYPE_MAP[type]?.label || type;
}

function analysisTypeTag(type: string) {
  return ANALYSIS_TYPE_MAP[type]?.tagType || "info";
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

async function fetchAnalyses() {
  loading.value = true;
  try {
    const { data } = await api.get("/ai/analyses");
    analyses.value = data?.data?.items || [];
  } finally {
    loading.value = false;
  }
}

async function fetchReports() {
  reportsLoading.value = true;
  try {
    const { data } = await api.get("/ai/reports");
    reports.value = data?.data || [];
  } finally {
    reportsLoading.value = false;
  }
}

async function fetchProducts() {
  try {
    const { data } = await api.get("/products", { params: { page_size: 200 } });
    products.value = data?.data?.items || [];
  } catch {}
}

function viewAnalysis(row: any) {
  currentResult.value = row;
  showResult.value = true;
}

async function viewReport(row: any) {
  try {
    const { data } = await api.get(`/ai/reports/${row.id}`);
    currentReport.value = data?.data || row;
    showReportView.value = true;
  } catch {
    ElMessage.error("加载报告失败");
  }
}

function exportReport(report: any, format: string) {
  if (!report?.content) {
    ElMessage.warning("报告内容为空");
    return;
  }

  let content: string;
  let mimeType: string;
  let extension: string;

  if (format === "markdown") {
    content = `# ${report.title}\n\n${report.content}\n\n---\n*生成时间：${formatDate(report.created_at)}*`;
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
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif; max-width: 800px; margin: 0 auto; padding: 48px 32px; color: #303133; line-height: 1.8; background: #fff; }
    .header { border-bottom: 3px solid #409EFF; padding-bottom: 20px; margin-bottom: 32px; }
    h1 { color: #303133; font-size: 28px; font-weight: 700; margin-bottom: 8px; }
    .subtitle { color: #409EFF; font-size: 14px; font-weight: 500; }
    .meta { color: #909399; font-size: 13px; margin-top: 12px; display: flex; gap: 16px; }
    .meta span { display: flex; align-items: center; gap: 4px; }
    .section { margin-bottom: 24px; }
    .section-title { font-size: 18px; font-weight: 600; color: #303133; margin-bottom: 12px; padding-left: 12px; border-left: 3px solid #409EFF; }
    .content { background: #f8f9fb; padding: 24px; border-radius: 8px; white-space: pre-wrap; font-size: 14px; line-height: 2; }
    .footer { margin-top: 48px; color: #909399; font-size: 12px; border-top: 1px solid #ebeef5; padding-top: 16px; display: flex; justify-content: space-between; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; background: #ecf5ff; color: #409EFF; }
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
  <div class="section">
    <div class="section-title">分析内容</div>
    <div class="content">${report.content}</div>
  </div>
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
      doc.setTextColor(64, 158, 255);
      doc.text(report.title || "AI Analysis Report", margin, 30);

      doc.setDrawColor(64, 158, 255);
      doc.setLineWidth(0.5);
      doc.line(margin, 34, pageWidth - margin, 34);

      doc.setFontSize(10);
      doc.setTextColor(144, 147, 153);
      doc.text(`Type: ${reportTypeLabel(report.report_type)} | Date: ${formatDate(report.created_at)}`, margin, 42);

      doc.setFontSize(11);
      doc.setTextColor(48, 49, 51);

      const content = typeof report.content === "string" ? report.content : JSON.stringify(report.content, null, 2);
      const lines = doc.splitTextToSize(content, contentWidth);

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
        doc.setTextColor(144, 147, 153);
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
    const { data } = await api.post("/ai/report", {
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
});
</script>
