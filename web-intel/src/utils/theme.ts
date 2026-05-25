export interface DomainTheme {
  name: string
  primary: string
  accent: string
  bg: string
  emoji: string
  tiers: { high: string; mid: string; low: string }
  categories: string[]
}

export const DOMAIN_THEMES: Record<string, DomainTheme> = {
  education: {
    name: "教育·升学",
    primary: "#1E3A5F",
    accent: "#D4A843",
    bg: "#F8F9FA",
    emoji: "🎓",
    tiers: { high: "#059669", mid: "#D97706", low: "#DC2626" },
    categories: ["考研决策", "考公决策", "考编决策", "教资备考", "一建二建", "留学决策", "高考志愿", "考证资格", "专升本"],
  },
  career: {
    name: "职业·成长",
    primary: "#2D2D2D",
    accent: "#2563EB",
    bg: "#FAFAFA",
    emoji: "💼",
    tiers: { high: "#059669", mid: "#D97706", low: "#DC2626" },
    categories: ["职业选择", "职场转型", "技能学习", "面试求职", "跳槽评估", "行业选择"],
  },
  lifestyle: {
    name: "生活·消费",
    primary: "#3D3D3D",
    accent: "#EA580C",
    bg: "#FFF7ED",
    emoji: "🛒",
    tiers: { high: "#059669", mid: "#D97706", low: "#DC2626" },
    categories: ["育儿教育", "消费决策", "健康决策", "保险配置", "买房决策", "租房决策", "买车决策"],
  },
  business: {
    name: "商业·副业",
    primary: "#0F0F23",
    accent: "#E11D48",
    bg: "#FEF2F2",
    emoji: "💰",
    tiers: { high: "#059669", mid: "#D97706", low: "#DC2626" },
    categories: ["副业选择", "自媒体运营", "副业变现", "创业方向", "跨境电商", "知识付费"],
  },
  tech: {
    name: "科技·工具",
    primary: "#0A0A2E",
    accent: "#00D4AA",
    bg: "#F5F5FF",
    emoji: "🤖",
    tiers: { high: "#059669", mid: "#D97706", low: "#DC2626" },
    categories: ["AI工具选择", "效率工具", "编程学习", "技术选型", "硬件选购"],
  },
  creative: {
    name: "设计·创意",
    primary: "#1A1A2E",
    accent: "#E94560",
    bg: "#FFF5F5",
    emoji: "🎨",
    tiers: { high: "#059669", mid: "#D97706", low: "#DC2626" },
    categories: ["设计软件", "素材资源", "配色方案", "字体选择", "创意工具"],
  },
}

const CATEGORY_THEME_MAP: Record<string, string> = {}

for (const [themeKey, theme] of Object.entries(DOMAIN_THEMES)) {
  for (const cat of theme.categories) {
    CATEGORY_THEME_MAP[cat] = themeKey
  }
}

const KEYWORD_THEME_HINTS: [RegExp, string][] = [
  [/考研|考公|考编|教资|一建|二建|留学|高考|专升本|考证/i, "education"],
  [/职业|职场|面试|跳槽|行业|求职/i, "career"],
  [/育儿|消费|健康|保险|买房|租房|买车/i, "lifestyle"],
  [/副业|自媒体|变现|创业|跨境|知识付费|代运营/i, "business"],
  [/AI|工具|编程|技术|硬件|效率/i, "tech"],
  [/设计|素材|配色|字体|创意/i, "creative"],
]

export function getThemeByCategory(category: string): DomainTheme {
  if (!category) return DOMAIN_THEMES.business
  const themeKey = CATEGORY_THEME_MAP[category]
  if (themeKey) return DOMAIN_THEMES[themeKey]
  for (const [regex, key] of KEYWORD_THEME_HINTS) {
    if (regex.test(category)) return DOMAIN_THEMES[key]
  }
  return DOMAIN_THEMES.business
}

export function getThemeKeyByCategory(category: string): string {
  if (!category) return "business"
  const themeKey = CATEGORY_THEME_MAP[category]
  if (themeKey) return themeKey
  for (const [regex, key] of KEYWORD_THEME_HINTS) {
    if (regex.test(category)) return key
  }
  return "business"
}

export function getTierColor(tier: string, theme?: DomainTheme): string {
  const t = theme || DOMAIN_THEMES.business
  const map: Record<string, string> = { high: t.tiers.high, mid: t.tiers.mid, low: t.tiers.low }
  return map[tier?.toLowerCase()] || t.tiers.mid
}

export function getVerdictColor(verdict: string): { bg: string; border: string; text: string } {
  const map: Record<string, { bg: string; border: string; text: string }> = {
    RECOMMENDED: { bg: "#f0f9eb", border: "#67c23a", text: "#099268" },
    CAUTION: { bg: "#fdf6ec", border: "#e6a23c", text: "#d97706" },
    AVOID: { bg: "#fef0f0", border: "#f56c6c", text: "#dc2626" },
  }
  return map[verdict] || map.CAUTION
}

export function getScoreColor(score: number): string {
  if (score >= 80) return "#059669"
  if (score >= 60) return "#d97706"
  return "#dc2626"
}

export function getIntensityColor(intensity: number): string {
  if (intensity >= 0.7) return "#dc2626"
  if (intensity >= 0.4) return "#d97706"
  return "#059669"
}

export function applyThemeToElement(el: HTMLElement, theme: DomainTheme) {
  el.style.setProperty("--domain-primary", theme.primary)
  el.style.setProperty("--domain-accent", theme.accent)
  el.style.setProperty("--domain-bg", theme.bg)
}

export function getDirectionIcon(direction: string): string {
  const map: Record<string, string> = { rising: "↑", stable: "→", falling: "↓" }
  return map[direction?.toLowerCase()] || "→"
}

export function getDirectionLabel(direction: string): string {
  const map: Record<string, string> = { rising: "上升", stable: "稳定", falling: "下降" }
  return map[direction?.toLowerCase()] || direction
}
