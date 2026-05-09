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

    <div class="filter-bar">
      <el-select v-model="filterStatus" placeholder="全部状态" clearable style="width: 130px" @change="fetchTasks">
        <el-option label="等待中" value="pending" />
        <el-option label="运行中" value="running" />
        <el-option label="已完成" value="completed" />
        <el-option label="失败" value="failed" />
        <el-option label="已取消" value="cancelled" />
      </el-select>
      <el-select v-model="filterPlatform" placeholder="全部平台" clearable style="width: 130px" @change="fetchTasks">
        <el-option label="小红书" value="xhs" />
        <el-option label="淘宝" value="taobao" />
        <el-option label="京东" value="jd" />
        <el-option label="拼多多" value="pdd" />
        <el-option label="抖音" value="douyin" />
      </el-select>
    </div>

    <el-table :data="tasks" stripe v-loading="loading" empty-text="暂无采集任务" @row-click="showTaskDetail">
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
      <el-table-column prop="target_type" label="目标类型" width="100">
        <template #default="{ row }">
          {{ targetTypeLabel(row.target_type) }}
        </template>
      </el-table-column>
      <el-table-column label="目标" min-width="180">
        <template #default="{ row }">
          <span class="target-ids">{{ (row.target_ids || []).join(', ') }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="progress" label="进度" width="120">
        <template #default="{ row }">
          <el-progress :percentage="row.progress || 0" :stroke-width="6" :status="progressStatus(row)" />
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="170">
        <template #default="{ row }">
          {{ formatTime(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click.stop="showTaskDetail(row)">详情</el-button>
          <el-button v-if="row.status === 'pending'" size="small" type="primary" @click.stop="executeTask(row.id)">执行</el-button>
          <el-button v-if="row.status === 'running' || row.status === 'pending'" size="small" type="danger" @click.stop="cancelTask(row.id)">取消</el-button>
          <el-button v-if="row.status === 'failed' || row.status === 'cancelled'" size="small" type="warning" @click.stop="retryTask(row.id)">重试</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination-bar" v-if="total > pageSize">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        @current-change="fetchTasks"
      />
    </div>

    <el-dialog v-model="showCreateDialog" title="创建采集任务" width="520px" :close-on-click-modal="false">
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

    <el-dialog v-model="detailVisible" title="任务详情" width="640px" destroy-on-close>
      <div v-if="detailLoading" style="text-align: center; padding: 30px;">
        <el-icon class="is-loading" :size="24"><Loading /></el-icon>
      </div>
      <template v-else-if="taskDetail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="任务ID">{{ taskDetail.id }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ taskTypeLabel(taskDetail.task_type) }}</el-descriptions-item>
          <el-descriptions-item label="平台">{{ platformLabel(taskDetail.platform) }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusType(taskDetail.status)" size="small">{{ statusLabel(taskDetail.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="目标类型">{{ targetTypeLabel(taskDetail.target_type) }}</el-descriptions-item>
          <el-descriptions-item label="进度">{{ taskDetail.progress || 0 }}%</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatTime(taskDetail.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="完成时间">{{ formatTime(taskDetail.completed_at) }}</el-descriptions-item>
        </el-descriptions>

        <div v-if="taskDetail.result_summary" class="result-summary">
          <h4>采集结果</h4>
          <el-row :gutter="12">
            <el-col :span="6">
              <div class="rs-item success">
                <div class="rs-val">{{ taskDetail.result_summary.success || 0 }}</div>
                <div class="rs-lbl">成功</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="rs-item fail">
                <div class="rs-val">{{ taskDetail.result_summary.failed || 0 }}</div>
                <div class="rs-lbl">失败</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="rs-item risk">
                <div class="rs-val">{{ taskDetail.result_summary.risk_detected || 0 }}</div>
                <div class="rs-lbl">风控</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="rs-item total">
                <div class="rs-val">{{ taskDetail.result_summary.total || 0 }}</div>
                <div class="rs-lbl">总计</div>
              </div>
            </el-col>
          </el-row>
        </div>

        <div v-if="taskDetail.error_message" class="error-box">
          <h4>错误信息</h4>
          <p>{{ taskDetail.error_message }}</p>
        </div>

        <div v-if="taskDetail.items && taskDetail.items.length" class="items-section">
          <h4>采集明细 ({{ taskDetail.items.length }})</h4>
          <el-table :data="taskDetail.items" size="small" max-height="300">
            <el-table-column prop="target_id" label="目标ID" min-width="180" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="statusType(row.status)" size="small">{{ statusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="结果" min-width="200">
              <template #default="{ row }">
                <span v-if="row.result && Object.keys(row.result).length">{{ JSON.stringify(row.result).slice(0, 80) }}...</span>
                <span v-else-if="row.error_message" style="color: #ef4444;">{{ row.error_message }}</span>
                <span v-else style="color: #4a4a5a;">—</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </template>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button v-if="taskDetail && (taskDetail.status === 'failed' || taskDetail.status === 'cancelled')" type="warning" @click="retryFromDetail">重试此任务</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import api from "../../utils/api";
import { ElMessage } from "element-plus";
import { Loading } from "@element-plus/icons-vue";

const loading = ref(false);
const creating = ref(false);
const tasks = ref<any[]>([]);
const total = ref(0);
const currentPage = ref(1);
const pageSize = ref(20);
const filterStatus = ref("");
const filterPlatform = ref("");
const showCreateDialog = ref(false);

const detailVisible = ref(false);
const detailLoading = ref(false);
const taskDetail = ref<any>(null);

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
    running: tasks.value.filter((t) => t.status === "running" || t.status === "pending").length,
    completed: tasks.value.filter((t) => t.status === "completed").length,
    failed: tasks.value.filter((t) => t.status === "failed" || t.status === "cancelled").length,
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

function targetTypeLabel(t: string) {
  const map: Record<string, string> = { product_id: "商品ID", shop_id: "店铺ID", category_url: "分类URL" };
  return map[t] || t;
}

function statusType(s: string) {
  const map: Record<string, string> = { pending: "warning", running: "primary", completed: "success", failed: "danger", cancelled: "info", risk_detected: "warning" };
  return map[s] || "info";
}

function statusLabel(s: string) {
  const map: Record<string, string> = { pending: "等待中", running: "运行中", completed: "已完成", failed: "失败", cancelled: "已取消", risk_detected: "风控拦截" };
  return map[s] || s;
}

function progressStatus(row: any) {
  if (row.status === "completed") return "success" as const;
  if (row.status === "failed") return "exception" as const;
  return undefined;
}

function formatTime(t: string | null) {
  if (!t) return "—";
  const d = new Date(t);
  return d.toLocaleString("zh-CN", { hour12: false });
}

async function fetchTasks() {
  loading.value = true;
  try {
    const params: any = { page: currentPage.value, page_size: pageSize.value };
    if (filterStatus.value) params.status = filterStatus.value;
    if (filterPlatform.value) params.platform = filterPlatform.value;
    const { data } = await api.get("/collect/tasks", { params });
    tasks.value = data?.data?.items || [];
    total.value = data?.data?.total || 0;
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
    const msg = e?.response?.data?.message || "创建失败";
    ElMessage.error(msg);
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

async function executeTask(id: string) {
  try {
    await api.post(`/collect/tasks/${id}/execute`);
    ElMessage.success("任务已开始执行");
    fetchTasks();
    setTimeout(fetchTasks, 5000);
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || "执行失败");
  }
}

async function retryTask(id: string) {
  try {
    await api.post(`/collect/tasks/${id}/retry`);
    ElMessage.success("重试任务已创建");
    fetchTasks();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || "重试失败");
  }
}

async function showTaskDetail(row: any) {
  detailVisible.value = true;
  detailLoading.value = true;
  taskDetail.value = null;
  try {
    const { data } = await api.get(`/collect/tasks/${row.id}`);
    taskDetail.value = data?.data || null;
  } catch {
    ElMessage.error("获取任务详情失败");
  } finally {
    detailLoading.value = false;
  }
}

async function retryFromDetail() {
  if (!taskDetail.value) return;
  try {
    await api.post(`/collect/tasks/${taskDetail.value.id}/retry`);
    ElMessage.success("重试任务已创建");
    detailVisible.value = false;
    fetchTasks();
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || "重试失败");
  }
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

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.target-ids {
  font-size: 12px;
  color: #9a9aaa;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 180px;
  display: inline-block;
}

.pagination-bar {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.result-summary {
  margin-top: 20px;
}

.result-summary h4 {
  font-size: 14px;
  color: #e0e0e6;
  margin: 0 0 12px;
}

.rs-item {
  text-align: center;
  padding: 12px 8px;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.03);
}

.rs-item.success { border-left: 3px solid #22c55e; }
.rs-item.fail { border-left: 3px solid #ef4444; }
.rs-item.risk { border-left: 3px solid #f59e0b; }
.rs-item.total { border-left: 3px solid #6366f1; }

.rs-val {
  font-size: 22px;
  font-weight: 700;
  color: #fff;
}

.rs-lbl {
  font-size: 12px;
  color: #6a6a7a;
  margin-top: 2px;
}

.error-box {
  margin-top: 16px;
  padding: 12px;
  background: rgba(239, 68, 68, 0.06);
  border: 1px solid rgba(239, 68, 68, 0.15);
  border-radius: 8px;
}

.error-box h4 {
  font-size: 14px;
  color: #fca5a5;
  margin: 0 0 8px;
}

.error-box p {
  font-size: 13px;
  color: #e0e0e6;
  margin: 0;
  word-break: break-all;
}

.items-section {
  margin-top: 20px;
}

.items-section h4 {
  font-size: 14px;
  color: #e0e0e6;
  margin: 0 0 12px;
}
</style>
