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
  { key: "gate:monitor:add", name: "添加监控商品", type: "limit", requiredPlan: "free", description: "免费版可用，监控数量不限" },
  { key: "gate:monitor:manual_refresh", name: "手动刷新采集", type: "feature", requiredPlan: "free", description: "手动触发数据采集" },
  { key: "gate:monitor:auto_refresh", name: "自动定时采集", type: "feature", requiredPlan: "free", description: "免费版支持定时采集" },
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
  { key: "gate:discovery:search", name: "商品发现搜索", type: "quota", requiredPlan: "free", description: "云端搜索添加（免费20次/天·按账号+IP），粘贴链接不限", quotaDaily: 20 },
  { key: "gate:discovery:burst", name: "爆品洞察", type: "quota", requiredPlan: "premium", description: "爆品榜单和飙升榜（Premium及以上，50次/天）", quotaDaily: 50 },
  { key: "gate:aipic:generate", name: "AI作图", type: "feature", requiredPlan: "free", description: "基础文生图/图生图" },
  { key: "gate:aipic:hd", name: "高清画质", type: "feature", requiredPlan: "pro", description: "HD画质生成" },
  { key: "gate:aipic:ultra", name: "超清画质", type: "feature", requiredPlan: "premium", description: "Ultra画质生成" },
  { key: "gate:aipic:style", name: "风格库", type: "feature", requiredPlan: "pro", description: "自定义风格" },
  { key: "gate:aipic:batch", name: "批量生成", type: "feature", requiredPlan: "premium", description: "批量生图" },
  { key: "gate:aipic:api", name: "API访问", type: "feature", requiredPlan: "premium", description: "API密钥调用" },
  { key: "gate:monitor:waterfall", name: "瀑布流视图", type: "feature", requiredPlan: "free", description: "瀑布流商品展示" },
  { key: "gate:monitor:category", name: "分类管理", type: "feature", requiredPlan: "pro", description: "商品分类筛选管理" },
  { key: "gate:monitor:growth_24h", name: "24h增长", type: "feature", requiredPlan: "pro", description: "24小时增长指标" },
  { key: "gate:monitor:anomaly", name: "异常检测", type: "feature", requiredPlan: "premium", description: "自动异常检测与告警" },
  { key: "gate:monitor:compare", name: "商品对比", type: "feature", requiredPlan: "pro", description: "多商品趋势对比分析" },
  { key: "gate:import:excel", name: "Excel导入", type: "feature", requiredPlan: "pro", description: "批量Excel导入商品" },
  { key: "gate:collect:create", name: "创建采集任务", type: "feature", requiredPlan: "free", description: "创建数据采集任务" },
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

export const PLAN_LIMITS: Record<PlanTier, { maxProducts: number; maxConcurrency: number; dailyCollectLimit: number; maxScheduleTasks: number; aiCallsPerDay: number; discoverySearchPerDay: number; discoveryBurstPerDay: number; aipicDailyLimit: number; aipicMaxQuality: string; excelImportPerDay: number; historyDays: number; anomalyDetection: boolean }> = {
  free: { maxProducts: -1, maxConcurrency: 2, dailyCollectLimit: 200, maxScheduleTasks: 100, aiCallsPerDay: 10, discoverySearchPerDay: 20, discoveryBurstPerDay: 0, aipicDailyLimit: 3, aipicMaxQuality: "standard", excelImportPerDay: 0, historyDays: 7, anomalyDetection: false },
  pro: { maxProducts: 50, maxConcurrency: 5, dailyCollectLimit: 500, maxScheduleTasks: 20, aiCallsPerDay: 50, discoverySearchPerDay: 200, discoveryBurstPerDay: 0, aipicDailyLimit: 50, aipicMaxQuality: "hd", excelImportPerDay: 10, historyDays: 30, anomalyDetection: false },
  premium: { maxProducts: 500, maxConcurrency: 8, dailyCollectLimit: 2000, maxScheduleTasks: 100, aiCallsPerDay: 200, discoverySearchPerDay: 200, discoveryBurstPerDay: 50, aipicDailyLimit: 200, aipicMaxQuality: "ultra", excelImportPerDay: 50, historyDays: 90, anomalyDetection: true },
  enterprise: { maxProducts: -1, maxConcurrency: 10, dailyCollectLimit: -1, maxScheduleTasks: -1, aiCallsPerDay: -1, discoverySearchPerDay: -1, discoveryBurstPerDay: -1, aipicDailyLimit: -1, aipicMaxQuality: "ultra", excelImportPerDay: -1, historyDays: -1, anomalyDetection: true },
};
