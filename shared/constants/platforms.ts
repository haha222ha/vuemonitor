export type Platform = "xhs" | "douyin" | "taobao" | "jd" | "pdd";

export const PLATFORM_LABELS: Record<Platform, string> = {
  xhs: "小红书",
  douyin: "抖音",
  taobao: "淘宝",
  jd: "京东",
  pdd: "拼多多",
};

export const PLATFORM_LIST: Platform[] = ["xhs", "douyin", "taobao", "jd", "pdd"];

export const XHS_URL_PATTERNS = {
  explore: /^https?:\/\/www\.xiaohongshu\.com\/explore\/([a-f0-9]+)/,
  note: /^https?:\/\/www\.xiaohongshu\.com\/discovery\/item\/([a-f0-9]+)/,
  goods: /^https?:\/\/www\.xiaohongshu\.com\/goods-detail\/([a-f0-9]+)/,
  shortNote: /^https?:\/\/xhslink\.com\/\w+/,
  search: /^https?:\/\/www\.xiaohongshu\.com\/search_result\?/,
  user: /^https?:\/\/www\.xiaohongshu\.com\/user\/profile\/([a-f0-9]+)/,
};

export function parseXHSUrl(url: string): { type: "note" | "user" | "search" | "goods" | "unknown"; id: string } {
  const goodsMatch = url.match(XHS_URL_PATTERNS.goods);
  if (goodsMatch) return { type: "goods", id: goodsMatch[1] };

  const exploreMatch = url.match(XHS_URL_PATTERNS.explore);
  if (exploreMatch) return { type: "note", id: exploreMatch[1] };

  const noteMatch = url.match(XHS_URL_PATTERNS.note);
  if (noteMatch) return { type: "note", id: noteMatch[1] };

  const userMatch = url.match(XHS_URL_PATTERNS.user);
  if (userMatch) return { type: "user", id: userMatch[1] };

  if (XHS_URL_PATTERNS.search.test(url)) return { type: "search", id: "" };

  if (XHS_URL_PATTERNS.shortNote.test(url)) return { type: "note", id: "short_url" };

  return { type: "unknown", id: "" };
}

export function buildXHSNoteUrl(noteId: string): string {
  return `https://www.xiaohongshu.com/explore/${noteId}`;
}

export function buildXHSGoodsUrl(goodsId: string): string {
  return `https://www.xiaohongshu.com/goods-detail/${goodsId}`;
}

export const DOUYIN_URL_PATTERNS = {
  video: /^https?:\/\/www\.douyin\.com\/video\/(\d+)/,
  user: /^https?:\/\/www\.douyin\.com\/user\/([A-Za-z0-9_-]+)/,
  short: /^https?:\/\/v\.douyin\.com\/\w+/,
  search: /^https?:\/\/www\.douyin\.com\/search\?/,
  live: /^https?:\/\/live\.douyin\.com\/(\w+)/,
};

export function parseDouyinUrl(url: string): { type: "video" | "user" | "search" | "live" | "unknown"; id: string } {
  const videoMatch = url.match(DOUYIN_URL_PATTERNS.video);
  if (videoMatch) return { type: "video", id: videoMatch[1] };

  const userMatch = url.match(DOUYIN_URL_PATTERNS.user);
  if (userMatch) return { type: "user", id: userMatch[1] };

  if (DOUYIN_URL_PATTERNS.live.test(url)) {
    const liveMatch = url.match(DOUYIN_URL_PATTERNS.live);
    if (liveMatch) return { type: "live", id: liveMatch[1] };
  }

  if (DOUYIN_URL_PATTERNS.search.test(url)) return { type: "search", id: "" };

  if (DOUYIN_URL_PATTERNS.short.test(url)) return { type: "video", id: "short_url" };

  return { type: "unknown", id: "" };
}

export function buildDouyinVideoUrl(id: string): string {
  return `https://www.douyin.com/video/${id}`;
}

export function buildDouyinUserUrl(secUid: string): string {
  return `https://www.douyin.com/user/${secUid}`;
}

export const TAOBAO_URL_PATTERNS = {
  item: /^https?:\/\/item\.taobao\.com\/item\.htm\?.*id=(\d+)/,
  shop: /^https?:\/\/shop\d+\.taobao\.com/,
  search: /^https?:\/\/s\.taobao\.com\/search\?/,
  detail: /^https?:\/\/detail\.taobao\.com\/item\.htm\?.*id=(\d+)/,
  short: /^https?:\/\/m\.tb\.cn\/\w+/,
};

export function parseTaobaoUrl(url: string): { type: "item" | "shop" | "search" | "unknown"; id: string } {
  const itemMatch = url.match(TAOBAO_URL_PATTERNS.item);
  if (itemMatch) return { type: "item", id: itemMatch[1] };

  const detailMatch = url.match(TAOBAO_URL_PATTERNS.detail);
  if (detailMatch) return { type: "item", id: detailMatch[1] };

  if (TAOBAO_URL_PATTERNS.shop.test(url)) return { type: "shop", id: "" };

  if (TAOBAO_URL_PATTERNS.search.test(url)) return { type: "search", id: "" };

  if (TAOBAO_URL_PATTERNS.short.test(url)) return { type: "item", id: "short_url" };

  return { type: "unknown", id: "" };
}

export function buildTaobaoItemUrl(id: string): string {
  return `https://item.taobao.com/item.htm?id=${id}`;
}

export const JD_URL_PATTERNS = {
  item: /^https?:\/\/item\.jd\.com\/(\d+)\.html/,
  search: /^https?:\/\/search\.jd\.com\/Search\?/,
  shop: /^https?:\/\/shop\.jd\.com/,
  short: /^https?:\/\/u\.jd\.com\/\w+/,
};

export function parseJdUrl(url: string): { type: "item" | "search" | "shop" | "unknown"; id: string } {
  const itemMatch = url.match(JD_URL_PATTERNS.item);
  if (itemMatch) return { type: "item", id: itemMatch[1] };

  if (JD_URL_PATTERNS.shop.test(url)) return { type: "shop", id: "" };

  if (JD_URL_PATTERNS.search.test(url)) return { type: "search", id: "" };

  if (JD_URL_PATTERNS.short.test(url)) return { type: "item", id: "short_url" };

  return { type: "unknown", id: "" };
}

export function buildJdItemUrl(id: string): string {
  return `https://item.jd.com/${id}.html`;
}

export const PDD_URL_PATTERNS = {
  goods: /^https?:\/\/mobile\.yangkeduo\.com\/goods\.html\?.*goods_id=(\d+)/,
  goods2: /^https?:\/\/yangkeduo\.cn\/goods\.html\?.*goods_id=(\d+)/,
  search: /^https?:\/\/mobile\.yangkeduo\.com\/search_result\.html\?/,
  short: /^https?:\/\/pdd\.lnk\.to\/\w+/,
};

export function parsePddUrl(url: string): { type: "goods" | "search" | "unknown"; id: string } {
  const goodsMatch = url.match(PDD_URL_PATTERNS.goods);
  if (goodsMatch) return { type: "goods", id: goodsMatch[1] };

  const goods2Match = url.match(PDD_URL_PATTERNS.goods2);
  if (goods2Match) return { type: "goods", id: goods2Match[1] };

  if (PDD_URL_PATTERNS.search.test(url)) return { type: "search", id: "" };

  if (PDD_URL_PATTERNS.short.test(url)) return { type: "goods", id: "short_url" };

  return { type: "unknown", id: "" };
}

export function buildPddGoodsUrl(id: string): string {
  return `https://mobile.yangkeduo.com/goods.html?goods_id=${id}`;
}

export type ParsedResult = { platform: Platform; type: string; id: string };

export function parsePlatformUrl(url: string): ParsedResult | null {
  const xhsResult = parseXHSUrl(url);
  if (xhsResult.type !== "unknown") {
    return { platform: "xhs", type: xhsResult.type, id: xhsResult.id };
  }

  const douyinResult = parseDouyinUrl(url);
  if (douyinResult.type !== "unknown") {
    return { platform: "douyin", type: douyinResult.type, id: douyinResult.id };
  }

  const taobaoResult = parseTaobaoUrl(url);
  if (taobaoResult.type !== "unknown") {
    return { platform: "taobao", type: taobaoResult.type, id: taobaoResult.id };
  }

  const jdResult = parseJdUrl(url);
  if (jdResult.type !== "unknown") {
    return { platform: "jd", type: jdResult.type, id: jdResult.id };
  }

  const pddResult = parsePddUrl(url);
  if (pddResult.type !== "unknown") {
    return { platform: "pdd", type: pddResult.type, id: pddResult.id };
  }

  return null;
}