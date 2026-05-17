<template>
  <div class="ai-recommendations">
    <div class="ai-rec-header">
      <h3 class="ai-rec-title">
        <el-icon><MagicStick /></el-icon>
        AI智能推荐
      </h3>
      <el-button text size="small" @click="$emit('refresh')" :loading="loading">刷新</el-button>
    </div>
    <div v-if="loading" style="padding: 24px"><el-skeleton :rows="3" animated /></div>
    <div v-else-if="recommendations.length > 0" class="ai-rec-grid">
      <div
        v-for="rec in recommendations"
        :key="rec.product_id || rec.type + rec.reason"
        class="ai-rec-card"
        @click="$emit('item-click', rec)"
      >
        <div class="ai-rec-card__badge">
          <el-tag size="small" :type="recTagType(rec.type)">{{ recLabel(rec.type) }}</el-tag>
        </div>
        <div class="ai-rec-card__body">
          <div v-if="rec.image_url" class="ai-rec-card__img">
            <img :src="rec.image_url" :alt="rec.product_name" />
          </div>
          <div class="ai-rec-card__info">
            <div class="ai-rec-card__name">{{ rec.product_name || rec.category || '未知' }}</div>
            <div class="ai-rec-card__reason">{{ rec.reason }}</div>
          </div>
        </div>
        <div v-if="rec.metric" class="ai-rec-card__metrics">
          <span v-if="rec.metric.growth_rate_7d != null" class="ai-rec-metric">
            <span class="ai-rec-metric__label">7日增长</span>
            <span class="ai-rec-metric__value ai-rec-metric__value--up">{{ rec.metric.growth_rate_7d.toFixed(1) }}%</span>
          </span>
          <span v-if="rec.metric.rank != null" class="ai-rec-metric">
            <span class="ai-rec-metric__label">排名</span>
            <span class="ai-rec-metric__value">#{{ rec.metric.rank }}</span>
          </span>
          <span v-if="rec.metric.avg_sales != null" class="ai-rec-metric">
            <span class="ai-rec-metric__label">均销</span>
            <span class="ai-rec-metric__value">{{ rec.metric.avg_sales }}</span>
          </span>
          <span v-if="rec.metric.competition_index != null" class="ai-rec-metric">
            <span class="ai-rec-metric__label">竞争</span>
            <span class="ai-rec-metric__value ai-rec-metric__value--danger">{{ rec.metric.competition_index.toFixed(2) }}</span>
          </span>
        </div>
      </div>
    </div>
    <div v-else class="ai-rec-empty">
      <el-icon class="ai-rec-empty__icon"><MagicStick /></el-icon>
      <p>暂无推荐</p>
      <p class="ai-rec-empty__desc">添加更多商品或监控规则后，AI将为您生成智能推荐</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { MagicStick } from "@element-plus/icons-vue";

interface RecMetric {
  growth_rate_7d?: number | null;
  rank?: number | null;
  avg_sales?: number | null;
  competition_index?: number | null;
}

interface RecommendationItem {
  product_id?: string;
  product_name?: string;
  category?: string;
  image_url?: string;
  type: string;
  reason: string;
  metric?: RecMetric | null;
  event_id?: string;
}

defineProps<{
  recommendations: RecommendationItem[];
  loading: boolean;
}>();

defineEmits<{
  refresh: [];
  "item-click": [item: RecommendationItem];
}>();

function recTagType(type: string): "" | "success" | "warning" | "danger" | "info" {
  const map: Record<string, "" | "success" | "warning" | "danger" | "info"> = {
    trending: "success", alert: "danger", category_insight: "warning", risk: "danger",
  };
  return map[type] || "info";
}

function recLabel(type: string): string {
  const map: Record<string, string> = {
    trending: "趋势上升", alert: "异动告警", category_insight: "品类洞察", risk: "竞争风险",
  };
  return map[type] || "推荐";
}
</script>

<style scoped>
.ai-recommendations {
  padding: 20px;
}

.ai-rec-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.ai-rec-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-size: var(--text-base);
  font-weight: 600;
  color: var(--color-text-primary);
}

.ai-rec-title .el-icon {
  color: var(--color-primary);
}

.ai-rec-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}

.ai-rec-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px;
  background: var(--color-bg-page);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all 0.2s;
}

.ai-rec-card:hover {
  border-color: var(--color-primary-light);
  box-shadow: var(--shadow-sm);
  transform: translateY(-1px);
}

.ai-rec-card__badge {
  display: flex;
}

.ai-rec-card__body {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

.ai-rec-card__img {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-base);
  overflow: hidden;
  flex-shrink: 0;
}

.ai-rec-card__img img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.ai-rec-card__info {
  flex: 1;
  min-width: 0;
}

.ai-rec-card__name {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ai-rec-card__reason {
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  margin-top: 2px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.ai-rec-card__metrics {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.ai-rec-metric {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.ai-rec-metric__label {
  font-size: 10px;
  color: var(--color-text-tertiary);
}

.ai-rec-metric__value {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--color-text-primary);
}

.ai-rec-metric__value--up {
  color: var(--color-success);
}

.ai-rec-metric__value--danger {
  color: var(--color-danger);
}

.ai-rec-empty {
  text-align: center;
  padding: 32px 0;
  color: var(--color-text-secondary);
}

.ai-rec-empty__icon {
  font-size: 36px;
  color: var(--color-text-tertiary);
  margin-bottom: 8px;
}

.ai-rec-empty__desc {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-top: 4px;
}
</style>
