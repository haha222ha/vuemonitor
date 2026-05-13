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
              <el-tag :type="planTagType">{{ planLabel }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item v-if="auth.user?.plan_expires_at" label="到期时间">
              <span :class="{ 'expiring-soon': isExpiringSoon }">
                {{ formatDate(auth.user.plan_expires_at) }}
                <el-tag v-if="isExpiringSoon" type="warning" size="small" style="margin-left: 8px;">即将到期</el-tag>
              </span>
            </el-descriptions-item>
          </el-descriptions>
          <el-button
            v-if="auth.userPlan === 'free'"
            type="primary"
            size="small"
            style="margin-top: 16px"
            @click="$router.push('/pricing')"
          >升级套餐</el-button>
          <el-button
            v-else
            size="small"
            style="margin-top: 16px"
            @click="$router.push('/pricing')"
          >续费/升级</el-button>
        </div>

        <div class="panel" style="margin-top: 20px;">
          <h3>套餐权益</h3>
          <div class="benefits-grid">
            <div class="benefit-item">
              <span class="benefit-label">监控商品上限</span>
              <span class="benefit-value">{{ planBenefits.maxProducts === -1 ? '无限' : planBenefits.maxProducts }}</span>
            </div>
            <div class="benefit-item">
              <span class="benefit-label">最大并发数</span>
              <span class="benefit-value">{{ planBenefits.maxConcurrency }}</span>
            </div>
            <div class="benefit-item">
              <span class="benefit-label">每日采集上限</span>
              <span class="benefit-value">{{ planBenefits.dailyCollectLimit === -1 ? '无限' : planBenefits.dailyCollectLimit }}</span>
            </div>
            <div class="benefit-item">
              <span class="benefit-label">AI分析</span>
              <span class="benefit-value">{{ aiBenefitLabel }}</span>
            </div>
          </div>
        </div>
      </el-col>

      <el-col :span="12">
        <div class="panel">
          <h3>授权码激活</h3>
          <el-input
            v-model="licenseCode"
            placeholder="请输入授权码"
            style="margin-bottom: 12px"
            @keyup.enter="activateLicense"
          >
            <template #prefix>
              <el-icon><Key /></el-icon>
            </template>
          </el-input>
          <el-button type="primary" :loading="activating" @click="activateLicense" style="width: 100%;">
            {{ activating ? '激活中...' : '激活授权码' }}
          </el-button>

          <div v-if="activateResult" class="activate-result success">
            <el-icon><CircleCheckFilled /></el-icon>
            <span>激活成功！已升级为 {{ planLabelMap[activateResult.plan] || activateResult.plan }}，有效期 {{ activateResult.duration_days }} 天</span>
          </div>
        </div>

        <div class="panel" style="margin-top: 20px;">
          <div class="panel-title-row">
            <h3>授权记录</h3>
            <el-button size="small" text @click="fetchLicenseStatus">
              <el-icon><Refresh /></el-icon>
            </el-button>
          </div>

          <div v-if="licenseLoading" style="text-align: center; padding: 20px;">
            <el-icon class="is-loading"><Loading /></el-icon>
          </div>

          <div v-else-if="licenseList.length === 0" class="empty-hint">
            <p>暂无授权记录</p>
          </div>

          <div v-else class="license-list">
            <div v-for="lic in licenseList" :key="lic.code" class="license-item">
              <div class="license-header">
                <el-tag :type="licenseStatusType(lic.status)" size="small">{{ licenseStatusLabel(lic.status) }}</el-tag>
                <el-tag size="small" type="info">{{ planLabelMap[lic.plan] || lic.plan }}</el-tag>
              </div>
              <div class="license-code">{{ maskCode(lic.code) }}</div>
              <div class="license-meta">
                <span v-if="lic.expires_at">到期：{{ formatDate(lic.expires_at) }}</span>
                <span v-if="lic.activated_at">激活：{{ formatDate(lic.activated_at) }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="panel" style="margin-top: 20px;">
          <h3>语言设置</h3>
          <el-form label-width="100px">
            <el-form-item label="界面语言">
              <el-select v-model="currentLocale" @change="changeLocale" style="width: 200px">
                <el-option label="简体中文" value="zh" />
                <el-option label="English" value="en" />
              </el-select>
            </el-form-item>
          </el-form>
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

        <div class="panel" style="margin-top: 20px;">
          <h3>隐私与数据管理</h3>

          <div class="privacy-section">
            <h4 class="privacy-subtitle">数据收集偏好</h4>
            <el-form label-width="140px" size="small">
              <el-form-item label="使用数据收集">
                <el-switch v-model="privacyConsent.data_collection" @change="saveConsent" />
                <span class="privacy-hint">帮助我们改进产品功能</span>
              </el-form-item>
              <el-form-item label="匿名聚合贡献">
                <el-switch v-model="privacyConsent.analytics" @change="saveConsent" />
                <span class="privacy-hint">您的数据将匿名化后用于群体洞察</span>
              </el-form-item>
              <el-form-item label="营销通信">
                <el-switch v-model="privacyConsent.marketing" @change="saveConsent" />
                <span class="privacy-hint">接收产品更新和优惠信息</span>
              </el-form-item>
              <el-form-item label="第三方数据共享">
                <el-switch v-model="privacyConsent.third_party_sharing" @change="saveConsent" />
                <span class="privacy-hint">与合作伙伴共享匿名统计数据</span>
              </el-form-item>
            </el-form>
          </div>

          <el-divider />

          <div class="privacy-section">
            <h4 class="privacy-subtitle">我的数据</h4>
            <div class="data-summary" v-if="dataSummary">
              <div class="data-summary-grid">
                <div v-for="(count, table) in dataSummary.tables" :key="table" class="data-summary-item">
                  <span class="data-summary-label">{{ tableLabel(table as string) }}</span>
                  <span class="data-summary-value" :class="{ 'data-summary-error': count < 0 }">{{ count < 0 ? '?' : count }}</span>
                </div>
              </div>
              <div class="data-summary-total">
                总记录数: <strong>{{ dataSummary.total_records }}</strong>
              </div>
            </div>
            <div class="data-actions">
              <el-button size="small" @click="exportMyData" :loading="exportingData">
                <el-icon><Download /></el-icon>
                导出我的数据 (JSON)
              </el-button>
              <el-button size="small" @click="showPrivacyPolicy">
                <el-icon><Document /></el-icon>
                隐私政策
              </el-button>
            </div>
          </div>

          <el-divider />

          <div class="privacy-section privacy-danger-zone">
            <h4 class="privacy-subtitle">危险区域</h4>
            <p class="privacy-warning">删除数据操作不可逆。根据 GDPR 被遗忘权，您可以请求删除所有个人数据。删除后账户将被匿名化且无法恢复。</p>
            <el-button type="danger" size="small" @click="confirmDeleteData" :loading="deletingData">
              请求删除所有数据
            </el-button>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { useAuthStore } from "../../stores/auth";
import api from "../../utils/api";
import { ElMessage, ElMessageBox } from "element-plus";
import { Key, Refresh, CircleCheckFilled, Loading, Download, Document } from "@element-plus/icons-vue";
import { useI18n, type Locale } from "../../i18n";

const auth = useAuthStore();
const { t, setLocale, getLocale } = useI18n();
const currentLocale = ref<Locale>(getLocale());

function changeLocale(val: Locale) {
  setLocale(val);
}
const licenseCode = ref("");
const activating = ref(false);
const activateResult = ref<any>(null);
const licenseLoading = ref(false);
const licenseList = ref<any[]>([]);

const notifSettings = reactive({
  collectDone: true,
  aiDone: true,
  riskAlert: true,
});

const privacyConsent = reactive({
  data_collection: true,
  analytics: true,
  marketing: false,
  third_party_sharing: false,
});

const dataSummary = ref<any>(null);
const exportingData = ref(false);
const deletingData = ref(false);

const TABLE_LABELS: Record<string, string> = {
  products: "商品数据",
  product_features: "商品特征",
  monitor_rules: "监控规则",
  ai_analyses: "AI分析",
  ai_reports: "AI报告",
  notifications: "通知",
  sync_records: "同步记录",
  alert_rules: "告警规则",
  alert_events: "告警事件",
  team_members: "团队成员",
  scheduled_tasks: "定时任务",
};

function tableLabel(table: string): string {
  return TABLE_LABELS[table] || table;
}

async function fetchDataSummary() {
  try {
    const { data } = await api.get("/gdpr/data-summary");
    dataSummary.value = data?.data || data;
  } catch {
    dataSummary.value = null;
  }
}

async function saveConsent() {
  try {
    await api.post("/gdpr/consent", null, {
      params: {
        data_collection: privacyConsent.data_collection,
        analytics: privacyConsent.analytics,
        marketing: privacyConsent.marketing,
        third_party_sharing: privacyConsent.third_party_sharing,
      },
    });
    ElMessage.success("隐私偏好已保存");
  } catch {
    ElMessage.error("保存失败");
  }
}

async function exportMyData() {
  exportingData.value = true;
  try {
    const { data } = await api.post("/gdpr/export", null, { params: { format: "json" } });
    const exportData = data?.data || data;
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `vuemonitor_data_export_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    ElMessage.success("数据导出成功");
  } catch {
    ElMessage.error("数据导出失败");
  } finally {
    exportingData.value = false;
  }
}

async function confirmDeleteData() {
  try {
    await ElMessageBox.confirm(
      "此操作将永久删除您的所有个人数据，账户将被匿名化且无法恢复。请确认您了解此操作的后果。",
      "确认删除所有数据",
      {
        confirmButtonText: "确认删除",
        cancelButtonText: "取消",
        type: "warning",
        dangerouslyUseHTMLString: false,
      }
    );
    const email = auth.user?.email;
    if (!email) {
      ElMessage.error("无法获取邮箱信息");
      return;
    }
    await ElMessageBox.prompt("请输入您的邮箱地址以确认删除操作", "邮箱确认", {
      confirmButtonText: "确认",
      cancelButtonText: "取消",
      inputPattern: new RegExp(`^${email.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}$`),
      inputErrorMessage: "邮箱地址不匹配",
    });
    deletingData.value = true;
    const { data } = await api.post("/gdpr/deletion-request", null, {
      params: { confirm_email: email },
    });
    const result = data?.data || data;
    ElMessage.success(`数据删除成功，共删除 ${result.total_deleted} 条记录`);
    auth.logout();
    window.location.href = "/login";
  } catch (e: any) {
    if (e !== "cancel" && e?.message !== "cancel") {
      ElMessage.error("数据删除失败");
    }
  } finally {
    deletingData.value = false;
  }
}

async function showPrivacyPolicy() {
  try {
    const { data } = await api.get("/gdpr/privacy-policy");
    const policy = data?.data || data;
    ElMessageBox.alert(
      `<div style="max-height: 400px; overflow-y: auto; text-align: left; font-size: 13px; line-height: 1.6;">
        <p><strong>数据控制者:</strong> ${policy.policy?.data_controller || "-"}</p>
        <p><strong>生效日期:</strong> ${policy.effective_date || "-"}</p>
        <p><strong>收集的数据类型:</strong></p>
        <ul>${(policy.policy?.data_types_collected || []).map((i: string) => `<li>${i}</li>`).join("")}</ul>
        <p><strong>数据处理目的:</strong></p>
        <ul>${(policy.policy?.data_purposes || []).map((i: string) => `<li>${i}</li>`).join("")}</ul>
        <p><strong>您的权利:</strong></p>
        <ul>${(policy.policy?.user_rights || []).map((i: string) => `<li>${i}</li>`).join("")}</ul>
        <p><strong>数据保留:</strong> ${policy.policy?.data_retention || "-"}</p>
        <p><strong>联系方式:</strong> ${policy.policy?.contact || "-"}</p>
      </div>`,
      "隐私政策",
      { dangerouslyUseHTMLString: true, confirmButtonText: "我已了解" }
    );
  } catch {
    ElMessage.error("获取隐私政策失败");
  }
}

const PLAN_LIMITS_MAP: Record<string, { maxProducts: number; maxConcurrency: number; dailyCollectLimit: number }> = {
  free: { maxProducts: 3, maxConcurrency: 2, dailyCollectLimit: 50 },
  pro: { maxProducts: 50, maxConcurrency: 8, dailyCollectLimit: 500 },
  premium: { maxProducts: -1, maxConcurrency: 16, dailyCollectLimit: 2000 },
  enterprise: { maxProducts: -1, maxConcurrency: 32, dailyCollectLimit: -1 },
};

const planLabelMap: Record<string, string> = {
  free: "免费版",
  pro: "Pro 专业版",
  premium: "Premium 高级版",
  enterprise: "Enterprise 企业版",
};

const planBenefits = computed(() => PLAN_LIMITS_MAP[auth.userPlan] || PLAN_LIMITS_MAP.free);

const planLabel = computed(() => planLabelMap[auth.userPlan] || "免费版");

const planTagType = computed(() => {
  const map: Record<string, string> = { pro: "primary", premium: "warning", enterprise: "danger" };
  return (map[auth.userPlan] || "info") as any;
});

const aiBenefitLabel = computed(() => {
  const plan = auth.userPlan;
  if (plan === "free") return "基础趋势描述";
  if (plan === "pro") return "趋势评分+报告";
  if (plan === "premium") return "爆品预测+风险预警";
  return "完整AI能力";
});

const isExpiringSoon = computed(() => {
  if (!auth.user?.plan_expires_at) return false;
  const expires = new Date(auth.user.plan_expires_at);
  const now = new Date();
  const daysLeft = (expires.getTime() - now.getTime()) / (1000 * 60 * 60 * 24);
  return daysLeft > 0 && daysLeft <= 7;
});

function formatDate(dateStr: string) {
  if (!dateStr) return "—";
  const d = new Date(dateStr);
  return d.toLocaleDateString("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit" });
}

function maskCode(code: string) {
  if (!code || code.length <= 8) return code || "—";
  return code.slice(0, 4) + "****" + code.slice(-4);
}

function licenseStatusType(status: string) {
  const map: Record<string, string> = { active: "success", expired: "danger", unused: "info", revoked: "warning" };
  return (map[status] || "info") as any;
}

function licenseStatusLabel(status: string) {
  const map: Record<string, string> = { active: "生效中", expired: "已过期", unused: "未使用", revoked: "已吊销" };
  return map[status] || status;
}

async function activateLicense() {
  if (!licenseCode.value.trim()) {
    ElMessage.warning("请输入授权码");
    return;
  }
  activating.value = true;
  activateResult.value = null;
  try {
    const { data: resp } = await api.post("/auth/license/activate", { code: licenseCode.value.trim() });
    const result = resp?.data || resp;
    if (resp?.code !== undefined && resp.code !== 0) {
      ElMessage.error(resp.message || "激活失败");
      return;
    }
    activateResult.value = result;
    ElMessage.success("授权码激活成功");
    licenseCode.value = "";
    auth.fetchUser();
    fetchLicenseStatus();
  } catch (e: any) {
  } finally {
    activating.value = false;
  }
}

async function fetchLicenseStatus() {
  licenseLoading.value = true;
  try {
    const { data } = await api.get("/auth/license/status");
    const result = data?.data || data;
    licenseList.value = result?.licenses || [];
  } catch {
    licenseList.value = [];
  } finally {
    licenseLoading.value = false;
  }
}

onMounted(() => {
  fetchLicenseStatus();
  fetchDataSummary();
});
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

.panel-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.panel-title-row h3 {
  margin: 0;
}

.activate-result {
  margin-top: 12px;
  padding: 12px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.activate-result.success {
  background: rgba(34, 197, 94, 0.1);
  border: 1px solid rgba(34, 197, 94, 0.2);
  color: #86efac;
}

.benefits-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.benefit-item {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.benefit-label {
  font-size: 12px;
  color: #6a6a7a;
}

.benefit-value {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
}

.expiring-soon {
  color: #fbbf24;
  font-weight: 600;
}

.empty-hint {
  text-align: center;
  padding: 20px 0;
  color: #4a4a5a;
  font-size: 13px;
}

.license-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.license-item {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 8px;
  padding: 12px;
}

.license-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.license-code {
  font-size: 14px;
  color: #e0e0e6;
  font-family: monospace;
  letter-spacing: 1px;
}

.license-meta {
  display: flex;
  gap: 16px;
  margin-top: 6px;
  font-size: 12px;
  color: #6a6a7a;
}

.privacy-section {
  margin-bottom: 8px;
}

.privacy-subtitle {
  font-size: 14px;
  font-weight: 600;
  color: #e0e0e6;
  margin: 0 0 12px;
}

.privacy-hint {
  font-size: 11px;
  color: #6a6a7a;
  margin-left: 8px;
}

.data-summary {
  margin-bottom: 16px;
}

.data-summary-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}

.data-summary-item {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: 6px;
  padding: 8px 12px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.data-summary-label {
  font-size: 12px;
  color: #8a8a9a;
}

.data-summary-value {
  font-size: 14px;
  font-weight: 600;
  color: #e0e0e6;
}

.data-summary-error {
  color: #6a6a7a;
}

.data-summary-total {
  font-size: 13px;
  color: #8a8a9a;
}

.data-summary-total strong {
  color: #e0e0e6;
}

.data-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.privacy-danger-zone {
  border: 1px solid rgba(245, 108, 108, 0.2);
  border-radius: 8px;
  padding: 16px;
  background: rgba(245, 108, 108, 0.03);
}

.privacy-warning {
  font-size: 12px;
  color: #f5a3a3;
  margin: 0 0 12px;
  line-height: 1.6;
}
</style>
