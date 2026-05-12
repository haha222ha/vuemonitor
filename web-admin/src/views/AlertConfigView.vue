<template>
  <div>
    <h2>告警配置</h2>
    <el-tabs v-model="activeTab">
      <el-tab-pane label="告警规则" name="rules">
        <div style="display:flex;justify-content:space-between;margin-bottom:16px">
          <span></span>
          <el-button type="primary" @click="openRuleDialog()">添加规则</el-button>
        </div>
        <el-table :data="rules" stripe v-loading="rulesLoading">
          <el-table-column prop="name" label="规则名称" min-width="150" />
          <el-table-column prop="condition_type" label="条件类型" width="140" />
          <el-table-column prop="severity" label="严重程度" width="100">
            <template #default="{ row }">
              <el-tag :type="row.severity === 'critical' ? 'danger' : row.severity === 'high' ? 'danger' : row.severity === 'medium' ? 'warning' : 'info'">{{ row.severity }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="channel" label="通知通道" width="120" />
          <el-table-column prop="is_active" label="启用" width="80">
            <template #default="{ row }">
              <el-switch v-model="row.is_active" @change="toggleRule(row)" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button size="small" @click="openRuleDialog(row)">编辑</el-button>
              <el-button size="small" type="danger" @click="deleteRule(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="通知通道" name="channels">
        <div style="display:flex;justify-content:space-between;margin-bottom:16px">
          <span></span>
          <el-button type="primary" @click="openChannelDialog()">添加通道</el-button>
        </div>
        <el-table :data="channels" stripe v-loading="channelsLoading">
          <el-table-column prop="type" label="类型" width="120">
            <template #default="{ row }">
              <el-tag>{{ channelTypeLabel(row.type) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="配置" min-width="200">
            <template #default="{ row }">
              <span>{{ channelConfigSummary(row.config) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="is_enabled" label="启用" width="80">
            <template #default="{ row }">
              <el-switch v-model="row.is_enabled" @change="toggleChannel(row)" />
            </template>
          </el-table-column>
          <el-table-column prop="last_test_at" label="最近测试" width="180" />
          <el-table-column label="操作" width="160">
            <template #default="{ row }">
              <el-button size="small" @click="testChannel(row.id)">测试</el-button>
              <el-button size="small" @click="openChannelDialog(row)">编辑</el-button>
              <el-button size="small" type="danger" @click="deleteChannel(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="ruleDialogVisible" :title="editingRule ? '编辑规则' : '添加规则'" width="500px">
      <el-form :model="ruleForm" label-width="90px">
        <el-form-item label="规则名称"><el-input v-model="ruleForm.name" /></el-form-item>
        <el-form-item label="条件类型">
          <el-select v-model="ruleForm.condition_type" style="width:100%">
            <el-option label="价格下降" value="price_drop" />
            <el-option label="销量激增" value="sales_surge" />
            <el-option label="评分下降" value="rating_drop" />
            <el-option label="缺货预警" value="out_of_stock" />
            <el-option label="自定义" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="严重程度">
          <el-select v-model="ruleForm.severity" style="width:100%">
            <el-option label="低" value="low" />
            <el-option label="中" value="medium" />
            <el-option label="高" value="high" />
            <el-option label="严重" value="critical" />
          </el-select>
        </el-form-item>
        <el-form-item label="条件配置"><el-input v-model="ruleForm.condition_config_text" type="textarea" :rows="3" placeholder="JSON格式配置" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ruleDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveRule">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="channelDialogVisible" :title="editingChannel ? '编辑通道' : '添加通道'" width="500px">
      <el-form :model="channelForm" label-width="90px">
        <el-form-item label="通道类型">
          <el-select v-model="channelForm.type" style="width:100%" :disabled="!!editingChannel">
            <el-option label="邮件" value="email" />
            <el-option label="Webhook" value="webhook" />
            <el-option label="钉钉" value="dingtalk" />
            <el-option label="企业微信" value="wechat" />
          </el-select>
        </el-form-item>
        <el-form-item label="配置"><el-input v-model="channelForm.config_text" type="textarea" :rows="4" :placeholder="channelConfigPlaceholder" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="channelDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveChannel">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from "vue";
import api from "../utils/api";
import { ElMessage } from "element-plus";

interface AlertRule {
  id: string;
  name: string;
  condition_type: string;
  condition_config: Record<string, unknown>;
  severity: string;
  channel: string;
  is_active: boolean;
}

interface AlertChannel {
  id: string;
  type: string;
  config: Record<string, unknown>;
  is_enabled: boolean;
  last_test_at: string;
}

const activeTab = ref("rules");
const rules = ref<AlertRule[]>([]);
const channels = ref<AlertChannel[]>([]);
const rulesLoading = ref(false);
const channelsLoading = ref(false);
const saving = ref(false);

const ruleDialogVisible = ref(false);
const channelDialogVisible = ref(false);
const editingRule = ref<AlertRule | null>(null);
const editingChannel = ref<AlertChannel | null>(null);

const ruleForm = reactive({ name: "", condition_type: "price_drop", severity: "medium", condition_config_text: "{}" });
const channelForm = reactive({ type: "email", config_text: "{}" });

const channelConfigPlaceholder = computed(() => {
  const map: Record<string, string> = {
    email: '{"email": "admin@example.com"}',
    webhook: '{"url": "https://hooks.example.com/xxx"}',
    dingtalk: '{"webhook": "https://oapi.dingtalk.com/robot/send?access_token=xxx"}',
    wechat: '{"webhook": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"}',
  };
  return map[channelForm.type] || "{}";
});

function channelTypeLabel(t: string): string {
  const map: Record<string, string> = { email: "邮件", webhook: "Webhook", dingtalk: "钉钉", wechat: "企业微信" };
  return map[t] || t;
}

function channelConfigSummary(config: Record<string, unknown>): string {
  const entries = Object.entries(config);
  if (entries.length === 0) return "-";
  return entries.slice(0, 2).map(([k, v]) => `${k}=${v}`).join(", ");
}

async function fetchRules() {
  rulesLoading.value = true;
  try {
    const { data } = await api.get("/admin/alert-rules");
    rules.value = data?.data?.items || [];
  } catch { ElMessage.error("获取告警规则失败"); }
  finally { rulesLoading.value = false; }
}

async function fetchChannels() {
  channelsLoading.value = true;
  try {
    const { data } = await api.get("/admin/alert-channels");
    channels.value = data?.data?.items || [];
  } catch { ElMessage.error("获取通知通道失败"); }
  finally { channelsLoading.value = false; }
}

function openRuleDialog(rule?: AlertRule) {
  editingRule.value = rule || null;
  if (rule) {
    ruleForm.name = rule.name;
    ruleForm.condition_type = rule.condition_type;
    ruleForm.severity = rule.severity;
    ruleForm.condition_config_text = JSON.stringify(rule.condition_config, null, 2);
  } else {
    ruleForm.name = "";
    ruleForm.condition_type = "price_drop";
    ruleForm.severity = "medium";
    ruleForm.condition_config_text = "{}";
  }
  ruleDialogVisible.value = true;
}

async function saveRule() {
  saving.value = true;
  try {
    let config = {};
    try { config = JSON.parse(ruleForm.condition_config_text); } catch { ElMessage.warning("条件配置JSON格式错误"); saving.value = false; return; }
    const payload = { name: ruleForm.name, condition_type: ruleForm.condition_type, severity: ruleForm.severity, condition_config: config };
    if (editingRule.value) {
      await api.put(`/admin/alert-rules/${editingRule.value.id}`, payload);
      ElMessage.success("规则已更新");
    } else {
      await api.post("/admin/alert-rules", payload);
      ElMessage.success("规则已创建");
    }
    ruleDialogVisible.value = false;
    fetchRules();
  } catch { ElMessage.error("保存规则失败"); }
  finally { saving.value = false; }
}

async function toggleRule(rule: AlertRule) {
  try { await api.put(`/admin/alert-rules/${rule.id}`, { is_active: rule.is_active }); }
  catch { rule.is_active = !rule.is_active; ElMessage.error("操作失败"); }
}

async function deleteRule(id: string) {
  try { await api.delete(`/admin/alert-rules/${id}`); ElMessage.success("已删除"); fetchRules(); }
  catch { ElMessage.error("删除失败"); }
}

function openChannelDialog(channel?: AlertChannel) {
  editingChannel.value = channel || null;
  if (channel) {
    channelForm.type = channel.type;
    channelForm.config_text = JSON.stringify(channel.config, null, 2);
  } else {
    channelForm.type = "email";
    channelForm.config_text = "{}";
  }
  channelDialogVisible.value = true;
}

async function saveChannel() {
  saving.value = true;
  try {
    let config = {};
    try { config = JSON.parse(channelForm.config_text); } catch { ElMessage.warning("配置JSON格式错误"); saving.value = false; return; }
    const payload = { type: channelForm.type, config };
    if (editingChannel.value) {
      await api.put(`/admin/alert-channels/${editingChannel.value.id}`, payload);
      ElMessage.success("通道已更新");
    } else {
      await api.post("/admin/alert-channels", payload);
      ElMessage.success("通道已创建");
    }
    channelDialogVisible.value = false;
    fetchChannels();
  } catch { ElMessage.error("保存通道失败"); }
  finally { saving.value = false; }
}

async function toggleChannel(channel: AlertChannel) {
  try { await api.put(`/admin/alert-channels/${channel.id}`, { is_enabled: channel.is_enabled }); }
  catch { channel.is_enabled = !channel.is_enabled; ElMessage.error("操作失败"); }
}

async function testChannel(id: string) {
  try { await api.post(`/admin/alert-channels/${id}/test`); ElMessage.success("测试消息已发送"); }
  catch { ElMessage.error("测试发送失败"); }
}

async function deleteChannel(id: string) {
  try { await api.delete(`/admin/alert-channels/${id}`); ElMessage.success("已删除"); fetchChannels(); }
  catch { ElMessage.error("删除失败"); }
}

onMounted(() => { fetchRules(); fetchChannels(); });
</script>
