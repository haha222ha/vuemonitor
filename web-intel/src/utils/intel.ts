import api from "@/utils/api"
import { ElMessage, ElMessageBox } from "element-plus"

interface CacheEntry<T> {
  data: T
  ts: number
}

const cache = new Map<string, CacheEntry<unknown>>()
const CACHE_TTL = 5 * 60 * 1000

export function getCached<T>(key: string): T | null {
  const entry = cache.get(key)
  if (!entry) return null
  if (Date.now() - entry.ts > CACHE_TTL) {
    cache.delete(key)
    return null
  }
  return entry.data as T
}

export function setCache<T>(key: string, data: T): void {
  cache.set(key, { data, ts: Date.now() })
}

export function clearCache(key?: string): void {
  if (key) cache.delete(key)
  else cache.clear()
}

export async function fetchWithCache<T>(key: string, url: string): Promise<T[]> {
  const cached = getCached<T[]>(key)
  if (cached) return cached
  const { data } = await api.get(url)
  const items = data?.items || data || []
  setCache(key, items)
  return items
}

export function isAdmin(): boolean {
  const token = localStorage.getItem("intel_token")
  if (!token) return false
  try {
    const parts = token.split(".")
    if (parts.length !== 3) return false
    const payload = JSON.parse(atob(parts[1]))
    return payload.role === "admin" || payload.role === "super_admin"
  } catch {
    return false
  }
}

export function exportJSON(data: unknown, filename: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = `${filename}_${new Date().toISOString().slice(0, 10)}.json`
  a.click()
  URL.revokeObjectURL(url)
}

export function exportCSV(items: Record<string, unknown>[], filename: string) {
  if (!items.length) return
  const keys = Object.keys(items[0]).filter((k) => typeof items[0][k] !== "object" || items[0][k] === null)
  const header = keys.join(",")
  const rows = items.map((item) =>
    keys.map((k) => {
      const v = item[k]
      if (v === null || v === undefined) return ""
      const s = String(v).replace(/"/g, '""')
      return `"${s}"`
    }).join(",")
  )
  const csv = "\uFEFF" + header + "\n" + rows.join("\n")
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = `${filename}_${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

export async function deleteItem(type: string, id: string, name: string): Promise<boolean> {
  try {
    await ElMessageBox.confirm(`确定删除「${name}」吗？此操作不可恢复。`, "删除确认", {
      confirmButtonText: "删除",
      cancelButtonText: "取消",
      type: "warning",
    })
    await api.delete(`/intel/data/${type}/${id}`)
    ElMessage.success("删除成功")
    return true
  } catch {
    return false
  }
}

export function formatValue(val: unknown): string {
  if (val === null || val === undefined) return "-"
  if (typeof val === "object") {
    if (Array.isArray(val)) return val.join("、")
    return JSON.stringify(val, null, 2)
  }
  return String(val)
}

export function truncate(text: string, max: number): string {
  if (!text) return ""
  return text.length > max ? text.slice(0, max) + "..." : text
}
