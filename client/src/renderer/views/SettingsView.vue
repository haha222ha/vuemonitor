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
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <h3 style="margin: 0">授权信息</h3>
          <el-button size="small" @click="$router.push('/license')">管理授权</el-button>
        </div>
      </template>
      <el-descriptions :column="2" border v-if="licenseStore.isActivated">
        <el-descriptions-item label="当前套餐">
          <el-tag type="success">{{ licenseStore.planLabel }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="到期时间">{{ licenseStore.expiresAtFormatted }}</el-descriptions-item>
        <el-descriptions-item label="设备ID">
          <span style="font-family: monospace; font-size: 12px">{{ licenseStore.license?.deviceId }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="最后验证">{{ licenseStore.license?.lastVerified }}</el-descriptions-item>
      </el-descriptions>
      <el-empty v-else description="未激活授权码" :image-size="60">
        <el-button type="primary" size="small" @click="$router.push('/license')">前往激活</el-button>
      </el-empty>
    </el-card>

    <el-card style="margin-top: 16px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <h3 style="margin: 0">数据同步</h3>
          <el-button size="small" :loading="syncing" @click="handleSyncNow">
            立即同步
          </el-button>
        </div>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="同步状态">
          <el-tag :type="syncStatus.isSyncing ? 'warning' : 'success'">
            {{ syncStatus.isSyncing ? "同步中..." : "空闲" }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="服务器">
          {{ syncStatus.serverUrl || "未配置" }}
        </el-descriptions-item>
        <el-descriptions-item label="上次同步">
          {{ syncStatus.lastSyncAt || "从未同步" }}
        </el-descriptions-item>
        <el-descriptions-item label="待同步">
          <el-badge :value="syncStatus.pendingCount" :type="syncStatus.pendingCount > 0 ? 'danger' : 'info'" />
        </el-descriptions-item>
        <el-descriptions-item label="已同步">{{ syncStatus.syncedCount }}</el-descriptions-item>
        <el-descriptions-item label="失败">{{ syncStatus.failedCount }}</el-descriptions-item>
      </el-descriptions>

      <div style="margin-top: 16px">
        <el-form :inline="true" v-if="!syncStatus.serverUrl">
          <el-form-item label="服务器地址">
            <el-input v-model="serverUrl" placeholder="https://api.xhs365.com" style="width: 280px" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleConnect">连接</el-button>
          </el-form-item>
        </el-form>
        <div v-else>
          <el-button size="small" @click="handleStartAutoSync" v-if="!autoSyncStarted">
            开启自动同步
          </el-button>
          <el-button size="small" type="danger" @click="handleStopAutoSync" v-else>
            停止自动同步
          </el-button>
        </div>
      </div>
    </el-card>

    <el-card style="margin-top: 16px">
      <h3>采集配置</h3>
      <el-form label-width="120px">
        <el-form-item label="最大并发数">
          <el-input-number v-model="concurrency" :min="1" :max="10" @change="handleConcurrencyChange" />
        </el-form-item>
        <el-form-item label="自动最小化">
          <el-switch v-model="autoMinimize" />
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted } from "vue";
import { useAuthStore } from "../stores/auth";
import { useLicenseStore } from "../stores/license";
import { ElMessage } from "element-plus";

const authStore = useAuthStore();
const licenseStore = useLicenseStore();

const serverUrl = ref("");
const syncing = ref(false);
const autoSyncStarted = ref(false);
const concurrency = ref(3);
const autoMinimize = ref(true);

const syncStatus = reactive({
  lastSyncAt: null as string | null,
  pendingCount: 0,
  syncedCount: 0,
  failedCount: 0,
  isSyncing: false,
  serverUrl: null as string | null,
});

let statusTimer: ReturnType<typeof setInterval> | null = null;

onMounted(async () => {
  await licenseStore.fetchLicense();
  await refreshSyncStatus();

  statusTimer = setInterval(refreshSyncStatus, 10000);
});

onUnmounted(() => {
  if (statusTimer) {
    clearInterval(statusTimer);
  }
});

async function refreshSyncStatus() {
  try {
    const status = await window.electronAPI.invoke("sync:status") as typeof syncStatus;
    Object.assign(syncStatus, status);
  } catch {}
}

async function handleSyncNow() {
  syncing.value = true;
  try {
    const result = await window.electronAPI.invoke("sync:now") as { pushed: number; pulled: number; errors: number };
    ElMessage.success(`同步完成：推送${result.pushed}条，拉取${result.pulled}条`);
    await refreshSyncStatus();
  } catch (err) {
    ElMessage.error("同步失败");
  } finally {
    syncing.value = false;
  }
}

async function handleConnect() {
  if (!serverUrl.value) {
    ElMessage.warning("请输入服务器地址");
    return;
  }
  try {
    const token = localStorage.getItem("access_token") || "";
    await window.electronAPI.invoke("sync:configure", serverUrl.value, token);
    ElMessage.success("服务器连接配置成功");
    await refreshSyncStatus();
  } catch (err) {
    ElMessage.error("连接配置失败");
  }
}

async function handleStartAutoSync() {
  try {
    await window.electronAPI.invoke("sync:start");
    autoSyncStarted.value = true;
    ElMessage.success("已开启自动同步（每5分钟）");
  } catch {
    ElMessage.error("启动自动同步失败");
  }
}

async function handleStopAutoSync() {
  try {
    await window.electronAPI.invoke("sync:stop");
    autoSyncStarted.value = false;
    ElMessage.info("已停止自动同步");
  } catch {
    ElMessage.error("停止自动同步失败");
  }
}

async function handleConcurrencyChange(val: number) {
  try {
    await window.electronAPI.invoke("concurrency:set", val);
  } catch {}
}
</script>
