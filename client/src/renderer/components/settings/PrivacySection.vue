<template>
  <div class="settings-section">
    <h2 class="section-title">隐私管理</h2>
    <div class="settings-card">
      <div class="setting-item">
        <div class="setting-info">
          <h3 class="setting-title">数据收集偏好</h3>
          <p class="setting-desc">控制您的数据如何被收集和使用</p>
        </div>
      </div>
      <div class="privacy-toggles">
        <div class="privacy-toggle-item">
          <div class="privacy-toggle-info">
            <span class="privacy-toggle-label">使用数据收集</span>
            <span class="privacy-toggle-desc">帮助我们改进产品功能</span>
          </div>
          <el-switch v-model="clientPrivacy.dataCollection" />
        </div>
        <div class="privacy-toggle-item">
          <div class="privacy-toggle-info">
            <span class="privacy-toggle-label">匿名聚合贡献</span>
            <span class="privacy-toggle-desc">您的数据将匿名化后用于群体洞察</span>
          </div>
          <el-switch v-model="clientPrivacy.anonymousAggregation" />
        </div>
        <div class="privacy-toggle-item">
          <div class="privacy-toggle-info">
            <span class="privacy-toggle-label">AI分析数据使用</span>
            <span class="privacy-toggle-desc">允许AI分析使用您的监控数据</span>
          </div>
          <el-switch v-model="clientPrivacy.aiDataUsage" />
        </div>
        <div class="privacy-toggle-item">
          <div class="privacy-toggle-info">
            <span class="privacy-toggle-label">错误报告自动发送</span>
            <span class="privacy-toggle-desc">自动发送崩溃和错误信息帮助排查问题</span>
          </div>
          <el-switch v-model="clientPrivacy.autoErrorReport" />
        </div>
      </div>
      <div class="setting-divider"></div>
      <div class="setting-item">
        <div class="setting-info">
          <h3 class="setting-title">云端数据管理 (GDPR)</h3>
          <p class="setting-desc">管理您在云端服务器上的个人数据</p>
        </div>
      </div>
      <div class="privacy-cloud-actions">
        <el-button size="small" @click="$emit('cloud-data-summary')" :loading="cloudDataLoading">查看数据摘要</el-button>
        <el-button size="small" @click="$emit('cloud-data-export')" :loading="cloudExportLoading">导出云端数据</el-button>
        <el-button size="small" @click="$emit('show-privacy-policy')">隐私政策</el-button>
      </div>
      <div v-if="cloudDataSummary" class="cloud-data-summary">
        <div class="cloud-data-grid">
          <div v-for="(count, table) in cloudDataSummary.tables" :key="table" class="cloud-data-item">
            <span class="cloud-data-label">{{ cloudTableLabel(table as string) }}</span>
            <span class="cloud-data-value">{{ count < 0 ? '?' : count }}</span>
          </div>
        </div>
        <div class="cloud-data-total">总记录数: <strong>{{ cloudDataSummary.total_records }}</strong></div>
      </div>
      <div class="setting-divider"></div>
      <div class="privacy-danger-zone">
        <h4 class="danger-zone-title">危险区域</h4>
        <p class="danger-zone-desc">删除数据操作不可逆。根据 GDPR 被遗忘权，您可以请求删除所有云端个人数据。删除后账户将被匿名化且无法恢复。</p>
        <el-button type="danger" size="small" @click="$emit('cloud-data-deletion')" :loading="cloudDeleteLoading">
          请求删除所有云端数据
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  clientPrivacy: any;
  cloudDataSummary: any;
  cloudDataLoading: boolean;
  cloudExportLoading: boolean;
  cloudDeleteLoading: boolean;
  cloudTableLabel: (table: string) => string;
}>();

defineEmits<{
  'cloud-data-summary': [];
  'cloud-data-export': [];
  'show-privacy-policy': [];
  'cloud-data-deletion': [];
}>();
</script>

<style scoped>
.settings-section { max-width: 800px; }
.section-title { margin: 0 0 16px; font-size: var(--text-xl); font-weight: 600; color: var(--color-text-primary); }
.settings-card { background: var(--color-bg-card); border: 1px solid var(--color-border-light); border-radius: var(--radius-lg); padding: 20px; }
.setting-item { display: flex; justify-content: space-between; align-items: center; padding: 16px 0; }
.setting-info { flex: 1; }
.setting-title { margin: 0 0 4px; font-size: var(--text-sm); font-weight: 500; color: var(--color-text-primary); }
.setting-desc { margin: 0; font-size: var(--text-xs); color: var(--color-text-secondary); }
.setting-divider { height: 1px; background: var(--color-border-light); }
.privacy-toggles { display: flex; flex-direction: column; gap: 12px; padding: 12px 0; }
.privacy-toggle-item { display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; background: var(--color-bg-page); border-radius: var(--radius-base); }
.privacy-toggle-info { display: flex; flex-direction: column; gap: 2px; }
.privacy-toggle-label { font-size: 13px; font-weight: 500; color: var(--color-text-primary); }
.privacy-toggle-desc { font-size: 11px; color: var(--color-text-secondary); }
.privacy-cloud-actions { display: flex; gap: 8px; flex-wrap: wrap; padding: 8px 0; }
.cloud-data-summary { margin-top: 12px; padding: 12px; background: var(--color-bg-page); border-radius: var(--radius-lg); }
.cloud-data-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 8px; }
.cloud-data-item { display: flex; justify-content: space-between; align-items: center; padding: 6px 10px; background: var(--color-bg-card); border-radius: var(--radius-sm); }
.cloud-data-label { font-size: 12px; color: var(--color-text-secondary); }
.cloud-data-value { font-size: 13px; font-weight: 600; color: var(--color-text-primary); }
.cloud-data-total { font-size: 13px; color: var(--color-text-secondary); }
.cloud-data-total strong { color: var(--color-text-primary); }
.privacy-danger-zone { border: 1px solid var(--color-danger-light); border-radius: var(--radius-lg); padding: 16px; background: rgba(245, 108, 108, 0.03); }
.danger-zone-title { font-size: 14px; font-weight: 600; color: var(--color-danger); margin: 0 0 8px; }
.danger-zone-desc { font-size: 12px; color: var(--color-text-secondary); margin: 0 0 12px; line-height: 1.6; }
</style>
