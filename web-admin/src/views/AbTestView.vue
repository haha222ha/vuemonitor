<template>
  <div class="ab-test-page">
    <div class="page-head">
      <h2>A/B 测试对比</h2>
      <div class="head-actions">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          :clearable="false"
          style="width: 280px"
        />
        <el-button @click="loadAll" :loading="loading">刷新</el-button>
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

    <!-- 累计节省费用卡片 -->
    <div class="kpi-cards" v-loading="loading">
      <el-card shadow="never" class="kpi-card">
        <div class="kpi-label">A 模式累计成本</div>
        <div class="kpi-value">¥{{ formatCny(totalA?.sum_cost) }}</div>
        <div class="kpi-sub">{{ totalA?.ranking_count || 0 }} 条记录 · {{ totalA?.sum_tokens || 0 }} tokens</div>
      </el-card>
      <el-card shadow="never" class="kpi-card kpi-b">
        <div class="kpi-label">B 模式累计成本</div>
        <div class="kpi-value">¥{{ formatCny(totalB?.sum_cost) }}</div>
        <div class="kpi-sub">{{ totalB?.ranking_count || 0 }} 条记录 · {{ totalB?.sum_tokens || 0 }} tokens</div>
      </el-card>
      <el-card shadow="never" class="kpi-card" :class="savingsPct >= 60 ? 'success' : 'warning'">
        <div class="kpi-label">累计节省</div>
        <div class="kpi-value">¥{{ formatCny(savingsCny) }}</div>
        <div class="kpi-sub">{{ savingsPct }}% · {{ avgDurationReductionPct }}% 耗时下降</div>
      </el-card>
      <el-card shadow="never" class="kpi-card">
        <div class="kpi-label">测试天数</div>
        <div class="kpi-value">{{ dailyRows.length }}</div>
        <div class="kpi-sub">{{ testDates.length }} 个有数据日</div>
      </el-card>
    </div>

    <!-- 判定结论 -->
    <el-card v-if="verdict" shadow="never" class="verdict-card">
      <el-alert
        :type="verdict.type"
        :closable="false"
        show-icon
        :title="verdict.title"
      >
        <div class="verdict-detail">{{ verdict.detail }}</div>
      </el-alert>
    </el-card>

    <!-- 按日聚合表格 -->
    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="card-head">
          <span>按日聚合对比</span>
          <el-button text @click="loadAggregate" :loading="loadingAggregate">刷新聚合</el-button>
        </div>
      </template>
      <el-table :data="dailyRows" stripe size="small" v-loading="loadingAggregate">
        <el-table-column prop="test_date" label="日期" width="110" fixed />
        <el-table-column label="A 模式" align="center">
          <el-table-column prop="a_tokens" label="Tokens" width="100" align="right">
            <template #default="{ row }">{{ row.a_tokens?.toLocaleString() || '—' }}</template>
          </el-table-column>
          <el-table-column prop="a_cost" label="成本(¥)" width="90" align="right">
            <template #default="{ row }">{{ formatCny(row.a_cost) }}</template>
          </el-table-column>
          <el-table-column prop="a_duration" label="平均耗时(ms)" width="110" align="right">
            <template #default="{ row }">{{ row.a_duration ? Math.round(row.a_duration).toLocaleString() : '—' }}</template>
          </el-table-column>
          <el-table-column prop="a_count" label="榜单数" width="80" align="right" />
        </el-table-column>
        <el-table-column label="B 模式" align="center">
          <el-table-column prop="b_tokens" label="Tokens" width="100" align="right">
            <template #default="{ row }">{{ row.b_tokens?.toLocaleString() || '—' }}</template>
          </el-table-column>
          <el-table-column prop="b_cost" label="成本(¥)" width="90" align="right">
            <template #default="{ row }">{{ formatCny(row.b_cost) }}</template>
          </el-table-column>
          <el-table-column prop="b_duration" label="平均耗时(ms)" width="110" align="right">
            <template #default="{ row }">{{ row.b_duration ? Math.round(row.b_duration).toLocaleString() : '—' }}</template>
          </el-table-column>
          <el-table-column prop="b_count" label="榜单数" width="80" align="right" />
        </el-table-column>
        <el-table-column label="节省率" width="100" align="right">
          <template #default="{ row }">
            <el-tag v-if="row.savings_pct !== null" :type="row.savings_pct >= 60 ? 'success' : 'warning'" size="small">
              {{ row.savings_pct }}%
            </el-tag>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button text size="small" @click="previewDate(row.test_date)">并排预览</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 明细表格 + 评分录入 -->
    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="card-head">
          <span>明细指标与人工评分</span>
          <div>
            <el-select v-model="filterRankingKey" placeholder="筛选榜单" clearable size="small" style="width: 200px; margin-right: 8px">
              <el-option v-for="k in rankingKeys" :key="k" :label="k" :value="k" />
            </el-select>
            <el-button text @click="loadMetrics" :loading="loadingMetrics">刷新明细</el-button>
          </div>
        </div>
      </template>
      <el-table :data="metricRows" stripe size="small" v-loading="loadingMetrics" max-height="600">
        <el-table-column prop="test_date" label="日期" width="110" fixed />
        <el-table-column prop="ranking_key" label="榜单" min-width="160">
          <template #default="{ row }">
            <code>{{ row.ranking_key }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="mode" label="模式" width="70">
          <template #default="{ row }">
            <el-tag :type="row.mode === 'A' ? 'danger' : 'success'" size="small">{{ row.mode }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="total_tokens" label="Tokens" width="100" align="right">
          <template #default="{ row }">{{ row.total_tokens?.toLocaleString() || '—' }}</template>
        </el-table-column>
        <el-table-column prop="cost_cny" label="成本(¥)" width="90" align="right">
          <template #default="{ row }">{{ formatCny(row.cost_cny) }}</template>
        </el-table-column>
        <el-table-column prop="duration_ms" label="耗时(ms)" width="100" align="right">
          <template #default="{ row }">{{ row.duration_ms?.toLocaleString() || '—' }}</template>
        </el-table-column>
        <el-table-column label="准确率" width="120">
          <template #default="{ row }">
            <el-rate v-model="row.accuracy_score" :max="5" size="small" @change="saveScore(row, 'accuracy')" />
          </template>
        </el-table-column>
        <el-table-column label="洞察分" width="120">
          <template #default="{ row }">
            <el-rate v-model="row.insight_score" :max="5" size="small" @change="saveScore(row, 'insight')" />
          </template>
        </el-table-column>
        <el-table-column label="幻觉" width="80">
          <template #default="{ row }">
            <el-switch v-model="row.hallucination" :active-value="1" :inactive-value="0" @change="saveScore(row, 'hallucination')" />
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 并排预览抽屉 -->
    <el-drawer v-model="previewVisible" size="90%" :title="`A/B 报告对比 — ${previewDateStr}`" direction="rtl">
      <div class="preview-container" v-loading="loadingPreview">
        <div class="preview-col">
          <div class="preview-head mode-a">A 模式（100% AI）</div>
          <div class="preview-body" v-html="renderMarkdown(previewA?.daily_overview?.content)"></div>
          <el-divider>方向解读 ({{ previewA?.direction_advices?.length || 0 }})</el-divider>
          <div v-for="(d, i) in previewA?.direction_advices || []" :key="i" class="preview-direction">
            <h4>{{ d.title }}</h4>
            <div v-html="renderMarkdown(d.content)"></div>
          </div>
        </div>
        <div class="preview-col">
          <div class="preview-head mode-b">B 模式（80% 程序 + 20% AI）</div>
          <div class="preview-body" v-html="renderMarkdown(previewB?.daily_overview?.content)"></div>
          <el-divider>方向解读 ({{ previewB?.direction_advices?.length || 0 }})</el-divider>
          <div v-for="(d, i) in previewB?.direction_advices || []" :key="i" class="preview-direction">
            <h4>{{ d.title }}</h4>
            <div v-html="renderMarkdown(d.content)"></div>
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { ElMessage } from "element-plus";
import api from "../utils/api";
import { useMemberCloudStore } from "../stores/memberCloud";

interface MetricRow {
  id: number;
  test_date: string;
  ranking_key: string;
  mode: "A" | "B";
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_cny: number;
  duration_ms: number;
  accuracy_score: number | null;
  insight_score: number | null;
  hallucination: number;
  report_path: string;
  model: string;
  extra_json: string | null;
  created_at: string;
}

interface DailyAggregate {
  test_date: string;
  mode: "A" | "B";
  ranking_count: number;
  sum_tokens: number;
  sum_cost: number;
  avg_duration_ms: number;
  avg_accuracy: number | null;
  avg_insight: number | null;
  hallucination_count: number;
}

interface DailyRow {
  test_date: string;
  a_tokens: number | null;
  a_cost: number | null;
  a_duration: number | null;
  a_count: number | null;
  b_tokens: number | null;
  b_cost: number | null;
  b_duration: number | null;
  b_count: number | null;
  savings_pct: number | null;
}

interface Advice {
  report_date: string;
  daily_overview?: { title?: string; summary?: string; content?: string };
  direction_advices?: Array<{ key?: string; title?: string; summary?: string; content?: string; key_points?: string[] }>;
  cross_summary?: { title?: string; content?: string; action_items?: string[] };
  disclaimer?: string;
}

const cloudStore = useMemberCloudStore();
const cloudOnline = computed(() => cloudStore.status?.online);

const today = new Date();
const sevenDaysAgo = new Date(today.getTime() - 6 * 24 * 60 * 60 * 1000);
const fmt = (d: Date) => d.toISOString().slice(0, 10);

const dateRange = ref<[string, string]>([fmt(sevenDaysAgo), fmt(today)]);
const loading = ref(false);
const loadingMetrics = ref(false);
const loadingAggregate = ref(false);
const loadingPreview = ref(false);

const metricRows = ref<MetricRow[]>([]);
const dailyAgg = ref<DailyAggregate[]>([]);
const testDates = ref<string[]>([]);
const filterRankingKey = ref<string>("");

const previewVisible = ref(false);
const previewDateStr = ref("");
const previewA = ref<Advice | null>(null);
const previewB = ref<Advice | null>(null);

const rankingKeys = computed(() => {
  const s = new Set<string>();
  metricRows.value.forEach((r) => s.add(r.ranking_key));
  return Array.from(s).sort();
});

const filteredMetrics = computed(() => {
  if (!filterRankingKey.value) return metricRows.value;
  return metricRows.value.filter((r) => r.ranking_key === filterRankingKey.value);
});

const totalA = computed(() => {
  return dailyAgg.value.find((d) => d.mode === "A");
});
const totalB = computed(() => {
  return dailyAgg.value.find((d) => d.mode === "B");
});

const savingsCny = computed(() => {
  const a = totalA.value?.sum_cost || 0;
  const b = totalB.value?.sum_cost || 0;
  return Math.round((a - b) * 10000) / 10000;
});

const savingsPct = computed(() => {
  const a = totalA.value?.sum_cost || 0;
  if (a <= 0) return 0;
  return Math.round(((a - (totalB.value?.sum_cost || 0)) / a) * 10000) / 100;
});

const avgDurationReductionPct = computed(() => {
  const a = totalA.value?.avg_duration_ms || 0;
  const b = totalB.value?.avg_duration_ms || 0;
  if (a <= 0) return 0;
  return Math.round(((a - b) / a) * 10000) / 100;
});

const dailyRows = computed<DailyRow[]>(() => {
  const byDate: Record<string, DailyRow> = {};
  for (const d of dailyAgg.value) {
    const row = byDate[d.test_date] ||= {
      test_date: d.test_date,
      a_tokens: null, a_cost: null, a_duration: null, a_count: null,
      b_tokens: null, b_cost: null, b_duration: null, b_count: null,
      savings_pct: null,
    };
    if (d.mode === "A") {
      row.a_tokens = d.sum_tokens;
      row.a_cost = d.sum_cost;
      row.a_duration = d.avg_duration_ms;
      row.a_count = d.ranking_count;
    } else {
      row.b_tokens = d.sum_tokens;
      row.b_cost = d.sum_cost;
      row.b_duration = d.avg_duration_ms;
      row.b_count = d.ranking_count;
    }
  }
  const list = Object.values(byDate).sort((a, b) => a.test_date > b.test_date ? -1 : 1);
  for (const r of list) {
    if (r.a_cost && r.a_cost > 0 && r.b_cost !== null) {
      r.savings_pct = Math.round(((r.a_cost - (r.b_cost || 0)) / r.a_cost) * 10000) / 100;
    }
  }
  return list;
});

const verdict = computed(() => {
  if (dailyRows.value.length < 7) return null;
  const savings = savingsPct.value;
  const aAcc = totalA.value?.avg_accuracy;
  const bAcc = totalB.value?.avg_insight;
  if (savings >= 60) {
    if (!aAcc || !bAcc) {
      return {
        type: "info" as const,
        title: `B 模式成本节省 ${savings}% — 待人工评分`,
        detail: "请完成抽检评分后再做最终判定。",
      };
    }
    if (bAcc >= aAcc) {
      return {
        type: "success" as const,
        title: `B 胜出 — 成本节省 ${savings}%，准确率持平或更优`,
        detail: "建议全量切换 B 模式（80% 程序 + 20% AI）。",
      };
    }
    return {
      type: "warning" as const,
      title: `B 成本节省 ${savings}% 但准确率低于 A`,
      detail: "建议调整 B 模式 prompt 后再测 7 天。",
    };
  }
  return {
    type: "error" as const,
    title: `A 胜出 — B 节省率仅 ${savings}%（< 60%）`,
    detail: "保留 A 模式，Feature Engine 仅用于数据层。",
  };
});

function formatCny(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return v.toFixed(4);
}

function renderMarkdown(s: string | undefined): string {
  if (!s) return '<p style="color:#999">（无内容）</p>';
  // 极简 markdown 渲染：标题 / 加粗 / 引用 / 代码 / 列表
  let html = s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
  html = html.replace(/^### (.+)$/gm, '<h4>$1</h4>');
  html = html.replace(/^## (.+)$/gm, '<h3>$1</h3>');
  html = html.replace(/^# (.+)$/gm, '<h2>$1</h2>');
  html = html.replace(/^&gt; (.+)$/gm, '<blockquote>$1</blockquote>');
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/`(.+?)`/g, "<code>$1</code>");
  html = html.replace(/^- (.+)$/gm, "<li>$1</li>");
  html = html.replace(/(<li>[\s\S]+?<\/li>)/g, "<ul>$1</ul>");
  html = html.replace(/\n\n/g, "</p><p>");
  return `<p>${html}</p>`;
}

async function loadAll() {
  loading.value = true;
  try {
    await cloudStore.fetchStatus();
    await Promise.all([loadMetrics(), loadAggregate(), loadDates()]);
  } finally {
    loading.value = false;
  }
}

async function loadMetrics() {
  loadingMetrics.value = true;
  try {
    const params: Record<string, string> = {};
    if (dateRange.value?.[0]) params.date_from = dateRange.value[0];
    if (dateRange.value?.[1]) params.date_to = dateRange.value[1];
    const { data } = await api.get("/xhs-cloud/admin/ab-test/metrics", { params });
    const payload = (data as { data?: { items?: MetricRow[] } })?.data || (data as { items?: MetricRow[] });
    metricRows.value = payload.items || [];
  } catch (e: unknown) {
    ElMessage.error((e as Error)?.message || "加载明细失败");
  } finally {
    loadingMetrics.value = false;
  }
}

async function loadAggregate() {
  loadingAggregate.value = true;
  try {
    const params: Record<string, string> = {};
    if (dateRange.value?.[0]) params.date_from = dateRange.value[0];
    if (dateRange.value?.[1]) params.date_to = dateRange.value[1];
    const { data } = await api.get("/xhs-cloud/admin/ab-test/aggregate", { params });
    const payload = (data as { data?: { daily?: DailyAggregate[] } })?.data || (data as { daily?: DailyAggregate[] });
    dailyAgg.value = payload.daily || [];
  } catch (e: unknown) {
    ElMessage.error((e as Error)?.message || "加载聚合失败");
  } finally {
    loadingAggregate.value = false;
  }
}

async function loadDates() {
  try {
    const { data } = await api.get("/xhs-cloud/admin/ab-test/dates");
    const payload = (data as { data?: { dates?: string[] } })?.data || (data as { dates?: string[] });
    testDates.value = payload.dates || [];
  } catch {
    testDates.value = [];
  }
}

async function saveScore(row: MetricRow, _field: "accuracy" | "insight" | "hallucination") {
  try {
    await api.put("/xhs-cloud/admin/ab-test/score", {
      test_date: row.test_date,
      ranking_key: row.ranking_key,
      mode: row.mode,
      accuracy_score: row.accuracy_score,
      insight_score: row.insight_score,
      hallucination: row.hallucination,
    });
    ElMessage.success(`${row.test_date} ${row.ranking_key} [${row.mode}] 评分已保存`);
  } catch (e: unknown) {
    ElMessage.error((e as Error)?.message || "评分保存失败");
  }
}

async function previewDate(d: string) {
  previewDateStr.value = d;
  previewVisible.value = true;
  loadingPreview.value = true;
  previewA.value = null;
  previewB.value = null;
  try {
    const [a, b] = await Promise.all([
      api.get("/xhs-cloud/admin/ab-test/report", { params: { report_date: d, mode: "A" } }),
      api.get("/xhs-cloud/admin/ab-test/report", { params: { report_date: d, mode: "B" } }),
    ]);
    previewA.value = ((a.data as { data?: Advice })?.data || (a.data as Advice)) as Advice;
    previewB.value = ((b.data as { data?: Advice })?.data || (b.data as Advice)) as Advice;
  } catch (e: unknown) {
    ElMessage.error((e as Error)?.message || "加载报告失败");
  } finally {
    loadingPreview.value = false;
  }
}

onMounted(loadAll);
</script>

<style scoped>
.ab-test-page { padding: 0; }
.page-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.head-actions { display: flex; gap: 8px; align-items: center; }
.mb-16 { margin-bottom: 16px; }

.kpi-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px; }
.kpi-card { text-align: left; }
.kpi-label { font-size: 12px; color: var(--el-text-color-secondary); margin-bottom: 6px; }
.kpi-value { font-size: 24px; font-weight: 600; color: var(--el-text-color-primary); margin-bottom: 4px; }
.kpi-sub { font-size: 11px; color: var(--el-text-color-secondary); }
.kpi-b .kpi-value { color: #07c160; }
.kpi-card.success .kpi-value { color: #67c23a; }
.kpi-card.warning .kpi-value { color: #e6a23c; }

.verdict-card { margin-bottom: 16px; }
.verdict-detail { margin-top: 6px; font-size: 13px; color: var(--el-text-color-secondary); }

.section-card { margin-bottom: 16px; }
.card-head { display: flex; justify-content: space-between; align-items: center; }

.preview-container { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; padding: 0 16px; }
.preview-col { background: var(--el-fill-color-light); border-radius: 8px; padding: 16px; max-height: calc(100vh - 120px); overflow-y: auto; }
.preview-head { font-size: 16px; font-weight: 600; padding: 8px 12px; border-radius: 6px; margin-bottom: 12px; color: #fff; }
.preview-head.mode-a { background: #f56c6c; }
.preview-head.mode-b { background: #07c160; }
.preview-body { line-height: 1.7; font-size: 14px; }
.preview-body :deep(h2), .preview-body :deep(h3), .preview-body :deep(h4) { margin: 12px 0 6px; }
.preview-body :deep(blockquote) { border-left: 3px solid #07c160; padding-left: 12px; color: #555; margin: 8px 0; }
.preview-body :deep(code) { background: #f5f5f5; padding: 2px 6px; border-radius: 3px; font-size: 13px; }
.preview-direction { margin-top: 16px; padding-top: 12px; border-top: 1px dashed var(--el-border-color); }
.preview-direction h4 { margin: 0 0 6px; color: var(--el-text-color-primary); }
</style>
