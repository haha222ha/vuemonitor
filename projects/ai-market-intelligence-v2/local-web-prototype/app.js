let selectedCategory = '';

async function api(path, opts = {}) {
  const r = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...opts });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || r.statusText);
  return data;
}

function showMsg(text, kind) {
  const el = document.getElementById('msg');
  el.textContent = text || '';
  el.className = 'msg' + (kind ? ' ' + kind : '');
}

async function loadCategories() {
  const box = document.getElementById('categoryList');
  try {
    const data = await api('/api/v1/insight/categories');
    box.innerHTML = data.items.map(it => `
      <label class="cat-item">
        <input type="radio" name="cat" value="${it.category}">
        <span><strong>${it.category}</strong>
          · 增速 ${it.growth_rate_pct}% · 蓝海 ${it.blue_ocean_score} · 竞争 ${it.competition_index}
        </span>
      </label>`).join('');
    box.querySelectorAll('input[name=cat]').forEach(inp => {
      inp.addEventListener('change', () => {
        selectedCategory = inp.value;
        document.getElementById('btnGen').disabled = !selectedCategory;
      });
    });
    if (data.items.length) {
      box.querySelector('input').checked = true;
      selectedCategory = data.items[0].category;
      document.getElementById('btnGen').disabled = false;
    }
  } catch (e) {
    box.textContent = '加载失败: ' + e.message;
  }
}

document.getElementById('btnGen').addEventListener('click', async () => {
  const btn = document.getElementById('btnGen');
  btn.disabled = true;
  btn.textContent = '生成中…';
  showMsg('', '');
  try {
    const res = await api('/api/v1/insight/report/generate', {
      method: 'POST',
      body: JSON.stringify({ category: selectedCategory, report_date: '2026-07-12' }),
    });
    showMsg(res.report.executive_summary || '生成成功', 'ok');
    document.getElementById('preview').src = res.preview_url + '?t=' + Date.now();
  } catch (e) {
    showMsg(e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = '生成 AI 情报';
  }
});

loadCategories();
