import { describe, it, expect } from "vitest";

function downsampleData<T>(data: T[], maxPoints: number): T[] {
  if (data.length <= maxPoints) return data;
  const step = data.length / maxPoints;
  const result: T[] = [data[0]];
  for (let i = 1; i < maxPoints - 1; i++) {
    result.push(data[Math.round(i * step)]);
  }
  result.push(data[data.length - 1]);
  return result;
}

function detectAnomalies(values: (number | null)[], metricType: string) {
  const valid = values.filter((v): v is number => v !== null);
  if (valid.length < 3) return [];

  const mean = valid.reduce((a, b) => a + b, 0) / valid.length;
  const std = Math.sqrt(valid.reduce((a, b) => a + (b - mean) ** 2, 0) / valid.length);
  if (std === 0) return [];

  const anomalies: { coord: [number, number]; value: number; type: string; changeRate: number }[] = [];
  const THRESHOLD = 2;

  values.forEach((v, i) => {
    if (v === null) return;
    const zScore = Math.abs(v - mean) / std;
    if (zScore <= THRESHOLD) return;

    let prevVal: number | null = null;
    for (let j = i - 1; j >= 0; j--) {
      if (values[j] !== null) { prevVal = values[j]; break; }
    }

    let changeRate = 0;
    if (prevVal !== null && prevVal !== 0) {
      changeRate = ((v - prevVal) / Math.abs(prevVal)) * 100;
    } else if (prevVal === 0 && v > 0) {
      changeRate = 100;
    }

    let type = "other";
    if (metricType === "price") {
      type = v > mean ? "price_spike" : "price_drop";
    } else if (metricType === "sales") {
      type = v > mean ? "sales_surge" : "sales_drop";
    }

    anomalies.push({ coord: [i, v], value: v, type, changeRate });
  });

  return anomalies;
}

describe("downsampleData", () => {
  it("returns data as-is when under maxPoints", () => {
    const data = [1, 2, 3, 4, 5];
    expect(downsampleData(data, 10)).toEqual(data);
  });

  it("returns data as-is when equal to maxPoints", () => {
    const data = [1, 2, 3, 4, 5];
    expect(downsampleData(data, 5)).toEqual(data);
  });

  it("preserves first and last elements", () => {
    const data = Array.from({ length: 1000 }, (_, i) => i);
    const result = downsampleData(data, 100);
    expect(result[0]).toBe(0);
    expect(result[result.length - 1]).toBe(999);
  });

  it("returns exactly maxPoints elements", () => {
    const data = Array.from({ length: 1000 }, (_, i) => i);
    const result = downsampleData(data, 100);
    expect(result).toHaveLength(100);
  });

  it("handles small maxPoints", () => {
    const data = Array.from({ length: 100 }, (_, i) => i * 2);
    const result = downsampleData(data, 3);
    expect(result).toHaveLength(3);
    expect(result[0]).toBe(0);
    expect(result[2]).toBe(198);
  });
});

describe("detectAnomalies", () => {
  it("returns empty for less than 3 values", () => {
    expect(detectAnomalies([1, 2], "price")).toEqual([]);
    expect(detectAnomalies([], "price")).toEqual([]);
  });

  it("returns empty when all values are identical (std=0)", () => {
    expect(detectAnomalies([5, 5, 5, 5, 5], "price")).toEqual([]);
  });

  it("detects price spike anomaly", () => {
    const values = [10, 10, 10, 10, 100, 10, 10, 10, 10, 10];
    const anomalies = detectAnomalies(values, "price");
    expect(anomalies.length).toBeGreaterThan(0);
    expect(anomalies[0].type).toBe("price_spike");
  });

  it("detects price drop anomaly", () => {
    const values = [100, 100, 100, 100, 1, 100, 100, 100, 100, 100];
    const anomalies = detectAnomalies(values, "price");
    expect(anomalies.length).toBeGreaterThan(0);
    expect(anomalies[0].type).toBe("price_drop");
  });

  it("detects sales surge anomaly", () => {
    const values = [10, 10, 10, 10, 500, 10, 10, 10, 10, 10];
    const anomalies = detectAnomalies(values, "sales");
    expect(anomalies.length).toBeGreaterThan(0);
    expect(anomalies[0].type).toBe("sales_surge");
  });

  it("detects sales drop anomaly", () => {
    const values = [100, 100, 100, 100, 1, 100, 100, 100, 100, 100];
    const anomalies = detectAnomalies(values, "sales");
    expect(anomalies.length).toBeGreaterThan(0);
    expect(anomalies[0].type).toBe("sales_drop");
  });

  it("handles null values gracefully", () => {
    const values: (number | null)[] = [10, null, 10, null, 100, null, 10, 10, 10, 10];
    const anomalies = detectAnomalies(values, "price");
    expect(anomalies.length).toBeGreaterThan(0);
  });

  it("calculates changeRate correctly", () => {
    const values = [100, 100, 100, 100, 500, 100, 100, 100, 100, 100];
    const anomalies = detectAnomalies(values, "price");
    expect(anomalies.length).toBeGreaterThan(0);
    expect(anomalies[0].changeRate).toBe(400);
  });
});
