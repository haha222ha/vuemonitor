<template>
  <div class="ai-analysis">
    <div class="page-toolbar">
      <h3>AI分析中心</h3>
      <div class="toolbar-right">
        <el-tag v-if="auth.userPlan === 'free'" type="info">免费版 — 基础趋势描述</el-tag>
        <el-tag v-else-if="auth.userPlan === 'pro'" type="primary">Pro — 趋势评分</el-tag>
        <el-tag v-else-if="auth.userPlan === 'premium'" type="warning">Premium — 完整AI决策</el-tag>
        <el-tag v-else type="danger">Enterprise — 全功能</el-tag>
        <el-tag v-if="quotaInfo.limit > 0" size="small" style="margin-left: 8px;">
          今日剩余 {{ Math.max(0, quotaInfo.limit - quotaInfo.used) }}/{{ quotaInfo.limit }}
        </el-tag>
        <el-tag v-else-if="quotaInfo.limit === -1" size="small" type="success" style="margin-left: 8px;">无限次</el-tag>
      </div>
    </div>

    <el-row :gutter="20">
      <el-col :span="16">
        <div class="panel">
          <div class="panel-header">
            <h4>选择分析商品</h4>
          </div>
          <el-select
            v-model="selectedProduct"
            placeholder="选择要分析的商品"
            filterable
            style="width: 100%; margin-bottom: 16px"
            @change="onProductSelect"
          >
            <el-option v-for="p in products" :key="p.id" :label="`${p.product_name || p.name} (${platformLabel(p.platform)})`" :value="p.id" />
          </el-select>

          <div v-if="selectedProduct" class="analysis-type-bar">
            <span class="type-label">分析类型：</span>
            <el-radio-group v-model="analysisType" size="small" @change="onTypeChange">
              <el-radio-button value="basic_analysis">基础分析</el-radio-button>
              <el-radio-button v-if="auth.userPlan !== 'free'" value="trend_score">趋势评分</el-radio-button>
              <el-radio-button v-if="auth.userPlan === 'premium' || auth.userPlan === 'enterprise'" value="prediction">爆品预测</el-radio-button>
              <el-radio-button v-if="auth.userPlan === 'premium' || auth.userPlan === 'enterprise'" value="risk_warning">风险预警</el-radio-button>
            </el-radio-group>
            <el-button type="primary" size="small" :loading="analysisLoading" @click="runAnalysis" style="margin-left: auto;">
              {{ analysisLoading ? '分析中...' : '开始分析' }}
            </el-button>
          </div>

          <div v-if="!selectedProduct" class="empty-hint">
            <p>请先选择一个商品进行AI分析</p>
          </div>

          <div v-else-if="analysisLoading" class="loading-hint">
            <el-icon class="is-loading"><Loading /></el-icon>
            <p>AI分析中，请稍候...</p>
          </div>

          <div v-else-if="gateError" class="gate-error">
            <el-icon :size="32" color="#f59e0b"><WarningFilled /></el-icon>
            <p class="gate-msg">{{ gateError }}</p>
            <el-button type="primary" size="small" @click="$router.push('/pricing')">查看升级方案</el-button>
          </div>

          <div v-else-if="analysisResult" class="analysis-result">
            <div v-if="auth.userPlan === 'free'" class="tier-free">
              <div class="result-card">
                <h4>趋势描述</h4>
                <p class="trend-text">{{ extractField('summary') || '该商品近期数据暂无显著变化' }}</p>
              </div>
              <div v-if="extractField('strengths')" class="result-card" style="margin-top: 12px;">
                <h4>优势</h4>
                <p class="trend-text">{{ extractField('strengths') }}</p>
              </div>
              <div v-if="extractField('weaknesses')" class="result-card" style="margin-top: 12px;">
                <h4>不足</h4>
                <p class="trend-text">{{ extractField('weaknesses') }}</p>
              </div>
              <div v-if="extractField('suggestion')" class="result-card" style="margin-top: 12px;">
                <h4>建议</h4>
                <p class="trend-text">{{ extractField('suggestion') }}</p>
              </div>
              <div class="upgrade-hint">
                <p>升级 Pro 查看趋势评分和历史对比</p>
                <p>升级 Premium 解锁爆品预测和风险预警</p>
                <el-button type="primary" size="small" @click="$router.push('/pricing')">查看方案</el-button>
              </div>
            </div>

            <div v-else-if="auth.userPlan === 'pro'" class="tier-pro">
              <el-row :gutter="16">
                <el-col :span="12">
                  <div class="result-card">
                    <h4>趋势评分</h4>
                    <div class="score-display">
                      <span class="score-number">{{ extractField('trend_score') || 0 }}</span>
                      <span class="score-max">/100</span>
                    </div>
                    <el-rate :model-value="Math.round((extractField('trend_score') || 0) / 20)" disabled />
                  </div>
                </el-col>
                <el-col :span="12">
                  <div class="result-card">
                    <h4>趋势方向</h4>
                    <div class="direction-display">
                      <span :class="['direction-icon', trendDirectionClass]">{{ trendDirectionIcon }}</span>
                      <span class="direction-text">{{ trendDirectionLabel }}</span>
                    </div>
                  </div>
                </el-col>
              </el-row>
              <div v-if="extractField('key_factors')" class="result-card" style="margin-top: 16px;">
                <h4>关键因素</h4>
                <div class="factors-list">
                  <template v-if="Array.isArray(extractField('key_factors'))">
                    <el-tag v-for="(f, i) in extractField('key_factors')" :key="i" size="small" style="margin: 2px 4px;">{{ f }}</el-tag>
                  </template>
                  <p v-else>{{ extractField('key_factors') }}</p>
                </div>
              </div>
              <div v-if="extractField('prediction')" class="result-card" style="margin-top: 12px;">
                <h4>短期预测</h4>
                <p class="trend-text">{{ extractField('prediction') }}</p>
              </div>
              <div class="upgrade-hint">
                <p>升级 Premium 解锁爆品预测 + 风险预警 + 多维评分</p>
                <el-button type="primary" size="small" @click="$router.push('/pricing')">升级 Premium</el-button>
              </div>
            </div>

            <div v-else class="tier-premium">
              <template v-if="analysisType === 'prediction' || analysisType === 'basic_analysis'">
                <el-row :gutter="16">
                  <el-col :span="8">
                    <div class="result-card highlight">
                      <h4>爆品概率</h4>
                      <div class="big-number accent">{{ extractField('explosion_score') || 0 }}</div>
                      <div class="sub-label">/100</div>
                    </div>
                  </el-col>
                  <el-col :span="8">
                    <div class="result-card">
                      <h4>潜力等级</h4>
                      <el-tag :type="potentialTagType(extractField('potential_level'))" size="large">
                        {{ potentialLabel(extractField('potential_level')) }}
                      </el-tag>
                    </div>
                  </el-col>
                  <el-col :span="8">
                    <h4>增长指标</h4>
                    <div class="result-card">
                      <div class="factors-list">
                        <template v-if="Array.isArray(extractField('growth_indicators'))">
                          <el-tag v-for="(g, i) in extractField('growth_indicators')" :key="i" size="small" type="success" style="margin: 2px 4px;">{{ g }}</el-tag>
                        </template>
                        <p v-else>{{ extractField('growth_indicators') || '暂无' }}</p>
                      </div>
                    </div>
                  </el-col>
                </el-row>
                <div v-if="extractField('risk_factors')" class="result-card" style="margin-top: 16px;">
                  <h4>风险因素</h4>
                  <div class="factors-list">
                    <template v-if="Array.isArray(extractField('risk_factors'))">
                      <el-tag v-for="(r, i) in extractField('risk_factors')" :key="i" size="small" type="danger" style="margin: 2px 4px;">{{ r }}</el-tag>
                    </template>
                    <p v-else>{{ extractField('risk_factors') }}</p>
                  </div>
                </div>
                <div v-if="extractField('recommended_action')" class="result-card" style="margin-top: 12px;">
                  <h4>建议操作</h4>
                  <p class="trend-text">{{ extractField('recommended_action') }}</p>
                </div>
              </template>

              <template v-else-if="analysisType === 'risk_warning'">
                <el-row :gutter="16">
                  <el-col :span="8">
                    <div class="result-card" :class="{ 'risk-high': extractField('risk_level') === 'high' }">
                      <h4>风险等级</h4>
                      <el-tag :type="riskTagType(extractField('risk_level'))" size="large">
                        {{ riskLevelLabel(extractField('risk_level')) }}
                      </el-tag>
                    </div>
                  </el-col>
                  <el-col :span="16">
                    <div class="result-card">
                      <h4>风险类型</h4>
                      <div class="factors-list">
                        <template v-if="Array.isArray(extractField('risk_types'))">
                          <el-tag v-for="(rt, i) in extractField('risk_types')" :key="i" size="small" type="warning" style="margin: 2px 4px;">{{ rt }}</el-tag>
                        </template>
                        <p v-else>{{ extractField('risk_types') || '暂无' }}</p>
                      </div>
                    </div>
                  </el-col>
                </el-row>
                <div v-if="extractField('risk_details')" class="result-card" style="margin-top: 16px;">
                  <h4>风险详情</h4>
                  <p class="trend-text">{{ extractField('risk_details') }}</p>
                </div>
                <div v-if="extractField('mitigation_suggestions')" class="result-card" style="margin-top: 12px;">
                  <h4>缓解建议</h4>
                  <div class="factors-list">
                    <template v-if="Array.isArray(extractField('mitigation_suggestions'))">
                      <el-tag v-for="(ms, i) in extractField('mitigation_suggestions')" :key="i" size="small" type="success" style="margin: 2px 4px;">{{ ms }}</el-tag>
                    </template>
                    <p v-else>{{ extractField('mitigation_suggestions') }}</p>
                  </div>
                </div>
              </template>

              <template v-else>
                <el-row :gutter="16">
                  <el-col :span="12">
                    <div class="result-card">
                      <h4>趋势评分</h4>
                      <div class="score-display">
                        <span class="score-number">{{ extractField('trend_score') || 0 }}</span>
                        <span class="score-max">/100</span>
                      </div>
                    </div>
                  </el-col>
                  <el-col :span="12">
                    <div class="result-card">
                      <h4>趋势方向</h4>
                      <div class="direction-display">
                        <span :class="['direction-icon', trendDirectionClass]">{{ trendDirectionIcon }}</span>
                        <span class="direction-text">{{ trendDirectionLabel }}</span>
                      </div>
                    </div>
                  </el-col>
                </el-row>
                <div v-if="extractField('key_factors')" class="result-card" style="margin-top: 16px;">
                  <h4>关键因素</h4>
                  <div class="factors-list">
                    <template v-if="Array.isArray(extractField('key_factors'))">
                      <el-tag v-for="(f, i) in extractField('key_factors')" :key="i" size="small" style="margin: 2px 4px;">{{ f }}</el-tag>
                    </template>
                    <p v-else>{{ extractField('key_factors') }}</p>
                  </div>
                </div>
                <div v-if="extractField('prediction')" class="result-card" style="margin-top: 12px;">
                  <h4>短期预测</h4>
                  <p class="trend-text">{{ extractField('prediction') }}</p>
                </div>
              </template>
            </div>
          </div>

          <div v-else-if="selectedProduct && !analysisLoading" class="empty-hint">
            <p>点击"开始分析"获取AI分析结果</p>
          </div>
        </div>
      </el-col>

      <el-col :span="8">
        <div class="panel">
          <div class="panel-header-row">
            <h4>分析历史</h4>
            <el-button size="small" text @click="fetchHistory">
              <el-icon><Refresh /></el-icon>
            </el-button>
          </div>
          <div v-if="historyLoading" style="text-align: center; padding: 20px;">
            <el-icon class="is-loading"><Loading /></el-icon>
          </div>
          <div v-else-if="history.length" class="history-list">
            <div v-for="h in history" :key="h.id" class="history-item" @click="loadHistory(h)">
              <div class="history-top">
                <el-tag size="small" :type="analysisTypeTag(h.analysis_type)">{{ analysisTypeLabel(h.analysis_type) }}</el-tag>
                <span class="history-time">{{ formatTime(h.created_at) }}</span>
              </div>
              <div class="history-product">{{ getProductName(h.product_id) }}</div>
              <div v-if="h.confidence" class="history-confidence">
                置信度: {{ Math.round(h.confidence * 100) }}%
              </div>
            </div>
          </div>
          <div v-else class="empty-hint"><p>暂无分析记录</p></div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { useAuthStore } from "../../stores/auth";
import api from "../../utils/api";
import { Loading, Refresh, WarningFilled } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";

const auth = useAuthStore();
const products = ref<any[]>([]);
const selectedProduct = ref("");
const analysisType = ref("basic_analysis");
const analysisLoading = ref(false);
const analysisResult = ref<any>(null);
const gateError = ref("");
const history = ref<any[]>([]);
const historyLoading = ref(false);

const quotaInfo = reactive({ used: 0, limit: 0 });

const planQuotaMap: Record<string, number> = {
  free: 5,
  pro: 50,
  premium: -1,
  enterprise: -1,
};

function platformLabel(p: string) {
  const map: Record<string, string> = { xhs: "小红书", taobao: "淘宝", jd: "京东", pdd: "拼多多", douyin: "抖音" };
  return map[p] || p || "";
}

function extractField(key: string): any {
  if (!analysisResult.value) return null;
  const r = analysisResult.value;
  if (r[key] !== undefined) return r[key];
  if (r.result && typeof r.result === "object" && r.result[key] !== undefined) return r.result[key];
  return null;
}

const trendDirectionIcon = computed(() => {
  const d = extractField("trend_direction");
  if (d === "up") return "↑";
  if (d === "down") return "↓";
  return "→";
});

const trendDirectionClass = computed(() => {
  const d = extractField("trend_direction");
  if (d === "up") return "dir-up";
  if (d === "down") return "dir-down";
  return "dir-stable";
});

const trendDirectionLabel = computed(() => {
  const d = extractField("trend_direction");
  if (d === "up") return "上升趋势";
  if (d === "down") return "下降趋势";
  return "平稳";
});

function riskTagType(level: string) {
  const map: Record<string, string> = { high: "danger", medium: "warning", low: "success", 高: "danger", 中: "warning", 低: "success" };
  return (map[level] || "info") as any;
}

function riskLevelLabel(level: string) {
  const map: Record<string, string> = { high: "高风险", medium: "中风险", low: "低风险", 高: "高风险", 中: "中风险", 低: "低风险" };
  return map[level] || level || "未知";
}

function potentialTagType(level: string) {
  const map: Record<string, string> = { high: "danger", medium: "warning", low: "info" };
  return (map[level] || "info") as any;
}

function potentialLabel(level: string) {
  const map: Record<string, string> = { high: "高潜力", medium: "中潜力", low: "低潜力" };
  return map[level] || level || "未知";
}

function analysisTypeTag(type: string) {
  const map: Record<string, string> = { basic_analysis: "", trend_score: "primary", prediction: "warning", risk_warning: "danger", report: "success" };
  return (map[type] || "info") as any;
}

function analysisTypeLabel(type: string) {
  const map: Record<string, string> = { basic_analysis: "基础分析", trend_score: "趋势评分", prediction: "爆品预测", risk_warning: "风险预警", report: "分析报告" };
  return map[type] || type;
}

function formatTime(iso: string) {
  if (!iso) return "";
  const d = new Date(iso);
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, "0")}:${d.getMinutes().toString().padStart(2, "0")}`;
}

function getProductName(productId: string) {
  const p = products.value.find((item) => item.id === productId);
  return p?.product_name || p?.name || productId?.slice(0, 8) || "未知商品";
}

function onTypeChange() {
  analysisResult.value = null;
  gateError.value = "";
}

async function onProductSelect() {
  analysisResult.value = null;
  gateError.value = "";
  if (auth.userPlan === "free") {
    analysisType.value = "basic_analysis";
  } else if (auth.userPlan === "pro") {
    if (analysisType.value === "prediction" || analysisType.value === "risk_warning") {
      analysisType.value = "trend_score";
    }
  }
}

async function runAnalysis() {
  if (!selectedProduct.value) return;
  analysisLoading.value = true;
  analysisResult.value = null;
  gateError.value = "";
  try {
    const { data } = await api.post("/ai/analyze", {
      product_id: selectedProduct.value,
      analysis_type: analysisType.value,
    });
    const result = data?.data || data;
    analysisResult.value = result;
    quotaInfo.used += 1;
    fetchHistory();
  } catch (e: any) {
    const resp = e?.response?.data;
    if (resp?.code === 42010 || resp?.code === 42011) {
      gateError.value = resp.message || "当前套餐不支持此功能";
    } else if (resp?.message) {
      ElMessage.error(resp.message);
    } else {
      ElMessage.error("分析请求失败，请稍后重试");
    }
  } finally {
    analysisLoading.value = false;
  }
}

function loadHistory(h: any) {
  selectedProduct.value = h.product_id || "";
  analysisResult.value = h.result || null;
  analysisType.value = h.analysis_type || "basic_analysis";
  gateError.value = "";
}

async function fetchHistory() {
  historyLoading.value = true;
  try {
    const { data } = await api.get("/ai/analyses", { params: { page_size: 20 } });
    history.value = data?.data?.items || [];
  } catch {}
  finally {
    historyLoading.value = false;
  }
}

async function fetchQuota() {
  quotaInfo.limit = planQuotaMap[auth.userPlan] ?? 5;
  try {
    const { data } = await api.get("/ai/analyses", { params: { page_size: 1 } });
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const items = data?.data?.items || [];
    let used = 0;
    for (const item of items) {
      if (item.created_at && new Date(item.created_at) >= today) used++;
    }
    quotaInfo.used = used;
  } catch {}
}

onMounted(async () => {
  try {
    const { data } = await api.get("/products", { params: { page_size: 100 } });
    products.value = data?.data?.items || [];
  } catch {}
  fetchHistory();
  fetchQuota();
});
</script>

<style scoped>
.ai-analysis {
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

.toolbar-right {
  display: flex;
  align-items: center;
}

.panel {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 20px;
}

.panel-header {
  margin-bottom: 16px;
}

.panel-header h4, .panel-header-row h4 {
  font-size: 15px;
  font-weight: 600;
  color: #fff;
  margin: 0;
}

.panel-header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.analysis-type-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  padding: 12px 16px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 8px;
  border: 1px solid rgba(255, 255, 255, 0.04);
}

.type-label {
  font-size: 13px;
  color: #8a8a9a;
  white-space: nowrap;
}

.empty-hint, .loading-hint {
  text-align: center;
  padding: 40px 0;
  color: #6a6a7a;
}

.loading-hint .el-icon {
  font-size: 24px;
  margin-bottom: 8px;
}

.gate-error {
  text-align: center;
  padding: 40px 20px;
}

.gate-msg {
  color: #f59e0b;
  font-size: 15px;
  margin: 12px 0;
}

.result-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 10px;
  padding: 16px;
}

.result-card.highlight {
  border-color: rgba(99, 102, 241, 0.3);
  background: rgba(99, 102, 241, 0.06);
}

.result-card.risk-high {
  border-color: rgba(239, 68, 68, 0.3);
  background: rgba(239, 68, 68, 0.06);
}

.result-card h4 {
  font-size: 13px;
  color: #6a6a7a;
  margin: 0 0 8px;
}

.trend-text {
  font-size: 15px;
  color: #e0e0e6;
  line-height: 1.6;
}

.score-display {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.score-number {
  font-size: 36px;
  font-weight: 800;
  color: #fff;
}

.score-max {
  font-size: 14px;
  color: #6a6a7a;
}

.direction-display {
  display: flex;
  align-items: center;
  gap: 8px;
}

.direction-icon {
  font-size: 28px;
  font-weight: 800;
}

.direction-icon.dir-up { color: #22c55e; }
.direction-icon.dir-down { color: #ef4444; }
.direction-icon.dir-stable { color: #f59e0b; }

.direction-text {
  font-size: 16px;
  color: #e0e0e6;
}

.big-number {
  font-size: 32px;
  font-weight: 800;
  color: #fff;
}

.big-number.accent {
  color: #6366f1;
}

.sub-label {
  font-size: 12px;
  color: #6a6a7a;
  margin-top: 2px;
}

.factors-list {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
}

.factors-list p {
  font-size: 14px;
  color: #e0e0e6;
  line-height: 1.5;
}

.upgrade-hint {
  text-align: center;
  padding: 20px 0;
  margin-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.upgrade-hint p {
  color: #6a6a7a;
  font-size: 13px;
  margin: 0 0 8px;
}

.history-list {
  max-height: 500px;
  overflow-y: auto;
}

.history-item {
  padding: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  cursor: pointer;
  transition: background 0.2s;
}

.history-item:hover {
  background: rgba(255, 255, 255, 0.04);
}

.history-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.history-product {
  font-size: 14px;
  color: #e0e0e6;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-time {
  font-size: 12px;
  color: #4a4a5a;
}

.history-confidence {
  font-size: 12px;
  color: #6366f1;
  margin-top: 2px;
}
</style>
