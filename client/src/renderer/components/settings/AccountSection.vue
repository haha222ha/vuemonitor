<template>
  <div class="settings-section">
    <h2 class="section-title">账户信息</h2>
    <div class="settings-card">
      <div class="account-info" v-if="authStore.user">
        <div class="account-avatar">
          <div class="avatar-circle">{{ (authStore.user.nickname || authStore.user.email || 'U')[0].toUpperCase() }}</div>
        </div>
        <div class="account-details">
          <div class="detail-row">
            <span class="detail-label">邮箱</span>
            <span class="detail-value">{{ authStore.user.email || '未设置' }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">昵称</span>
            <span class="detail-value">{{ authStore.user.nickname }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">套餐</span>
            <el-tag class="plan-tag" effect="plain">{{ authStore.user.plan }}</el-tag>
          </div>
          <div class="detail-row">
            <span class="detail-label">套餐到期</span>
            <span class="detail-value">{{ authStore.user.plan_expires_at || "永久" }}</span>
          </div>
        </div>
      </div>
    </div>

    <h2 class="section-title" style="margin-top: 32px">授权信息</h2>
    <div class="settings-card">
      <div v-if="licenseStore.isActivated" class="license-info">
        <div class="license-grid">
          <div class="license-item">
            <span class="license-label">当前套餐</span>
            <el-tag type="success" effect="plain">{{ licenseStore.planLabel }}</el-tag>
          </div>
          <div class="license-item">
            <span class="license-label">到期时间</span>
            <span class="license-value">{{ licenseStore.expiresAtFormatted }}</span>
          </div>
          <div class="license-item">
            <span class="license-label">设备ID</span>
            <code class="device-id">{{ licenseStore.license?.deviceId }}</code>
          </div>
          <div class="license-item">
            <span class="license-label">最后验证</span>
            <span class="license-value">{{ licenseStore.license?.lastVerified }}</span>
          </div>
        </div>
      </div>
      <div v-else class="license-empty">
        <el-icon class="empty-icon"><Key /></el-icon>
        <p>未激活授权码</p>
        <el-button type="primary" @click="$router.push('/license')">前往激活</el-button>
      </div>
      <div class="card-actions">
        <el-button @click="$router.push('/license')">管理授权</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Key } from "@element-plus/icons-vue";

defineProps<{
  authStore: any;
  licenseStore: any;
}>();
</script>

<style scoped>
.settings-section { max-width: 800px; }
.section-title { margin: 0 0 16px; font-size: var(--text-xl); font-weight: 600; color: var(--color-text-primary); }
.settings-card { background: var(--color-bg-card); border: 1px solid var(--color-border-light); border-radius: var(--radius-lg); padding: 20px; }
.account-info { display: flex; gap: 20px; }
.account-avatar { flex-shrink: 0; }
.avatar-circle { width: 64px; height: 64px; border-radius: 50%; background: var(--gradient-hero); display: flex; align-items: center; justify-content: center; color: #fff; font-size: 24px; font-weight: 600; }
.account-details { flex: 1; display: flex; flex-direction: column; gap: 12px; }
.detail-row { display: flex; align-items: center; gap: 12px; }
.detail-label { font-size: var(--text-sm); color: var(--color-text-secondary); min-width: 80px; }
.detail-value { font-size: var(--text-sm); color: var(--color-text-primary); }
.plan-tag { padding: 4px 10px; border-radius: var(--radius-sm); }
.license-info { margin-bottom: 16px; }
.license-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
.license-item { display: flex; flex-direction: column; gap: 6px; }
.license-label { font-size: var(--text-xs); color: var(--color-text-secondary); }
.license-value { font-size: var(--text-sm); color: var(--color-text-primary); }
.device-id { font-family: monospace; font-size: var(--text-xs); background: var(--color-bg-page); padding: 4px 8px; border-radius: var(--radius-sm); color: var(--color-text-primary); }
.license-empty { text-align: center; padding: 32px 0; color: var(--color-text-secondary); }
.empty-icon { font-size: 48px; color: var(--color-text-tertiary); margin-bottom: 12px; }
.card-actions { display: flex; justify-content: flex-end; padding-top: 16px; border-top: 1px solid var(--color-border-light); }
@media (max-width: 768px) { .account-info { flex-direction: column; align-items: center; text-align: center; } .license-grid { grid-template-columns: 1fr; } }
</style>
