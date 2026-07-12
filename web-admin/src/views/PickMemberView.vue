<template>
  <div class="pick-member-page">
    <div class="page-head">
      <h2>选品会员</h2>
      <div class="head-actions">
        <el-button @click="refreshAll" :loading="store.statusLoading">刷新状态</el-button>
        <el-button type="primary" :disabled="!store.status?.online" @click="showCreate = true">
          生成授权码
        </el-button>
      </div>
    </div>

    <el-alert
      v-if="!store.status?.configured"
      type="warning"
      :closable="false"
      show-icon
      title="选品云尚未对接 admin 后台"
      class="mb-16"
    >
      <p>请在服务器 <code>server/.env</code> 中配置：</p>
      <ul>
        <li><code>XHS_CLOUD_API_URL=http://127.0.0.1:8080</code></li>
        <li><code>XHS_CLOUD_SYNC_KEY=</code>（与 <code>/opt/xhs-cloud/.env</code> 里一致）</li>
        <li><code>XHS_CLOUD_MEMBER_PORTAL_URL=</code>（可选，发给客户的会员页链接）</li>
      </ul>
    </el-alert>

    <el-row :gutter="16" class="mb-16">
      <el-col :span="6">
        <el-card shadow="never" v-loading="store.statusLoading">
          <div class="stat-label">服务状态</div>
          <div class="stat-value">
            <el-tag :type="store.status?.online ? 'success' : 'danger'" size="large">
              {{ store.status?.online ? "在线" : "离线" }}
            </el-tag>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" v-loading="store.statusLoading">
          <div class="stat-label">有效会员</div>
          <div class="stat-value">{{ store.status?.stats?.active_members ?? "—" }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" v-loading="store.statusLoading">
          <div class="stat-label">未用授权码</div>
          <div class="stat-value">{{ store.status?.stats?.auth_codes_unused ?? "—" }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" v-loading="store.statusLoading">
          <div class="stat-label">最新日报</div>
          <div class="stat-value stat-value--sm">
            {{ store.status?.stats?.latest_report_date || "暂无" }}
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="mb-16" v-if="store.status?.member_portal_url">
      <div class="portal-row">
        <span>会员看板（发给客户注册/下载）：</span>
        <el-link type="primary" :href="store.status.member_portal_url" target="_blank">
          {{ store.status.member_portal_url }}
        </el-link>
        <el-button link type="primary" @click="copyPortal">复制链接</el-button>
      </div>
    </el-card>

    <el-alert
      v-if="store.status?.error"
      type="error"
      :closable="false"
      show-icon
      :title="String(store.status.error)"
      class="mb-16"
    />

    <div class="toolbar">
      <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width: 140px" @change="fetchCodes">
        <el-option label="未使用" value="unused" />
        <el-option label="已激活" value="active" />
        <el-option label="已吊销" value="revoked" />
      </el-select>
    </div>

    <el-table :data="store.codes" stripe v-loading="store.loading">
      <el-table-column prop="code" label="授权码" min-width="200" fixed="left">
        <template #default="{ row }">
          <span class="code-cell">{{ row.code }}</span>
          <el-button link type="primary" size="small" @click="copyOne(row.code)">复制</el-button>
        </template>
      </el-table-column>
      <el-table-column prop="plan_code" label="套餐" width="110">
        <template #default="{ row }">{{ planLabel(row.plan_code) }}</template>
      </el-table-column>
      <el-table-column prop="duration_days" label="天数" width="60" />
      <el-table-column label="激活/上限" width="85">
        <template #default="{ row }">{{ row.current_activations }}/{{ row.max_activations }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="85">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="activated_usernames" label="激活账号" min-width="110" show-overflow-tooltip>
        <template #default="{ row }">{{ row.activated_usernames || "—" }}</template>
      </el-table-column>
      <el-table-column prop="first_activated_at" label="激活时间" width="165">
        <template #default="{ row }">{{ formatTime(row.first_activated_at) }}</template>
      </el-table-column>
      <el-table-column prop="membership_expires_at" label="到期时间" width="165">
        <template #default="{ row }">{{ formatTime(row.membership_expires_at) }}</template>
      </el-table-column>
      <el-table-column label="剩余天数" width="85">
        <template #default="{ row }">
          <span v-if="row.days_remaining != null" :class="daysClass(row.days_remaining)">
            {{ row.days_remaining }} 天
          </span>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column prop="note" label="备注" min-width="100" show-overflow-tooltip />
      <el-table-column prop="created_at" label="创建时间" width="165">
        <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="80" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status !== 'revoked'"
            type="danger"
            text
            size="small"
            @click="revoke(row.code)"
          >吊销</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showCreate" title="生成选品会员授权码" width="440px" @closed="generatedCodes = []">
      <el-form :model="form" :rules="formRules" ref="formRef" label-width="80px">
        <el-form-item label="套餐" prop="plan_code">
          <el-select v-model="form.plan_code" style="width: 100%" @change="onPlanChange">
            <el-option label="周会员 (7天)" value="weekly" />
            <el-option label="月度会员 (30天)" value="monthly" />
            <el-option label="年度会员 (365天)" value="yearly" />
            <el-option label="体验会员 (PC全功能 + 指定报告下载)" value="experience" />
            <el-option label="AI 情报体验 (7天 · insight_only)" value="experience_insight" />
          </el-select>
        </el-form-item>
        <template v-if="form.plan_code === 'experience'">
          <el-form-item label="可下报告" prop="allowed_report_dates">
            <el-select
              v-model="form.allowed_report_dates"
              multiple
              filterable
              allow-create
              default-first-option
              placeholder="选择或输入日期 YYYY-MM-DD"
              style="width: 100%"
            >
              <el-option
                v-for="d in suggestedReportDates"
                :key="d"
                :label="d"
                :value="d"
              />
            </el-select>
            <div class="form-hint">体验码永久有效，但会员中心仅可下载此处勾选的日报（可多选）</div>
          </el-form-item>
          <el-form-item label="报告类型">
            <el-checkbox-group v-model="form.allowed_archive_types">
              <el-checkbox label="member_daily_zip">日报</el-checkbox>
              <el-checkbox label="member_weekly_zip">周报</el-checkbox>
              <el-checkbox label="member_monthly_zip">月报</el-checkbox>
            </el-checkbox-group>
          </el-form-item>
        </template>
        <el-form-item v-if="form.plan_code !== 'experience'" label="天数" prop="duration_days">
          <el-input-number v-model="form.duration_days" :min="0" :max="3650" style="width: 100%" />
          <div class="form-hint">填 0 则按套餐默认天数</div>
        </el-form-item>
        <el-form-item label="数量" prop="count">
          <el-input-number v-model="form.count" :min="1" :max="100" style="width: 100%" />
        </el-form-item>
        <el-form-item label="可激活" prop="max_activations">
          <el-input-number v-model="form.max_activations" :min="1" :max="10" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.note" placeholder="如：客户 QQ / 订单号" />
        </el-form-item>
      </el-form>

      <div v-if="generatedCodes.length" class="codes-box">
        <div class="codes-head">
          <span>已生成 {{ generatedCodes.length }} 个（复制发给客户）</span>
          <el-button type="primary" link @click="copyAll">复制全部</el-button>
        </div>
        <el-input type="textarea" :rows="6" readonly :model-value="generatedCodes.join('\n')" />
      </div>

      <template #footer>
        <el-button @click="showCreate = false">关闭</el-button>
        <el-button type="primary" :loading="generating" @click="generate">生成</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";
import { useMemberCloudStore } from "../stores/memberCloud";

const store = useMemberCloudStore();
const filterStatus = ref("");
const showCreate = ref(false);
const generating = ref(false);
const generatedCodes = ref<string[]>([]);
const formRef = ref<FormInstance>();
const form = reactive({
  plan_code: "monthly",
  duration_days: 0,
  count: 1,
  max_activations: 1,
  note: "",
  allowed_report_dates: [] as string[],
  allowed_archive_types: ["member_daily_zip"] as string[],
});

const suggestedReportDates = computed(() => {
  const latest = store.status?.stats?.latest_report_date;
  const dates: string[] = [];
  if (latest) dates.push(String(latest).slice(0, 10));
  const now = new Date();
  for (let i = 0; i < 7; i++) {
    const d = new Date(now);
    d.setDate(d.getDate() - i);
    dates.push(d.toISOString().slice(0, 10));
  }
  return [...new Set(dates)];
});

const formRules: FormRules = {
  plan_code: [{ required: true, message: "请选择套餐", trigger: "change" }],
  count: [{ required: true, message: "请输入数量", trigger: "blur" }],
  allowed_report_dates: [{
    validator: (_r, v, cb) => {
      if (form.plan_code === "experience" && (!v || !v.length)) {
        cb(new Error("体验会员请至少选择一个可下载报告日期"));
        return;
      }
      cb();
    },
    trigger: "change",
  }],
};

function onPlanChange(plan: string) {
  if (plan === "experience") {
    form.duration_days = 0;
    form.max_activations = 1;
    if (!form.allowed_archive_types.length) {
      form.allowed_archive_types = ["member_daily_zip"];
    }
  } else if (plan === "experience_insight") {
    form.duration_days = 7;
    form.max_activations = 1;
  }
}

function planLabel(plan: string) {
  const map: Record<string, string> = {
    weekly: "周会员",
    monthly: "月度会员",
    yearly: "年度会员",
    experience: "体验会员",
    experience_insight: "AI情报体验",
  };
  return map[plan] || plan;
}

function statusLabel(status: string) {
  const map: Record<string, string> = { unused: "未使用", active: "已激活", revoked: "已吊销" };
  return map[status] || status;
}

function statusType(status: string) {
  if (status === "unused") return "success";
  if (status === "active") return "primary";
  return "danger";
}

function formatTime(value?: string) {
  if (!value) return "—";
  return value.replace("T", " ").slice(0, 19);
}

function daysClass(days: number) {
  if (days <= 0) return "days-expired";
  if (days <= 7) return "days-warn";
  return "";
}

async function revoke(code: string) {
  try {
    await ElMessageBox.confirm(
      `确定吊销授权码 ${code}？\n未使用的码将无法再激活；已激活会员的到期时间不受影响。`,
      "吊销确认",
      { type: "warning", confirmButtonText: "吊销", cancelButtonText: "取消" },
    );
    await store.revokeCode(code);
    ElMessage.success("已吊销");
    refreshAll();
  } catch (e) {
    if (e !== "cancel") ElMessage.error("吊销失败");
  }
}

async function fetchCodes() {
  await store.fetchCodes(100, filterStatus.value || undefined);
}

async function refreshAll() {
  await store.fetchStatus();
  await fetchCodes();
}

async function generate() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;
  generating.value = true;
  try {
    const result = await store.generateCodes({
      plan_code: form.plan_code,
      count: form.count,
      duration_days: form.plan_code === "experience" ? undefined : (form.duration_days || undefined),
      max_activations: form.max_activations,
      note: form.note || undefined,
      allowed_report_dates: form.plan_code === "experience" ? form.allowed_report_dates : undefined,
      allowed_archive_types: form.plan_code === "experience" ? form.allowed_archive_types : undefined,
    });
    generatedCodes.value = (result.codes || []).map((c) => c.code);
    ElMessage.success(`已生成 ${generatedCodes.value.length} 个授权码`);
    refreshAll();
  } catch {
    ElMessage.error("生成失败，请检查选品云服务是否在线");
  } finally {
    generating.value = false;
  }
}

function copyOne(code: string) {
  navigator.clipboard.writeText(code).then(() => ElMessage.success("已复制"));
}

function copyAll() {
  navigator.clipboard.writeText(generatedCodes.value.join("\n")).then(() => ElMessage.success("已复制全部"));
}

function copyPortal() {
  const url = store.status?.member_portal_url;
  if (!url) return;
  navigator.clipboard.writeText(url).then(() => ElMessage.success("会员链接已复制"));
}

onMounted(refreshAll);
</script>

<style scoped>
.pick-member-page { max-width: 1400px; }
.page-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-head h2 { margin: 0; }
.head-actions { display: flex; gap: 8px; }
.mb-16 { margin-bottom: 16px; }
.stat-label { color: #909399; font-size: 13px; margin-bottom: 8px; }
.stat-value { font-size: 28px; font-weight: 600; }
.stat-value--sm { font-size: 18px; }
.portal-row { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.toolbar { margin-bottom: 16px; }
.code-cell { font-family: monospace; margin-right: 8px; }
.codes-box { margin-top: 12px; }
.codes-head { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 13px; }
.form-hint { font-size: 12px; color: #909399; margin-top: 4px; }
.days-warn { color: #e6a23c; font-weight: 600; }
.days-expired { color: #f56c6c; font-weight: 600; }
</style>
