/** 会员中心实验室原型 — 纯 mock，无真实 PG/LLM */
let selectedCategory = '';
let selectedForCompare = new Set();
let uxCopy = {};
let progressSteps = [];
let watchlistDraft = new Set();
let allCategories = [];
let planInfo = null;
let lastPrintUrl = '';

async function api(path, opts = {}) {
  const r = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...opts });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || data.message || r.statusText);
  return data;
}

/** HTML 转义，防止 innerHTML 注入 XSS */
function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, m => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[m]));
}

function showMsg(text, kind) {
  const el = document.getElementById('msg');
  el.textContent = text || '';
  el.className = 'msg' + (kind ? ' ' + kind : '');
}

function miniBar(value, color) {
  const v = Math.max(0, Math.min(100, Number(value) || 0));
  return `<div class="mini-bar"><span style="width:${v}%;background:${color}"></span></div>`;
}

async function loadPlan() {
  try {
    planInfo = await api('/api/v1/member/plan');
    const u = planInfo.usage_today || {};
    const p = planInfo.plan || {};
    document.getElementById('planBar').innerHTML = `
      <span class="plan-badge">${esc(p.display || planInfo.plan_id)}</span>
      <span class="usage-text">今日额度 ${esc(u.generated_count || 0)}/${esc(u.limit || 1)} 类目</span>
      <label style="margin-left:auto;font-size:12px">切换套餐（demo）
        <select id="selPlan">${Object.entries(planInfo.available_plans || {}).map(([k, v]) =>
          `<option value="${esc(k)}" ${k === planInfo.plan_id ? 'selected' : ''}>${esc(v.display)}</option>`).join('')}
        </select>
      </label>`;
    document.getElementById('selPlan')?.addEventListener('change', async e => {
      planInfo = await api('/api/v1/member/plan', { method: 'POST', body: JSON.stringify({ plan_id: e.target.value }) });
      loadPlan();
      showMsg(`已切换至 ${planInfo.plan?.display}`, 'ok');
    });
    document.getElementById('btnExport').disabled = !p.pdf_export;
    if (!p.compare_enabled) {
      document.getElementById('btnCompare').title = '当前套餐不支持对比，请升级 Pro';
    }
    const notif = await api('/api/v1/notifications');
    const dot = document.getElementById('notifDot');
    if (notif.unread_count > 0) dot.classList.remove('hidden');
    else dot.classList.add('hidden');
    loadTeamPanel();
  } catch (e) {
    document.getElementById('planBar').textContent = '套餐加载失败';
  }
}

// --- Tabs ---
document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => {
      t.classList.toggle('active', t === btn);
      t.setAttribute('aria-selected', t === btn ? 'true' : 'false');
    });
    const tab = btn.dataset.tab;
    document.getElementById('panelLegacy').classList.toggle('active', tab === 'legacy');
    document.getElementById('panelLegacy').hidden = tab !== 'legacy';
    document.getElementById('panelInsight').classList.toggle('active', tab === 'insight');
    document.getElementById('panelInsight').hidden = tab !== 'insight';
  });
});

// --- Legacy mock ---
function renderLegacyList() {
  const items = [
    { date: '2026-07-11', name: '全量0711.zip', size: '12.4 MB' },
    { date: '2026-07-10', name: '全量0710.zip', size: '12.1 MB' },
    { date: '2026-07-09', name: '全量0709.zip', size: '11.8 MB' },
  ];
  document.getElementById('legacyList').innerHTML = items.map(it => `
    <div class="report-row">
      <div><strong>${esc(it.name)}</strong><br><span class="muted">${esc(it.date)} · ${esc(it.size)} · member_daily_zip</span></div>
      <button class="btn primary" style="padding:6px 12px;font-size:13px" disabled title="实验室不提供真实下载">下载</button>
    </div>`).join('');
}

// --- Categories ---
async function loadCategories() {
  const grid = document.getElementById('categoryGrid');
  try {
    const [catData, copyData] = await Promise.all([
      api('/api/v1/insight/categories'),
      api('/api/v1/ux/copy').catch(() => ({})),
    ]);
    uxCopy = copyData || {};
    progressSteps = (uxCopy.steps || [
      '聚合类目指标', '市场分析师', '数据分析师', '风险分析师', '运营顾问', 'CEO 总结', '合规检查',
    ]);

    grid.innerHTML = catData.items.map(it => `
      <div class="cat-card" data-category="${it.category}">
        <h3>${it.category}</h3>
        ${miniBar(it.growth_rate_pct, '#34c759')}
        <div class="cat-stats">
          <span>增速 <strong>${it.growth_rate_pct}%</strong></span>
          <span>蓝海 <strong>${it.blue_ocean_score}</strong></span>
          <span>竞争 <strong>${it.competition_index}</strong></span>
        </div>
      </div>`).join('');

    grid.querySelectorAll('.cat-card').forEach(card => {
      card.addEventListener('click', () => selectCategory(card.dataset.category));
      card.addEventListener('dblclick', () => toggleCompare(card.dataset.category));
      card.addEventListener('contextmenu', e => {
        e.preventDefault();
        location.href = `timeline.html?category=${encodeURIComponent(card.dataset.category)}`;
      });
    });

    if (catData.items.length) selectCategory(catData.items[0].category);
    await loadWatchlistEditor(catData.items.map(it => it.category));
    sortCategoryGridByWatchlist();
  } catch (e) {
    grid.innerHTML = `<p class="msg error">加载失败: ${esc(e.message)}</p>`;
  }
}

function selectCategory(cat) {
  selectedCategory = cat;
  document.querySelectorAll('.cat-card').forEach(c => {
    c.classList.toggle('selected', c.dataset.category === cat);
  });
  document.getElementById('btnGen').disabled = !cat;
}

function toggleCompare(cat) {
  if (selectedForCompare.has(cat)) selectedForCompare.delete(cat);
  else if (selectedForCompare.size < 3) selectedForCompare.add(cat);
  updateCompareBtn();
}

function updateCompareBtn() {
  const btn = document.getElementById('btnCompare');
  btn.textContent = `对比已选（${selectedForCompare.size}）`;
  btn.disabled = selectedForCompare.size < 2;
}

document.getElementById('btnCompare').addEventListener('click', () => {
  if (planInfo?.plan && !planInfo.plan.compare_enabled) {
    showMsg('当前套餐不支持类目对比，请升级 V2-Pro', 'error');
    return;
  }
  const cats = [...selectedForCompare];
  if (cats.length < 2) return;
  location.href = `compare.html?categories=${encodeURIComponent(cats.join(','))}`;
});

document.getElementById('btnExport').addEventListener('click', () => {
  const url = lastPrintUrl || (selectedCategory
    ? `/api/v1/insight/report/print?category=${encodeURIComponent(selectedCategory)}&report_date=2026-07-12`
    : '');
  if (!url) {
    showMsg('请先生成报告', 'error');
    return;
  }
  window.open(url, '_blank', 'noopener');
});

async function loadWatchlistEditor(categories) {
  allCategories = categories || [];
  try {
    const wl = await api('/api/v1/member/insight/watchlist');
    watchlistDraft = new Set(wl.categories || []);
  } catch (e) {
    watchlistDraft = new Set();
  }
  renderWatchlistEditor();
}

function renderWatchlistEditor() {
  const box = document.getElementById('watchlistEditor');
  if (!allCategories.length) {
    box.textContent = '无类目';
    return;
  }
  box.innerHTML = allCategories.map(cat => `
    <label><input type="checkbox" value="${esc(cat)}" ${watchlistDraft.has(cat) ? 'checked' : ''}>
      ${esc(cat)}</label>`).join('');
  box.querySelectorAll('input').forEach(inp => {
    inp.addEventListener('change', () => {
      if (inp.checked) watchlistDraft.add(inp.value);
      else watchlistDraft.delete(inp.value);
    });
  });
}

document.getElementById('btnSaveWatchlist').addEventListener('click', async () => {
  const msg = document.getElementById('watchlistMsg');
  try {
    const res = await api('/api/v1/member/insight/watchlist', {
      method: 'PUT',
      body: JSON.stringify({ categories: [...watchlistDraft] }),
    });
    msg.textContent = `已保存 ${res.count} 个关注类目`;
    msg.className = 'msg ok';
    sortCategoryGridByWatchlist();
  } catch (e) {
    msg.textContent = e.message;
    msg.className = 'msg error';
  }
});

function sortCategoryGridByWatchlist() {
  const grid = document.getElementById('categoryGrid');
  const cards = [...grid.querySelectorAll('.cat-card')];
  cards.sort((a, b) => {
    const aw = watchlistDraft.has(a.dataset.category) ? 0 : 1;
    const bw = watchlistDraft.has(b.dataset.category) ? 0 : 1;
    return aw - bw;
  });
  cards.forEach(c => grid.appendChild(c));
}

async function loadTeamPanel() {
  const panel = document.getElementById('teamPanel');
  if (!planInfo || planInfo.plan_id !== 'insight_team_monthly') {
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  try {
    const t = await api('/api/v1/member/team');
    document.getElementById('teamSeats').innerHTML = `
      <p style="font-size:13px;color:var(--muted)">${esc(t.org.name)} · ${t.used_seats}/${t.max_seats} 席</p>
      <ul style="font-size:13px;padding-left:18px">${t.seats.map(s =>
        `<li>${esc(s.label)} — ${esc(s.status)}</li>`).join('')}</ul>`;
  } catch (e) {
    document.getElementById('teamSeats').textContent = e.message;
  }
}

// --- Library ---
async function loadLibrary() {
  const box = document.getElementById('libraryList');
  try {
    const data = await api('/api/v1/insight/library');
    if (!data.items?.length) {
      box.innerHTML = `<p class="muted">${esc(uxCopy.insight?.empty_library || '暂无情报')}</p>`;
      return;
    }
    box.innerHTML = data.items.map(it => `
      <div class="lib-item" data-date="${it.report_date}" data-cat="${it.category}">
        <div><strong>${it.category}</strong><br><span class="muted">${it.report_date}</span></div>
        <span class="stars">${'★'.repeat(it.stars || 3)}</span>
      </div>`).join('');
    box.querySelectorAll('.lib-item').forEach(el => {
      el.addEventListener('click', () => openLibraryItem(el.dataset.date, el.dataset.cat));
    });
  } catch (e) {
    box.textContent = '加载失败';
  }
}

async function openLibraryItem(date, category) {
  try {
    const res = await api('/api/v1/insight/report/generate', {
      method: 'POST',
      body: JSON.stringify({ report_date: date, category }),
    });
    document.getElementById('preview').src = res.preview_url + '?t=' + Date.now();
    showMsg(`已打开：${category} (${date})`, 'ok');
  } catch (e) {
    showMsg(e.message, 'error');
  }
}

// --- Generate with simulated progress ---
async function simulateProgress(onStep) {
  const steps = progressSteps;
  for (let i = 0; i < steps.length; i++) {
    onStep(i, steps.length);
    await new Promise(r => setTimeout(r, i === 0 ? 200 : 280));
  }
}

document.getElementById('btnGen').addEventListener('click', async () => {
  const btn = document.getElementById('btnGen');
  const wrap = document.getElementById('progressWrap');
  const fill = document.getElementById('progressFill');
  const stepsEl = document.getElementById('progressSteps');

  btn.disabled = true;
  btn.textContent = uxCopy.insight?.generating || '生成中…';
  showMsg('');
  wrap.classList.remove('hidden');
  stepsEl.innerHTML = progressSteps.map(s => `<li>${esc(s)}</li>`).join('');

  let genPromise = api('/api/v1/insight/report/generate', {
    method: 'POST',
    body: JSON.stringify({ category: selectedCategory, report_date: '2026-07-12' }),
  });

  await simulateProgress((idx, total) => {
    fill.style.width = `${Math.round(((idx + 1) / total) * 100)}%`;
    stepsEl.querySelectorAll('li').forEach((li, i) => {
      li.classList.toggle('done', i < idx);
      li.classList.toggle('active', i === idx);
    });
  });

  try {
    const res = await genPromise;
    stepsEl.querySelectorAll('li').forEach(li => li.classList.add('done'));
    fill.style.width = '100%';
    showMsg(res.report?.executive_summary || uxCopy.insight?.success || '完成', 'ok');
    document.getElementById('preview').src = res.preview_url + '?t=' + Date.now();
    lastPrintUrl = res.print_url || '';
    document.getElementById('btnExport').disabled = !(planInfo?.plan?.pdf_export);
    loadLibrary();
    loadPlan();
  } catch (e) {
    showMsg(e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = uxCopy.insight?.generate_btn || '生成 AI 情报';
    setTimeout(() => wrap.classList.add('hidden'), 1200);
  }
});

// --- Feedback modal ---
const modal = document.getElementById('feedbackModal');
document.getElementById('fabFeedback').addEventListener('click', () => modal.classList.remove('hidden'));
document.getElementById('fbCancel').addEventListener('click', () => modal.classList.add('hidden'));
document.querySelector('.modal-backdrop').addEventListener('click', () => modal.classList.add('hidden'));

document.getElementById('fbSubmit').addEventListener('click', async () => {
  const content = document.getElementById('fbContent').value.trim();
  const fbMsg = document.getElementById('fbMsg');
  if (!content) {
    fbMsg.textContent = '请填写内容';
    fbMsg.className = 'msg error';
    return;
  }
  try {
    const res = await api('/api/v1/feedback', {
      method: 'POST',
      body: JSON.stringify({
        type: document.getElementById('fbType').value,
        content,
        category: selectedCategory,
        report_date: '2026-07-12',
      }),
    });
    fbMsg.textContent = res.message || '已提交';
    fbMsg.className = 'msg ok';
    document.getElementById('fbContent').value = '';
    setTimeout(() => modal.classList.add('hidden'), 1500);
  } catch (e) {
    fbMsg.textContent = e.message;
    fbMsg.className = 'msg error';
  }
});

renderLegacyList();
loadPlan();
loadCategories();
loadLibrary();
