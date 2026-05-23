<template>
  <div class="aipic-view">
    <div class="aipic-header">
      <h2>AI智能作图</h2>
      <div class="aipic-credits">
        <el-tag type="primary">{{ credits }} 积分</el-tag>
        <el-tag type="info">今日剩余 {{ remainingToday }} 次</el-tag>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="aipic-tabs">
      <el-tab-pane label="创作" name="create">
        <div class="create-panel">
          <el-form :model="form" label-position="top" class="create-form">
            <el-form-item label="提示词">
              <el-input
                v-model="form.prompt"
                type="textarea"
                :rows="3"
                placeholder="描述你想生成的图片..."
                maxlength="2000"
                show-word-limit
              />
            </el-form-item>

            <el-form-item label="反向提示词">
              <el-input
                v-model="form.negative_prompt"
                type="textarea"
                :rows="2"
                placeholder="描述你不想出现的内容..."
                maxlength="1000"
              />
            </el-form-item>

            <div class="form-row">
              <el-form-item label="画幅比例" class="form-item-half">
                <el-select v-model="form.ratio" placeholder="选择比例">
                  <el-option label="1:1 方形" value="square" />
                  <el-option label="2:3 竖版" value="portrait" />
                  <el-option label="3:2 横版" value="landscape" />
                  <el-option label="16:9 宽屏" value="wide" />
                </el-select>
              </el-form-item>

              <el-form-item label="画质" class="form-item-half">
                <el-select v-model="form.quality" placeholder="选择画质">
                  <el-option label="标准 (1积分)" value="standard" />
                  <el-option
                    label="高清 (2积分)"
                    value="hd"
                    :disabled="!canAccess('gate:aipic:hd')"
                  />
                  <el-option
                    label="超清 (4积分)"
                    value="ultra"
                    :disabled="!canAccess('gate:aipic:ultra')"
                  />
                </el-select>
              </el-form-item>
            </div>

            <el-form-item label="风格">
              <el-select v-model="form.style" placeholder="选择风格" clearable :disabled="!canAccess('gate:aipic:style')">
                <el-option
                  v-for="s in styles"
                  :key="s.style_name"
                  :label="s.style_name"
                  :value="s.style_name"
                >
                  <span>{{ s.style_name }}</span>
                  <el-tag size="small" type="info" class="style-category-tag">{{ s.category }}</el-tag>
                </el-option>
              </el-select>
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                size="large"
                :loading="generating"
                :disabled="!form.prompt.trim()"
                @click="handleGenerate"
                class="generate-btn"
              >
                {{ generating ? '生成中...' : '开始生成' }}
              </el-button>
            </el-form-item>
          </el-form>

          <div v-if="currentTask" class="task-status">
            <el-card shadow="never">
              <div class="task-info">
                <el-icon v-if="currentTask.task_status === '待执行'" class="is-loading"><Loading /></el-icon>
                <el-icon v-else-if="currentTask.task_status === '执行中'" class="is-loading"><Loading /></el-icon>
                <el-icon v-else-if="currentTask.task_status === '已完成'" color="#67c23a"><CircleCheck /></el-icon>
                <el-icon v-else color="#f56c6c"><CircleClose /></el-icon>
                <span>{{ taskStatusLabel[currentTask.task_status] || currentTask.task_status }}</span>
                <el-button
                  v-if="currentTask.task_status === '待执行'"
                  type="danger"
                  size="small"
                  link
                  @click="handleCancel(currentTask.task_id)"
                >
                  取消
                </el-button>
              </div>
              <div v-if="currentTask.task_status === '已完成' && currentTask.output_image_path" class="task-result">
                <img :src="getImageUrl(currentTask.output_image_path)" alt="生成结果" class="result-image" />
              </div>
              <div v-if="currentTask.task_status === '失败'" class="task-error">
                {{ currentTask.fail_reason }}
              </div>
            </el-card>
          </div>
        </div>
      </el-tab-pane>

      <el-tab-pane label="我的作品" name="works">
        <div class="works-toolbar">
          <el-checkbox v-model="showFavoritesOnly">仅显示收藏</el-checkbox>
        </div>
        <div v-if="works.length === 0" class="empty-state">
          <p>暂无作品，去创作吧！</p>
        </div>
        <div v-else class="works-grid">
          <div v-for="w in works" :key="w.id" class="work-card" @click="previewWork(w)">
            <img v-if="w.output_image_path" :src="getImageUrl(w.output_image_path)" alt="" class="work-thumb" />
            <div v-else class="work-thumb-placeholder">无图片</div>
            <div class="work-info">
              <div class="work-prompt">{{ w.prompt }}</div>
              <div class="work-meta">
                <span>{{ w.quality_tier }}</span>
                <span>{{ w.ratio_key }}</span>
                <el-icon
                  :class="{ 'is-favorite': w.is_favorite }"
                  @click.stop="toggleFavorite(w)"
                >
                  <Star />
                </el-icon>
              </div>
            </div>
          </div>
        </div>
        <div v-if="worksTotal > works.length" class="load-more">
          <el-button link type="primary" @click="loadMoreWorks">加载更多</el-button>
        </div>
      </el-tab-pane>

      <el-tab-pane label="积分" name="credits">
        <el-card shadow="never" class="credits-card">
          <div class="credits-overview">
            <div class="credit-stat">
              <div class="credit-value">{{ credits }}</div>
              <div class="credit-label">当前积分</div>
            </div>
            <div class="credit-stat">
              <div class="credit-value">{{ creditsData.total_purchased || 0 }}</div>
              <div class="credit-label">累计获得</div>
            </div>
            <div class="credit-stat">
              <div class="credit-value">{{ creditsData.total_used || 0 }}</div>
              <div class="credit-label">累计使用</div>
            </div>
          </div>
        </el-card>

        <div class="credits-log">
          <h4>积分流水</h4>
          <el-table :data="creditsLog" stripe>
            <el-table-column prop="created_at" label="时间" width="180">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
            <el-table-column prop="change_type" label="类型" width="100">
              <template #default="{ row }">
                <el-tag :type="changeTypeTag(row.change_type)" size="small">{{ changeTypeLabel(row.change_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="change_amount" label="变动" width="100">
              <template #default="{ row }">
                <span :class="row.change_amount > 0 ? 'amount-positive' : 'amount-negative'">
                  {{ row.change_amount > 0 ? '+' : '' }}{{ row.change_amount }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="balance_after" label="余额" width="100" />
            <el-table-column prop="description" label="说明" />
          </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from "vue";
import { Loading, CircleCheck, CircleClose, Star } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import api from "../../utils/api";
import { useFeatureGate } from "../../composables/useFeatureGate";

const { canAccess, guard } = useFeatureGate();

const activeTab = ref("create");
const generating = ref(false);
const currentTask = ref<any>(null);
const works = ref<any[]>([]);
const worksTotal = ref(0);
const worksPage = ref(1);
const showFavoritesOnly = ref(false);
const styles = ref<any[]>([]);
const credits = ref(0);
const remainingToday = ref(0);
const creditsData = ref<any>({});
const creditsLog = ref<any[]>([]);
let pollTimer: ReturnType<typeof setInterval> | null = null;

const form = ref({
  prompt: "",
  negative_prompt: "",
  ratio: "square",
  quality: "standard",
  style: "",
});

const taskStatusLabel: Record<string, string> = {
  "待执行": "排队中",
  "执行中": "生成中",
  "已完成": "已完成",
  "失败": "生成失败",
  "已取消": "已取消",
};

function getImageUrl(path: string): string {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return `/api/v1/aipic/outputs/${encodeURIComponent(path.split(/[\\/]/).pop() || "")}`;
}

async function fetchCredits() {
  try {
    const { data } = await api.get("/aipic/user/credits");
    if (data?.code === 0) {
      credits.value = data.data.credits;
      remainingToday.value = data.data.remaining_today;
      creditsData.value = data.data;
    }
  } catch {}
}

async function fetchStyles() {
  try {
    const { data } = await api.get("/aipic/generate/styles");
    if (data?.code === 0) {
      styles.value = data.data.items || [];
    }
  } catch {}
}

async function fetchWorks() {
  try {
    const { data } = await api.get("/aipic/user/works", {
      params: { page: worksPage.value, page_size: 20, favorite_only: showFavoritesOnly.value },
    });
    if (data?.code === 0) {
      if (worksPage.value === 1) {
        works.value = data.data.items || [];
      } else {
        works.value = [...works.value, ...(data.data.items || [])];
      }
      worksTotal.value = data.data.total || 0;
    }
  } catch {}
}

async function fetchCreditsLog() {
  try {
    const { data } = await api.get("/aipic/user/credits/log", { params: { page: 1, page_size: 50 } });
    if (data?.code === 0) {
      creditsLog.value = data.data.items || [];
    }
  } catch {}
}

async function handleGenerate() {
  if (!form.value.prompt.trim()) return;

  if (!guard("gate:aipic:generate")) return;

  generating.value = true;
  try {
    const { data } = await api.post("/aipic/generate/text2img", {
      prompt: form.value.prompt,
      negative_prompt: form.value.negative_prompt,
      ratio: form.value.ratio,
      quality: form.value.quality,
      style: form.value.style,
    });

    if (data?.code === 0) {
      ElMessage.success(`任务已提交，排队位置：${data.data.queue_position}`);
      currentTask.value = { task_id: data.data.task_id, task_status: "待执行" };
      startPolling(data.data.task_id);
      fetchCredits();
    } else {
      ElMessage.error(data?.message || "生成失败");
    }
  } catch (e: any) {
    const msg = e?.response?.data?.message || "生成请求失败";
    ElMessage.error(msg);
  } finally {
    generating.value = false;
  }
}

function startPolling(taskId: string) {
  stopPolling();
  pollTimer = setInterval(async () => {
    try {
      const { data } = await api.get(`/aipic/generate/status/${taskId}`);
      if (data?.code === 0) {
        currentTask.value = data.data;
        if (["已完成", "失败", "已取消"].includes(data.data.task_status)) {
          stopPolling();
          if (data.data.task_status === "已完成") {
            fetchCredits();
            fetchWorks();
          }
        }
      }
    } catch {
      stopPolling();
    }
  }, 3000);
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

async function handleCancel(taskId: string) {
  try {
    const { data } = await api.post(`/aipic/generate/cancel/${taskId}`);
    if (data?.code === 0) {
      ElMessage.success("任务已取消");
      stopPolling();
      currentTask.value = null;
      fetchCredits();
    }
  } catch {}
}

async function toggleFavorite(work: any) {
  try {
    const { data } = await api.post(`/aipic/user/works/${work.id}/favorite`);
    if (data?.code === 0) {
      work.is_favorite = data.data.is_favorite;
    }
  } catch {}
}

function previewWork(work: any) {}

function loadMoreWorks() {
  worksPage.value++;
  fetchWorks();
}

function formatTime(dateStr: string) {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleString();
}

function changeTypeLabel(type: string) {
  const map: Record<string, string> = { purchase: "充值", consume: "消费", refund: "退还", daily_reset: "每日重置" };
  return map[type] || type;
}

function changeTypeTag(type: string) {
  const map: Record<string, string> = { purchase: "success", consume: "danger", refund: "warning", daily_reset: "info" };
  return map[type] || "info";
}

watch(showFavoritesOnly, () => {
  worksPage.value = 1;
  fetchWorks();
});

watch(activeTab, (tab) => {
  if (tab === "works") fetchWorks();
  if (tab === "credits") { fetchCredits(); fetchCreditsLog(); }
});

onMounted(() => {
  fetchCredits();
  fetchStyles();
});

onUnmounted(() => {
  stopPolling();
});
</script>

<style scoped>
.aipic-view {
  padding: 0;
}

.aipic-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.aipic-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: #e0e0e6;
  margin: 0;
}

.aipic-credits {
  display: flex;
  gap: 8px;
}

.aipic-tabs :deep(.el-tabs__item) {
  color: #8a8a9a;
}

.aipic-tabs :deep(.el-tabs__item.is-active) {
  color: #a5b4fc;
}

.aipic-tabs :deep(.el-tabs__active-bar) {
  background: #6366f1;
}

.create-panel {
  max-width: 720px;
}

.create-form .form-row {
  display: flex;
  gap: 16px;
}

.form-item-half {
  flex: 1;
}

.generate-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
}

.task-status {
  margin-top: 20px;
}

.task-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #e0e0e6;
}

.task-result {
  margin-top: 16px;
}

.result-image {
  max-width: 100%;
  max-height: 512px;
  border-radius: 8px;
}

.task-error {
  margin-top: 8px;
  color: #f56c6c;
  font-size: 13px;
}

.works-toolbar {
  margin-bottom: 16px;
}

.empty-state {
  text-align: center;
  padding: 60px 0;
  color: #6a6a7a;
}

.works-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.work-card {
  background: #1a1a24;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.15s;
}

.work-card:hover {
  transform: translateY(-2px);
}

.work-thumb {
  width: 100%;
  height: 200px;
  object-fit: cover;
}

.work-thumb-placeholder {
  width: 100%;
  height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #252530;
  color: #5a5a6a;
}

.work-info {
  padding: 10px;
}

.work-prompt {
  font-size: 12px;
  color: #e0e0e6;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.work-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  font-size: 11px;
  color: #6a6a7a;
}

.work-meta .is-favorite {
  color: #f59e0b;
  margin-left: auto;
  cursor: pointer;
}

.load-more {
  text-align: center;
  padding: 16px 0;
}

.credits-card {
  margin-bottom: 24px;
}

.credits-overview {
  display: flex;
  justify-content: space-around;
}

.credit-stat {
  text-align: center;
}

.credit-value {
  font-size: 28px;
  font-weight: 700;
  color: #a5b4fc;
}

.credit-label {
  font-size: 13px;
  color: #8a8a9a;
  margin-top: 4px;
}

.credits-log h4 {
  font-size: 16px;
  color: #e0e0e6;
  margin-bottom: 12px;
}

.amount-positive {
  color: #67c23a;
}

.amount-negative {
  color: #f56c6c;
}

.style-category-tag {
  margin-left: 8px;
}
</style>
