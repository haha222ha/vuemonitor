<template>
  <div class="insight-llm-page">
    <div class="page-head">
      <h2>情报 LLM 配置</h2>
      <div class="head-actions">
        <el-button @click="load" :loading="loading">刷新</el-button>
        <el-button @click="testConn" :loading="testing" :disabled="!config">测试连接</el-button>
        <el-button type="primary" @click="save" :loading="saving">保存</el-button>
      </div>
    </div>

    <el-alert
      v-if="!cloudOnline"
      type="warning"
      :closable="false"
      show-icon
      title="选品云离线或未对接"
      class="mb-16"
    >
      请先在 server/.env 配置 XHS_CLOUD_API_URL 与 XHS_CLOUD_SYNC_KEY。
    </el-alert>

    <el-card shadow="never" v-loading="loading">
      <p class="hint">
        L0 夜间预生成（Shadow timer）在此配置 PackyAPI / DeepSeek Key；用户白天访问情报库<strong>不调用</strong> LLM。
        开启后 pipeline 自动使用真 AI；未配置 Key 时降级 mock。
      </p>

      <el-form label-width="140px" class="form-block">
        <el-form-item label="启用真 LLM">
          <el-switch v-model="form.enabled" active-text="开" inactive-text="关" />
          <span class="field-tip">等效 INSIGHT_USE_LLM=1（写入 PG，无需改 .env）</span>
        </el-form-item>

        <el-form-item label="Provider">
          <el-select v-model="form.provider" style="width: 280px" @change="onProviderChange">
            <el-option label="PackyAPI + DeepSeek V4 Flash" value="packy_deepseek" />
            <el-option label="DeepSeek 官方" value="deepseek_direct" />
            <el-option label="智谱 GLM" value="zhipu" />
          </el-select>
        </el-form-item>

        <el-form-item label="Base URL">
          <el-input v-model="form.base_url" placeholder="https://www.packyapi.com/v1" style="max-width: 480px" />
        </el-form-item>

        <el-form-item label="Model">
          <el-input v-model="form.model" placeholder="deepseek-v4-flash" style="max-width: 320px" />
        </el-form-item>

        <el-form-item label="API Key">
          <el-input
            v-model="form.api_key"
            type="password"
            show-password
            placeholder="留空表示不修改已保存的 Key"
            style="max-width: 480px"
          />
          <div v-if="config?.api_key_hint" class="field-tip">已保存：{{ config.api_key_hint }}</div>
        </el-form-item>

        <el-form-item label="关闭 Thinking">
          <el-switch v-model="form.thinking_disabled" />
          <span class="field-tip">DeepSeek V4 JSON 任务建议关闭以降延迟/成本</span>
        </el-form-item>

        <el-form-item label="日 Token 预算">
          <el-input-number v-model="form.budget_tokens_per_day" :min="10000" :max="5000000" :step="10000" />
        </el-form-item>
      </el-form>

      <el-descriptions v-if="config" :column="2" border size="small" class="status-desc">
        <el-descriptions-item label="有效状态">
          <el-tag :type="config.effective_enabled ? 'success' : 'info'">
            {{ config.effective_enabled ? "LLM 已就绪" : "Mock / 未启用" }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="环境变量 INSIGHT_USE_LLM">
          {{ config.env_insight_use_llm ? "1" : "0" }}
        </el-descriptions-item>
        <el-descriptions-item label="最后更新">{{ config.updated_at || "—" }}</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import api from "../utils/api";
import { useMemberCloudStore } from "../stores/memberCloud";

interface InsightLlmConfig {
  enabled: boolean;
  provider: string;
  base_url: string;
  model: string;
  thinking_disabled: boolean;
  budget_tokens_per_day: number;
  api_key_set?: boolean;
  api_key_hint?: string;
  effective_enabled?: boolean;
  env_insight_use_llm?: boolean;
  updated_at?: string | null;
}

const cloudStore = useMemberCloudStore();
const loading = ref(false);
const saving = ref(false);
const testing = ref(false);
const config = ref<InsightLlmConfig | null>(null);

const form = reactive({
  enabled: false,
  provider: "packy_deepseek",
  base_url: "https://www.packyapi.com/v1",
  model: "deepseek-v4-flash",
  api_key: "",
  thinking_disabled: true,
  budget_tokens_per_day: 200000,
});

const cloudOnline = computed(() => cloudStore.status?.online);

const providerDefaults: Record<string, { base_url: string; model: string }> = {
  packy_deepseek: { base_url: "https://www.packyapi.com/v1", model: "deepseek-v4-flash" },
  deepseek_direct: { base_url: "https://api.deepseek.com", model: "deepseek-v4-flash" },
  zhipu: { base_url: "https://open.bigmodel.cn/api/paas/v4", model: "glm-4-flash" },
};

function applyConfig(c: InsightLlmConfig) {
  config.value = c;
  form.enabled = !!c.enabled;
  form.provider = c.provider || "packy_deepseek";
  form.base_url = c.base_url || providerDefaults[form.provider]?.base_url || "";
  form.model = c.model || providerDefaults[form.provider]?.model || "";
  form.thinking_disabled = c.thinking_disabled !== false;
  form.budget_tokens_per_day = c.budget_tokens_per_day || 200000;
  form.api_key = "";
}

function onProviderChange() {
  const d = providerDefaults[form.provider];
  if (d) {
    form.base_url = d.base_url;
    form.model = d.model;
  }
}

async function load() {
  loading.value = true;
  try {
    await cloudStore.fetchStatus();
    const { data } = await api.get("/xhs-cloud/admin/insight-llm-config");
    const cfg = (data.data?.config || data.data) as InsightLlmConfig;
    if (cfg) applyConfig(cfg);
  } catch (e: unknown) {
    ElMessage.error((e as Error)?.message || "加载配置失败");
  } finally {
    loading.value = false;
  }
}

async function save() {
  saving.value = true;
  try {
    const payload: Record<string, unknown> = {
      enabled: form.enabled,
      provider: form.provider,
      base_url: form.base_url,
      model: form.model,
      thinking_disabled: form.thinking_disabled,
      budget_tokens_per_day: form.budget_tokens_per_day,
    };
    if (form.api_key.trim()) payload.api_key = form.api_key.trim();
    const { data } = await api.put("/xhs-cloud/admin/insight-llm-config", payload);
    const cfg = (data.data?.config || data.data) as InsightLlmConfig;
    if (cfg?.enabled !== undefined) applyConfig(cfg);
    ElMessage.success("已保存");
  } catch (e: unknown) {
    ElMessage.error((e as Error)?.message || "保存失败");
  } finally {
    saving.value = false;
  }
}

async function testConn() {
  testing.value = true;
  try {
    const { data } = await api.post("/xhs-cloud/admin/insight-llm-config/test");
    const r = data.data || data;
    ElMessage.success(r.message || "连接成功");
  } catch (e: unknown) {
    ElMessage.error((e as Error)?.message || "测试失败");
  } finally {
    testing.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.page-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.head-actions { display: flex; gap: 8px; }
.mb-16 { margin-bottom: 16px; }
.hint { color: var(--el-text-color-secondary); margin-bottom: 20px; line-height: 1.6; }
.field-tip { margin-left: 12px; font-size: 12px; color: var(--el-text-color-secondary); }
.form-block { max-width: 720px; }
.status-desc { margin-top: 24px; }
</style>
