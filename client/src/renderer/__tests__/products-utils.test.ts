import { describe, it, expect } from "vitest";

function formatNumber(num: number): string {
  if (num >= 10000) return `${(num / 10000).toFixed(1)}万`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}k`;
  return String(num);
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function lifecycleTagType(stage: string): "" | "success" | "warning" | "danger" | "info" {
  const map: Record<string, "" | "success" | "warning" | "danger" | "info"> = {
    new: "warning", growth: "success", rising: "success", stable: "info", declining: "danger", decline: "danger", mature: "info",
  };
  return map[stage] || "info";
}

function lifecycleLabel(stage: string): string {
  const map: Record<string, string> = { new: "新品期", growth: "成长期", rising: "上升期", stable: "稳定期", declining: "衰退期", decline: "衰退期", mature: "成熟期" };
  return map[stage] || stage;
}

function trendIcon(trend: string) {
  if (trend === "上升") return "📈";
  if (trend === "下降") return "📉";
  return "➡️";
}

describe("formatNumber", () => {
  it("formats numbers under 1000 as-is", () => {
    expect(formatNumber(0)).toBe("0");
    expect(formatNumber(999)).toBe("999");
  });

  it("formats thousands with k suffix", () => {
    expect(formatNumber(1000)).toBe("1.0k");
    expect(formatNumber(5500)).toBe("5.5k");
    expect(formatNumber(9999)).toBe("10.0k");
  });

  it("formats ten-thousands with 万 suffix", () => {
    expect(formatNumber(10000)).toBe("1.0万");
    expect(formatNumber(15000)).toBe("1.5万");
    expect(formatNumber(100000)).toBe("10.0万");
  });
});

describe("formatDate", () => {
  it("formats ISO date string correctly", () => {
    const result = formatDate("2026-05-22T14:30:00Z");
    expect(result).toContain("/");
    expect(result).toContain(":");
  });

  it("pads minutes with leading zero", () => {
    const result = formatDate("2026-05-22T08:05:00Z");
    expect(result).toContain(":05");
  });
});

describe("lifecycleTagType", () => {
  it("returns correct tag types for known stages", () => {
    expect(lifecycleTagType("new")).toBe("warning");
    expect(lifecycleTagType("growth")).toBe("success");
    expect(lifecycleTagType("stable")).toBe("info");
    expect(lifecycleTagType("declining")).toBe("danger");
    expect(lifecycleTagType("mature")).toBe("info");
  });

  it("returns info for unknown stages", () => {
    expect(lifecycleTagType("unknown")).toBe("info");
    expect(lifecycleTagType("")).toBe("info");
  });
});

describe("lifecycleLabel", () => {
  it("returns Chinese labels for known stages", () => {
    expect(lifecycleLabel("new")).toBe("新品期");
    expect(lifecycleLabel("growth")).toBe("成长期");
    expect(lifecycleLabel("rising")).toBe("上升期");
    expect(lifecycleLabel("stable")).toBe("稳定期");
    expect(lifecycleLabel("declining")).toBe("衰退期");
    expect(lifecycleLabel("mature")).toBe("成熟期");
  });

  it("returns raw stage for unknown values", () => {
    expect(lifecycleLabel("custom")).toBe("custom");
  });
});

describe("trendIcon", () => {
  it("returns correct emoji for trend directions", () => {
    expect(trendIcon("上升")).toBe("📈");
    expect(trendIcon("下降")).toBe("📉");
    expect(trendIcon("稳定")).toBe("➡️");
    expect(trendIcon("")).toBe("➡️");
  });
});
