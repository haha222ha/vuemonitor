<template>
  <div class="ai-report">
    <div class="page-toolbar">
      <h3>AI分析报告</h3>
      <div class="toolbar-right">
        <el-button size="small" @click="showCreateDialog = true" type="primary">
          <el-icon><Plus /></el-icon> 生成报告
        </el-button>
      </div>
    </div>

    <div v-if="loading" style="text-align: center; padding: 60px;">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
      <p style="color: #6a6a7a; margin-top: 12px;">加载报告列表...</p>
    </div>

    <div v-else-if="reports.length === 0" class="empty-state">
      <el-icon :size="48" color="#4a4a5a"><Document /></el-icon>
      <p>暂无分析报告</p>
      <el-button type="primary" @click="showCreateDialog = true">生成第一份报告</el-button>
    </div>

    <div v-else class="report-grid">
      <div v-for="r in reports" :key="r.id" class="report-card" @click="viewReport(r)">
        <div class="report-card-header">
          <el-tag :type="reportTypeTag(r.report_type)" size="small">{{ reportTypeLabel(r.report_type) }}</el-tag>
          <el-tag :type="statusTag(r.status)" size="small">{{ statusLabel(r.status) }}</el-tag>
        </div>
        <h4 class="report-title">{{ r.title }}</h4>
        <div class="report-meta">
          <span>{{ formatTime(r.created_at) }}</span>
        </div>
        <div class="report-actions" @click.stop>
          <el-button size="small" text @click="viewReport(r)">查看</el-button>
          <el-button size="small" text @click="exportReport(r, 'pdf')" :disabled="r.status !== 'completed'">PDF</el-button>
          <el-button size="small" text @click="exportReport(r, 'xlsx')" :disabled="r.status !== 'completed'">Excel</el-button>
          <el-button size="small" text type="danger" @click="confirmDelete(r)">删除</el-button>
        </div>
      </div>
    </div>

    <el-dialog v-model="showCreateDialog" title="生成AI分析报告" width="520px" :close-on-click-modal="false">
      <el-form label-width="80px">
        <el-form-item label="报告标题">
          <el-input v-model="createForm.title" placeholder="输入报告标题" maxlength="255" show-word-limit />
        </el-form-item>
        <el-form-item label="报告类型">
          <el-select v-model="createForm.report_type" style="width: 100%;">
            <el-option value="product" label="商品分析报告" />
            <el-option value="category" label="品类分析报告" />
            <el-option value="trend" label="趋势分析报告" />
            <el-option value="risk" label="风险分析报告" />
          </el-select>
        </el-form-item>
        <el-form-item label="选择商品">
          <el-select v-model="createForm.product_ids" multiple placeholder="选择要分析的商品" style="width: 100%;">
            <el-option v-for="p in products" :key="p.id" :value="p.id" :label="p.product_name || p.name || p.id.slice(0, 8)" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="createReport">生成报告</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showReportDialog" :title="currentReport?.title || '报告详情'" width="700px" top="5vh">
      <div v-if="reportLoading" style="text-align: center; padding: 40px;">
        <el-icon class="is-loading" :size="24"><Loading /></el-icon>
      </div>
      <div v-else-if="currentReport" class="report-content">
        <div class="report-content-header">
          <el-tag :type="reportTypeTag(currentReport.report_type)">{{ reportTypeLabel(currentReport.report_type) }}</el-tag>
          <span class="report-date">{{ formatTime(currentReport.created_at) }}</span>
        </div>
        <div v-if="currentReport.status === 'processing'" class="report-status-hint">
          <el-icon class="is-loading"><Loading /></el-icon> 报告生成中，请稍后刷新查看...
        </div>
        <div v-else-if="currentReport.status === 'failed'" class="report-status-hint error">
          报告生成失败，请重新生成
        </div>
        <div v-else-if="currentReport.content" class="report-body" v-html="renderMarkdown(currentReport.content)"></div>
        <div v-else class="report-status-hint">暂无报告内容</div>
      </div>
      <template #footer>
        <el-button @click="showReportDialog = false">关闭</el-button>
        <el-button type="primary" @click="exportReport(currentReport, 'pdf')" :disabled="!currentReport || currentReport.status !== 'completed'">导出PDF</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus, Document, Loading } from "@element-plus/icons-vue";
import api from "../../utils/api";
import { useAuthStore } from "../../stores/auth";

const auth = useAuthStore();

const reports = ref<any[]>([]);
const loading = ref(false);
const showCreateDialog = ref(false);
const showReportDialog = ref(false);
const creating = ref(false);
const reportLoading = ref(false);
const currentReport = ref<any>(null);
const products = ref<any[]>([]);

const createForm = reactive({
  title: "",
  report_type: "product",
  product_ids: [] as string[],
});

function reportTypeTag(type: string) {
  const map: Record<string, string> = { product: "primary", category: "success", trend: "warning", risk: "danger" };
  return (map[type] || "info") as any;
}

function reportTypeLabel(type: string) {
  const map: Record<string, string> = { product: "商品分析", category: "品类分析", trend: "趋势分析", risk: "风险分析" };
  return map[type] || type;
}

function statusTag(status: string) {
  const map: Record<string, string> = { completed: "success", processing: "warning", failed: "danger", pending: "info" };
  return (map[status] || "info") as any;
}

function statusLabel(status: string) {
  const map: Record<string, string> = { completed: "已完成", processing: "生成中", failed: "失败", pending: "等待中" };
  return map[status] || status;
}

function formatTime(iso: string) {
  if (!iso) return "";
  const d = new Date(iso);
  return `${d.getFullYear()}-${(d.getMonth() + 1).toString().padStart(2, "0")}-${d.getDate().toString().padStart(2, "0")} ${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}`;
}

function renderMarkdown(text: string) {
  if (!text) return "";
  return text
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')
    .replace(/\n{2,}/g, "<br><br>")
    .replace(/\n/g, "<br>");
}

async function fetchReports() {
  loading.value = true;
  try {
    const { data } = await api.get("/ai/reports", { params: { page_size: 50 } });
    reports.value = data?.data?.items || [];
  } catch {
    reports.value = [];
  } finally {
    loading.value = false;
  }
}

async function fetchProducts() {
  try {
    const { data } = await api.get("/products", { params: { page_size: 100 } });
    products.value = data?.data?.items || [];
  } catch {}
}

async function createReport() {
  if (!createForm.title.trim()) {
    ElMessage.warning("请输入报告标题");
    return;
  }
  if (createForm.product_ids.length === 0) {
    ElMessage.warning("请选择至少一个商品");
    return;
  }
  creating.value = true;
  try {
    await api.post("/ai/report", {
      title: createForm.title,
      report_type: createForm.report_type,
      product_ids: createForm.product_ids,
    });
    ElMessage.success("报告生成请求已提交");
    showCreateDialog.value = false;
    createForm.title = "";
    createForm.report_type = "product";
    createForm.product_ids = [];
    setTimeout(fetchReports, 2000);
  } catch (e: any) {
    const msg = e?.response?.data?.message || "报告生成失败";
    ElMessage.error(msg);
  } finally {
    creating.value = false;
  }
}

async function viewReport(r: any) {
  currentReport.value = r;
  showReportDialog.value = true;
  if (r.status === "processing" || r.status === "pending") {
    reportLoading.value = true;
    try {
      const { data } = await api.get(`/ai/reports/${r.id}`);
      currentReport.value = data?.data || r;
    } catch {}
    finally {
      reportLoading.value = false;
    }
  }
}

function exportReport(r: any, format: string) {
  if (!r || r.status !== "completed") return;
  const content = r.content || "";
  const title = r.title || "AI分析报告";

  if (format === "pdf") {
    const printWindow = window.open("", "_blank");
    if (printWindow) {
      printWindow.document.write(`
        <!DOCTYPE html>
        <html><head><title>${title}</title>
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #333; line-height: 1.8; }
          h1 { font-size: 24px; border-bottom: 2px solid #409eff; padding-bottom: 8px; }
          h2 { font-size: 20px; color: #409eff; margin-top: 24px; }
          h3 { font-size: 16px; color: #606266; }
          ul { padding-left: 20px; }
          li { margin: 4px 0; }
          strong { color: #303133; }
          @media print { body { margin: 0; } }
        </style></head>
        <body>${renderMarkdown(content)}</body></html>
      `);
      printWindow.document.close();
      setTimeout(() => printWindow.print(), 500);
    }
  } else if (format === "xlsx") {
    const lines = content.split("\n").filter((l: string) => l.trim());
    let csv = "\uFEFF";
    for (const line of lines) {
      csv += line.replace(/^#+\s*/, "").replace(/\*\*/g, "") + "\n";
    }
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    ElMessage.success("Excel导出成功");
  }
}

async function confirmDelete(r: any) {
  try {
    await ElMessageBox.confirm(`确定删除报告"${r.title}"？`, "删除确认", { type: "warning" });
    await api.delete(`/ai/reports/${r.id}`);
    ElMessage.success("报告已删除");
    fetchReports();
  } catch {}
}

onMounted(() => {
  fetchReports();
  fetchProducts();
});
</script>

<style scoped>
.ai-report {
  padding: 4px;
}

.page-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.page-toolbar h3 {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  margin: 0;
}

.toolbar-right {
  display: flex;
  align-items: center;
}

.empty-state {
  text-align: center;
  padding: 80px 0;
  color: #6a6a7a;
}

.empty-state p {
  margin: 16px 0;
  font-size: 15px;
}

.report-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.report-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;
}

.report-card:hover {
  border-color: rgba(64, 158, 255, 0.3);
  background: rgba(255, 255, 255, 0.05);
}

.report-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.report-title {
  font-size: 15px;
  font-weight: 600;
  color: #fff;
  margin: 0 0 8px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.report-meta {
  font-size: 12px;
  color: #6a6a7a;
  margin-bottom: 12px;
}

.report-actions {
  display: flex;
  gap: 4px;
  border-top: 1px solid rgba(255, 255, 255, 0.04);
  padding-top: 12px;
}

.report-content {
  max-height: 60vh;
  overflow-y: auto;
}

.report-content-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.report-date {
  font-size: 13px;
  color: #6a6a7a;
}

.report-status-hint {
  text-align: center;
  padding: 40px;
  color: #8a8a9a;
  font-size: 14px;
}

.report-status-hint.error {
  color: #f56c6c;
}

.report-body {
  color: #e0e0e0;
  line-height: 1.8;
  font-size: 14px;
}

.report-body :deep(h1) {
  font-size: 20px;
  color: #fff;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding-bottom: 8px;
  margin-top: 24px;
}

.report-body :deep(h2) {
  font-size: 17px;
  color: #409eff;
  margin-top: 20px;
}

.report-body :deep(h3) {
  font-size: 15px;
  color: #67c23a;
  margin-top: 16px;
}

.report-body :deep(ul) {
  padding-left: 20px;
}

.report-body :deep(li) {
  margin: 4px 0;
}

.report-body :deep(strong) {
  color: #fff;
}
</style>
