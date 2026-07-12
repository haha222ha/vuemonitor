import { api, esc, renderLabNav, renderRadar } from "./lab-charts.js";

const selected = new Set();
const params = new URLSearchParams(location.search);
const preselect = (params.get("categories") || "").split(",").filter(Boolean);

document.getElementById("labNav").innerHTML = renderLabNav("compare");

async function loadChips() {
  const box = document.getElementById("catChips");
  const data = await api("/api/v1/insight/categories");
  box.innerHTML = data.items.map(it => `
    <button type="button" class="cat-chip" data-cat="${esc(it.category)}">${esc(it.category)}</button>`).join("");

  box.querySelectorAll(".cat-chip").forEach(chip => {
    if (preselect.includes(chip.dataset.cat)) {
      selected.add(chip.dataset.cat);
      chip.classList.add("selected");
    }
    chip.addEventListener("click", () => {
      const cat = chip.dataset.cat;
      if (selected.has(cat)) {
        selected.delete(cat);
        chip.classList.remove("selected");
      } else if (selected.size < 3) {
        selected.add(cat);
        chip.classList.add("selected");
      }
      document.getElementById("btnCompare").disabled = selected.size < 2;
    });
  });
  document.getElementById("btnCompare").disabled = selected.size < 2;
  if (selected.size >= 2) runCompare();
}

async function runCompare() {
  const msg = document.getElementById("msg");
  msg.textContent = "";
  const cats = [...selected].join(",");
  try {
    const data = await api(`/api/v1/insight/compare?categories=${encodeURIComponent(cats)}`);
    document.getElementById("result").classList.remove("hidden");
    document.getElementById("aiSummary").innerHTML =
      `<strong>AI 对比摘要</strong><br>${esc(data.ai_summary)}`;

    const radarHost = document.getElementById("radarHost");
    radarHost.innerHTML = "";
    renderRadar(radarHost, data.categories, data.radar_labels);

    const order = data.recommendation_order || [];
    const rows = data.categories.map(c => {
      const rank = order.indexOf(c.category) + 1;
      return `<tr>
        <td>${rank ? `<span class="rank-badge">${rank}</span>` : "—"}</td>
        <td><strong>${esc(c.category)}</strong></td>
        <td>${esc(c.growth_rate_pct)}%</td>
        <td>${esc(c.blue_ocean_score)}</td>
        <td>${esc(c.competition_index)}</td>
        <td>${esc(c.heat_score)}</td>
        <td>${esc(c.trend_label)}</td>
        <td>${esc(c.price_band)}</td>
      </tr>`;
    }).join("");
    document.getElementById("tableHost").innerHTML = `
      <table class="compare-table">
        <thead><tr><th>序</th><th>类目</th><th>增速</th><th>蓝海</th><th>竞争</th><th>热度</th><th>趋势</th><th>价格带</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>`;
  } catch (e) {
    msg.textContent = e.message;
    msg.className = "msg error";
  }
}

document.getElementById("btnCompare").addEventListener("click", runCompare);
loadChips();
