// AIGC START
/** 决策报告展示分类（与上传文件名、标题推断一致） */

export type ReportDisplayType = "weekly" | "monthly" | "quarterly" | "topic" | "daily" | "other"

export interface ReportListItem {
  id: string
  report_type: string
  display_type?: string
  title: string
  week_number?: string
  report_date?: string
  content_html?: string
  file_path?: string
  topic_id?: string
}

export const REPORT_SECTION_ORDER: ReportDisplayType[] = [
  "weekly",
  "monthly",
  "quarterly",
  "topic",
  "daily",
  "other",
]

export const REPORT_SECTION_META: Record<
  ReportDisplayType,
  { title: string; hint: string }
> = {
  weekly: { title: "周度决策报告", hint: "每周副业决策周报，按周次归档" },
  monthly: { title: "月度深度报告", hint: "月度复盘与策略汇总" },
  quarterly: { title: "季度洞察", hint: "季度趋势与机会盘点" },
  topic: { title: "选题深度报告", hint: "单选题完整决策路径（HTML）" },
  daily: { title: "每日简报", hint: "日更要点摘要" },
  other: { title: "其他报告", hint: "未归类的历史报告" },
}

function extractFilename(path: string): string {
  const clean = path.split("?")[0]
  return clean.split("/").pop() || ""
}

function extractTopicId(title: string, filename: string): string {
  const m = title.match(/T20\d{8,}/) || filename.match(/T20\d{8,}/)
  return m ? m[0] : ""
}

/** 根据文件名与标题推断展示分类，避免周度与选题报告混在同一列表 */
export function normalizeReportDisplayType(item: ReportListItem): ReportDisplayType {
  if (item.display_type && REPORT_SECTION_ORDER.includes(item.display_type as ReportDisplayType)) {
    return item.display_type as ReportDisplayType
  }

  const path = item.content_html || item.file_path || ""
  const fn = extractFilename(path).toLowerCase()
  const title = item.title || ""

  if (fn.startsWith("weekly_")) return "weekly"
  if (fn.startsWith("monthly_")) return "monthly"
  if (fn.startsWith("quarterly_")) return "quarterly"
  if (fn.startsWith("daily_")) return "daily"

  if (/^DIH-|选题|路径决策|副业决策报告/i.test(title) || /^DIH-/i.test(fn)) {
    return "topic"
  }
  if (/^T20\d{8,}/.test(title) || /^T20\d{8,}/.test(fn)) {
    return "topic"
  }
  if (item.report_type === "topic") return "topic"
  if (item.report_type === "monthly") return "monthly"
  if (item.report_type === "quarterly") return "quarterly"
  if (item.report_type === "daily") return "daily"
  if (item.report_type === "weekly" && item.week_number) return "weekly"

  return (item.report_type as ReportDisplayType) || "other"
}

export function enrichReportItem(item: ReportListItem): ReportListItem {
  const path = item.content_html || item.file_path || ""
  const fn = extractFilename(path)
  const display_type = normalizeReportDisplayType(item)
  const topic_id = extractTopicId(item.title, fn)
  return { ...item, display_type, topic_id: topic_id || undefined }
}

export function sortReports(items: ReportListItem[]): ReportListItem[] {
  return [...items].sort((a, b) => {
    const da = a.report_date ? new Date(a.report_date).getTime() : 0
    const db = b.report_date ? new Date(b.report_date).getTime() : 0
    return db - da
  })
}

export interface ReportSection {
  key: ReportDisplayType
  title: string
  hint: string
  items: ReportListItem[]
}

export function groupReportsBySection(items: ReportListItem[]): ReportSection[] {
  const enriched = sortReports(items.map(enrichReportItem))
  const buckets = new Map<ReportDisplayType, ReportListItem[]>()

  for (const key of REPORT_SECTION_ORDER) {
    buckets.set(key, [])
  }

  for (const item of enriched) {
    const key = normalizeReportDisplayType(item)
    buckets.get(key)!.push(item)
  }

  return REPORT_SECTION_ORDER.map((key) => ({
    key,
    title: REPORT_SECTION_META[key].title,
    hint: REPORT_SECTION_META[key].hint,
    items: buckets.get(key) || [],
  })).filter((s) => s.items.length > 0)
}
// AIGC END
