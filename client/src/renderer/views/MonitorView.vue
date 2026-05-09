<template>
  <div>
    <h2>监控规则</h2>
    <el-table :data="rules" stripe v-loading="loading">
      <el-table-column prop="rule_name" label="规则名称" />
      <el-table-column prop="rule_type" label="类型" width="120" />
      <el-table-column prop="is_active" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? "启用" : "停用" }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="trigger_count" label="触发次数" width="100" />
      <el-table-column label="操作" width="150">
        <template #default="{ row }">
          <el-button size="small" @click="toggleRule(row)">{{ row.is_active ? "停用" : "启用" }}</el-button>
          <el-button size="small" type="danger" @click="confirmDeleteRule(row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <h2 style="margin-top: 24px">通知</h2>
    <el-table :data="notifications" stripe>
      <el-table-column prop="title" label="标题" />
      <el-table-column prop="type" label="类型" width="120" />
      <el-table-column prop="is_read" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.is_read ? 'info' : 'warning'">{{ row.is_read ? "已读" : "未读" }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="时间" width="180" />
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import api from "../utils/api";
import { ElMessage, ElMessageBox } from "element-plus";

const rules = ref([]);
const notifications = ref([]);
const loading = ref(false);

async function fetchData() {
  loading.value = true;
  try {
    const [rulesRes, notifRes] = await Promise.all([
      api.get("/monitor/rules"),
      api.get("/monitor/notifications"),
    ]);
    rules.value = rulesRes.data?.data || [];
    notifications.value = notifRes.data?.data?.items || [];
  } catch {
    ElMessage.error("获取数据失败");
  } finally {
    loading.value = false;
  }
}

async function toggleRule(rule: any) {
  try {
    await api.put(`/monitor/rules/${rule.id}`, { is_active: !rule.is_active });
    ElMessage.success(rule.is_active ? "已停用" : "已启用");
    fetchData();
  } catch {
    ElMessage.error("操作失败");
  }
}

async function confirmDeleteRule(id: string) {
  try {
    await ElMessageBox.confirm("确定要删除该规则吗？", "确认删除", {
      confirmButtonText: "删除",
      cancelButtonText: "取消",
      type: "warning",
    });
    await deleteRule(id);
  } catch {}
}

async function deleteRule(id: string) {
  try {
    await api.delete(`/monitor/rules/${id}`);
    ElMessage.success("删除成功");
    fetchData();
  } catch {
    ElMessage.error("删除失败");
  }
}

onMounted(fetchData);
</script>
