// AIGC START
/** 副业情报评分展示（机会判断 0–50 分制；趋势分可选隐藏） */

export function isDisplayableScore(score: unknown): boolean {
  const n = Number(score)
  return Number.isFinite(n) && n > 0
}

export function formatScore(score: unknown, suffix = "分"): string {
  if (!isDisplayableScore(score)) return ""
  return `${Math.round(Number(score))}${suffix}`
}

/** 商业机会 verdict_score：0–50 */
export function getOpportunityScoreColor(score: number): string {
  if (!isDisplayableScore(score)) return "#94a3b8"
  const n = Number(score)
  if (n >= 35) return "#059669"
  if (n >= 25) return "#d97706"
  return "#dc2626"
}

/** 趋势 opportunity_score：若有值按 0–100 或 0–50 自适应 */
export function getTrendScoreColor(score: number): string {
  if (!isDisplayableScore(score)) return "#94a3b8"
  const n = Number(score)
  const scale = n <= 50 ? 50 : 100
  const pct = n / scale
  if (pct >= 0.7) return "#059669"
  if (pct >= 0.5) return "#d97706"
  return "#dc2626"
}

export function opportunityScoreLabel(score: unknown): string {
  if (!isDisplayableScore(score)) return ""
  const n = Number(score)
  if (n >= 35) return "强烈推荐"
  if (n >= 25) return "谨慎推荐"
  return "观望"
}
// AIGC END
