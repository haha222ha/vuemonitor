<template>
  <div class="market-insight">
    <div class="market-insight__header">
      <div class="market-insight__title-group">
        <el-icon class="market-insight__icon" :size="20"><TrendCharts /></el-icon>
        <h3 class="market-insight__title">市场洞察</h3>
      </div>
      <el-button size="small" @click="$emit('refresh')">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>
    <div class="market-insight__body">
      <div v-if="loading" class="market-insight__loading">
        <el-skeleton :rows="3" animated />
      </div>
      <div v-else-if="heatmap.length > 0" class="market-insight__content">
        <div class="insight-section">
          <h4 class="insight-section__title">品类热度</h4>
          <div class="crowd-heatmap">
            <div v-for="item in heatmap.slice(0, 8)" :key="item.category" class="crowd-heatmap__item">
              <div class="crowd-heatmap__label">{{ item.category }}</div>
              <div class="crowd-heatmap__bar">
                <div
                  class="crowd-heatmap__fill"
                  :style="{ width: `${item.heat_score}%` }"
                  :class="item.heat_level"
                />
              </div>
              <div class="crowd-heatmap__score">
                <el-tag :type="heatTagType(item.heat_level)" size="small" effect="light">
                  {{ item.heat_score }}
                </el-tag>
              </div>
            </div>
          </div>
        </div>

        <div v-if="patterns" class="insight-section crowd-patterns">
          <div class="crowd-patterns__row" v-if="patterns.dominant_lifecycle">
            <span class="crowd-patterns__label">主流生命周期</span>
            <el-tag size="small" effect="light">{{ lifecycleLabel(patterns.dominant_lifecycle) }}</el-tag>
          </div>
          <div class="crowd-patterns__row" v-if="patterns.dominant_trend">
            <span class="crowd-patterns__label">主流趋势</span>
            <el-tag :type="trendTagType(patterns.dominant_trend)" size="small" effect="light">
              {{ trendLabel(patterns.dominant_trend) }}
            </el-tag>
          </div>
          <div class="crowd-patterns__row" v-if="patterns.best_seller_price_band">
            <span class="crowd-patterns__label">最佳价格带</span>
            <el-tag size="small" type="success" effect="light">{{ priceBandLabel(patterns.best_seller_price_band.band) }}</el-tag>
          </div>
        </div>

        <div v-if="trendSeries.length > 0" class="insight-section">
          <h4 class="insight-section__title">市场趋势（近30天）</h4>
          <div class="trend-categories">
            <div
              v-for="cat in trendSeries.slice(0, 3)"
              :key="cat.category"
              class="trend-category"
            >
              <div class="trend-category__header">
                <span class="trend-category__name">{{ cat.category }}</span>
                <span
                  v-if="cat.latestGrowth !== null"
                  class="trend-category__growth"
                  :class="growthClass(cat.latestGrowth)"
                >
                  {{ formatGrowth(cat.latestGrowth) }}
                </span>
              </div>
              <div class="trend-category__sparkline">
                <svg :viewBox="`0 0 ${cat.sparklineWidth} 32`" preserveAspectRatio="none" class="sparkline">
                  <polyline
                    :points="cat.sparklinePoints"
                    fill="none"
                    :stroke="sparklineColor(cat.latestGrowth)"
                    stroke-width="1.5"
                    stroke-linejoin="round"
                  />
                </svg>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="market-insight__empty">
        <span class="cell-secondary">暂无群体数据，需连接云端服务</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { TrendCharts, Refresh } from "@element-plus/icons-vue";

interface HeatmapItem {
  category: string;
  heat_score: number;
  heat_level: "hot" | "warm" | "cold";
}

interface PatternData {
  dominant_lifecycle?: string;
  dominant_trend?: string;
  best_seller_price_band?: { band: string };
}

interface TrendSeriesItem {
  category: string;
  sparklinePoints: string;
  sparklineWidth: number;
  latestGrowth: number | null;
}

defineProps<{
  heatmap: HeatmapItem[];
  patterns: PatternData | null;
  trendSeries: TrendSeriesItem[];
  loading: boolean;
}>();

defineEmits<{
  refresh: [];
}>();

function heatTagType(level: string): "" | "danger" | "warning" | "info" {
  const map: Record<string, "" | "danger" | "warning" | "info"> = { hot: "danger", warm: "warning", cold: "info" };
  return map[level] || "info";
}

function lifecycleLabel(stage: string): string {
  const map: Record<string, string> = { new: "新品期", growth: "成长期", rising: "上升期", stable: "稳定期", declining: "衰退期", decline: "衰退期", mature: "成熟期" };
  return map[stage] || stage;
}

function trendLabel(trend: string): string {
  const map: Record<string, string> = { up: "上升", down: "下降", stable: "平稳", unknown: "未知" };
  return map[trend] || trend;
}

function trendTagType(trend: string): "" | "success" | "danger" | "info" {
  const map: Record<string, "" | "success" | "danger" | "info"> = { up: "success", down: "danger", stable: "info", unknown: "info" };
  return map[trend] || "info";
}

function priceBandLabel(band: string): string {
  const map: Record<string, string> = { under_50: "¥50以下", "50_100": "¥50-100", "100_200": "¥100-200", "200_500": "¥200-500", over_500: "¥500+" };
  return map[band] || band;
}

function growthClass(growth: number): string {
  if (growth > 0) return "trend-category__growth--up";
  if (growth < 0) return "trend-category__growth--down";
  return "";
}

function formatGrowth(growth: number): string {
  return `${growth > 0 ? "+" : ""}${(growth * 100).toFixed(1)}%`;
}

function sparklineColor(growth: number | null): string {
  if (growth === null) return "#6366f1";
  if (growth > 0) return "#10B981";
  if (growth < 0) return "#EF4444";
  return "#6366f1";
}
</script>

<style scoped>
.market-insight__header {
  padding: 20px 24px;
  border-bottom: 1px solid var(--color-border-light);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.market-insight__title-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.market-insight__icon {
  color: var(--color-primary);
}

.market-insight__title {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-text-primary);
}

.market-insight__body {
  padding: 20px 24px;
}

.market-insight__loading {
  padding: 16px 0;
}

.market-insight__empty {
  padding: 24px 0;
  text-align: center;
}

.insight-section {
  margin-bottom: 16px;
}

.insight-section:last-child {
  margin-bottom: 0;
}

.insight-section__title {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin: 0 0 12px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.crowd-heatmap {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.crowd-heatmap__item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.crowd-heatmap__label {
  font-size: 12px;
  color: var(--color-text-primary);
  min-width: 80px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.crowd-heatmap__bar {
  flex: 1;
  height: 6px;
  border-radius: 3px;
  background: var(--color-bg-page);
  overflow: hidden;
}

.crowd-heatmap__fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.6s ease;
}

.crowd-heatmap__fill.hot {
  background: linear-gradient(90deg, #ef4444, #f97316);
}

.crowd-heatmap__fill.warm {
  background: linear-gradient(90deg, #f59e0b, #eab308);
}

.crowd-heatmap__fill.cold {
  background: linear-gradient(90deg, #6366f1, #818cf8);
}

.crowd-heatmap__score {
  min-width: 40px;
  text-align: right;
}

.crowd-patterns {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border-lighter);
}

.crowd-patterns__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.crowd-patterns__label {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.trend-categories {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.trend-category {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: var(--color-bg-page);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-base);
}

.trend-category__header {
  min-width: 100px;
  flex-shrink: 0;
}

.trend-category__name {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-primary);
  display: block;
}

.trend-category__growth {
  font-size: 12px;
  font-weight: 600;
  margin-top: 2px;
  display: block;
}

.trend-category__growth--up {
  color: #10B981;
}

.trend-category__growth--down {
  color: #EF4444;
}

.trend-category__sparkline {
  flex: 1;
  height: 32px;
}

.sparkline {
  width: 100%;
  height: 100%;
}
</style>
