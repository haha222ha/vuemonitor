<template>
  <div class="license fade-in">
    <PageHeader title="授权管理" subtitle="激活授权码以解锁完整功能" />

    <div class="license__content">
      <div v-if="licenseStore.isActivated" class="license__activated">
        <div class="license__status-icon">
          <el-icon :size="56" color="#67c23a"><CircleCheckFilled /></el-icon>
        </div>
        <h3 class="license__status-title">已激活</h3>

        <div class="license__info-card">
          <div class="license__info-grid">
            <div class="license__info-item">
              <span class="license__info-label">当前套餐</span>
              <el-tag :type="planTagType" size="large">{{ licenseStore.planLabel }}</el-tag>
            </div>
            <div class="license__info-item">
              <span class="license__info-label">到期时间</span>
              <span :class="['license__info-value', { expired: licenseStore.isExpired }]">
                {{ licenseStore.expiresAtFormatted }}
              </span>
            </div>
            <div class="license__info-item">
              <span class="license__info-label">设备ID</span>
              <span class="license__device-id">{{ licenseStore.license?.deviceId }}</span>
            </div>
            <div class="license__info-item">
              <span class="license__info-label">激活时间</span>
              <span class="license__info-value">
                {{ licenseStore.license?.activatedAt ? new Date(licenseStore.license.activatedAt).toLocaleString("zh-CN") : '-' }}
              </span>
            </div>
          </div>
        </div>

        <div v-if="quotaItems.length" class="license__quotas">
          <h4 class="license__section-title">配额使用</h4>
          <div v-for="item in quotaItems" :key="item.key" class="quota-item">
            <div class="quota-item__header">
              <span class="quota-item__label">{{ item.label }}</span>
              <span class="quota-item__value">{{ item.limit === -1 ? '无限' : `${item.current}/${item.limit}` }}</span>
            </div>
            <el-progress
              v-if="item.limit !== -1"
              :percentage="Math.min(100, Math.round((item.current / item.limit) * 100))"
              :color="item.current / item.limit > 0.9 ? '#f56c6c' : item.current / item.limit > 0.7 ? '#e6a23c' : '#67c23a'"
              :stroke-width="6"
              :show-text="false"
            />
          </div>
        </div>

        <div class="license__actions">
          <el-button @click="handleRefresh">刷新状态</el-button>
          <el-button type="danger" @click="handleDeactivate">解除绑定</el-button>
        </div>
      </div>

      <div v-else class="license__activate">
        <div class="license__activate-card">
          <el-form :model="form" :rules="rules" ref="formRef" label-width="80px">
            <el-form-item label="授权码" prop="licenseKey">
              <el-input
                v-model="form.licenseKey"
                placeholder="VM-XXXX-XXXX-XXXX-XXXX"
                maxlength="27"
                @input="formatLicenseKey"
                style="font-family: monospace; letter-spacing: 2px"
              />
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

          <el-button
            type="primary"
            size="large"
            :loading="licenseStore.loading"
            @click="handleActivate"
            class="license__activate-btn"
          >
            激活
          </el-button>

          <div class="license__device-info">
            <span>设备ID: {{ deviceInfo?.deviceId || '获取中...' }}</span>
            <span>指纹: {{ deviceInfo?.fingerprint?.substring(0, 16) || '...' }}...</span>
          </div>
        </div>
      </div>

      <div class="license__plans">
        <h4 class="license__section-title">套餐对比</h4>
        <div class="license__plans-grid">
          <div v-for="plan in planCards" :key="plan.name" :class="['plan-card', { 'plan-card--active': licenseStore.plan === plan.key }]">
            <div class="plan-card__name">{{ plan.name }}</div>
            <div class="plan-card__price">{{ plan.price }}</div>
            <div class="plan-card__features">
              <div v-for="f in plan.features" :key="f" class="plan-card__feature">
                <el-icon :size="12" color="#67c23a"><CircleCheckFilled /></el-icon>
                <span>{{ f }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from "vue";
import { useLicenseStore } from "../stores/license";
import { ElMessage, ElMessageBox } from "element-plus";
import { CircleCheckFilled } from "@element-plus/icons-vue";
import type { FormInstance, FormRules } from "element-plus";
import PageHeader from "../components/PageHeader.vue";

const licenseStore = useLicenseStore();
const formRef = ref<FormInstance>();
const deviceInfo = ref<{ deviceId: string; fingerprint: string } | null>(null);

const form = reactive({
  licenseKey: "",
  verifyMode: "online" as "online" | "offline",
  serverUrl: "",
});

const rules: FormRules = {
  licenseKey: [{ required: true, message: "请输入授权码", trigger: "blur" }],
  serverUrl: [
    {
      validator: (_rule, value, callback) => {
        if (form.verifyMode === "online" && !value) {
          callback(new Error("在线验证需要填写服务器地址"));
        } else {
          callback();
        }
      },
      trigger: "blur",
    },
  ],
};

const planTagType = computed(() => {
  const map: Record<string, string> = { free: "info", pro: "", premium: "warning", enterprise: "danger" };
  return map[licenseStore.plan] || "info";
});

const quotaItems = computed(() => {
  const q = licenseStore.quotas;
  return [
    { key: "maxProducts", label: "监控商品数", limit: q.maxProducts ?? 10, current: 0 },
    { key: "maxConcurrency", label: "并发采集数", limit: q.maxConcurrency ?? 2, current: 0 },
    { key: "maxScheduleTasks", label: "定时任务数", limit: q.maxScheduleTasks ?? 0, current: 0 },
    { key: "aiCallsPerDay", label: "AI分析次数/天", limit: q.aiCallsPerDay ?? 5, current: 0 },
    { key: "dailyCollectLimit", label: "日采集上限", limit: q.dailyCollectLimit ?? 50, current: 0 },
  ];
});

const planCards = [
  { key: "free", name: "免费版", price: "免费", features: ["10个监控商品", "2并发采集", "50次/日采集", "5次AI分析/天"] },
  { key: "pro", name: "专业版", price: "¥99/月", features: ["100个监控商品", "5并发采集", "500次/日采集", "50次AI分析/天", "趋势评分", "数据导出"] },
  { key: "premium", name: "高级版", price: "¥299/月", features: ["500个监控商品", "8并发采集", "2000次/日采集", "200次AI分析/天", "爆品预测", "风险预警", "团队协作"] },
  { key: "enterprise", name: "企业版", price: "联系销售", features: ["无限监控商品", "10并发采集", "无限日采集", "无限AI分析", "全部高级功能", "专属支持"] },
];

function formatLicenseKey(val: string) {
  const raw = val.replace(/[^A-Za-z0-9]/g, "").toUpperCase();
  const parts = [];
  for (let i = 0; i < raw.length && i < 24; i += 4) {
    parts.push(raw.substring(i, i + 4));
  }
  form.licenseKey = parts.join("-");
}

async function handleActivate() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;
  const serverUrl = form.verifyMode === "online" ? form.serverUrl : undefined;
  const success = await licenseStore.activate(form.licenseKey, serverUrl);
  if (success) {
    ElMessage.success("激活成功！功能已解锁");
    await licenseStore.fetchPlan();
  }
}

async function handleDeactivate() {
  try {
    await ElMessageBox.confirm("解除绑定后将恢复为免费版，确定继续？", "确认解绑", {
      confirmButtonText: "确定解绑",
      cancelButtonText: "取消",
      type: "warning",
    });
    await licenseStore.deactivate();
    ElMessage.success("已解除绑定");
  } catch {}
}

async function handleRefresh() {
  await licenseStore.fetchLicense();
  await licenseStore.fetchPlan();
  ElMessage.success("状态已刷新");
}

onMounted(async () => {
  await licenseStore.fetchLicense();
  await licenseStore.fetchPlan();
  deviceInfo.value = await licenseStore.getDeviceInfo();
});
</script>

<style scoped>
.license {
  padding: 0;
}

.license__content {
  max-width: 800px;
  margin: 0 auto;
}

.license__activated {
  text-align: center;
  padding: 40px 0;
}

.license__status-icon {
  margin-bottom: 12px;
}

.license__status-title {
  font-size: var(--text-xl);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 24px;
}

.license__info-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: 24px;
  margin-bottom: 24px;
}

.license__info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
}

.license__info-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.license__info-label {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}

.license__info-value {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
}

.license__info-value.expired {
  color: var(--color-danger);
}

.license__device-id {
  font-family: monospace;
  font-size: var(--text-xs);
  background: var(--color-bg-page);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  color: var(--color-text-primary);
}

.license__quotas {
  text-align: left;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: 24px;
  margin-bottom: 24px;
}

.license__section-title {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 16px;
}

.quota-item {
  margin-bottom: 14px;
}

.quota-item:last-child {
  margin-bottom: 0;
}

.quota-item__header {
  display: flex;
  justify-content: space-between;
  font-size: var(--text-xs);
  margin-bottom: 6px;
}

.quota-item__label {
  color: var(--color-text-secondary);
}

.quota-item__value {
  color: var(--color-text-primary);
  font-weight: 500;
}

.license__actions {
  display: flex;
  gap: 10px;
  justify-content: center;
}

.license__activate {
  padding: 20px 0;
}

.license__activate-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: 32px;
  max-width: 480px;
  margin: 0 auto;
}

.license__error {
  margin: 12px 0;
}

.license__activate-btn {
  width: 100%;
  margin-top: 20px;
}

.license__device-info {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border-light);
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  display: flex;
  flex-direction: column;
  gap: 4px;
  text-align: center;
}

.license__plans {
  margin-top: 32px;
}

.license__plans-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.plan-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: 20px;
  transition: all 0.2s;
}

.plan-card:hover {
  border-color: var(--color-primary);
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.1);
}

.plan-card--active {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.2);
}

.plan-card__name {
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 4px;
}

.plan-card__price {
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--color-primary);
  margin-bottom: 16px;
}

.plan-card__features {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.plan-card__feature {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}

@media (max-width: 768px) {
  .license__info-grid {
    grid-template-columns: 1fr;
  }

  .license__plans-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
