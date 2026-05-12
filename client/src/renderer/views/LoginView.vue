<template>
  <div class="login-container">
    <el-card class="login-card">
      <h2>XHS365 登录</h2>
      <el-form :model="form" :rules="loginRules" ref="loginFormRef" @submit.prevent="handleLogin">
        <el-form-item prop="account">
          <el-input v-model="form.account" placeholder="昵称或邮箱" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" placeholder="密码" type="password" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleLogin" style="width: 100%">登录</el-button>
        </el-form-item>
        <el-form-item>
          <el-button text @click="showRegister = true">没有账号？注册</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-dialog v-model="showRegister" title="注册" width="400px">
      <el-form :model="regForm" :rules="regRules" ref="regFormRef">
        <el-form-item prop="nickname">
          <el-input v-model="regForm.nickname" placeholder="昵称（必填）" />
        </el-form-item>
        <el-form-item prop="email">
          <el-input v-model="regForm.email" placeholder="邮箱（选填）" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="regForm.password" placeholder="密码（至少8位，含大小写和数字）" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRegister = false">取消</el-button>
        <el-button type="primary" :loading="regLoading" @click="handleRegister">注册</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import { ElMessage } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";

const router = useRouter();
const authStore = useAuthStore();
const loading = ref(false);
const regLoading = ref(false);
const showRegister = ref(false);
const loginFormRef = ref<FormInstance>();
const regFormRef = ref<FormInstance>();

const form = reactive({ account: "", password: "" });
const regForm = reactive({ email: "", nickname: "", password: "" });

const loginRules: FormRules = {
  account: [
    { required: true, message: "请输入昵称或邮箱", trigger: "blur" },
  ],
  password: [
    { required: true, message: "请输入密码", trigger: "blur" },
  ],
};

const emailPattern = /^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$/;

const regRules: FormRules = {
  nickname: [
    { required: true, message: "请输入昵称", trigger: "blur" },
    { min: 2, max: 20, message: "昵称长度2-20个字符", trigger: "blur" },
  ],
  email: [
    {
      validator: (_rule, value, callback) => {
        if (!value || value.trim() === "") {
          callback();
        } else if (!emailPattern.test(value.trim())) {
          callback(new Error("邮箱格式不正确"));
        } else {
          callback();
        }
      },
      trigger: "blur",
    },
  ],
  password: [
    { required: true, message: "请输入密码", trigger: "blur" },
    { min: 8, message: "密码至少8位", trigger: "blur" },
    {
      validator: (_rule, value, callback) => {
        if (value && !/[A-Z]/.test(value)) {
          callback(new Error("密码需包含大写字母"));
        } else if (value && !/[a-z]/.test(value)) {
          callback(new Error("密码需包含小写字母"));
        } else if (value && !/[0-9]/.test(value)) {
          callback(new Error("密码需包含数字"));
        } else {
          callback();
        }
      },
      trigger: "blur",
    },
  ],
};

async function handleLogin() {
  const valid = await loginFormRef.value?.validate().catch(() => false);
  if (!valid) return;

  loading.value = true;
  try {
    await authStore.login(form.account, form.password);
    router.push("/dashboard");
    ElMessage.success("登录成功");
  } catch {
    ElMessage.error("登录失败，请检查账号和密码");
  } finally {
    loading.value = false;
  }
}

async function handleRegister() {
  const valid = await regFormRef.value?.validate().catch(() => false);
  if (!valid) return;

  regLoading.value = true;
  try {
    await authStore.register(regForm.email || undefined, regForm.nickname, regForm.password);
    ElMessage.success("注册成功，请登录");
    showRegister.value = false;
    form.account = regForm.nickname;
    regForm.email = "";
    regForm.nickname = "";
    regForm.password = "";
  } catch (e: any) {
    const msg = e?.response?.data?.message || e?.message || "注册失败，请稍后重试";
    ElMessage.error(msg);
  } finally {
    regLoading.value = false;
  }
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f2f5;
}
.login-card {
  width: 400px;
  padding: 20px;
}
.login-card h2 {
  text-align: center;
  margin-bottom: 24px;
}
</style>
