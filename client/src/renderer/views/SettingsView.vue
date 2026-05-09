<template>
  <div>
    <h2>设置</h2>
    <el-card style="margin-top: 16px">
      <h3>账户信息</h3>
      <el-descriptions :column="1" border v-if="authStore.user">
        <el-descriptions-item label="邮箱">{{ authStore.user.email }}</el-descriptions-item>
        <el-descriptions-item label="昵称">{{ authStore.user.nickname }}</el-descriptions-item>
        <el-descriptions-item label="套餐">{{ authStore.user.plan }}</el-descriptions-item>
        <el-descriptions-item label="套餐到期">{{ authStore.user.plan_expires_at || "永久" }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card style="margin-top: 16px">
      <h3>授权码激活</h3>
      <el-form :inline="true">
        <el-form-item>
          <el-input v-model="licenseCode" placeholder="输入授权码" style="width: 300px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="activateLicense">激活</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useAuthStore } from "../stores/auth";
import { ElMessage } from "element-plus";

const authStore = useAuthStore();
const licenseCode = ref("");

async function activateLicense() {
  if (!licenseCode.value) {
    ElMessage.warning("请输入授权码");
    return;
  }
  ElMessage.info("授权码激活功能将在后续版本实现");
}
</script>
