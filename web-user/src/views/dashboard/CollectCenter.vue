<template>
  <div class="collect-center">
    <div class="page-toolbar">
      <h3>采集任务</h3>
      <el-button type="primary" @click="showCreateDialog = true">+ 创建采集任务</el-button>
    </div>

    <el-row :gutter="20" class="collect-stats">
      <el-col :span="6">
        <div class="mini-stat">
          <div class="mini-value">{{ taskStats.total }}</div>
          <div class="mini-label">总任务</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="mini-stat">
          <div class="mini-value" style="color: #6366f1;">{{ taskStats.running }}</div>
          <div class="mini-label">运行中</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="mini-stat">
          <div class="mini-value" style="color: #22c55e;">{{ taskStats.completed }}</div>
          <div class="mini-label">已完成</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="mini-stat">
          <div class="mini-value" style="color: #ef4444;">{{ taskStats.failed }}</div>
          <div class="mini-label">失败</div>
        </div>
      </el-col>
    </el-row>

    <el-table :data="tasks" stripe v-loading="loading" empty-text="暂无采集任务">
      <el-table-column prop="task_type" label="类型" width="100">
        <template #default="{ row }">
          <el-tag size="small">{{ taskTypeLabel(row.task_type) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="platform" label="平台" width="90">
        <template #default="{ row }">
          <el-tag size="small">{{ platformLabel(row.platform) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="target_type" label="目标类型" width="100" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="progress" label="进度" width="120">
        <template #default="{ row }">
          <el-progress :percentage="row.progress || 0" :stroke-width="6" />
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180" />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button v-if="row.status === 'running' || row.status === 'pending'" size="small" type="danger" @click="cancelTask(row.id)">取消</el-button>
          <el-button v-else size="small" @click="retryTask(row.id)">重试</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showCreateDialog" title="创建采集任务" width="520px">
      <el-form :model="createForm" label-width="90px">
        <el-form-item label="采集类型">
          <el-select v-model="createForm.task_type" style="width: 100%">
            <el-option label="商品采集" value="product" />
            <el-option label="店铺采集" value="shop" />
            <el-option label="分类采集" value="category" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标平台">
          <el-select v-model="createForm.platform" style="width: 100%">
            <el-option label="小红书" value="xhs" />
            <el-option label="淘宝" value="taobao" />
            <el-option label="京东" value="jd" />
            <el-option label="拼多多" value="pdd" />
            <el-option label="抖音" value="douyin" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标类型">
          <el-select v-model="createForm.target_type" style="width: 100%">
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
        <el-button type="primary" :loading="creating" @click="createTask">创建任务</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import api from "../../utils/api";
import { ElMessage } from "element-plus";

const loading = ref(false);
const creating = ref(false);
const tasks = ref<any[]>([]);
const showCreateDialog = ref(false);

const createForm = reactive({
  task_type: "product",
  platform: "xhs",
  target_type: "product_id",
  target_ids_text: "",
});

const taskStats = computed(() => {
  const total = tasks.value.length;
  return {
    total,
    running: tasks.value.filter((t) => t.status === "running").length,
    completed: tasks.value.filter((t) => t.status === "completed").length,
    failed: tasks.value.filter((t) => t.status === "failed").length,
  };
});

function taskTypeLabel(t: string) {
  const map: Record<string, string> = { product: "商品", shop: "店铺", category: "分类" };
  return map[t] || t;
}

function platformLabel(p: string) {
  const map: Record<string, string> = { xhs: "小红书", taobao: "淘宝", jd: "京东", pdd: "拼多多", douyin: "抖音" };
  return map[p] || p;
}

function statusType(s: string) {
  const map: Record<string, string> = { pending: "warning", running: "primary", completed: "success", failed: "danger", cancelled: "info" };
  return map[s] || "info";
}

function statusLabel(s: string) {
  const map: Record<string, string> = { pending: "等待中", running: "运行中", completed: "已完成", failed: "失败", cancelled: "已取消" };
  return map[s] || s;
}

async function fetchTasks() {
  loading.value = true;
  try {
    const { data } = await api.get("/collect/tasks");
    tasks.value = data?.data?.items || [];
  } catch {
    ElMessage.error("获取采集任务失败");
  } finally {
    loading.value = false;
  }
}

async function createTask() {
  const targetIds = createForm.target_ids_text
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);

  if (!targetIds.length) {
    ElMessage.warning("请输入至少一个目标ID");
    return;
  }

  creating.value = true;
  try {
    await api.post("/collect/tasks", {
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

async function cancelTask(id: string) {
  try {
    await api.post(`/collect/tasks/${id}/cancel`);
    ElMessage.success("已取消");
    fetchTasks();
  } catch {
    ElMessage.error("取消失败");
  }
}

async function retryTask(id: string) {
  ElMessage.info("重试功能开发中");
}

onMounted(fetchTasks);
</script>

<style scoped>
.collect-center {
  padding: 4px;
}

.page-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.page-toolbar h3 {
  font-size: 18px;
  font-weight: 600;
  color: #fff;
  margin: 0;
}

.collect-stats {
  margin-bottom: 20px;
}

.mini-stat {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  padding: 16px;
  text-align: center;
}

.mini-value {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
}

.mini-label {
  font-size: 13px;
  color: #6a6a7a;
  margin-top: 4px;
}
</style>
