// AIGC START
/** 业务分类 / 报告类型 的标签配色，全站统一 */

export interface CategoryStyle {
  label: string
  type: "primary" | "success" | "warning" | "danger" | "info"
  accent: string
  bg: string
}

const DEFAULT_STYLE: CategoryStyle = {
  label: "",
  type: "info",
  accent: "#909399",
  bg: "rgba(144, 147, 153, 0.12)",
}

const CATEGORY_MAP: Record<string, Partial<CategoryStyle>> = {
  AI副业: { type: "primary", accent: "#409eff", bg: "rgba(64, 158, 255, 0.12)" },
  轻创业: { type: "success", accent: "#67c23a", bg: "rgba(103, 194, 58, 0.12)" },
  平台红利: { type: "warning", accent: "#e6a23c", bg: "rgba(230, 162, 60, 0.12)" },
  AI设计: { type: "primary", accent: "#a855f7", bg: "rgba(168, 85, 247, 0.12)" },
  AI直播: { type: "danger", accent: "#f56c6c", bg: "rgba(245, 108, 108, 0.12)" },
  虚拟产品: { type: "success", accent: "#10b981", bg: "rgba(16, 185, 129, 0.12)" },
  知识付费: { type: "warning", accent: "#f59e0b", bg: "rgba(245, 158, 11, 0.12)" },
  电商: { type: "info", accent: "#6366f1", bg: "rgba(99, 102, 241, 0.12)" },
}

const REPORT_TYPE_STYLES: Record<string, CategoryStyle> = {
  weekly: { label: "周度", type: "primary", accent: "#409eff", bg: "rgba(64, 158, 255, 0.1)" },
  monthly: { label: "月度", type: "success", accent: "#67c23a", bg: "rgba(103, 194, 58, 0.1)" },
  quarterly: { label: "季度", type: "warning", accent: "#e6a23c", bg: "rgba(230, 162, 60, 0.1)" },
  topic: { label: "选题", type: "warning", accent: "#e6a23c", bg: "rgba(230, 162, 60, 0.1)" },
  daily: { label: "日更", type: "info", accent: "#909399", bg: "rgba(144, 147, 153, 0.1)" },
  other: { label: "其他", type: "info", accent: "#909399", bg: "rgba(144, 147, 153, 0.1)" },
}

export function getCategoryStyle(category: string | undefined | null): CategoryStyle {
  if (!category) return { ...DEFAULT_STYLE, label: "未分类" }
  const hit = CATEGORY_MAP[category]
  if (hit) {
    return { label: category, type: hit.type ?? "info", accent: hit.accent!, bg: hit.bg!, ...hit }
  }
  return { label: category, type: "info", accent: "#606266", bg: "rgba(96, 98, 102, 0.1)" }
}

export function getReportTypeStyle(key: string): CategoryStyle {
  return REPORT_TYPE_STYLES[key] || REPORT_TYPE_STYLES.other
}

export function collectCategories<T>(items: T[], getter: (item: T) => string | undefined): string[] {
  const set = new Set<string>()
  for (const item of items) {
    const c = getter(item)?.trim()
    if (c) set.add(c)
  }
  return Array.from(set).sort((a, b) => a.localeCompare(b, "zh-CN"))
}
// AIGC END
