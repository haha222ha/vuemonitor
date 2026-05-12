<template>
  <div>
    <h2>风控事件</h2>
    <el-table :data="store.events" stripe v-loading="store.loading">
      <el-table-column prop="platform" label="平台" width="80" />
      <el-table-column prop="risk_type" label="风险类型" width="120" />
      <el-table-column prop="severity" label="严重程度" width="100">
        <template #default="{ row }"><el-tag :type="row.severity === 'high' ? 'danger' : row.severity === 'medium' ? 'warning' : 'info'">{{ row.severity }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="detail" label="详情" min-width="200" />
      <el-table-column prop="resolved" label="已处理" width="80">
        <template #default="{ row }"><el-tag :type="row.resolved ? 'success' : 'warning'">{{ row.resolved ? "是" : "否" }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="created_at" label="时间" width="180" />
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import { ElMessage } from "element-plus";
import { useRiskEventsStore } from "../stores/riskEvents";

const store = useRiskEventsStore();

onMounted(async () => {
  try {
    await store.fetchEvents();
  } catch {
    ElMessage.error("获取风控事件失败");
  }
});
</script>
