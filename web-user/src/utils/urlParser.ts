interface ParsedURL {
  platform: string;
  targetType: string;
  targetId: string;
  originalUrl: string;
}

const URL_PATTERNS: {
  pattern: RegExp;
  platform: string;
  targetType: string;
  extractId: (match: RegExpMatchArray) => string;
}[] = [
  {
    pattern: /xiaohongshu\.com\/explore\/([a-f0-9]+)/i,
    platform: "xhs",
    targetType: "product_id",
    extractId: (m) => m[1],
  },
  {
    pattern: /xiaohongshu\.com\/discovery\/item\/([a-f0-9]+)/i,
    platform: "xhs",
    targetType: "product_id",
    extractId: (m) => m[1],
  },
  {
    pattern: /xiaohongshu\.com\/goods\/([a-f0-9]+)/i,
    platform: "xhs",
    targetType: "product_id",
    extractId: (m) => m[1],
  },
  {
    pattern: /xiaohongshu\.com\/user\/profile\/([a-f0-9]+)/i,
    platform: "xhs",
    targetType: "shop_id",
    extractId: (m) => m[1],
  },
  {
    pattern: /xiaohongshu\.com\/search_result\/\?keyword=([^&]+)/i,
    platform: "xhs",
    targetType: "category_url",
    extractId: (m) => decodeURIComponent(m[1]),
  },
  {
    pattern: /douyin\.com\/video\/(\d+)/i,
    platform: "douyin",
    targetType: "product_id",
    extractId: (m) => m[1],
  },
  {
    pattern: /douyin\.com\/user\/([A-Za-z0-9_-]+)/i,
    platform: "douyin",
    targetType: "shop_id",
    extractId: (m) => m[1],
  },
  {
    pattern: /item\.taobao\.com\/item\.htm.*[?&]id=(\d+)/i,
    platform: "taobao",
    targetType: "product_id",
    extractId: (m) => m[1],
  },
  {
    pattern: /taobao\.com\/shop\/view_shop\.htm.*[?&]user_number_id=(\d+)/i,
    platform: "taobao",
    targetType: "shop_id",
    extractId: (m) => m[1],
  },
  {
    pattern: /detail\.tmall\.com\/item\.htm.*[?&]id=(\d+)/i,
    platform: "taobao",
    targetType: "product_id",
    extractId: (m) => m[1],
  },
  {
    pattern: /item\.jd\.com\/(\d+)\.html/i,
    platform: "jd",
    targetType: "product_id",
    extractId: (m) => m[1],
  },
  {
    pattern: /jd\.com\/shop\/(\d+)/i,
    platform: "jd",
    targetType: "shop_id",
    extractId: (m) => m[1],
  },
  {
    pattern: /mobile\.yangkeduo\.com\/goods\.html.*[?&]goods_id=(\d+)/i,
    platform: "pdd",
    targetType: "product_id",
    extractId: (m) => m[1],
  },
  {
    pattern: /pinduoduo\.com\/goods\.html.*[?&]goods_id=(\d+)/i,
    platform: "pdd",
    targetType: "product_id",
    extractId: (m) => m[1],
  },
];

const PLATFORM_ID_PATTERNS: {
  pattern: RegExp;
  platform: string;
  targetType: string;
}[] = [
  { pattern: /^[a-f0-9]{24}$/, platform: "xhs", targetType: "product_id" },
  { pattern: /^\d{19}$/, platform: "douyin", targetType: "product_id" },
  { pattern: /^\d{9,12}$/, platform: "taobao", targetType: "product_id" },
  { pattern: /^\d{6,8}$/, platform: "jd", targetType: "product_id" },
];

export function parseURL(input: string): ParsedURL | null {
  const trimmed = input.trim();
  if (!trimmed) return null;

  for (const config of URL_PATTERNS) {
    const match = trimmed.match(config.pattern);
    if (match) {
      return {
        platform: config.platform,
        targetType: config.targetType,
        targetId: config.extractId(match),
        originalUrl: trimmed,
      };
    }
  }

  return null;
}

export function parseBatchInput(text: string): ParsedURL[] {
  const lines = text.split(/[\n,;，；]+/).map((s) => s.trim()).filter(Boolean);
  const results: ParsedURL[] = [];

  for (const line of lines) {
    const parsed = parseURL(line);
    if (parsed) {
      results.push(parsed);
    } else {
      for (const config of PLATFORM_ID_PATTERNS) {
        if (config.pattern.test(line)) {
          results.push({
            platform: config.platform,
            targetType: config.targetType,
            targetId: line,
            originalUrl: line,
          });
          break;
        }
      }
    }
  }

  return results;
}

export function detectPlatformFromInput(text: string): string {
  const parsed = parseURL(text.trim());
  if (parsed) return parsed.platform;

  const lower = text.toLowerCase();
  if (lower.includes("xiaohongshu") || lower.includes("xhs")) return "xhs";
  if (lower.includes("douyin") || lower.includes("抖音")) return "douyin";
  if (lower.includes("taobao") || lower.includes("tmall") || lower.includes("淘宝")) return "taobao";
  if (lower.includes("jd.com") || lower.includes("京东") || lower.includes("jd")) return "jd";
  if (lower.includes("pinduoduo") || lower.includes("yangkeduo") || lower.includes("拼多多")) return "pdd";

  return "";
}

export const PLATFORM_ICONS: Record<string, string> = {
  xhs: "📕",
  douyin: "🎵",
  taobao: "🛒",
  jd: "🏪",
  pdd: "🍊",
};

export const PLATFORM_COLORS: Record<string, string> = {
  xhs: "#ff2442",
  douyin: "#161823",
  taobao: "#ff5000",
  jd: "#e1251b",
  pdd: "#e02e24",
};
