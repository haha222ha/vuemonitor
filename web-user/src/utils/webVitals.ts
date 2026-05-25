type MetricName = "CLS" | "FCP" | "FID" | "INP" | "LCP" | "TTFB";
type MetricRating = "good" | "needs-improvement" | "poor";

interface WebVitalMetric {
  name: MetricName;
  value: number;
  rating: MetricRating;
  delta: number;
  navigationType: string;
}

const REPORT_URL = "/api/v1/monitoring/web-vitals";
const QUEUE: WebVitalMetric[] = [];
let flushTimer: ReturnType<typeof setTimeout> | null = null;

function getRating(name: MetricName, value: number): MetricRating {
  const thresholds: Record<MetricName, [number, number]> = {
    CLS: [0.1, 0.25],
    FCP: [1800, 3000],
    FID: [100, 300],
    INP: [200, 500],
    LCP: [2500, 4000],
    TTFB: [800, 1800],
  };
  const [good, poor] = thresholds[name];
  if (value <= good) return "good";
  if (value <= poor) return "needs-improvement";
  return "poor";
}

function observeLCP() {
  try {
    const po = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      const last = entries[entries.length - 1];
      queueMetric("LCP", last.startTime);
    });
    po.observe({ type: "largest-contentful-paint", buffered: true });
  } catch {}
}

function observeCLS() {
  try {
    let clsValue = 0;
    const po = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        if (!(entry as any).hadRecentInput) {
          clsValue += (entry as any).value;
        }
      }
      queueMetric("CLS", clsValue);
    });
    po.observe({ type: "layout-shift", buffered: true });
  } catch {}
}

function observeFID() {
  try {
    const po = new PerformanceObserver((list) => {
      const first = list.getEntries()[0];
      if (first) {
        queueMetric("FID", (first as any).processingStart - first.startTime);
      }
    });
    po.observe({ type: "first-input", buffered: true });
  } catch {}
}

function observeINP() {
  try {
    let maxINP = 0;
    const po = new PerformanceObserver((list) => {
      for (const entry of list.getEntries()) {
        const duration = (entry as any).duration || 0;
        if (duration > maxINP) {
          maxINP = duration;
        }
      }
      queueMetric("INP", maxINP);
    });
    po.observe({ type: "event", buffered: true });
  } catch {}
}

function measureTTFB() {
  try {
    const nav = performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming;
    if (nav) {
      queueMetric("TTFB", nav.responseStart - nav.requestStart);
    }
  } catch {}
}

function measureFCP() {
  try {
    const fcp = performance.getEntriesByName("first-contentful-paint")[0];
    if (fcp) {
      queueMetric("FCP", fcp.startTime);
    }
  } catch {}
}

function queueMetric(name: MetricName, value: number) {
  const metric: WebVitalMetric = {
    name,
    value: Math.round(value * 100) / 100,
    rating: getRating(name, value),
    delta: value,
    navigationType: performance.getEntriesByType("navigation")[0]
      ? (performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming).type
      : "unknown",
  };
  QUEUE.push(metric);
  scheduleFlush();
}

function scheduleFlush() {
  if (flushTimer) return;
  flushTimer = setTimeout(flush, 3000);
}

async function flush() {
  flushTimer = null;
  if (QUEUE.length === 0) return;

  const metrics = QUEUE.splice(0);
  try {
    if (navigator.sendBeacon) {
      const blob = new Blob([JSON.stringify({ metrics })], { type: "application/json" });
      navigator.sendBeacon(REPORT_URL, blob);
    } else {
      fetch(REPORT_URL, {
        method: "POST",
        body: JSON.stringify({ metrics }),
        headers: { "Content-Type": "application/json" },
        keepalive: true,
      });
    }
  } catch {}
}

export function initWebVitals() {
  if (typeof window === "undefined" || !("PerformanceObserver" in window)) return;

  measureTTFB();
  measureFCP();
  observeLCP();
  observeCLS();
  observeFID();
  observeINP();

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") {
      flush();
    }
  });
}
