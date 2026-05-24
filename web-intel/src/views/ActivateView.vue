<template>
  <div class="activate-page">
    <div class="activate-card">
      <h2>激活授权码</h2>
      <p>请输入您的授权码以激活商业情报系统访问权限</p>
      <el-form :model="form" label-position="top" @submit.prevent="handleActivate">
        <el-form-item label="授权码">
          <el-input v-model="form.code" placeholder="请输入16位授权码" size="large" maxlength="20" @keyup.enter="handleActivate" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" size="large" :loading="auth.loading" class="activate-btn" @click="handleActivate">
            激 活
          </el-button>
        </el-form-item>
      </el-form>
      <div class="activate-info">
        <el-alert v-if="auth.hasMembership" title="已激活" type="success" :closable="false" show-icon>
          <template #default>
            <p>当前方案：{{ auth.planLabel }}</p>
            <p>剩余天数：{{ auth.daysRemaining }} 天</p>
            <p>过期时间：{{ auth.membership?.expires_at }}</p>
          </template>
        </el-alert>
      </div>
      <div class="back-link">
        <el-button text type="primary" @click="$router.push('/dashboard')">
          ← 返回仪表盘
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, onMounted } from "vue"
import { useRouter } from "vue-router"
import { ElMessage } from "element-plus"
import { useIntelAuthStore } from "@/stores/auth"

const router = useRouter()
const auth = useIntelAuthStore()
const form = reactive({ code: "" })

onMounted(() => {
  auth.fetchMembership()
})

async function handleActivate() {
  if (!form.code.trim()) {
    ElMessage.warning("请输入授权码")
    return
  }
  const success = await auth.activateCode(form.code)
  if (success) {
    ElMessage.success("激活成功！")
    form.code = ""
    setTimeout(() => router.push("/dashboard"), 1500)
  } else {
    ElMessage.error(auth.error || "激活失败")
  }
}
</script>

<style scoped>
.activate-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}
.activate-card {
  width: 440px;
  padding: 40px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}
.activate-card h2 {
  text-align: center;
  color: #1a1a2e;
  margin-bottom: 8px;
}
.activate-card p {
  text-align: center;
  color: #909399;
  font-size: 14px;
  margin-bottom: 24px;
}
.activate-btn {
  width: 100%;
}
.activate-info {
  margin: 16px 0;
}
.back-link {
  text-align: center;
  margin-top: 12px;
}
</style>