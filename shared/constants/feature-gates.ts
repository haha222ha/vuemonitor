export type PlanTier = "free" | "pro" | "premium" | "enterprise";

export type GateType = "feature" | "quota" | "limit";

export interface FeatureGateDefinition {
  key: string;
  name: string;
  type: GateType;
  requiredPlan: PlanTier;
  description: string;
  quotaDaily?: number;
  quotaMonthly?: number;
}

export const FEATURE_GATES: FeatureGateDefinition[] = [
  { key: "gate:monitor:add", name: "添加监控商品", type: "limit", requiredPlan: "free", description: "Free最多10个" },
  { key: "gate:monitor:manual_refresh", name: "手动刷新采集", type: "feature", requiredPlan: "free", description: "手动触发数据采集" },
  { key: "gate:monitor:auto_refresh", name: "自动定时采集", type: "feature", requiredPlan: "pro", description: "Pro及以上支持" },
  { key: "gate:monitor:history", name: "历史趋势对比", type: "feature", requiredPlan: "pro", description: "Pro及以上支持" },
  { key: "gate:monitor:export", name: "数据导出", type: "feature", requiredPlan: "pro", description: "Pro及以上支持" },
  { key: "gate:ai:basic_analysis", name: "AI基础分析", type: "feature", requiredPlan: "free", description: "基础文本描述" },
  { key: "gate:ai:trend_score", name: "AI趋势评分", type: "feature", requiredPlan: "pro", description: "趋势评分+结构化分析" },
  { key: "gate:ai:prediction", name: "AI爆款预测", type: "feature", requiredPlan: "premium", description: "爆款预测+多维评分" },
  { key: "gate:ai:risk_warning", name: "AI风险预警", type: "feature", requiredPlan: "premium", description: "实时风险识别" },
  { key: "gate:ai:report", name: "AI报告生成", type: "feature", requiredPlan: "pro", description: "Pro及以上支持" },
  { key: "gate:ai:batch_analysis", name: "批量AI分析", type: "feature", requiredPlan: "premium", description: "Premium及以上支持" },
  { key: "gate:collect:playwright", name: "Playwright深度采集", type: "feature", requiredPlan: "pro", description: "Pro及以上支持SPA/搜索页采集" },
  { key: "gate:collect:author_full", name: "博主全量采集", type: "feature", requiredPlan: "pro", description: "Pro及以上支持" },
  { key: "gate:sync:cloud", name: "云端数据同步", type: "feature", requiredPlan: "pro", description: "Pro及以上支持" },
];

export const PLAN_HIERARCHY: Record<PlanTier, number> = {
  free: 0,
  pro: 1,
  premium: 2,
  enterprise: 3,
};

export function isPlanSufficient(userPlan: PlanTier, requiredPlan: PlanTier): boolean {
  return PLAN_HIERARCHY[userPlan] >= PLAN_HIERARCHY[requiredPlan];
}

export const PLAN_LIMITS: Record<PlanTier, { maxProducts: number; maxConcurrency: number; dailyCollectLimit: number; maxScheduleTasks: number; aiCallsPerDay: number }> = {
  free: { maxProducts: 10, maxConcurrency: 2, dailyCollectLimit: 50, maxScheduleTasks: 0, aiCallsPerDay: 5 },
  pro: { maxProducts: 100, maxConcurrency: 5, dailyCollectLimit: 500, maxScheduleTasks: 20, aiCallsPerDay: 50 },
  premium: { maxProducts: 500, maxConcurrency: 8, dailyCollectLimit: 2000, maxScheduleTasks: 100, aiCallsPerDay: 200 },
  enterprise: { maxProducts: -1, maxConcurrency: 10, dailyCollectLimit: -1, maxScheduleTasks: -1, aiCallsPerDay: -1 },
};
