// AIGC START
/** 小红书三档 SKU ↔ 后端 weekly / monthly / yearly */

export type IntelPlan = "free" | "weekly" | "monthly" | "yearly" | "enterprise" | "pro"

export const PLAN_RANK: Record<string, number> = {
  free: 0,
  weekly: 1,
  monthly: 2,
  yearly: 3,
  enterprise: 3,
  pro: 2,
}

export const PLAN_LABELS: Record<string, string> = {
  free: "未激活",
  weekly: "7天精选",
  monthly: "月度会员",
  yearly: "年费会员",
  enterprise: "企业版",
  pro: "专业版",
}

export const PLAN_TAG_TYPE: Record<string, string> = {
  free: "info",
  weekly: "warning",
  monthly: "success",
  yearly: "",
  enterprise: "danger",
  pro: "success",
}

/** 小红书店铺链接，可在 .env 设置 VITE_XHS_SHOP_URL */
export const XHS_SHOP_URL = import.meta.env.VITE_XHS_SHOP_URL || ""

export interface MenuItemDef {
  path: string
  label: string
  minPlan: IntelPlan
}

export const ALL_MENU_ITEMS: MenuItemDef[] = [
  { path: "/dashboard", label: "仪表盘", minPlan: "weekly" },
  { path: "/trends", label: "趋势分析", minPlan: "weekly" },
  { path: "/opportunities", label: "商业机会", minPlan: "weekly" },
  { path: "/risks", label: "风险预警", minPlan: "weekly" },
  { path: "/reports", label: "决策报告", minPlan: "weekly" },
  { path: "/topics", label: "选题库", minPlan: "monthly" },
  { path: "/signals", label: "平台信号", minPlan: "monthly" },
  { path: "/emotions", label: "用户情绪", minPlan: "yearly" },
]

export function planLabel(plan: string): string {
  return PLAN_LABELS[plan] || plan || "未知"
}

export function canAccessRoute(plan: string, path: string): boolean {
  const item = ALL_MENU_ITEMS.find((m) => m.path === path)
  if (!item) return true
  return (PLAN_RANK[plan] ?? 0) >= (PLAN_RANK[item.minPlan] ?? 0)
}

export function visibleMenuItems(plan: string): MenuItemDef[] {
  return ALL_MENU_ITEMS.filter((m) => canAccessRoute(plan, m.path))
}

export function upgradeTarget(plan: string): "monthly" | "yearly" | null {
  const rank = PLAN_RANK[plan] ?? 0
  if (rank < PLAN_RANK.monthly) return "monthly"
  if (rank < PLAN_RANK.yearly) return "yearly"
  return null
}

export function upgradeHint(plan: string): string {
  const target = upgradeTarget(plan)
  if (target === "monthly") return "升级月度会员，解锁选题库、平台信号与全部周报"
  if (target === "yearly") return "升级年费会员，解锁用户情绪库与全部月报"
  return ""
}

export const REPORT_TYPE_LABELS: Record<string, string> = {
  weekly: "周度决策报告",
  monthly: "月度深度报告",
  quarterly: "季度洞察",
  daily: "每日简报",
}
// AIGC END
