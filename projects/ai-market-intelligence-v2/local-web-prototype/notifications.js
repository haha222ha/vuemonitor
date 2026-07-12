import { api, renderLabNav } from "./lab-charts.js";

document.getElementById("labNav").innerHTML = renderLabNav("notifications");

const TYPE_ICON = { opportunity: "🟢", trend: "📈", risk: "⚠️", account: "ℹ️" };

async function load(refresh = false) {
  const data = await api(`/api/v1/notifications?refresh=${refresh}`);
  document.getElementById("unreadBadge").textContent =
    data.unread_count ? `${data.unread_count} 未读` : "全部已读";

  const box = document.getElementById("notifList");
  if (!data.items?.length) {
    box.innerHTML = "<p class='muted'>暂无提醒</p>";
    return;
  }
  box.innerHTML = data.items.map(it => `
    <article class="notif-card ${it.read ? "read" : ""}" data-id="${it.id}">
      <div class="notif-head">
        <span>${TYPE_ICON[it.type] || "•"}</span>
        <strong>${it.title}</strong>
        ${it.priority === "high" ? '<span class="tag-high">重要</span>' : ""}
      </div>
      <p class="notif-body">${it.body}</p>
      <div class="notif-foot">
        ${it.category ? `<a href="member-demo.html#insight">${it.category}</a>` : ""}
        <button type="button" class="btn-link" data-read="${it.id}">${it.read ? "已读" : "标记已读"}</button>
      </div>
    </article>`).join("");

  box.querySelectorAll("[data-read]").forEach(btn => {
    btn.addEventListener("click", async () => {
      await api("/api/v1/notifications/read", {
        method: "POST",
        body: JSON.stringify({ id: btn.dataset.read }),
      });
      load();
    });
  });
}

document.getElementById("btnRefresh").addEventListener("click", () => load(true));
document.getElementById("btnReadAll").addEventListener("click", async () => {
  await api("/api/v1/notifications/read-all", { method: "POST" });
  load();
});

load();
