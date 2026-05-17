<template>
  <div class="product-card">
    <div class="product-card__header">
      <el-image v-if="product.image_url" :src="product.image_url" class="product-card__image" fit="cover" />
      <div v-else class="product-card__image product-card__image--placeholder">
        <el-icon :size="24"><Goods /></el-icon>
      </div>
      <div class="product-card__info">
        <div class="product-card__name">{{ product.product_name }}</div>
        <div class="product-card__shop">{{ product.shop_name || '未知店铺' }}</div>
      </div>
      <div v-if="ranking" class="product-card__rank-badge">
        <span class="rank-badge__number">#{{ ranking.rank }}</span>
        <span class="rank-badge__total" v-if="ranking.total">/{{ ranking.total }}</span>
      </div>
    </div>
    <div class="product-card__body">
      <div class="product-card__metrics" v-if="product.latest_feature">
        <div class="product-card__metric">
          <span class="product-card__metric-label">价格</span>
          <span class="product-card__metric-value product-card__metric-value--price">{{ product.latest_feature.price != null ? `¥${product.latest_feature.price}` : '-' }}</span>
        </div>
        <div class="product-card__metric">
          <span class="product-card__metric-label">销量</span>
          <span class="product-card__metric-value">{{ product.latest_feature.sales_count != null ? formatNumber(product.latest_feature.sales_count) : '-' }}</span>
        </div>
        <div class="product-card__metric">
          <span class="product-card__metric-label">评分</span>
          <span class="product-card__metric-value">{{ product.latest_feature.rating != null ? product.latest_feature.rating.toFixed(1) : '-' }}</span>
        </div>
      </div>
      <div class="product-card__meta">
        <span class="product-card__id">{{ product.platform_product_id }}</span>
        <span class="product-card__time">{{ product.last_collected_at ? formatDate(product.last_collected_at) : '未采集' }}</span>
      </div>
      <div v-if="ranking" class="product-card__rank-tags">
        <el-tag v-if="ranking.lifecycle" size="small" effect="light" :type="lifecycleTagType(ranking.lifecycle)">
          {{ lifecycleLabel(ranking.lifecycle) }}
        </el-tag>
        <el-tag v-if="ranking.trend" size="small" effect="light"
          :type="ranking.trend === '上升' ? 'success' : ranking.trend === '下降' ? 'danger' : 'info'">
          {{ trendIcon(ranking.trend) }} {{ ranking.trend }}
        </el-tag>
      </div>
      <div v-if="ranking && ranking.total > 0" class="product-card__percentile">
        <div class="product-card__percentile-label">
          排名超过 <span class="product-card__percentile-value">{{ percentileText }}</span> 同类商品
        </div>
        <div class="product-card__percentile-bar">
          <div class="product-card__percentile-fill" :style="{ width: percentileWidth }" />
        </div>
      </div>
      <div v-if="competitionIndex != null" class="product-card__competition">
        <div class="product-card__competition-header">
          <span class="product-card__competition-label">竞争力指数</span>
          <span :class="['product-card__competition-value', `product-card__competition-value--${competitionLevel}`]">
            {{ competitionIndex.toFixed(2) }}
          </span>
        </div>
        <div class="product-card__competition-bar">
          <div class="product-card__competition-track">
            <div class="product-card__competition-seg product-card__competition-seg--low" style="width: 40%" />
            <div class="product-card__competition-seg product-card__competition-seg--mid" style="width: 30%" />
            <div class="product-card__competition-seg product-card__competition-seg--high" style="width: 30%" />
          </div>
          <div class="product-card__competition-marker" :style="{ left: `${Math.min(competitionIndex * 100, 100)}%` }" />
        </div>
        <div class="product-card__competition-labels">
          <span>弱</span>
          <span>中</span>
          <span>强</span>
        </div>
      </div>
    </div>
    <div class="product-card__actions">
      <el-button size="small" @click="$emit('detail', product)">详情</el-button>
      <el-button size="small" type="primary" @click="$emit('collect', product)">采集</el-button>
      <el-dropdown v-permission="'gate:ai:basic_analysis'" @command="(cmd: string) => $emit('ai-analysis', product, cmd)" size="small">
        <el-button size="small" type="warning">
          <el-icon><MagicStick /></el-icon>AI
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="trend_score">趋势评分</el-dropdown-item>
            <el-dropdown-item command="prediction">爆品预测</el-dropdown-item>
            <el-dropdown-item command="risk_warning">风险预警</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      <el-button v-permission="'gate:monitor:auto_refresh'" size="small" @click="$emit('schedule', product)">定时</el-button>
      <el-button size="small" type="danger" plain @click="$emit('delete', product.id)">删除</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { Goods, MagicStick } from "@element-plus/icons-vue";

export interface ProductRanking {
  rank: number;
  total: number;
  trend: string;
  lifecycle: string;
}

const props = defineProps<{
  product: any;
  ranking?: ProductRanking | null;
}>();

defineEmits<{
  detail: [product: any];
  collect: [product: any];
  'ai-analysis': [product: any, type: string];
  schedule: [product: any];
  delete: [id: string];
}>();

const percentileText = computed(() => {
  if (!props.ranking || props.ranking.total === 0) return "-";
  return `${Math.round(((props.ranking.total - props.ranking.rank) / props.ranking.total) * 100)}%`;
});

const percentileWidth = computed(() => {
  if (!props.ranking || props.ranking.total === 0) return "0%";
  return `${Math.round(((props.ranking.total - props.ranking.rank) / props.ranking.total) * 100)}%`;
});

const competitionIndex = computed(() => {
  return props.product.latest_feature?.competition_index ?? props.product.competition_index ?? null;
});

const competitionLevel = computed(() => {
  const idx = competitionIndex.value;
  if (idx == null) return 'unknown';
  if (idx >= 0.7) return 'high';
  if (idx >= 0.4) return 'medium';
  return 'low';
});

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function formatNumber(num: number): string {
  if (num >= 10000) return `${(num / 10000).toFixed(1)}万`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}k`;
  return String(num);
}

function trendIcon(trend: string) {
  if (trend === "上升") return "📈";
  if (trend === "下降") return "📉";
  return "➡️";
}

function lifecycleTagType(stage: string): "" | "success" | "warning" | "danger" | "info" {
  const map: Record<string, "" | "success" | "warning" | "danger" | "info"> = {
    new: "warning", growth: "success", rising: "success", stable: "info", declining: "danger", decline: "danger", mature: "info",
  };
  return map[stage] || "info";
}

function lifecycleLabel(stage: string): string {
  const map: Record<string, string> = { new: "新品期", growth: "成长期", rising: "上升期", stable: "稳定期", declining: "衰退期", decline: "衰退期", mature: "成熟期" };
  return map[stage] || stage;
}
</script>

<style scoped>
.product-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-border-light);
  padding: 20px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.product-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.product-card__header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.product-card__image {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-base);
  flex-shrink: 0;
  border: 1px solid var(--color-border-light);
}

.product-card__image--placeholder {
  background: var(--color-bg-page);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-tertiary);
}

.product-card__info {
  flex: 1;
  min-width: 0;
}

.product-card__name {
  font-weight: 500;
  font-size: var(--text-base);
  color: var(--color-text-primary);
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.product-card__shop {
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}

.product-card__body {
  margin-bottom: 16px;
}

.product-card__metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}

.product-card__metric {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 6px 4px;
  background: var(--color-bg-page);
  border-radius: var(--radius-base);
}

.product-card__metric-label {
  font-size: 10px;
  color: var(--color-text-tertiary);
  font-weight: 500;
}

.product-card__metric-value {
  font-size: var(--text-sm);
  font-weight: 700;
  color: var(--color-text-primary);
}

.product-card__metric-value--price {
  color: var(--color-danger, #EF4444);
}

.product-card__meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.product-card__id {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}

.product-card__time {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.product-card__actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.product-card__rank-badge {
  flex-shrink: 0;
  background: linear-gradient(135deg, #F59E0B, #D97706);
  color: #fff;
  border-radius: 8px;
  padding: 2px 8px;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.6;
  white-space: nowrap;
}

.rank-badge__number { font-size: 14px; }
.rank-badge__total { font-size: 10px; opacity: 0.8; }

.product-card__rank-tags {
  display: flex;
  gap: 6px;
  margin-top: 8px;
}

.product-card__percentile { margin-top: 10px; }

.product-card__percentile-label {
  font-size: 12px;
  color: var(--color-text-secondary);
  margin-bottom: 4px;
}

.product-card__percentile-value {
  font-weight: 600;
  color: #10B981;
}

.product-card__percentile-bar {
  width: 100%;
  height: 6px;
  background: var(--color-border-light);
  border-radius: 3px;
  overflow: hidden;
}

.product-card__percentile-fill {
  height: 100%;
  background: linear-gradient(90deg, #F59E0B, #10B981);
  border-radius: 3px;
  transition: width 0.6s ease;
}
.product-card__competition { margin-top: 10px; }
.product-card__competition-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.product-card__competition-label { font-size: 12px; color: var(--color-text-secondary); }
.product-card__competition-value { font-size: 14px; font-weight: 700; }
.product-card__competition-value--low { color: #10B981; }
.product-card__competition-value--medium { color: #F59E0B; }
.product-card__competition-value--high { color: #EF4444; }
.product-card__competition-bar { position: relative; height: 6px; margin-bottom: 2px; }
.product-card__competition-track { display: flex; height: 100%; border-radius: 3px; overflow: hidden; }
.product-card__competition-seg--low { background: #BBF7D0; }
.product-card__competition-seg--mid { background: #FDE68A; }
.product-card__competition-seg--high { background: #FCA5A5; }
.product-card__competition-marker { position: absolute; top: -3px; width: 4px; height: 12px; background: var(--color-text-primary); border-radius: 2px; transform: translateX(-50%); transition: left 0.5s ease-out; }
.product-card__competition-labels { display: flex; justify-content: space-between; font-size: 10px; color: var(--color-text-tertiary); }
</style>
