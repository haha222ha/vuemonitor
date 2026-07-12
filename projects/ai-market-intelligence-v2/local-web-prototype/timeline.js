import { api, renderLabNav, renderLineChart } from "./lab-charts.js";

document.getElementById("labNav").innerHTML = renderLabNav("timeline");

const params = new URLSearchParams(location.search);
const preCat = params.get("category") || "";

async function init() {
  const data = await api("/api/v1/insight/categories");
  const sel = document.getElementById("selCategory");
  sel.innerHTML = data.items.map(it =>
    `<option value="${it.category}">${it.category}</option>`).join("");
  if (preCat && [...sel.options].some(o => o.value === preCat)) sel.value = preCat;
  loadTimeline();
}

async function loadTimeline() {
  const cat = document.getElementById("selCategory").value;
  const days = document.getElementById("selDays").value;
  const data = await api(`/api/v1/insight/timeline?category=${encodeURIComponent(cat)}&days=${days}`);

  const ai = document.getElementById("aiWeekly");
  ai.textContent = data.ai_weekly || "";
  ai.classList.remove("hidden");

  const charts = document.getElementById("charts");
  charts.innerHTML = "";
  const specs = [
    ["growth_rate_pct", "增速指数", "#34c759"],
    ["blue_ocean_score", "蓝海指数", "#0071e3"],
    ["competition_index", "竞争指数", "#ff9500"],
    ["heat_score", "热度指数", "#5856d6"],
  ];
  specs.forEach(([key, label, color]) => {
    const div = document.createElement("div");
    div.className = "chart-card mini-line";
    charts.appendChild(div);
    renderLineChart(div, data.points, key, `${label}（${days} 天）`, color);
  });
}

document.getElementById("btnLoad").addEventListener("click", loadTimeline);
init();
