<template>
  <div class="dashboard">
    <div class="page-header">
      <h2>商业情报仪表盘</h2>
      <el-tag v-if="intel.dashboard" type="success" size="small">
        {{ planLabel }} · 数据实时更新
      </el-tag>
    </div>

    <el-row :gutter="20" v-if="intel.dashboard">
      <el-col :span="8">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ intel.dashboard.summary.active_trends }}</div>
          <div class="stat-label">活跃趋势</div>
          <div class="stat-icon trend-icon">
            <el-icon :size="20"><TrendCharts /></el-icon>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ intel.dashboard.summary.recommended_opportunities }}</div>
          <div class="stat-label">推荐机会</div>
          <div class="stat-icon opp-icon">
            <el-icon :size="20"><Opportunity /></el-icon>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-value">{{ intel.dashboard.summary.active_risks }}</div>
          <div class="stat-label">活跃风险</div>
          <div class="stat-icon risk-icon">
            <el-icon :size="20"><Warning /></el-icon>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>🔥 热门趋势</span>
              <el-button text type="primary" @click="$router.push('/trends')">查看全部</el-button>
            </div>
          </template>
          <div v-if="intel.loading" class="loading-placeholder">
            <el-skeleton :rows="5" animated />
          </div>
          <el-empty v-else-if="!intel.dashboard?.top_trends?.length" description="暂无趋势数据" />
          <div v-else class="trend-list">
            <div v-for="item in intel.dashboard.top_trends" :key="item.id" class="trend-item">
              <div class="trend-title">{{ item.title }}</div>
              <div class="trend-meta">
                <el-tag size="small">{{ item.category }}</el-tag>
                <el-tag size="small" :type="item.opportunity_score >= 80 ? 'success' : item.opportunity_score >= 60 ? 'warning' : 'info'">
                  {{ item.opportunity_score }}分
                </el-tag>
                <el-tag size="small" v-if="item.lifecycle">{{ item.lifecycle }}</el-tag>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>💡 推荐机会</span>
              <el-button text type="primary" @click="$router.push('/opportunities')">查看全部</el-button>
            </div>
          </template>
          <div v-if="intel.loading" class="loading-placeholder">
            <el-skeleton :rows="5" animated />
          </div>
          <el-empty v-else-if="!intel.dashboard?.top_opportunities?.length" description="暂无机会数据" />
          <div v-else class="opp-list">
            <div v-for="item in intel.dashboard.top_opportunities" :key="item.id" class="opp-item">
              <div class="opp-title">{{ item.name }}</div>
              <div class="opp-meta">
                <el-tag size="small">{{ item.category }}</el-tag>
                <el-tag size="small" :type="item.verdict_score >= 80 ? 'success' : item.verdict_score >= 60 ? 'warning' : 'info'">
                  {{ item.verdict_score }}分
                </el-tag>
                <el-tag size="small" v-if="item.difficulty">{{ item.difficulty }}</el-tag>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-top: 20px">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>⚠️ 风险预警</span>
              <el-button text type="primary" @click="$router.push('/risks')">查看全部</el-button>
            </div>
          </template>
          <div v-if="intel.loading" class="loading-placeholder">
            <el-skeleton :rows="3" animated />
          </div>
          <el-empty v-else-if="!intel.dashboard?.top_risks?.length" description="暂无风险数据" />
          <el-table v-else :data="intel.dashboard.top_risks" style="width: 100%" size="small">
            <el-table-column prop="name" label="风险项" min-width="180" />
            <el-table-column prop="severity" label="严重程度" width="100">
              <template #default="{ row }">
                <el-tag :type="severityTagType(row.severity)" size="small">{{ row.severity }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="row.status === 'active' ? 'danger' : 'info'" size="small">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="reason" label="原因" min-width="200" show-overflow-tooltip />
            <el-table-column prop="alternative" label="替代方案" min-width="180" show-overflow-tooltip />
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { onMounted, computed } from "vue"
import { useIntelStore } from "@/stores/intel"
import { useIntelAuthStore } from "@/stores/auth"
import { TrendCharts, Opportunity, Warning } from "@element-plus/icons-vue"

const intel = useIntelStore()
const auth = useIntelAuthStore()

const planLabel = computed(() => auth.planLabel)

function severityTagType(severity: string): string {
  const map: Record<string, string> = { high: "danger", medium: "warning", low: "info" }
  return map[severity?.toLowerCase()] || "info"
}

onMounted(() => {
  intel.fetchDashboard()
})
</script>

<style scoped>
.dashboard { max-width: 1400px; }
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.page-header h2 { margin: 0; font-size: 20px; }
.stat-card {
  position: relative;
  overflow: hidden;
}
.stat-value {
  font-size: 36px;
  font-weight: 700;
  color: #303133;
}
.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}
.stat-icon {
  position: absolute;
  right: 16px;
  top: 50%;
  transform: translateY(-50%);
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.trend-icon { background: #e3f2fd; color: #1976d2; }
.opp-icon { background: #e8f5e9; color: #388e3c; }
.risk-icon { background: #fff3e0; color: #f57c00; }
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.loading-placeholder { padding: 16px; }
.trend-item, .opp-item {
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
}
.trend-item:last-child, .opp-item:last-child { border-bottom: none; }
.trend-title, .opp-title {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 6px;
}
.trend-meta, .opp-meta {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
</style>