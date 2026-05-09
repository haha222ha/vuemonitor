<template>
  <div class="ai-analysis">
    <div class="page-toolbar">
      <h3>AI分析中心</h3>
      <el-tag v-if="auth.userPlan === 'free'" type="info">免费版 — 基础趋势描述</el-tag>
      <el-tag v-else-if="auth.userPlan === 'pro'" type="primary">Pro — 趋势评分</el-tag>
      <el-tag v-else type="warning">Premium — 完整AI决策</el-tag>
    </div>

    <el-row :gutter="20">
      <el-col :span="16">
        <div class="panel">
          <div class="panel-header">
            <h4>选择分析商品</h4>
          </div>
          <el-select v-model="selectedProduct" placeholder="选择要分析的商品" style="width: 100%; margin-bottom: 16px" @change="onProductSelect">
            <el-option v-for="p in products" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>

          <div v-if="!selectedProduct" class="empty-hint">
            <p>请先选择一个商品进行AI分析</p>
          </div>

          <div v-else-if="analysisLoading" class="loading-hint">
            <el-icon class="is-loading"><Loading /></el-icon>
            <p>AI分析中...</p>
          </div>

          <div v-else-if="analysisResult" class="analysis-result">
            <div v-if="auth.userPlan === 'free'" class="tier-free">
              <div class="result-card">
                <h4>趋势描述</h4>
                <p class="trend-text">{{ analysisResult.trendDescription || "该商品近期数据暂无显著变化" }}</p>
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
                    <el-rate :model-value="Math.round((analysisResult.trendScore || 0) / 20)" disabled size="large" />
                  </div>
                </el-col>
                <el-col :span="12">
                  <div class="result-card">
                    <h4>增长概率</h4>
                    <div class="big-number">{{ analysisResult.growthProbability || 0 }}%</div>
                  </div>
                </el-col>
              </el-row>
              <div class="result-card" style="margin-top: 16px;">
                <h4>趋势描述</h4>
                <p>{{ analysisResult.trendDescription || "暂无分析结果" }}</p>
              </div>
              <div class="upgrade-hint">
                <p>升级 Premium 解锁爆品预测 + 风险预警 + 多维评分</p>
                <el-button type="primary" size="small" @click="$router.push('/pricing')">升级 Premium</el-button>
              </div>
            </div>

            <div v-else class="tier-premium">
              <el-row :gutter="16">
                <el-col :span="8">
                  <div class="result-card highlight">
                    <h4>爆品概率</h4>
                    <div class="big-number accent">{{ analysisResult.hitProbability || 0 }}%</div>
                  </div>
                </el-col>
                <el-col :span="8">
                  <div class="result-card">
                    <h4>竞争指数</h4>
                    <div class="big-number">{{ analysisResult.competitionIndex || 0 }}</div>
                  </div>
                </el-col>
                <el-col :span="8">
                  <div class="result-card">
                    <h4>风险等级</h4>
                    <el-tag :type="riskTagType(analysisResult.riskLevel)" size="large">{{ analysisResult.riskLevel || '低' }}</el-tag>
                  </div>
                </el-col>
              </el-row>
              <el-row :gutter="16" style="margin-top: 16px;">
                <el-col :span="12">
                  <div class="result-card">
                    <h4>多维评分</h4>
                    <div class="score-grid">
                      <div class="score-item"><span>流量</span><strong>{{ analysisResult.trafficScore || 0 }}</strong></div>
                      <div class="score-item"><span>增长</span><strong>{{ analysisResult.growthScore || 0 }}</strong></div>
                      <div class="score-item"><span>竞争</span><strong>{{ analysisResult.competitionScore || 0 }}</strong></div>
                    </div>
                  </div>
                </el-col>
                <el-col :span="12">
                  <div class="result-card">
                    <h4>AI建议</h4>
                    <p>{{ analysisResult.suggestion || "暂无建议" }}</p>
                  </div>
                </el-col>
              </el-row>
            </div>
          </div>
        </div>
      </el-col>

      <el-col :span="8">
        <div class="panel">
          <div class="panel-header"><h4>分析历史</h4></div>
          <div class="history-list" v-if="history.length">
            <div v-for="h in history" :key="h.id" class="history-item" @click="loadHistory(h)">
              <div class="history-name">{{ h.productName }}</div>
              <div class="history-time">{{ h.createdAt }}</div>
            </div>
          </div>
          <div v-else class="empty-hint"><p>暂无分析记录</p></div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useAuthStore } from "../../stores/auth";
import api from "../../utils/api";
import { Loading } from "@element-plus/icons-vue";

const auth = useAuthStore();
const products = ref<any[]>([]);
const selectedProduct = ref("");
const analysisLoading = ref(false);
const analysisResult = ref<any>(null);
const history = ref<any[]>([]);

function riskTagType(level: string) {
  const map: Record<string, string> = { 低: "success", 中: "warning", 高: "danger" };
  return (map[level] || "info") as any;
}

async function onProductSelect(productId: string) {
  if (!productId) return;
  analysisLoading.value = true;
  analysisResult.value = null;
  try {
    const { data } = await api.post(`/ai/analyze/${productId}`);
    analysisResult.value = data?.data || data;
  } catch (e: any) {
    analysisResult.value = { trendDescription: "该商品近期数据暂无显著变化" };
  } finally {
    analysisLoading.value = false;
  }
}

function loadHistory(h: any) {
  selectedProduct.value = h.productId;
  analysisResult.value = h.result;
}

onMounted(async () => {
  try {
    const { data } = await api.get("/products", { params: { page_size: 50 } });
    products.value = data?.data?.items || [];
  } catch {}
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

.panel {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 20px;
}

.panel-header {
  margin-bottom: 16px;
}

.panel-header h4 {
  font-size: 15px;
  font-weight: 600;
  color: #fff;
  margin: 0;
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

.big-number {
  font-size: 32px;
  font-weight: 800;
  color: #fff;
}

.big-number.accent {
  color: #6366f1;
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

.score-grid {
  display: flex;
  gap: 16px;
}

.score-item {
  flex: 1;
  text-align: center;
}

.score-item span {
  display: block;
  font-size: 12px;
  color: #6a6a7a;
  margin-bottom: 4px;
}

.score-item strong {
  font-size: 20px;
  color: #fff;
}

.history-list {
  max-height: 400px;
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

.history-name {
  font-size: 14px;
  color: #e0e0e6;
}

.history-time {
  font-size: 12px;
  color: #4a4a5a;
  margin-top: 4px;
}
</style>
