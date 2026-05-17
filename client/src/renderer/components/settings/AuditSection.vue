<template>
  <div class="settings-section">
    <h2 class="section-title">操作审计</h2>
    <div class="settings-card">
      <div class="audit-filters">
        <el-select v-model="auditFilterModel.action" placeholder="操作类型" clearable style="width: 140px" @change="$emit('fetch-audit-logs')">
          <el-option value="create" label="创建" />
          <el-option value="update" label="更新" />
          <el-option value="delete" label="删除" />
          <el-option value="login" label="登录" />
          <el-option value="export" label="导出" />
        </el-select>
        <el-select v-model="auditFilterModel.resource_type" placeholder="资源类型" clearable style="width: 140px" @change="$emit('fetch-audit-logs')">
          <el-option value="product" label="商品" />
          <el-option value="rule" label="规则" />
          <el-option value="task" label="任务" />
          <el-option value="user" label="用户" />
        </el-select>
        <el-button @click="$emit('fetch-audit-logs')">刷新</el-button>
      </div>
      <div v-if="auditLoading" style="padding: 24px"><el-skeleton :rows="5" animated /></div>
      <el-table v-else :data="auditLogs" class="audit-table" stripe>
        <el-table-column prop="action" label="操作" width="100">
          <template #default="{ row }">
            <el-tag size="small" :type="auditActionTagType(row.action)">{{ row.action }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="resource_type" label="资源" width="100" />
        <el-table-column prop="description" label="描述" min-width="200" />
        <el-table-column prop="user_email" label="操作人" width="180" />
        <el-table-column prop="created_at" label="时间" width="180">
          <template #default="{ row }">{{ row.created_at?.substring(0, 19).replace('T', ' ') }}</template>
        </el-table-column>
      </el-table>
      <div v-if="!auditLoading && auditLogs.length === 0" class="audit-empty">暂无审计记录</div>
      <div v-if="auditTotal > auditPageSize" class="audit-pagination">
        <el-pagination v-model:current-page="auditPageModel" :page-size="auditPageSize" :total="auditTotal" layout="prev, pager, next" @current-change="$emit('fetch-audit-logs')" />
      </div>
    </div>

    <h2 class="section-title" style="margin-top: 32px">安全审计</h2>
    <div class="settings-card">
      <div v-if="securitySummary" class="security-summary">
        <div class="security-stat">
          <span class="security-stat__label">今日请求</span>
          <span class="security-stat__value">{{ securitySummary.today_requests || 0 }}</span>
        </div>
        <div class="security-stat">
          <span class="security-stat__label">异常请求</span>
          <span class="security-stat__value security-stat__value--danger">{{ securitySummary.anomaly_requests || 0 }}</span>
        </div>
        <div class="security-stat">
          <span class="security-stat__label">被拦截</span>
          <span class="security-stat__value security-stat__value--warning">{{ securitySummary.blocked_requests || 0 }}</span>
        </div>
        <div class="security-stat">
          <span class="security-stat__label">活跃IP</span>
          <span class="security-stat__value">{{ securitySummary.active_ips || 0 }}</span>
        </div>
      </div>

      <div class="audit-filters" style="margin-top: 16px">
        <el-input v-model="securityFilterModel.path" placeholder="路径" clearable style="width: 160px" @clear="$emit('fetch-security-logs')" />
        <el-input v-model="securityFilterModel.client_ip" placeholder="IP地址" clearable style="width: 140px" @clear="$emit('fetch-security-logs')" />
        <el-select v-model="securityFilterModel.method" placeholder="方法" clearable style="width: 100px" @change="$emit('fetch-security-logs')">
          <el-option value="GET" label="GET" />
          <el-option value="POST" label="POST" />
          <el-option value="PUT" label="PUT" />
          <el-option value="DELETE" label="DELETE" />
        </el-select>
        <el-button @click="$emit('fetch-security-logs')">查询</el-button>
      </div>
      <div v-if="securityLoading" style="padding: 24px"><el-skeleton :rows="5" animated /></div>
      <el-table v-else :data="securityLogs" class="audit-table" stripe>
        <el-table-column prop="method" label="方法" width="80">
          <template #default="{ row }">
            <el-tag size="small" :type="row.method === 'DELETE' ? 'danger' : row.method === 'POST' ? 'warning' : 'info'">{{ row.method }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="path" label="路径" min-width="200" />
        <el-table-column prop="client_ip" label="IP" width="140" />
        <el-table-column prop="status_code" label="状态码" width="90">
          <template #default="{ row }">
            <span :class="{ 'text-danger': row.status_code >= 400 }">{{ row.status_code }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="risk_level" label="风险" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.risk_level" size="small" :type="row.risk_level === 'high' ? 'danger' : row.risk_level === 'medium' ? 'warning' : 'info'">{{ row.risk_level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="170">
          <template #default="{ row }">{{ row.created_at?.substring(0, 19).replace('T', ' ') }}</template>
        </el-table-column>
      </el-table>
      <div v-if="!securityLoading && securityLogs.length === 0" class="audit-empty">暂无安全审计记录</div>
      <div v-if="securityTotal > securityPageSize" class="audit-pagination">
        <el-pagination v-model:current-page="securityPageModel" :page-size="securityPageSize" :total="securityTotal" layout="prev, pager, next" @current-change="$emit('fetch-security-logs')" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  auditLogs: any[];
  auditLoading: boolean;
  auditPage: number;
  auditPageSize: number;
  auditTotal: number;
  auditFilter: { action: string; resource_type: string };
  auditActionTagType: (action: string) => string;
  securityLogs: any[];
  securityLoading: boolean;
  securityPage: number;
  securityPageSize: number;
  securityTotal: number;
  securityFilter: { path: string; client_ip: string; method: string; min_risk: number | null };
  securitySummary: any;
}>();

const emit = defineEmits<{
  'fetch-audit-logs': [];
  'fetch-security-logs': [];
  'update:auditPage': [value: number];
  'update:securityPage': [value: number];
  'update:auditFilter': [value: any];
  'update:securityFilter': [value: any];
}>();

const auditPageModel = computed({
  get: () => props.auditPage,
  set: (v: number) => emit('update:auditPage', v),
});
const securityPageModel = computed({
  get: () => props.securityPage,
  set: (v: number) => emit('update:securityPage', v),
});
const auditFilterModel = computed({
  get: () => props.auditFilter,
  set: (v: any) => emit('update:auditFilter', v),
});
const securityFilterModel = computed({
  get: () => props.securityFilter,
  set: (v: any) => emit('update:securityFilter', v),
});
</script>

<style scoped>
.settings-section { max-width: 800px; }
.section-title { margin: 0 0 16px; font-size: var(--text-xl); font-weight: 600; color: var(--color-text-primary); }
.settings-card { background: var(--color-bg-card); border: 1px solid var(--color-border-light); border-radius: var(--radius-lg); padding: 20px; }
.audit-filters { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }
.audit-empty { text-align: center; padding: 32px 0; color: var(--color-text-secondary); font-size: var(--text-sm); }
.audit-pagination { display: flex; justify-content: center; padding-top: 16px; }
.security-summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; padding: 16px; background: var(--color-bg-page); border-radius: var(--radius-lg); }
.security-stat { display: flex; flex-direction: column; align-items: center; gap: 4px; }
.security-stat__label { font-size: var(--text-xs); color: var(--color-text-secondary); }
.security-stat__value { font-size: var(--text-xl); font-weight: 700; color: var(--color-text-primary); }
.security-stat__value--danger { color: var(--color-danger); }
.security-stat__value--warning { color: var(--color-warning); }
.text-danger { color: var(--color-danger); font-weight: 600; }
@media (max-width: 768px) { .security-summary { grid-template-columns: repeat(2, 1fr); } }
</style>
