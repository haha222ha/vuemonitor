<template>
  <div>
    <div style="display:flex;justify-content:space-between;margin-bottom:16px">
      <h2>情报授权码管理</h2>
      <el-button type="primary" @click="showCreate = true">生成授权码</el-button>
    </div>

    <div style="display:flex;gap:12px;margin-bottom:16px">
      <el-select v-model="filterPlan" placeholder="套餐筛选" clearable style="width:140px" @change="fetch">
        <el-option label="7天趋势精选" value="weekly" />
        <el-option label="月度会员" value="monthly" />
        <el-option label="年费会员" value="yearly" />
      </el-select>
      <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width:120px" @change="fetch">
        <el-option label="未使用" value="unused" />
        <el-option label="已激活" value="active" />
        <el-option label="已吊销" value="revoked" />
      </el-select>
    </div>

    <el-table :data="store.codes" stripe v-loading="store.loading">
      <el-table-column prop="code" label="授权码" width="200" />
      <el-table-column prop="plan" label="套餐" width="130">
        <template #default="{ row }">{{ planLabel(row.plan) }}</template>
      </el-table-column>
      <el-table-column prop="duration_days" label="天数" width="70" />
      <el-table-column prop="current_activations" label="激活/上限" width="90">
        <template #default="{ row }">{{ row.current_activations }}/{{ row.max_activations }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="80">
        <template #default="{ row }">
          <el-tag :type="row.status === 'unused' ? 'success' : row.status === 'active' ? 'primary' : 'danger'">
            {{ statusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="batch_id" label="批次" width="120" />
      <el-table-column prop="created_at" label="创建时间" width="170" />
      <el-table-column label="操作" width="80" fixed="right">
        <template #default="{ row }">
          <el-button v-if="row.status !== 'revoked'" type="danger" text size="small" @click="revoke(row.id)">吊销</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div style="display:flex;justify-content:flex-end;margin-top:16px">
      <el-pagination
        v-model:current-page="page"
        :page-size="20"
        :total="store.total"
        layout="total, prev, pager, next"
        @current-change="fetch"
      />
    </div>

    <el-dialog v-model="showCreate" title="生成情报授权码" width="440px">
      <el-form :model="form" :rules="formRules" ref="formRef" label-width="80px">
        <el-form-item label="套餐" prop="plan">
          <el-select v-model="form.plan" style="width:100%">
            <el-option label="7天趋势精选" value="weekly" />
            <el-option label="月度会员" value="monthly" />
            <el-option label="年费会员" value="yearly" />
          </el-select>
        </el-form-item>
        <el-form-item label="数量" prop="count"><el-input-number v-model="form.count" :min="1" :max="100" style="width:100%" /></el-form-item>
        <el-form-item label="可激活" prop="max_activations"><el-input-number v-model="form.max_activations" :min="1" :max="10" style="width:100%" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.note" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="generate">生成</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showResult" title="生成结果" width="500px">
      <el-alert type="success" :closable="false" style="margin-bottom:12px">
        成功生成 {{ generatedCodes.length }} 个授权码（批次: {{ generatedBatchId }}）
      </el-alert>
      <el-table :data="generatedCodes" size="small" max-height="300">
        <el-table-column prop="code" label="授权码" />
        <el-table-column prop="plan" label="套餐" width="130">
          <template #default="{ row }">{{ planLabel(row.plan) }}</template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="showResult = false">关闭</el-button>
        <el-button type="primary" @click="copyCodes">复制全部</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";
import { useIntelCodesStore } from "../stores/intelCodes";

const store = useIntelCodesStore();
const page = ref(1);
const filterPlan = ref("");
const filterStatus = ref("");
const showCreate = ref(false);
const showResult = ref(false);
const generatedCodes = ref<{ code: string; plan: string }[]>([]);
const generatedBatchId = ref("");
const formRef = ref<FormInstance>();
const form = reactive({ plan: "weekly", count: 1, max_activations: 1, note: "" });

const formRules: FormRules = {
  plan: [{ required: true, message: "请选择套餐", trigger: "change" }],
  count: [{ required: true, message: "请输入数量", trigger: "blur" }],
};

function planLabel(plan: string) {
  const map: Record<string, string> = { weekly: "7天趋势精选", monthly: "月度会员", yearly: "年费会员" };
  return map[plan] || plan;
}

function statusLabel(status: string) {
  const map: Record<string, string> = { unused: "未使用", active: "已激活", revoked: "已吊销" };
  return map[status] || status;
}

async function fetch() {
  await store.fetchCodes(page.value, 20, {
    plan: filterPlan.value || undefined,
    status: filterStatus.value || undefined,
  });
}

async function generate() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;
  try {
    const result = await store.generateCodes({
      plan: form.plan,
      count: form.count,
      max_activations: form.max_activations,
      note: form.note || undefined,
    });
    generatedCodes.value = result.codes || [];
    generatedBatchId.value = result.batch_id || "";
    showCreate.value = false;
    showResult.value = true;
    fetch();
  } catch {
    ElMessage.error("生成失败");
  }
}

async function revoke(codeId: string) {
  try {
    await ElMessageBox.confirm("确定吊销该授权码？关联会员也将失效", "确认吊销", { type: "warning" });
    await store.revokeCode(codeId);
    ElMessage.success("已吊销");
    fetch();
  } catch {}
}

function copyCodes() {
  const text = generatedCodes.value.map((c) => `${c.code} (${planLabel(c.plan)})`).join("\n");
  navigator.clipboard.writeText(text).then(() => ElMessage.success("已复制到剪贴板"));
}

onMounted(fetch);
</script>
