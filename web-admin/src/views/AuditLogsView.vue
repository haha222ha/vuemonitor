<template>
  <div>
    <h2>操作日志</h2>
    <el-table :data="logs" stripe v-loading="loading">
      <el-table-column prop="operator" label="操作人" width="120" />
      <el-table-column prop="action" label="操作" width="150" />
      <el-table-column prop="target" label="目标" width="150" />
      <el-table-column prop="detail" label="详情" min-width="200" />
      <el-table-column prop="ip" label="IP" width="130" />
      <el-table-column prop="created_at" label="时间" width="180" />
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import api from "../utils/api";
import { ElMessage } from "element-plus";

const logs = ref([]);
const loading = ref(false);

onMounted(async () => {
  loading.value = true;
  try {
    const { data } = await api.get("/admin/audit-logs");
    logs.value = data?.data?.items || [];
  } catch {
    ElMessage.error("获取操作日志失败");
  } finally {
    loading.value = false;
  }
});
</script>
