<template>
  <div>
    <h2>仪表盘</h2>
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="监控商品" :value="stats.productCount" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="今日采集" :value="stats.todayCollect" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="监控规则" :value="stats.ruleCount" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <el-statistic title="未读通知" :value="stats.unreadNotifications" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { reactive, onMounted } from "vue";
import api from "../utils/api";
import { ElMessage } from "element-plus";

const stats = reactive({
  productCount: 0,
  todayCollect: 0,
  ruleCount: 0,
  unreadNotifications: 0,
});

onMounted(async () => {
  try {
    const [products, rules, notifications] = await Promise.allSettled([
      api.get("/products"),
      api.get("/monitor/rules"),
      api.get("/monitor/notifications", { params: { is_read: false, page_size: 1 } }),
    ]);

    if (products.status === "fulfilled") {
      stats.productCount = products.value.data?.data?.total || 0;
    }
    if (rules.status === "fulfilled") {
      stats.ruleCount = rules.value.data?.data?.length || 0;
    }
    if (notifications.status === "fulfilled") {
      stats.unreadNotifications = notifications.value.data?.data?.total || 0;
    }

    const failedCount = [products, rules, notifications].filter((r) => r.status === "rejected").length;
    if (failedCount > 0) {
      ElMessage.warning(`${failedCount}项数据加载失败`);
    }
  } catch {
    ElMessage.error("仪表盘数据加载失败");
  }
});
</script>
