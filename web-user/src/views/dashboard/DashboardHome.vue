<template>
  <div class="dashboard-home">
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon" style="background: rgba(99, 102, 241, 0.12); color: #a5b4fc;">📊</div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.productCount }}</div>
            <div class="stat-label">监控商品</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon" style="background: rgba(34, 197, 94, 0.12); color: #86efac;">📈</div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.todayTrend }}</div>
            <div class="stat-label">今日趋势</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon" style="background: rgba(245, 158, 11, 0.12); color: #fcd34d;">🔮</div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.aiRecommendations }}</div>
            <div class="stat-label">AI推荐</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon" style="background: rgba(239, 68, 68, 0.12); color: #fca5a5;">⚠️</div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.riskAlerts }}</div>
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
          <el-table :data="recentProducts" stripe style="width: 100%" empty-text="暂无监控商品">
            <el-table-column prop="name" label="商品名称" min-width="180" />
            <el-table-column prop="platform" label="平台" width="80">
              <template #default="{ row }">
                <el-tag size="small">{{ platformLabel(row.platform) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="price" label="价格" width="100" />
            <el-table-column label="趋势(7d)" width="100">
              <template #default="{ row }">
                <span :class="row.trend > 0 ? 'trend-up' : row.trend < 0 ? 'trend-down' : ''">
                  {{ row.trend > 0 ? '↑' : row.trend < 0 ? '↓' : '—' }} {{ Math.abs(row.trend || 0) }}%
                </span>
              </template>
            </el-table-column>
            <el-table-column label="AI评分" width="120">
              <template #default="{ row }">
                <span v-if="auth.userPlan === 'free'" class="ai-locked">升级查看</span>
                <span v-else>{{ row.aiScore || '—' }}</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="panel">
          <div class="panel-header">
            <h3>采集状态</h3>
            <el-tag :type="collectRunning ? 'success' : 'info'" size="small">
              {{ collectRunning ? '运行中' : '空闲' }}
            </el-tag>
          </div>
          <div class="collect-status">
            <div class="collect-item">
              <span class="collect-label">今日采集</span>
              <span class="collect-value">{{ stats.todayCollect }}</span>
            </div>
            <div class="collect-item">
              <span class="collect-label">活跃任务</span>
              <span class="collect-value">{{ stats.activeTasks }}</span>
            </div>
            <div class="collect-item">
              <span class="collect-label">成功率</span>
              <span class="collect-value">{{ stats.successRate }}%</span>
            </div>
          </div>
          <el-button type="primary" style="width: 100%; margin-top: 16px;" @click="$router.push('/dashboard/collect')">
            进入采集中心
          </el-button>
        </div>

        <div class="panel" style="margin-top: 20px;">
          <div class="panel-header">
            <h3>AI分析</h3>
          </div>
          <div v-if="auth.userPlan === 'free'" class="ai-upgrade-hint">
            <p>升级 Pro 解锁AI趋势评分</p>
            <p>升级 Premium 解锁爆品预测</p>
            <el-button type="primary" size="small" @click="$router.push('/pricing')">查看方案</el-button>
          </div>
          <div v-else class="ai-quick-actions">
            <el-button @click="$router.push('/dashboard/ai')">进入AI分析中心</el-button>
          </div>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted } from "vue";
import { useAuthStore } from "../../stores/auth";
import api from "../../utils/api";

const auth = useAuthStore();

const stats = reactive({
  productCount: 0,
  todayTrend: "+0%",
  aiRecommendations: 0,
  riskAlerts: 0,
  todayCollect: 0,
  activeTasks: 0,
  successRate: 0,
});

const recentProducts = ref<any[]>([]);
const collectRunning = ref(false);

function platformLabel(p: string) {
  const map: Record<string, string> = { xhs: "小红书", taobao: "淘宝", jd: "京东", pdd: "拼多多", douyin: "抖音" };
  return map[p] || p;
}

onMounted(async () => {
  try {
    const [productsRes, tasksRes] = await Promise.allSettled([
      api.get("/products", { params: { page_size: 5 } }),
      api.get("/collect/tasks", { params: { page_size: 5 } }),
    ]);

    if (productsRes.status === "fulfilled") {
      const items = productsRes.value.data?.data?.items || [];
      recentProducts.value = items;
      stats.productCount = productsRes.value.data?.data?.total || 0;
    }

    if (tasksRes.status === "fulfilled") {
      const taskItems = tasksRes.value.data?.data?.items || [];
      stats.activeTasks = taskItems.filter((t: any) => t.status === "running").length;
      stats.todayCollect = tasksRes.value.data?.data?.total || 0;
      collectRunning.value = taskItems.some((t: any) => t.status === "running");
    }
  } catch {}
});
</script>

<style scoped>
.dashboard-home {
  padding: 4px;
}

.stats-row .stat-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: #fff;
}

.stat-label {
  font-size: 13px;
  color: #6a6a7a;
  margin-top: 2px;
}

.panel {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
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

.trend-up { color: #22c55e; }
.trend-down { color: #ef4444; }

.ai-locked {
  color: #4a4a5a;
  font-size: 12px;
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
  padding: 8px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.collect-label {
  color: #6a6a7a;
  font-size: 14px;
}

.collect-value {
  color: #fff;
  font-size: 16px;
  font-weight: 600;
}

.ai-upgrade-hint {
  text-align: center;
  padding: 16px 0;
}

.ai-upgrade-hint p {
  color: #6a6a7a;
  font-size: 13px;
  margin: 0 0 8px;
}

.ai-quick-actions {
  text-align: center;
  padding: 12px 0;
}
</style>
