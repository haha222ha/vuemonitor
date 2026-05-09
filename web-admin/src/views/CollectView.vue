<template>
  <div>
    <h2>采集任务管理</h2>
    <el-table :data="tasks" stripe v-loading="loading">
      <el-table-column prop="task_type" label="类型" width="100" />
      <el-table-column prop="platform" label="平台" width="80" />
      <el-table-column prop="target_type" label="目标类型" width="100" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }"><el-tag :type="statusType(row.status)">{{ row.status }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="progress" label="进度" width="100">
        <template #default="{ row }"><el-progress :percentage="row.progress || 0" :stroke-width="6" /></template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180" />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button v-if="row.status === 'running'" size="small" type="danger" @click="cancelTask(row.id)">取消</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import api from "../utils/api";
import { ElMessage } from "element-plus";

const tasks = ref([]);
const loading = ref(false);

function statusType(status: string) {
  const map: Record<string, string> = { pending: "warning", running: "primary", completed: "success", failed: "danger", cancelled: "info" };
  return map[status] || "info";
}

async function fetchTasks() {
  loading.value = true;
  try {
    const { data } = await api.get("/admin/collect/tasks");
    tasks.value = data?.data?.items || [];
  } catch {
    ElMessage.error("获取采集任务列表失败");
  } finally {
    loading.value = false;
  }
}

async function cancelTask(id: string) {
  try {
    await api.put(`/admin/collect/tasks/${id}/cancel`);
    ElMessage.success("已取消");
    fetchTasks();
  } catch {
    ElMessage.error("取消任务失败");
  }
}

onMounted(fetchTasks);
</script>
