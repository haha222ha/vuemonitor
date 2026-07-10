<template>
  <div class="member-feedback-page">
    <div class="page-head">
      <h2>用户反馈与关键词</h2>
      <el-button @click="refreshAll" :loading="store.feedbackLoading || store.keywordLoading">刷新</el-button>
    </div>

    <el-tabs v-model="activeTab" @tab-change="onTabChange">
      <el-tab-pane label="功能建议" name="feedback">
        <div class="toolbar">
          <el-select v-model="feedbackStatus" placeholder="状态" clearable style="width: 140px" @change="loadFeedback">
            <el-option label="全部" value="" />
            <el-option label="新提交" value="new" />
            <el-option label="已读" value="read" />
            <el-option label="已处理" value="done" />
            <el-option label="已忽略" value="ignored" />
          </el-select>
        </div>
        <el-table :data="store.feedbackItems" v-loading="store.feedbackLoading" stripe>
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="created_at" label="时间" width="170" />
          <el-table-column prop="username" label="会员" width="120" />
          <el-table-column prop="category" label="类型" width="100" />
          <el-table-column prop="content" label="内容" min-width="260" show-overflow-tooltip />
          <el-table-column prop="app_version" label="版本" width="100" />
          <el-table-column prop="status" label="状态" width="90">
            <template #default="{ row }">
              <el-tag size="small" :type="statusTag(row.status)">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openEdit('feedback', row)">备注/状态</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="监控关键词申请" name="keywords">
        <el-alert type="info" :closable="false" show-icon class="mb-16"
          title="会员提交的关键词会进入监控总词库排队，不保证有采集结果；定向定制请引导使用会员定制词库服务。" />
        <div class="toolbar">
          <el-select v-model="keywordStatus" placeholder="状态" clearable style="width: 140px" @change="loadKeywords">
            <el-option label="全部" value="" />
            <el-option label="排队中" value="pending" />
            <el-option label="已纳入" value="merged" />
            <el-option label="已拒绝" value="rejected" />
          </el-select>
        </div>
        <el-table :data="store.keywordItems" v-loading="store.keywordLoading" stripe>
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="created_at" label="时间" width="170" />
          <el-table-column prop="username" label="会员" width="120" />
          <el-table-column prop="keywords" label="关键词" min-width="220" show-overflow-tooltip />
          <el-table-column prop="note" label="说明" min-width="180" show-overflow-tooltip />
          <el-table-column prop="status" label="状态" width="90">
            <template #default="{ row }">
              <el-tag size="small" :type="keywordStatusTag(row.status)">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="openEdit('keyword', row)">备注/状态</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="editVisible" title="更新记录" width="480px">
      <el-form label-width="80px">
        <el-form-item label="状态">
          <el-select v-model="editForm.status" style="width: 100%">
            <template v-if="editKind === 'feedback'">
              <el-option label="新提交" value="new" />
              <el-option label="已读" value="read" />
              <el-option label="已处理" value="done" />
              <el-option label="已忽略" value="ignored" />
            </template>
            <template v-else>
              <el-option label="排队中" value="pending" />
              <el-option label="已纳入" value="merged" />
              <el-option label="已拒绝" value="rejected" />
            </template>
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="editForm.admin_note" type="textarea" :rows="4" maxlength="2000" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { useMemberFeedbackStore } from "../stores/memberFeedback";

const store = useMemberFeedbackStore();
const activeTab = ref("feedback");
const feedbackStatus = ref("");
const keywordStatus = ref("");
const editVisible = ref(false);
const editKind = ref<"feedback" | "keyword">("feedback");
const editId = ref(0);
const saving = ref(false);
const editForm = reactive({ status: "", admin_note: "" });

function statusTag(s: string) {
  if (s === "done") return "success";
  if (s === "ignored") return "info";
  if (s === "read") return "warning";
  return "danger";
}

function keywordStatusTag(s: string) {
  if (s === "merged") return "success";
  if (s === "rejected") return "info";
  return "warning";
}

async function loadFeedback() {
  await store.fetchFeedback(200, feedbackStatus.value || undefined);
}

async function loadKeywords() {
  await store.fetchKeywords(200, keywordStatus.value || undefined);
}

function onTabChange(name: string | number) {
  if (name === "keywords") loadKeywords();
  else loadFeedback();
}

async function refreshAll() {
  await loadFeedback();
  await loadKeywords();
}

function openEdit(kind: "feedback" | "keyword", row: { id: number; status: string; admin_note?: string }) {
  editKind.value = kind;
  editId.value = row.id;
  editForm.status = row.status || (kind === "feedback" ? "new" : "pending");
  editForm.admin_note = row.admin_note || "";
  editVisible.value = true;
}

async function saveEdit() {
  saving.value = true;
  try {
    const payload = { status: editForm.status, admin_note: editForm.admin_note };
    if (editKind.value === "feedback") {
      await store.updateFeedback(editId.value, payload);
      await loadFeedback();
    } else {
      await store.updateKeyword(editId.value, payload);
      await loadKeywords();
    }
    editVisible.value = false;
    ElMessage.success("已保存");
  } catch (e: unknown) {
    ElMessage.error((e as Error)?.message || "保存失败");
  } finally {
    saving.value = false;
  }
}

onMounted(() => {
  loadFeedback();
});
</script>

<style scoped>
.member-feedback-page { padding: 0 4px; }
.page-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.page-head h2 { margin: 0; }
.toolbar { margin-bottom: 12px; }
.mb-16 { margin-bottom: 16px; }
</style>
