<template>
  <div>
    <h2>安全审计</h2>
    <el-row :gutter="12" style="margin-bottom: 16px">
      <el-col :span="5">
        <el-select v-model="filters.event_type" placeholder="事件类型" clearable style="width:100%">
          <el-option label="登录失败" value="login_failure" />
          <el-option label="权限变更" value="permission_change" />
          <el-option label="数据访问" value="data_access" />
          <el-option label="API滥用" value="api_abuse" />
          <el-option label="可疑活动" value="suspicious_activity" />
        </el-select>
      </el-col>
      <el-col :span="5">
        <el-select v-model="filters.severity" placeholder="严重程度" clearable style="width:100%">
          <el-option label="低" value="low" />
          <el-option label="中" value="medium" />
          <el-option label="高" value="high" />
          <el-option label="严重" value="critical" />
        </el-select>
      </el-col>
      <el-col :span="8">
        <el-date-picker v-model="filters.dateRange" type="daterange" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" style="width:100%" />
      </el-col>
      <el-col :span="3"><el-button type="primary" @click="fetchEvents">查询</el-button></el-col>
      <el-col :span="3"><el-button @click="exportCsv">导出CSV</el-button></el-col>
    </el-row>

    <el-table :data="store.events" stripe v-loading="store.loading" row-key="id">
      <el-table-column type="expand">
        <template #default="{ row }">
          <div style="padding: 12px 48px">
            <p><strong>完整详情：</strong></p>
            <p style="white-space: pre-wrap">{{ row.detail }}</p>
            <p v-if="row.ip"><strong>IP地址：</strong>{{ row.ip }}</p>
            <p v-if="row.user_id"><strong>用户ID：</strong>{{ row.user_id }}</p>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="event_type" label="事件类型" width="140">
        <template #default="{ row }">{{ eventTypeLabel(row.event_type) }}</template>
      </el-table-column>
      <el-table-column prop="severity" label="严重程度" width="100">
        <template #default="{ row }">
          <el-tag :type="severityType(row.severity)">{{ severityLabel(row.severity) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="user_id" label="用户ID" width="120" show-overflow-tooltip />
      <el-table-column prop="ip" label="IP" width="140" />
      <el-table-column prop="detail" label="详情" min-width="200" show-overflow-tooltip />
      <el-table-column prop="created_at" label="时间" width="180" />
    </el-table>

    <el-pagination
      v-model:current-page="page"
      :page-size="20"
      :total="store.total"
      layout="prev, pager, next"
      style="margin-top: 16px; justify-content: flex-end"
      @current-change="fetchEvents"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { useSecurityAuditStore } from "../stores/securityAudit";

const store = useSecurityAuditStore();

const page = ref(1);
const filters = reactive({
  event_type: "" as string,
  severity: "" as string,
  dateRange: null as [string, string] | null,
});

function eventTypeLabel(t: string): string {
  const map: Record<string, string> = { login_failure: "登录失败", permission_change: "权限变更", data_access: "数据访问", api_abuse: "API滥用", suspicious_activity: "可疑活动" };
  return map[t] || t;
}

function severityType(s: string): string {
  const map: Record<string, string> = { critical: "danger", high: "danger", medium: "warning", low: "info" };
  return map[s] || "info";
}

function severityLabel(s: string): string {
  const map: Record<string, string> = { critical: "严重", high: "高", medium: "中", low: "低" };
  return map[s] || s;
}

async function fetchEvents() {
  try {
    const params: Record<string, unknown> = {};
    if (filters.event_type) params.event_type = filters.event_type;
    if (filters.severity) params.severity = filters.severity;
    if (filters.dateRange && filters.dateRange.length === 2) {
      params.start_date = filters.dateRange[0];
      params.end_date = filters.dateRange[1];
    }
    await store.fetchEvents(page.value, 20, params);
  } catch {
    ElMessage.error("获取安全审计数据失败");
  }
}

async function exportCsv() {
  try {
    const params: Record<string, unknown> = {};
    if (filters.event_type) params.event_type = filters.event_type;
    if (filters.severity) params.severity = filters.severity;
    if (filters.dateRange && filters.dateRange.length === 2) {
      params.start_date = filters.dateRange[0];
      params.end_date = filters.dateRange[1];
    }
    const blob = await store.exportCsv(params);
    const url = window.URL.createObjectURL(new Blob([blob as BlobPart]));
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", "security-audit.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch { ElMessage.error("导出失败"); }
}

onMounted(fetchEvents);
</script>
