<template>
  <div class="login-container">
    <el-card class="login-card">
      <h2>XHS365 管理后台</h2>
      <el-form :model="form" @submit.prevent="handleLogin">
        <el-form-item><el-input v-model="form.username" placeholder="管理员账号" /></el-form-item>
        <el-form-item><el-input v-model="form.password" placeholder="密码" type="password" show-password /></el-form-item>
        <el-button type="primary" :loading="loading" @click="handleLogin" style="width:100%">登录</el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import api from "../utils/api";

const router = useRouter();
const loading = ref(false);
const form = reactive({ username: "", password: "" });

async function handleLogin() {
  loading.value = true;
  try {
    const { data } = await api.post("/admin/login", form);
    localStorage.setItem("admin_token", data.access_token);
    router.push("/dashboard");
    ElMessage.success("登录成功");
  } catch { ElMessage.error("登录失败"); }
  finally { loading.value = false; }
}
</script>

<style scoped>
.login-container { height: 100vh; display: flex; align-items: center; justify-content: center; background: #f0f2f5; }
.login-card { width: 400px; padding: 20px; }
.login-card h2 { text-align: center; margin-bottom: 24px; }
</style>
