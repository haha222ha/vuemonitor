<template>
  <div class="opportunity-card">
    <div class="opportunity-card__header">
      <div class="opportunity-card__title-group">
        <el-icon class="opportunity-card__icon" :size="20"><Opportunity /></el-icon>
        <h3 class="opportunity-card__title">今日机会榜</h3>
        <el-tag v-if="rankings.length > 0" type="warning" size="small" effect="light">
          TOP {{ rankings.length }}
        </el-tag>
      </div>
      <el-button size="small" @click="$emit('refresh')">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>
    <div class="opportunity-card__body">
      <div v-if="loading" class="opportunity-card__loading">
        <el-skeleton :rows="4" animated />
      </div>
      <div v-else-if="rankings.length > 0" class="opportunity-list">
        <div
          v-for="(item, idx) in rankings.slice(0, 5)"
          :key="item.product_id || idx"
          class="opportunity-item"
          @click="$emit('item-click', item)"
        >
          <div class="opportunity-item__rank" :class="{ 'opportunity-item__rank--top': idx < 3 }">
            {{ idx + 1 }}
          </div>
          <div class="opportunity-item__info">
            <div class="opportunity-item__name">{{ item.product_name || item.product_id }}</div>
            <div class="opportunity-item__meta">
              <span v-if="item.category" class="opportunity-item__category">{{ item.category }}</span>
              <div v-if="item.overall_score !== undefined" class="opportunity-item__score-bar">
                <div
                  class="opportunity-item__score-fill"
                  :style="{ width: `${Math.min((item.overall_score / 100) * 100, 100)}%` }"
                />
              </div>
              <span class="opportunity-item__score">{{ item.overall_score }}</span>
            </div>
          </div>
          <div class="opportunity-item__trend">
            <el-tag
              v-if="item.trend_short"
              :type="trendTagType(item.trend_short)"
              size="small"
              effect="light"
            >
              {{ trendLabel(item.trend_short) }}
            </el-tag>
            <el-tag
              v-if="item.lifecycle_stage"
              :type="lifecycleTagType(item.lifecycle_stage)"
              size="small"
              effect="plain"
            >
              {{ lifecycleLabel(item.lifecycle_stage) }}
            </el-tag>
          </div>
        </div>
      </div>
      <EmptyState
        v-else
        :icon="Opportunity"
        title="暂无排名数据"
        description="添加更多商品并采集数据后自动生成排名"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { Opportunity, Refresh } from "@element-plus/icons-vue";
import EmptyState from "./EmptyState.vue";

interface RankingItem {
  product_id?: string;
  product_name?: string;
  category?: string;
  overall_score?: number;
  trend_short?: string;
  lifecycle_stage?: string;
}

defineProps<{
  rankings: RankingItem[];
  loading: boolean;
}>();

defineEmits<{
  refresh: [];
  "item-click": [item: RankingItem];
}>();

function trendLabel(trend: string): string {
  const map: Record<string, string> = { up: "上升", down: "下降", stable: "平稳", unknown: "未知" };
  return map[trend] || trend;
}

function trendTagType(trend: string): "" | "success" | "danger" | "info" {
  const map: Record<string, "" | "success" | "danger" | "info"> = { up: "success", down: "danger", stable: "info", unknown: "info" };
  return map[trend] || "info";
}

function lifecycleLabel(stage: string): string {
  const map: Record<string, string> = { new: "新品期", growth: "成长期", rising: "上升期", stable: "稳定期", declining: "衰退期", decline: "衰退期", mature: "成熟期" };
  return map[stage] || stage;
}

function lifecycleTagType(stage: string): "" | "success" | "warning" | "danger" | "info" {
  const map: Record<string, "" | "success" | "warning" | "danger" | "info"> = {
    new: "warning",
    growth: "success",
    rising: "success",
    stable: "info",
    declining: "danger",
    decline: "danger",
    mature: "info",
  };
  return map[stage] || "info";
}
</script>

<style scoped>
.opportunity-card__header {
  padding: 20px 24px;
  border-bottom: 1px solid var(--color-border-light);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.opportunity-card__title-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.opportunity-card__icon {
  color: #F59E0B;
}

.opportunity-card__title {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-text-primary);
}

.opportunity-card__body {
  padding: 20px 24px;
}

.opportunity-card__loading {
  padding: 16px 0;
}

.opportunity-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.opportunity-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: var(--color-bg-page);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-base);
  transition: all 0.2s;
  cursor: pointer;
}

.opportunity-item:hover {
  background: var(--color-bg-hover);
  border-color: var(--color-border);
  transform: translateX(4px);
}

.opportunity-item__rank {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text-tertiary);
  background: var(--color-border-light);
  flex-shrink: 0;
}

.opportunity-item__rank--top {
  background: linear-gradient(135deg, #F59E0B, #D97706);
  color: #fff;
}

.opportunity-item__info {
  flex: 1;
  min-width: 0;
}

.opportunity-item__name {
  font-size: var(--text-base);
  font-weight: 500;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.opportunity-item__meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.opportunity-item__category {
  padding: 1px 6px;
  background: var(--color-border-light);
  border-radius: 4px;
  font-size: 11px;
  color: var(--color-text-secondary);
}

.opportunity-item__score-bar {
  width: 60px;
  height: 4px;
  background: var(--color-border-light);
  border-radius: 2px;
  overflow: hidden;
}

.opportunity-item__score-fill {
  height: 100%;
  background: linear-gradient(90deg, #F59E0B, #FBBF24);
  border-radius: 2px;
  transition: width 0.6s ease;
}

.opportunity-item__score {
  color: #D97706;
  font-weight: 700;
  font-size: 12px;
}

.opportunity-item__trend {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}
</style>
