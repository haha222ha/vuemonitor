<template>
  <div>
    <div class="toolbar">
      <h2>授权码管理</h2>
      <div class="toolbar-actions">
        <el-button @click="exportCsv">导出 CSV</el-button>
        <el-button type="primary" @click="showCreate = true">生成授权码</el-button>
      </div>
    </div>

    <el-table :data="store.licenses" stripe v-loading="store.loading">
      <el-table-column prop="code" label="授权码" min-width="200">
        <template #default="{ row }">
          <span class="code-cell">{{ row.code }}</span>
          <el-button link type="primary" size="small" @click="copyOne(row.code)">复制</el-button>
        </template>
      </el-table-column>
      <el-table-column prop="plan" label="套餐" width="100" />
      <el-table-column prop="duration_days" label="天数" width="80" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="batch_id" label="批次" width="120" show-overflow-tooltip />
      <el-table-column prop="created_at" label="创建时间" width="180" />
    </el-table>

    <el-pagination
      v-if="store.total > pageSize"
      class="pager"
      layout="prev, pager, next"
      :total="store.total"
      :page-size="pageSize"
      v-model:current-page="page"
      @current-change="fetchLicenses"
    />

    <el-dialog v-model="showCreate" title="生成授权码" width="420px" @closed="generatedCodes = []">
      <el-form :model="form" :rules="formRules" ref="formRef" label-width="80px">
        <el-form-item label="套餐" prop="plan">
          <el-select v-model="form.plan" style="width: 100%">
            <el-option label="Pro" value="pro" />
            <el-option label="Premium" value="premium" />
            <el-option label="Enterprise" value="enterprise" />
          </el-select>
        </el-form-item>
        <el-form-item label="天数" prop="duration_days">
          <el-input-number v-model="form.duration_days" :min="1" :max="3650" style="width: 100%" />
        </el-form-item>
        <el-form-item label="数量" prop="count">
          <el-input-number v-model="form.count" :min="1" :max="100" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注" prop="note">
          <el-input v-model="form.note" placeholder="如：订单号 / 客户 QQ" />
        </el-form-item>
      </el-form>

      <div v-if="generatedCodes.length" class="codes-box">
        <div class="codes-head">
          <span>已生成 {{ generatedCodes.length }} 个（请复制发给客户）</span>
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
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
import type { FormInstance, FormRules } from "element-plus";
import { useLicensesStore } from "../stores/licenses";
import api from "../utils/api";

const store = useLicensesStore();
const showCreate = ref(false);
const generating = ref(false);
const formRef = ref<FormInstance>();
const form = reactive({ plan: "pro", duration_days: 30, count: 1, note: "" });
const generatedCodes = ref<string[]>([]);
const page = ref(1);
const pageSize = 20;

const formRules: FormRules = {
  plan: [{ required: true, message: "请选择套餐", trigger: "change" }],
  duration_days: [{ required: true, message: "请输入天数", trigger: "blur" }],
  count: [{ required: true, message: "请输入数量", trigger: "blur" }],
};

function statusType(status: string) {
  if (status === "unused") return "success";
  if (status === "active") return "primary";
  return "info";
}

async function fetchLicenses() {
  try {
    await store.fetchLicenses(page.value, pageSize);
  } catch {
    ElMessage.error("获取授权码列表失败");
  }
}

async function generate() {
  const valid = await formRef.value?.validate().catch(() => false);
  if (!valid) return;
  generating.value = true;
  try {
    const data = await store.generateLicense({
      plan: form.plan,
      duration_days: form.duration_days,
      count: form.count,
      note: form.note || undefined,
    });
    generatedCodes.value = data?.codes || [];
    ElMessage.success(`已生成 ${generatedCodes.value.length} 个授权码`);
    await fetchLicenses();
  } catch {
    ElMessage.error("生成失败");
  } finally {
    generating.value = false;
  }
}

async function copyOne(code: string) {
  try {
    await navigator.clipboard.writeText(code);
    ElMessage.success("已复制");
  } catch {
    ElMessage.info(code);
  }
}

async function copyAll() {
  if (!generatedCodes.value.length) return;
  await copyOne(generatedCodes.value.join("\n"));
}

async function exportCsv() {
  try {
    const { data } = await api.get("/admin/licenses/export", { params: { page: 1, page_size: 10000 } });
    const items = data?.items || data || [];
    if (!items.length) {
      ElMessage.warning("无数据可导出");
      return;
    }
    const header = "code,plan,duration_days,status,batch_id,created_at\n";
    const rows = items.map((r: Record<string, unknown>) =>
      [r.code, r.plan, r.duration_days, r.status, r.batch_id, r.created_at]
        .map((v) => `"${String(v ?? "").replace(/"/g, '""')}"`)
        .join(",")
    );
    const blob = new Blob(["\ufeff" + header + rows.join("\n")], { type: "text/csv;charset=utf-8" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `licenses-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
    ElMessage.success("已导出");
  } catch {
    ElMessage.error("导出失败");
  }
}

onMounted(fetchLicenses);
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.toolbar h2 {
  margin: 0;
}
.toolbar-actions {
  display: flex;
  gap: 8px;
}
.code-cell {
  font-family: ui-monospace, monospace;
  font-size: 12px;
  margin-right: 8px;
}
.pager {
  margin-top: 16px;
  justify-content: flex-end;
}
.codes-box {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--el-border-color);
}
.codes-head {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 13px;
}
</style>
