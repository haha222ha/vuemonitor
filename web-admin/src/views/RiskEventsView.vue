<template>
  <div>
    <h2>风控事件</h2>
    <el-table :data="events" stripe v-loading="loading">
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
import { ref, onMounted } from "vue";
import api from "../utils/api";
import { ElMessage } from "element-plus";

const events = ref([]);
const loading = ref(false);

onMounted(async () => {
  loading.value = true;
  try {
    const { data } = await api.get("/admin/risk-events");
    events.value = data?.data?.items || [];
  } catch {
    ElMessage.error("获取风控事件失败");
  } finally {
    loading.value = false;
  }
});
</script>
