<template>
  <div>
    <div style="display:flex;justify-content:space-between;margin-bottom:16px">
      <h2>采集任务管理</h2>
      <el-button type="primary" @click="showCreateDialog = true">+ 手动创建采集任务</el-button>
    </div>

    <el-table :data="tasks" stripe v-loading="loading">
      <el-table-column prop="user_id" label="用户ID" width="120" show-overflow-tooltip />
      <el-table-column prop="task_type" label="类型" width="100">
        <template #default="{ row }">{{ taskTypeLabel(row.task_type) }}</template>
      </el-table-column>
      <el-table-column prop="platform" label="平台" width="80">
        <template #default="{ row }">{{ platformLabel(row.platform) }}</template>
      </el-table-column>
      <el-table-column prop="target_type" label="目标类型" width="100" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }"><el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="progress" label="进度" width="120">
        <template #default="{ row }"><el-progress :percentage="row.progress || 0" :stroke-width="6" /></template>
      </el-table-column>
      <el-table-column prop="result_summary" label="结果摘要" min-width="150" show-overflow-tooltip />
      <el-table-column prop="created_at" label="创建时间" width="180" />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button v-if="row.status === 'running' || row.status === 'pending'" size="small" type="danger" @click="cancelTask(row.id)">取消</el-button>
          <el-button v-else-if="row.status === 'failed'" size="small" @click="retryTask(row.id)">重试</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showCreateDialog" title="手动创建采集任务" width="520px">
      <el-form :model="createForm" label-width="90px">
        <el-form-item label="采集类型">
          <el-select v-model="createForm.task_type" style="width:100%">
            <el-option label="商品采集" value="product" />
            <el-option label="店铺采集" value="shop" />
            <el-option label="分类采集" value="category" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标平台">
          <el-select v-model="createForm.platform" style="width:100%">
            <el-option label="小红书" value="xhs" />
            <el-option label="淘宝" value="taobao" />
            <el-option label="京东" value="jd" />
            <el-option label="拼多多" value="pdd" />
            <el-option label="抖音" value="douyin" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标类型">
          <el-select v-model="createForm.target_type" style="width:100%">
            <el-option label="商品ID" value="product_id" />
            <el-option label="店铺ID" value="shop_id" />
            <el-option label="分类URL" value="category_url" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标ID">
          <el-input v-model="createForm.target_ids_text" type="textarea" :rows="3" placeholder="每行一个ID或URL" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="createTask">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import api from "../utils/api";
import { ElMessage } from "element-plus";

const tasks = ref([]);
const loading = ref(false);
const showCreateDialog = ref(false);
const creating = ref(false);
const createForm = reactive({
  task_type: "product",
  platform: "xhs",
  target_type: "product_id",
  target_ids_text: "",
});

function taskTypeLabel(t: string) {
  const map: Record<string, string> = { product: "商品", shop: "店铺", category: "分类" };
  return map[t] || t;
}

function platformLabel(p: string) {
  const map: Record<string, string> = { xhs: "小红书", taobao: "淘宝", jd: "京东", pdd: "拼多多", douyin: "抖音" };
  return map[p] || p;
}

function statusType(status: string) {
  const map: Record<string, string> = { pending: "warning", running: "primary", completed: "success", failed: "danger", cancelled: "info" };
  return map[status] || "info";
}

function statusLabel(s: string) {
  const map: Record<string, string> = { pending: "等待中", running: "运行中", completed: "已完成", failed: "失败", cancelled: "已取消" };
  return map[s] || s;
}

async function fetchTasks() {
  loading.value = true;
  try {
    const { data } = await api.get("/admin/collect/tasks");
    tasks.value = data?.data?.items || [];
  } catch {
    ElMessage.error("获取采集任务列表失败");
  } finally {
    loading.value = false;
  }
}

async function cancelTask(id: string) {
  try {
    await api.put(`/admin/collect/tasks/${id}/cancel`);
    ElMessage.success("已取消");
    fetchTasks();
  } catch {
    ElMessage.error("取消任务失败");
  }
}

async function retryTask(id: string) {
  ElMessage.info("重试功能开发中");
}

async function createTask() {
  const targetIds = createForm.target_ids_text.split("\n").map((s) => s.trim()).filter(Boolean);
  if (!targetIds.length) {
    ElMessage.warning("请输入至少一个目标ID");
    return;
  }
  creating.value = true;
  try {
    await api.post("/admin/collect/tasks", {
      task_type: createForm.task_type,
      platform: createForm.platform,
      target_type: createForm.target_type,
      target_ids: targetIds,
    });
    ElMessage.success("采集任务已创建");
    showCreateDialog.value = false;
    createForm.target_ids_text = "";
    fetchTasks();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || "创建失败");
  } finally {
    creating.value = false;
  }
}

onMounted(fetchTasks);
</script>
