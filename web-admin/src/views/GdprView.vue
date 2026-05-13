<template>
  <div>
    <h2>数据合规</h2>
    <el-tabs v-model="activeTab">
      <el-tab-pane label="数据导出请求" name="exports">
        <div style="display:flex;justify-content:space-between;margin-bottom:16px">
          <el-select v-model="exportFilter.status" placeholder="状态筛选" clearable style="width:160px">
            <el-option label="待处理" value="pending" />
            <el-option label="处理中" value="processing" />
            <el-option label="已完成" value="completed" />
            <el-option label="已拒绝" value="rejected" />
          </el-select>
          <el-button type="primary" @click="fetchExports">查询</el-button>
        </div>
        <el-table :data="store.exports" stripe v-loading="store.exportsLoading" row-key="id">
          <el-table-column prop="user_id" label="用户ID" width="120" show-overflow-tooltip />
          <el-table-column prop="request_type" label="请求类型" width="120">
            <template #default="{ row }">
              <el-tag>{{ requestTypeLabel(row.request_type) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="data_scope" label="数据范围" min-width="150" show-overflow-tooltip />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="gdprStatusType(row.status)">{{ gdprStatusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="请求时间" width="180" />
          <el-table-column prop="completed_at" label="完成时间" width="180" />
          <el-table-column label="操作" width="180">
            <template #default="{ row }">
              <el-button v-if="row.status === 'pending'" size="small" type="primary" @click="approveRequest(row.id, 'export')">批准</el-button>
              <el-button v-if="row.status === 'pending'" size="small" type="danger" @click="rejectRequest(row.id, 'export')">拒绝</el-button>
              <el-button v-if="row.status === 'completed'" size="small" @click="downloadExport(row.id)">下载</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination
          v-model:current-page="exportPage"
          :page-size="20"
          :total="store.exportsTotal"
          layout="prev, pager, next"
          style="margin-top:16px;justify-content:flex-end"
          @current-change="fetchExports"
        />
      </el-tab-pane>

      <el-tab-pane label="数据删除请求" name="deletions">
        <div style="display:flex;justify-content:space-between;margin-bottom:16px">
          <el-select v-model="deletionFilter.status" placeholder="状态筛选" clearable style="width:160px">
            <el-option label="待处理" value="pending" />
            <el-option label="处理中" value="processing" />
            <el-option label="已完成" value="completed" />
            <el-option label="已拒绝" value="rejected" />
          </el-select>
          <el-button type="primary" @click="fetchDeletions">查询</el-button>
        </div>
        <el-table :data="store.deletions" stripe v-loading="store.deletionsLoading" row-key="id">
          <el-table-column prop="user_id" label="用户ID" width="120" show-overflow-tooltip />
          <el-table-column prop="request_type" label="请求类型" width="120">
            <template #default="{ row }">
              <el-tag type="warning">{{ requestTypeLabel(row.request_type) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="data_scope" label="数据范围" min-width="150" show-overflow-tooltip />
          <el-table-column prop="reason" label="原因" min-width="180" show-overflow-tooltip />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="gdprStatusType(row.status)">{{ gdprStatusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="请求时间" width="180" />
          <el-table-column prop="completed_at" label="完成时间" width="180" />
          <el-table-column label="操作" width="140">
            <template #default="{ row }">
              <el-button v-if="row.status === 'pending'" size="small" type="primary" @click="approveRequest(row.id, 'deletion')">批准</el-button>
              <el-button v-if="row.status === 'pending'" size="small" type="danger" @click="rejectRequest(row.id, 'deletion')">拒绝</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination
          v-model:current-page="deletionPage"
          :page-size="20"
          :total="store.deletionsTotal"
          layout="prev, pager, next"
          style="margin-top:16px;justify-content:flex-end"
          @current-change="fetchDeletions"
        />
      </el-tab-pane>

      <el-tab-pane label="合规统计" name="stats">
        <el-row :gutter="16" style="margin-bottom:20px">
          <el-col :span="6">
            <el-card shadow="hover"><el-statistic title="待处理导出请求" :value="store.stats.pendingExports" /></el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover"><el-statistic title="待处理删除请求" :value="store.stats.pendingDeletions" /></el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover"><el-statistic title="本月已完成请求" :value="store.stats.completedThisMonth" /></el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover"><el-statistic title="平均处理时长(h)" :value="store.stats.avgProcessingHours" :precision="1" /></el-card>
          </el-col>
        </el-row>
        <el-descriptions title="数据保留策略" :column="2" border>
          <el-descriptions-item label="用户行为数据保留">12个月</el-descriptions-item>
          <el-descriptions-item label="采集商品数据保留">24个月</el-descriptions-item>
          <el-descriptions-item label="操作日志保留">6个月</el-descriptions-item>
          <el-descriptions-item label="AI分析结果保留">12个月</el-descriptions-item>
          <el-descriptions-item label="自动清理策略">已启用</el-descriptions-item>
          <el-descriptions-item label="数据匿名化">到期自动匿名化</el-descriptions-item>
        </el-descriptions>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useGdprStore } from "../stores/gdpr";

const store = useGdprStore();

const activeTab = ref("exports");
const exportPage = ref(1);
const deletionPage = ref(1);
const exportFilter = reactive({ status: "" as string });
const deletionFilter = reactive({ status: "" as string });

function requestTypeLabel(t: string): string {
  const map: Record<string, string> = { full_export: "全量导出", partial_export: "部分导出", full_deletion: "全量删除", partial_deletion: "部分删除" };
  return map[t] || t;
}

function gdprStatusType(s: string): string {
  const map: Record<string, string> = { pending: "warning", processing: "", completed: "success", rejected: "danger" };
  return map[s] || "info";
}

function gdprStatusLabel(s: string): string {
  const map: Record<string, string> = { pending: "待处理", processing: "处理中", completed: "已完成", rejected: "已拒绝" };
  return map[s] || s;
}

async function fetchExports() {
  try {
    await store.fetchExports(exportPage.value, 20, exportFilter.status || undefined);
  } catch { ElMessage.error("获取导出请求失败"); }
}

async function fetchDeletions() {
  try {
    await store.fetchDeletions(deletionPage.value, 20, deletionFilter.status || undefined);
  } catch { ElMessage.error("获取删除请求失败"); }
}

async function fetchStats() {
  try {
    await store.fetchStats();
  } catch { ElMessage.error("获取合规统计失败"); }
}

async function approveRequest(id: string, type: string) {
  const label = type === "export" ? "导出" : "删除";
  try {
    await ElMessageBox.confirm(`确认批准此${label}请求？`, "操作确认", { type: "warning" });
    await store.approveRequest(Number(id));
    ElMessage.success("已批准");
    if (type === "export") fetchExports(); else fetchDeletions();
    fetchStats();
  } catch { /* cancelled or error */ }
}

async function rejectRequest(id: string, type: string) {
  try {
    await ElMessageBox.confirm("确认拒绝此请求？", "操作确认", { type: "warning" });
    await store.rejectRequest(Number(id));
    ElMessage.success("已拒绝");
    if (type === "export") fetchExports(); else fetchDeletions();
    fetchStats();
  } catch { /* cancelled or error */ }
}

async function downloadExport(id: string) {
  try {
    const blob = await store.downloadExport(Number(id));
    const url = window.URL.createObjectURL(new Blob([blob as BlobPart]));
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", `gdpr-export-${id}.zip`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch { ElMessage.error("下载失败"); }
}

onMounted(() => { fetchExports(); fetchDeletions(); fetchStats(); });
</script>
