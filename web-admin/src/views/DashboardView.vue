<template>
  <div>
    <h2>管理仪表盘</h2>
    <el-row :gutter="20">
      <el-col :span="6"><el-card shadow="hover"><el-statistic title="总用户数" :value="stats.totalUsers" /></el-card></el-col>
      <el-col :span="6"><el-card shadow="hover"><el-statistic title="活跃用户" :value="stats.activeUsers" /></el-card></el-col>
      <el-col :span="6"><el-card shadow="hover"><el-statistic title="今日采集任务" :value="stats.todayTasks" /></el-card></el-col>
      <el-col :span="6"><el-card shadow="hover"><el-statistic title="可用代理" :value="stats.availableProxies" /></el-card></el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { reactive, onMounted } from "vue";
import api from "../utils/api";

const stats = reactive({ totalUsers: 0, activeUsers: 0, todayTasks: 0, availableProxies: 0 });

onMounted(async () => {
  try {
    const { data } = await api.get("/admin/stats");
    Object.assign(stats, data?.data || {});
  } catch {}
});
</script>
