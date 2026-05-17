<template>
  <div class="license__activate">
    <div class="license__activate-card">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
        <el-form-item label="授权码" prop="licenseKey">
          <el-input v-model="form.licenseKey" placeholder="VM-XXXX-XXXX-XXXX-XXXX" maxlength="27" @input="formatLicenseKey" style="font-family: monospace; letter-spacing: 2px" />
        </el-form-item>
        <el-form-item label="验证方式">
          <el-radio-group v-model="form.verifyMode">
            <el-radio value="online">在线验证</el-radio>
            <el-radio value="offline">离线验证</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="form.verifyMode === 'online'" label="服务器" prop="serverUrl">
          <el-input v-model="form.serverUrl" placeholder="https://api.example.com" />
        </el-form-item>
      </el-form>

      <div v-if="licenseStore.error" class="license__error">
        <el-alert :title="licenseStore.error" type="error" show-icon :closable="false" />
      </div>

      <el-button type="primary" size="large" :loading="licenseStore.loading" @click="$emit('activate')" class="license__activate-btn">激活</el-button>

      <div class="license__device-info">
        <span>设备ID: {{ deviceInfo?.deviceId || '获取中...' }}</span>
        <span>指纹: {{ deviceInfo?.fingerprint?.substring(0, 16) || '...' }}...</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  form: { licenseKey: string; verifyMode: string; serverUrl: string };
  rules: any;
  formRef: any;
  licenseStore: any;
  deviceInfo: { deviceId: string; fingerprint: string } | null;
  formatLicenseKey: (val: string) => void;
}>();

defineEmits<{
  (e: "activate"): void;
}>();
</script>

<style scoped>
.license__activate { padding: 20px 0; }
.license__activate-card { background: var(--color-bg-card); border: 1px solid var(--color-border-light); border-radius: var(--radius-lg); padding: 32px; max-width: 480px; margin: 0 auto; }
.license__error { margin: 12px 0; }
.license__activate-btn { width: 100%; margin-top: 20px; }
.license__device-info { margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--color-border-light); font-size: var(--text-xs); color: var(--color-text-tertiary); display: flex; flex-direction: column; gap: 4px; text-align: center; }
</style>
