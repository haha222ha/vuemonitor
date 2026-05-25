export function platformTagType(platform: string) {
  const map: Record<string, string> = { xhs: "danger", taobao: "warning", jd: "primary", pdd: "success", douyin: "" };
  return map[platform] || "info";
}

export function statusTagType(status: string) {
  const map: Record<string, string> = { pending: "info", running: "", completed: "success", failed: "danger", cancelled: "warning" };
  return map[status] || "info";
}

export function statusLabel(status: string) {
  const map: Record<string, string> = { pending: "待执行", running: "运行中", completed: "已完成", failed: "失败", cancelled: "已取消" };
  return map[status] || status;
}

export function taskTypeLabel(type: string) {
  const map: Record<string, string> = { product: "商品采集", shop: "店铺采集", category: "品类采集" };
  return map[type] || type;
}