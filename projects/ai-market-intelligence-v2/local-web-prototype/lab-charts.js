/** SVG 雷达图（纯 JS，无第三方库） */
const RADAR_COLORS = ["#0071e3", "#34c759", "#ff9500", "#5856d6", "#ff3b30"];

/** HTML 转义，防止 innerHTML 注入 XSS */
export function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, m => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[m]));
}

function polar(cx, cy, r, angleDeg) {
  const a = ((angleDeg - 90) * Math.PI) / 180;
  return [cx + r * Math.cos(a), cy + r * Math.sin(a)];
}

export function renderRadar(container, series, labels) {
  const n = labels.length;
  const cx = 160, cy = 160, maxR = 120;
  const gridLevels = [25, 50, 75, 100];

  let svg = `<svg viewBox="0 0 320 320" class="radar-svg" role="img" aria-label="类目对比雷达图">`;

  gridLevels.forEach(level => {
    const r = (level / 100) * maxR;
    const pts = labels.map((_, i) => polar(cx, cy, r, (360 / n) * i).join(",")).join(" ");
    svg += `<polygon points="${pts}" fill="none" stroke="#e5e5ea" stroke-width="1"/>`;
  });

  labels.forEach((label, i) => {
    const [x, y] = polar(cx, cy, maxR, (360 / n) * i);
    svg += `<line x1="${cx}" y1="${cy}" x2="${x}" y2="${y}" stroke="#e5e5ea"/>`;
    const [lx, ly] = polar(cx, cy, maxR + 18, (360 / n) * i);
    svg += `<text x="${lx}" y="${ly}" text-anchor="middle" dominant-baseline="middle" font-size="11" fill="#6e6e73">${esc(label)}</text>`;
  });

  series.forEach((s, si) => {
    const color = RADAR_COLORS[si % RADAR_COLORS.length];
    const vals = labels.map(l => s.radar[l] ?? 0);
    const pts = vals.map((v, i) => polar(cx, cy, (v / 100) * maxR, (360 / n) * i).join(",")).join(" ");
    svg += `<polygon points="${pts}" fill="${color}" fill-opacity="0.2" stroke="${color}" stroke-width="2"/>`;
  });

  svg += "</svg>";
  container.innerHTML = svg;

  const legend = document.createElement("div");
  legend.className = "radar-legend";
  legend.innerHTML = series.map((s, i) =>
    `<span><i style="background:${RADAR_COLORS[i % RADAR_COLORS.length]}"></i>${s.category}</span>`
  ).join("");
  container.appendChild(legend);
}

/** 折线图 SVG */
export function renderLineChart(container, points, key, label, color = "#0071e3") {
  if (!points.length) {
    container.innerHTML = "<p class='muted'>暂无数据</p>";
    return;
  }
  const w = 400, h = 120, pad = 24;
  const vals = points.map(p => Number(p[key]) || 0);
  const minV = Math.min(...vals, 0);
  const maxV = Math.max(...vals, 100);
  const range = maxV - minV || 1;

  const coords = points.map((p, i) => {
    const x = pad + (i / Math.max(points.length - 1, 1)) * (w - pad * 2);
    const y = h - pad - ((Number(p[key]) - minV) / range) * (h - pad * 2);
    return [x, y];
  });
  const poly = coords.map(c => c.join(",")).join(" ");
  const area = `${pad},${h - pad} ${poly} ${w - pad},${h - pad}`;

  container.innerHTML = `
    <div class="chart-title">${label}</div>
    <svg viewBox="0 0 ${w} ${h}" class="line-chart" role="img">
      <polygon points="${area}" fill="${color}" fill-opacity="0.12"/>
      <polyline points="${poly}" fill="none" stroke="${color}" stroke-width="2"/>
      ${coords.map((c, i) => `<circle cx="${c[0]}" cy="${c[1]}" r="3" fill="${color}"/>`).join("")}
    </svg>
    <div style="font-size:11px;color:#6e6e73;display:flex;justify-content:space-between;margin-top:4px">
      <span>${esc(points[0].date)}</span><span>${esc(points[points.length - 1].date)}</span>
    </div>`;
}

export async function api(path, opts = {}) {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || data.message || r.statusText);
  return data;
}

export function renderLabNav(active) {
  const pages = [
    { href: "insight_portal.html", id: "insight", label: "AI 选品情报" },
    { href: "compare.html", id: "compare", label: "类目对比" },
    { href: "timeline.html", id: "timeline", label: "趋势时间轴" },
    { href: "workflow.html", id: "workflow", label: "决策工作流" },
    { href: "notifications.html", id: "notifications", label: "提醒中心" },
    { href: "member-demo.html", id: "member", label: "双轨对照" },
  ];
  return `<nav class="lab-nav">${pages.map(p =>
    `<a href="${p.href}" class="${p.id === active ? "active" : ""}">${p.label}</a>`
  ).join("")}</nav>`;
}
