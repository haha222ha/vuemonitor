// AIGC START
const DEMO_PATTERN = /测试|test\s|demo|示例|placeholder|mock|假数据/i

export function isDemoContent(...parts: (string | undefined | null)[]): boolean {
  const text = parts.filter(Boolean).join(" ")
  return DEMO_PATTERN.test(text)
}

export interface CategoryGroup<T> {
  category: string
  items: T[]
}

export function groupByCategory<T extends { category?: string }>(
  items: T[],
  fallback = "未分类",
): CategoryGroup<T>[] {
  const map = new Map<string, T[]>()
  for (const item of items) {
    const key = (item.category || fallback).trim() || fallback
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(item)
  }
  return Array.from(map.entries())
    .map(([category, groupItems]) => ({ category, items: groupItems }))
    .sort((a, b) => b.items.length - a.items.length)
}
// AIGC END
