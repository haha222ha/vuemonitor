export type Platform = "xhs";

export const PLATFORM_LABELS: Record<Platform, string> = {
  xhs: "小红书",
};

export const PLATFORM_LIST: Platform[] = ["xhs"];

export const CURRENT_PLATFORM: Platform = "xhs";

export const XHS_URL_PATTERNS = {
  explore: /^https?:\/\/www\.xiaohongshu\.com\/explore\/([a-f0-9]+)/,
  note: /^https?:\/\/www\.xiaohongshu\.com\/discovery\/item\/([a-f0-9]+)/,
  shortNote: /^https?:\/\/xhslink\.com\/\w+/,
  search: /^https?:\/\/www\.xiaohongshu\.com\/search_result\?/,
  user: /^https?:\/\/www\.xiaohongshu\.com\/user\/profile\/([a-f0-9]+)/,
};

export function parseXHSUrl(url: string): { type: "note" | "user" | "search" | "unknown"; id: string } {
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
