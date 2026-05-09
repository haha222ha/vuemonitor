<template>
  <div class="dashboard-home">
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <div class="stat-card stat-card--indigo">
          <div class="stat-icon-wrap">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="M18.7 8l-5.1 5.2-2.8-2.7L7 14.3"/></svg>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ animatedStats.productCount }}</div>
            <div class="stat-label">监控商品</div>
            <div class="stat-sub" v-if="stats.activeProductCount > 0">{{ stats.activeProductCount }} 活跃</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card stat-card--green">
          <div class="stat-icon-wrap">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>
          </div>
          <div class="stat-info">
            <div class="stat-value" :class="trendClass">{{ stats.todayTrend }}</div>
            <div class="stat-label">今日趋势</div>
            <div class="stat-sub">
              <span class="trend-up">↑{{ stats.trendUpCount }}</span> /
              <span class="trend-down">↓{{ stats.trendDownCount }}</span>
            </div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card stat-card--amber">
          <div class="stat-icon-wrap">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ animatedStats.aiRecommendations }}</div>
            <div class="stat-label">AI推荐</div>
            <div class="stat-sub" v-if="stats.todayAiCount > 0">今日 {{ stats.todayAiCount }} 次</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card stat-card--red">
          <div class="stat-icon-wrap">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ animatedStats.riskAlerts }}</div>
            <div class="stat-label">风险提示</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="16">
        <div class="panel">
          <div class="panel-header">
            <h3>商品监控列表</h3>
            <el-button type="primary" size="small" @click="$router.push('/dashboard/monitor')">查看全部</el-button>
          </div>
          <el-table :data="recentProducts" stripe style="width: 100%" empty-text="暂无监控商品" :header-cell-style="{ background: 'rgba(255,255,255,0.02)', color: '#8a8a9a', borderColor: 'rgba(255,255,255,0.04)' }">
            <el-table-column label="商品" min-width="220">
              <template #default="{ row }">
                <div class="product-cell">
                  <div v-if="row.image_url" class="product-thumb" :style="{ backgroundImage: `url(${row.image_url})` }"></div>
                  <div v-else class="product-thumb product-thumb--placeholder">{{ platformLabel(row.platform)[0] }}</div>
                  <div class="product-info">
                    <div class="product-name">{{ row.name }}</div>
                    <el-tag size="small" :type="platformTagType(row.platform)">{{ platformLabel(row.platform) }}</el-tag>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="价格" width="100" align="right">
              <template #default="{ row }">
                <span v-if="row.price" class="price-text">¥{{ row.price }}</span>
                <span v-else class="muted">—</span>
              </template>
            </el-table-column>
            <el-table-column label="趋势" width="100" align="center">
              <template #default="{ row }">
                <span :class="['trend-badge', row.trend > 0 ? 'trend-badge--up' : row.trend < 0 ? 'trend-badge--down' : 'trend-badge--flat']">
                  {{ row.trend > 0 ? '↑' : row.trend < 0 ? '↓' : '—' }} {{ Math.abs(row.trend || 0) }}%
                </span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="80" align="center">
              <template #default="{ row }">
                <span :class="['status-dot', row.is_active ? 'status-dot--active' : 'status-dot--inactive']"></span>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div class="panel" style="margin-top: 20px;" v-if="Object.keys(platformDist).length > 0">
          <div class="panel-header">
            <h3>平台分布</h3>
          </div>
          <div class="platform-bars">
            <div v-for="(count, platform) in platformDist" :key="platform" class="platform-bar-row">
              <div class="platform-bar-label">{{ platformLabel(platform as string) }}</div>
              <div class="platform-bar-track">
                <div class="platform-bar-fill" :class="`platform-bar-fill--${platform}`" :style="{ width: barWidth(count) }"></div>
              </div>
              <div class="platform-bar-count">{{ count }}</div>
            </div>
          </div>
        </div>
      </el-col>

      <el-col :span="8">
        <div class="panel">
          <div class="panel-header">
            <h3>采集状态</h3>
            <div class="collect-status-tag">
              <span :class="['pulse-dot', collectRunning ? 'pulse-dot--active' : '']"></span>
              <el-tag :type="collectRunning ? 'success' : 'info'" size="small" effect="dark">
                {{ collectRunning ? '运行中' : '空闲' }}
              </el-tag>
            </div>
          </div>
          <div class="collect-status">
            <div class="collect-item">
              <span class="collect-label">今日采集</span>
              <span class="collect-value">{{ stats.todayCollect }}</span>
            </div>
            <div class="collect-item">
              <span class="collect-label">活跃任务</span>
              <span class="collect-value" :class="{ 'value-accent': stats.activeTasks > 0 }">{{ stats.activeTasks }}</span>
            </div>
            <div class="collect-item">
              <span class="collect-label">成功率</span>
              <span class="collect-value" :class="successRateClass">{{ stats.successRate }}%</span>
            </div>
          </div>
          <el-button type="primary" style="width: 100%; margin-top: 16px;" @click="$router.push('/dashboard/collect')">
            进入采集中心
          </el-button>
        </div>

        <div class="panel" style="margin-top: 20px;">
          <div class="panel-header">
            <h3>AI分析</h3>
            <el-tag v-if="stats.todayAiCount > 0" size="small" type="warning" effect="dark">今日 {{ stats.todayAiCount }} 次</el-tag>
          </div>
          <div v-if="auth.userPlan === 'free'" class="ai-upgrade-hint">
            <div class="ai-upgrade-icon">🔮</div>
            <p>升级 Pro 解锁AI趋势评分</p>
            <p>升级 Premium 解锁爆品预测</p>
            <el-button type="primary" size="small" @click="$router.push('/pricing')">查看方案</el-button>
          </div>
          <div v-else class="ai-quick-actions">
            <div class="ai-summary-row" v-if="stats.aiRecommendations > 0">
              <div class="ai-summary-item">
                <span class="ai-summary-num">{{ stats.aiRecommendations }}</span>
                <span class="ai-summary-label">已完成分析</span>
              </div>
              <div class="ai-summary-item" v-if="stats.riskAlerts > 0">
                <span class="ai-summary-num risk-num">{{ stats.riskAlerts }}</span>
                <span class="ai-summary-label">风险预警</span>
              </div>
            </div>
            <el-button type="primary" @click="$router.push('/dashboard/ai')" style="width: 100%;">进入AI分析中心</el-button>
          </div>
        </div>

        <div class="panel quick-nav-panel" style="margin-top: 20px;">
          <div class="panel-header">
            <h3>快捷操作</h3>
          </div>
          <div class="quick-nav-grid">
            <div class="quick-nav-item" @click="$router.push('/dashboard/monitor')">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
              <span>商品监控</span>
            </div>
            <div class="quick-nav-item" @click="$router.push('/dashboard/collect')">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
              <span>数据采集</span>
            </div>
            <div class="quick-nav-item" @click="$router.push('/dashboard/ai')">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
              <span>AI分析</span>
            </div>
            <div class="quick-nav-item" @click="$router.push('/dashboard/settings')">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
              <span>设置</span>
            </div>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed, onMounted } from "vue";
import { useAuthStore } from "../../stores/auth";
import api from "../../utils/api";

const auth = useAuthStore();

const stats = reactive({
  productCount: 0,
  activeProductCount: 0,
  todayTrend: "0%",
  trendUpCount: 0,
  trendDownCount: 0,
  aiRecommendations: 0,
  riskAlerts: 0,
  todayCollect: 0,
  activeTasks: 0,
  successRate: 0,
  todayAiCount: 0,
});

const animatedStats = reactive({
  productCount: 0,
  aiRecommendations: 0,
  riskAlerts: 0,
});

const recentProducts = ref<any[]>([]);
const platformDist = ref<Record<string, number>>({});
const collectRunning = ref(false);

const trendClass = computed(() => {
  if (stats.todayTrend.startsWith("+")) return "trend-up";
  if (stats.todayTrend.startsWith("-")) return "trend-down";
  return "";
});

const successRateClass = computed(() => {
  if (stats.successRate >= 80) return "value-good";
  if (stats.successRate >= 50) return "value-warn";
  return "value-bad";
});

function platformLabel(p: string) {
  const map: Record<string, string> = { xhs: "小红书", taobao: "淘宝", jd: "京东", pdd: "拼多多", douyin: "抖音" };
  return map[p] || p;
}

function platformTagType(p: string) {
  const map: Record<string, string> = { xhs: "danger", taobao: "warning", jd: "", pdd: "success", douyin: "" };
  return map[p] || "info";
}

function barWidth(count: number) {
  const max = Math.max(...Object.values(platformDist.value), 1);
  return `${Math.round((count / max) * 100)}%`;
}

function animateNumber(target: keyof typeof animatedStats, end: number, duration = 800) {
  const start = animatedStats[target];
  if (start === end) return;
  const startTime = performance.now();
  function tick(now: number) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    animatedStats[target] = Math.round(start + (end - start) * eased);
    if (progress < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

onMounted(async () => {
  try {
    const { data } = await api.get("/dashboard/stats");
    const d = data?.data || {};

    stats.productCount = d.product_count || 0;
    stats.activeProductCount = d.active_product_count || 0;
    stats.todayTrend = d.today_trend || "0%";
    stats.trendUpCount = d.trend_up_count || 0;
    stats.trendDownCount = d.trend_down_count || 0;
    stats.aiRecommendations = d.ai_recommendations || 0;
    stats.riskAlerts = d.risk_alerts || 0;
    stats.todayCollect = d.today_collect || 0;
    stats.activeTasks = d.active_tasks || 0;
    stats.successRate = d.success_rate || 0;
    stats.todayAiCount = d.today_ai_count || 0;
    collectRunning.value = d.collect_running || false;

    recentProducts.value = d.recent_products || [];
    platformDist.value = d.platform_distribution || {};

    animateNumber("productCount", stats.productCount);
    animateNumber("aiRecommendations", stats.aiRecommendations);
    animateNumber("riskAlerts", stats.riskAlerts);
  } catch {}
});
</script>

<style scoped>
.dashboard-home {
  padding: 4px;
}

.stats-row .stat-card {
  border-radius: 14px;
  padding: 22px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  position: relative;
  overflow: hidden;
  transition: transform 0.2s, box-shadow 0.2s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

.stat-card--indigo {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(99, 102, 241, 0.05) 100%);
  border: 1px solid rgba(99, 102, 241, 0.2);
}

.stat-card--green {
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.15) 0%, rgba(34, 197, 94, 0.05) 100%);
  border: 1px solid rgba(34, 197, 94, 0.2);
}

.stat-card--amber {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(245, 158, 11, 0.05) 100%);
  border: 1px solid rgba(245, 158, 11, 0.2);
}

.stat-card--red {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(239, 68, 68, 0.05) 100%);
  border: 1px solid rgba(239, 68, 68, 0.2);
}

.stat-icon-wrap {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-card--indigo .stat-icon-wrap { background: rgba(99, 102, 241, 0.2); color: #a5b4fc; }
.stat-card--green .stat-icon-wrap { background: rgba(34, 197, 94, 0.2); color: #86efac; }
.stat-card--amber .stat-icon-wrap { background: rgba(245, 158, 11, 0.2); color: #fcd34d; }
.stat-card--red .stat-icon-wrap { background: rgba(239, 68, 68, 0.2); color: #fca5a5; }

.stat-icon-wrap svg {
  width: 24px;
  height: 24px;
}

.stat-value {
  font-size: 26px;
  font-weight: 700;
  color: #fff;
  line-height: 1.1;
}

.stat-label {
  font-size: 13px;
  color: #8a8a9a;
  margin-top: 3px;
}

.stat-sub {
  font-size: 11px;
  color: #5a5a6a;
  margin-top: 2px;
}

.panel {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 14px;
  padding: 20px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.panel-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  margin: 0;
}

.product-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.product-thumb {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background-size: cover;
  background-position: center;
  flex-shrink: 0;
}

.product-thumb--placeholder {
  background: rgba(99, 102, 241, 0.15);
  color: #a5b4fc;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
}

.product-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.product-name {
  font-size: 13px;
  color: #e0e0ea;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 140px;
}

.price-text {
  color: #fcd34d;
  font-weight: 600;
  font-size: 13px;
}

.muted {
  color: #4a4a5a;
}

.trend-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}

.trend-badge--up {
  background: rgba(34, 197, 94, 0.12);
  color: #86efac;
}

.trend-badge--down {
  background: rgba(239, 68, 68, 0.12);
  color: #fca5a5;
}

.trend-badge--flat {
  background: rgba(255, 255, 255, 0.05);
  color: #6a6a7a;
}

.trend-up { color: #22c55e; }
.trend-down { color: #ef4444; }

.status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot--active {
  background: #22c55e;
  box-shadow: 0 0 6px rgba(34, 197, 94, 0.4);
}

.status-dot--inactive {
  background: #4a4a5a;
}

.collect-status-tag {
  display: flex;
  align-items: center;
  gap: 6px;
}

.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #4a4a5a;
}

.pulse-dot--active {
  background: #22c55e;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.4); }
  70% { box-shadow: 0 0 0 8px rgba(34, 197, 94, 0); }
  100% { box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); }
}

.collect-status {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.collect-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.collect-item:last-child {
  border-bottom: none;
}

.collect-label {
  color: #8a8a9a;
  font-size: 14px;
}

.collect-value {
  color: #fff;
  font-size: 18px;
  font-weight: 700;
}

.value-accent {
  color: #a5b4fc;
}

.value-good { color: #22c55e; }
.value-warn { color: #f59e0b; }
.value-bad { color: #ef4444; }

.ai-upgrade-hint {
  text-align: center;
  padding: 20px 0;
}

.ai-upgrade-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.ai-upgrade-hint p {
  color: #8a8a9a;
  font-size: 13px;
  margin: 0 0 8px;
}

.ai-quick-actions {
  padding: 8px 0;
}

.ai-summary-row {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 10px;
}

.ai-summary-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
}

.ai-summary-num {
  font-size: 22px;
  font-weight: 700;
  color: #fcd34d;
}

.ai-summary-num.risk-num {
  color: #fca5a5;
}

.ai-summary-label {
  font-size: 12px;
  color: #6a6a7a;
  margin-top: 2px;
}

.platform-bars {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.platform-bar-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.platform-bar-label {
  width: 50px;
  font-size: 13px;
  color: #8a8a9a;
  text-align: right;
  flex-shrink: 0;
}

.platform-bar-track {
  flex: 1;
  height: 8px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 4px;
  overflow: hidden;
}

.platform-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
}

.platform-bar-fill--xhs { background: linear-gradient(90deg, #ef4444, #f87171); }
.platform-bar-fill--taobao { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.platform-bar-fill--jd { background: linear-gradient(90deg, #ef4444, #dc2626); }
.platform-bar-fill--pdd { background: linear-gradient(90deg, #22c55e, #4ade80); }
.platform-bar-fill--douyin { background: linear-gradient(90deg, #6366f1, #818cf8); }

.platform-bar-count {
  width: 30px;
  font-size: 13px;
  color: #e0e0ea;
  font-weight: 600;
}

.quick-nav-panel {
  padding: 16px 20px;
}

.quick-nav-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.quick-nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px 4px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.2s;
}

.quick-nav-item:hover {
  background: rgba(255, 255, 255, 0.06);
}

.quick-nav-item svg {
  width: 22px;
  height: 22px;
  color: #8a8a9a;
  transition: color 0.2s;
}

.quick-nav-item:hover svg {
  color: #a5b4fc;
}

.quick-nav-item span {
  font-size: 11px;
  color: #6a6a7a;
}
</style>
