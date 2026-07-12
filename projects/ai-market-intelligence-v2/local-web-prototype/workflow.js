import { api, esc, renderLabNav } from "./lab-charts.js";

document.getElementById("labNav").innerHTML = renderLabNav("workflow");

const COLUMN_FLOW = ["idea", "ai_review", "validate", "launch", "retro"];

async function loadBoard() {
  const board = await api("/api/v1/workflow/board");
  const kanban = document.getElementById("kanban");
  const colSel = document.getElementById("cardColumn");
  const catSel = document.getElementById("cardCategory");

  colSel.innerHTML = board.columns.map(c =>
    `<option value="${esc(c.id)}">${esc(c.title)}</option>`).join("");

  const cats = await api("/api/v1/insight/categories");
  catSel.innerHTML = `<option value="">关联类目（可选）</option>` +
    cats.items.map(it => `<option value="${esc(it.category)}">${esc(it.category)}</option>`).join("");

  kanban.innerHTML = board.columns.map(col => `
    <div class="kanban-col" data-col="${esc(col.id)}">
      <h3>${esc(col.title)} (${(col.cards || []).length})</h3>
      <div class="cards">${(col.cards || []).map(card => renderCard(card, col.id)).join("")}</div>
    </div>`).join("");

  kanban.querySelectorAll("[data-move]").forEach(btn => {
    btn.addEventListener("click", async () => {
      try {
        await api("/api/v1/workflow/card/move", {
          method: "POST",
          body: JSON.stringify({ card_id: btn.dataset.card, to_column: btn.dataset.move }),
        });
        loadBoard();
      } catch (e) {
        showMsg(e.message, "error");
      }
    });
  });
}

function renderCard(card, colId) {
  const idx = COLUMN_FLOW.indexOf(colId);
  const prev = idx > 0 ? COLUMN_FLOW[idx - 1] : null;
  const next = idx < COLUMN_FLOW.length - 1 ? COLUMN_FLOW[idx + 1] : null;
  let actions = "";
  if (prev) actions += `<button type="button" data-move="${esc(prev)}" data-card="${esc(card.id)}">← 退回</button>`;
  if (next) actions += `<button type="button" data-move="${esc(next)}" data-card="${esc(card.id)}">推进 →</button>`;
  return `
    <div class="kanban-card">
      <strong>${esc(card.title)}</strong>
      <div style="color:var(--muted);font-size:12px">${esc(card.note || "")}</div>
      ${card.category ? `<span class="tag">${esc(card.category)}</span>` : ""}
      <div class="kanban-actions">${actions}</div>
    </div>`;
}

function showMsg(t, kind) {
  const el = document.getElementById("msg");
  el.textContent = t;
  el.className = "msg" + (kind ? " " + kind : "");
}

document.getElementById("addForm").addEventListener("submit", async e => {
  e.preventDefault();
  try {
    await api("/api/v1/workflow/card", {
      method: "POST",
      body: JSON.stringify({
        column_id: document.getElementById("cardColumn").value,
        title: document.getElementById("cardTitle").value,
        category: document.getElementById("cardCategory").value,
      }),
    });
    document.getElementById("cardTitle").value = "";
    showMsg("已添加", "ok");
    loadBoard();
  } catch (err) {
    showMsg(err.message, "error");
  }
});

loadBoard();
