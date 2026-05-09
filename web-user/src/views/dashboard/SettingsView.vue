<template>
  <div class="settings-page">
    <el-row :gutter="20">
      <el-col :span="12">
        <div class="panel">
          <h3>账户信息</h3>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="邮箱">{{ auth.user?.email || "—" }}</el-descriptions-item>
            <el-descriptions-item label="昵称">{{ auth.user?.nickname || "—" }}</el-descriptions-item>
            <el-descriptions-item label="当前套餐">
              <el-tag>{{ auth.userPlan }}</el-tag>
            </el-descriptions-item>
          </el-descriptions>
          <el-button type="primary" size="small" style="margin-top: 16px" @click="$router.push('/pricing')">升级套餐</el-button>
        </div>
      </el-col>
      <el-col :span="12">
        <div class="panel">
          <h3>授权码激活</h3>
          <el-input v-model="licenseCode" placeholder="输入授权码" style="margin-bottom: 12px" />
          <el-button type="primary" :loading="activating" @click="activateLicense">激活</el-button>
        </div>

        <div class="panel" style="margin-top: 20px;">
          <h3>通知偏好</h3>
          <el-form label-width="100px">
            <el-form-item label="采集完成">
              <el-switch v-model="notifSettings.collectDone" />
            </el-form-item>
            <el-form-item label="AI分析完成">
              <el-switch v-model="notifSettings.aiDone" />
            </el-form-item>
            <el-form-item label="风险预警">
              <el-switch v-model="notifSettings.riskAlert" />
            </el-form-item>
          </el-form>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from "vue";
import { useAuthStore } from "../../stores/auth";
import api from "../../utils/api";
import { ElMessage } from "element-plus";

const auth = useAuthStore();
const licenseCode = ref("");
const activating = ref(false);
const notifSettings = reactive({
  collectDone: true,
  aiDone: true,
  riskAlert: true,
});

async function activateLicense() {
  if (!licenseCode.value.trim()) {
    ElMessage.warning("请输入授权码");
    return;
  }
  activating.value = true;
  try {
    await api.post("/auth/license/activate", { code: licenseCode.value.trim() });
    ElMessage.success("授权码激活成功");
    licenseCode.value = "";
    auth.fetchUser();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || "激活失败");
  } finally {
    activating.value = false;
  }
}
</script>

<style scoped>
.settings-page {
  padding: 4px;
}

.panel {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 20px;
}

.panel h3 {
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  margin: 0 0 16px;
}
</style>
