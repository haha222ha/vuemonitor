import api from "@/utils/api"
import { ElMessage, ElMessageBox } from "element-plus"

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
