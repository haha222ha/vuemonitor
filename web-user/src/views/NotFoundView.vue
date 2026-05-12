<template>
  <div class="not-found-view">
    <el-result
      icon="error"
      title="404"
      sub-title="页面未找到"
    >
      <template #extra>
        <el-button type="primary" @click="goBack">返回首页</el-button>
      </template>
    </el-result>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";

const router = useRouter();

function goBack() {
  router.push({ name: "Dashboard" });
}
</script>

<style scoped>
.not-found-view {
  margin-top: 20vh;
  text-align: center;
}
</style>