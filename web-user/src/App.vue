<template>
  <div v-if="error" class="global-error-boundary">
    <div class="error-content">
      <div class="error-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
      </div>
      <h2>页面出现异常</h2>
      <p class="error-message">{{ errorMessage }}</p>
      <div class="error-actions">
        <el-button type="primary" @click="retry">重新加载</el-button>
        <el-button @click="goHome">返回首页</el-button>
      </div>
    </div>
  </div>
  <router-view v-else />
</template>

<script setup lang="ts">
import { ref, onErrorCaptured, computed } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();
const error = ref<Error | null>(null);

const errorMessage = computed(() => {
  if (!error.value) return "";
  const msg = error.value.message || "未知错误";
  return msg.length > 200 ? msg.slice(0, 200) + "..." : msg;
});

onErrorCaptured((err: Error) => {
  error.value = err;
  console.error("[ErrorBoundary]", err);
  return false;
});

function retry() {
  error.value = null;
}

function goHome() {
  error.value = null;
  router.push("/dashboard");
}
</script>

<style scoped>
.global-error-boundary {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: #0f0f1a;
  color: #e0e0e0;
}

.error-content {
  text-align: center;
  max-width: 480px;
  padding: 40px;
}

.error-icon {
  margin-bottom: 24px;
}

.error-icon svg {
  width: 64px;
  height: 64px;
  color: #f59e0b;
}

.error-content h2 {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 12px;
  color: #fff;
}

.error-message {
  font-size: 14px;
  color: #8a8a9a;
  margin-bottom: 24px;
  word-break: break-all;
}

.error-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
}
</style>
