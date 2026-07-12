/**
 * PR-2 + Q2：会员中心 AI 选品情报 Tab
 * ES5 兼容（避免旧 WebView / 扩展干扰解析）
 */
(function (global) {
  'use strict';

  var STORAGE = { token: 'xhs_member_token' };
  var _insightEnt = {};
  var _libraryItems = [];
  var _comparePick = [];
  var _preview = { date: '', category: '' };

  function loadStored(key) {
    try { return localStorage.getItem(key) || ''; } catch (e) { return ''; }
  }

  function esc(s) {
    if (s === null || s === undefined) s = '';
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
  }

  function api(path, opts) {
    opts = opts || {};
    if (typeof global.api === 'function') {
      return global.api(path, Object.assign({ auth: true }, opts));
    }
    var headers = Object.assign({}, opts.headers || {});
    var t = loadStored(STORAGE.token);
    if (t) headers.Authorization = 'Bearer ' + t;
    return fetch(path, Object.assign({}, opts, { credentials: 'include', headers: headers }))
      .then(function (r) {
        return r.text().then(function (text) {
          var data = {};
          if (text) {
            try { data = JSON.parse(text); } catch (e) {}
          }
          if (!r.ok) {
            var err = new Error((data && data.detail) || r.statusText || '请求失败');
            err.status = r.status;
            throw err;
          }
          return data;
        });
      });
  }

  function insightViewUrl(reportDate, category) {
    var t = loadStored(STORAGE.token);
    var base = '/api/v1/member/insight/' + encodeURIComponent(reportDate) + '/' + encodeURIComponent(category) + '/view';
    return t ? base + '?access_token=' + encodeURIComponent(t) : base;
  }

  function applyEntitlements(m) {
    m = m || {};
    var ent = m.entitlements || {};
    var legacy = true;
    if (m.legacy_zip_enabled === false || ent.legacy_zip_enabled === false) legacy = false;
    if (m.legacy_zip_enabled === true || ent.legacy_zip_enabled === true) legacy = true;
    var insight = m.insight_enabled === true || ent.insight_enabled === true;

    var tabReports = document.getElementById('dashTabReports');
    var tabInsight = document.getElementById('dashTabInsight');
    if (tabReports) tabReports.classList.toggle('hidden', !legacy);
    if (tabInsight) tabInsight.classList.toggle('hidden', !insight);

    var previewBanner = document.getElementById('insightPreviewBanner');
    if (previewBanner) {
      previewBanner.classList.toggle('hidden', m.portal_route !== 'legacy_with_preview');
    }

    var defaultDash = 'reports';
    if (insight && (!legacy || m.portal_route === 'insight_only')) {
      defaultDash = 'insight';
    } else if (insight && legacy) {
      defaultDash = loadStored('xhs_member_dash_tab') || 'insight';
    }
    if (typeof global.switchDash === 'function') {
      global.switchDash(defaultDash);
    }
  }

  function renderPlanBar(m) {
    var bar = document.getElementById('insightPlanBar');
    if (!bar) return;
    _insightEnt = (m && m.entitlements) || {};
    var limit = _insightEnt.insight_categories_per_day || 0;
    bar.innerHTML =
      '<span class="insight-badge">' + esc(m.plan_label || m.plan_code || '会员') + '</span>' +
      '<span class="insight-meta">情报额度 ' + esc(limit) + ' 类目/日</span>' +
      (_insightEnt.insight_compare ? '<span class="insight-meta">对比 ✓</span>' : '') +
      (_insightEnt.insight_timeline_days > 0 ? '<span class="insight-meta">时间轴 ' + esc(_insightEnt.insight_timeline_days) + ' 天</span>' : '') +
      (_insightEnt.insight_workflow ? '<span class="insight-meta">工作流 ✓</span>' : '');
    renderToolsBar();
  }

  function renderToolsBar() {
    var bar = document.getElementById('insightToolsBar');
    if (!bar) return;
    var parts = [];
    if (_insightEnt.insight_compare) {
      parts.push('<button type="button" class="btn btn-ghost btn-xs" id="insightBtnCompare">类目对比</button>');
    }
    if (_insightEnt.insight_timeline_days > 0) {
      parts.push('<button type="button" class="btn btn-ghost btn-xs" id="insightBtnTimeline">时间轴</button>');
    }
    if (_insightEnt.insight_workflow) {
      parts.push('<button type="button" class="btn btn-ghost btn-xs" id="insightBtnWorkflow">记录决策</button>');
    }
    if (!parts.length) {
      bar.classList.add('hidden');
      return;
    }
    bar.innerHTML = parts.join('');
    bar.classList.remove('hidden');
    var btnCmp = document.getElementById('insightBtnCompare');
    if (btnCmp) btnCmp.addEventListener('click', toggleComparePanel);
    var btnTl = document.getElementById('insightBtnTimeline');
    if (btnTl) btnTl.addEventListener('click', function () {
      if (_preview.category) loadTimeline(_preview.category);
      else alert('请先在情报库或雷达中选择类目');
    });
    var btnWf = document.getElementById('insightBtnWorkflow');
    if (btnWf) btnWf.addEventListener('click', showWorkflowPanel);
  }

  function toggleComparePanel() {
    var panel = document.getElementById('insightComparePanel');
    if (!panel) return;
    if (!panel.classList.contains('hidden')) {
      panel.classList.add('hidden');
      return;
    }
    _comparePick = [];
    var cats = _libraryItems.map(function (it) { return it.category; }).filter(Boolean);
    var uniq = [];
    cats.forEach(function (c) { if (uniq.indexOf(c) < 0) uniq.push(c); });
    var picks = uniq.slice(0, 12).map(function (c) {
      return '<span class="insight-cmp-pick" data-cat="' + esc(c) + '">' + esc(c) + '</span>';
    }).join('');
    panel.innerHTML =
      '<strong>类目对比</strong> · 点选 2～3 个类目后点击「开始对比」<div style="margin-top:8px">' + picks + '</div>' +
      '<button type="button" class="btn btn-primary btn-xs" style="margin-top:10px" id="insightRunCompare">开始对比</button>' +
      '<div id="insightCompareResult"></div>';
    panel.classList.remove('hidden');
    panel.querySelectorAll('.insight-cmp-pick').forEach(function (el) {
      el.addEventListener('click', function () {
        var cat = el.dataset.cat;
        var idx = _comparePick.indexOf(cat);
        if (idx >= 0) {
          _comparePick.splice(idx, 1);
          el.classList.remove('active');
        } else if (_comparePick.length < 3) {
          _comparePick.push(cat);
          el.classList.add('active');
        }
      });
    });
    var runBtn = document.getElementById('insightRunCompare');
    if (runBtn) runBtn.addEventListener('click', runCompare);
  }

  function runCompare() {
    if (_comparePick.length < 2) {
      alert('请至少选择 2 个类目');
      return;
    }
    var q = encodeURIComponent(_comparePick.join(','));
    api('/api/v1/member/insight/compare?categories=' + q).then(function (data) {
      var box = document.getElementById('insightCompareResult');
      if (!box) return;
      var rows = (data.categories || []).map(function (r) {
        return '<tr><td>' + esc(r.category) + '</td><td>' + esc(r.growth_rate_pct) + '%</td><td>' +
          esc(r.blue_ocean_score) + '</td><td>' + esc(r.competition_index) + '</td><td>' + esc(r.heat_score) + '</td></tr>';
      }).join('');
      box.innerHTML =
        '<p style="margin-top:10px">' + esc(data.ai_summary || '') + '</p>' +
        '<table><thead><tr><th>类目</th><th>增速</th><th>蓝海</th><th>竞争</th><th>热度</th></tr></thead><tbody>' +
        rows + '</tbody></table>';
    }).catch(function (e) {
      alert((e && e.message) || '对比失败');
    });
  }

  function loadTimeline(category) {
    var panel = document.getElementById('insightTimelinePanel');
    if (!panel) return;
    var days = _insightEnt.insight_timeline_days || 7;
    panel.classList.remove('hidden');
    panel.innerHTML = '<strong>时间轴 · ' + esc(category) + '</strong> · 加载中…';
    api('/api/v1/member/insight/timeline?category=' + encodeURIComponent(category) + '&days=' + days)
      .then(function (data) {
        var pts = data.points || [];
        var rows = pts.map(function (p) {
          return '<tr><td>' + esc(p.date) + '</td><td>' + esc(p.growth_rate_pct) + '%</td><td>' +
            esc(p.blue_ocean_score) + '</td><td>' + esc(p.trend_label) + '</td></tr>';
        }).join('');
        panel.innerHTML =
          '<strong>时间轴 · ' + esc(category) + '</strong>（近 ' + esc(data.days || days) + ' 日）' +
          '<p style="margin:8px 0">' + esc(data.ai_weekly || '') + '</p>' +
          (rows ? '<table><thead><tr><th>日期</th><th>增速</th><th>蓝海</th><th>标签</th></tr></thead><tbody>' + rows + '</tbody></table>' : '<p>暂无序列数据</p>');
      })
      .catch(function (e) {
        panel.innerHTML = '<strong>时间轴</strong> · ' + esc((e && e.message) || '加载失败');
      });
  }

  function showWorkflowPanel() {
    var panel = document.getElementById('insightWorkflowPanel');
    if (!panel) return;
    var cat = _preview.category || '';
    var dt = _preview.date || '';
    panel.innerHTML =
      '<strong>记录决策</strong> · ' + esc(cat || '未选类目') +
      '<div style="margin-top:10px;display:flex;flex-wrap:wrap;gap:8px;align-items:center">' +
      '<select id="wfStatus" class="field" style="padding:6px 8px;font-size:13px">' +
      '<option value="stocked">已进货</option><option value="skipped">暂不跟进</option><option value="watching">继续观察</option>' +
      '</select>' +
      '<input id="wfNote" placeholder="备注（可选）" style="flex:1;min-width:120px;padding:6px 8px;border:1px solid var(--line);border-radius:8px">' +
      '<button type="button" class="btn btn-primary btn-xs" id="wfSave">保存</button>' +
      '</div><div id="wfMsg" class="insight-meta" style="margin-top:8px"></div>';
    panel.classList.remove('hidden');
    var saveBtn = document.getElementById('wfSave');
    if (saveBtn) saveBtn.addEventListener('click', function () {
      if (!cat) {
        alert('请先在情报库中选择类目');
        return;
      }
      var statusEl = document.getElementById('wfStatus');
      var noteEl = document.getElementById('wfNote');
      api('/api/v1/member/insight/workflow', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category: cat,
          report_date: dt,
          status: statusEl ? statusEl.value : 'stocked',
          note: noteEl ? noteEl.value : '',
        }),
      }).then(function () {
        var msg = document.getElementById('wfMsg');
        if (msg) msg.textContent = '已记录，30 天后可回访';
      }).catch(function (e) {
        alert((e && e.message) || '保存失败');
      });
    });
  }

  function renderRadar(data) {
    var bar = document.getElementById('insightRadarBar');
    if (!bar || !data) return;
    var msg = data.message || '';
    var hl = (data.highlights || []).slice(0, 3);
    if (!msg && !hl.length) {
      bar.classList.add('hidden');
      return;
    }
    var chips = hl.map(function (it) {
      return '<span class="insight-badge insight-radar-chip" data-category="' + esc(it.category || '') + '">' +
        esc(it.category) + ' ★' + esc(it.blue_ocean_score || it.stars || '') + '</span>';
    }).join('');
    bar.innerHTML = '<strong>今日机会雷达</strong> · ' + esc(msg) + (chips ? '<div style="margin-top:8px;display:flex;flex-wrap:wrap;gap:6px">' + chips + '</div>' : '');
    bar.classList.remove('hidden');
    bar.querySelectorAll('.insight-radar-chip').forEach(function (el) {
      el.addEventListener('click', function () {
        var cat = el.dataset.category;
        if (!cat) return;
        if (_insightEnt.insight_timeline_days > 0) {
          loadTimeline(cat);
        }
        var match = _libraryItems.filter(function (it) { return it.category === cat; })[0];
        if (match) openPreview(match.report_date, cat);
      });
    });
  }

  function loadRadar() {
    return api('/api/v1/member/insight/radar').then(function (data) {
      renderRadar(data);
      return data;
    }).catch(function (e) {
      var bar = document.getElementById('insightRadarBar');
      if (bar) {
        bar.classList.remove('hidden');
        bar.innerHTML = '<strong>今日机会雷达</strong> · 加载失败（' + esc(e && e.message ? e.message : '网络错误') + '）';
      }
    });
  }

  function renderRecommendations(data) {
    var bar = document.getElementById('insightRecommendBar');
    if (!bar || !data || !(data.items || []).length) return;
    var chips = (data.items || []).slice(0, 4).map(function (it) {
      var hint = it.reason_label || it.reason || '';
      return '<span class="insight-badge insight-rec-chip" title="' + esc(hint) + '" data-date="' +
        esc(String(it.report_date || '').slice(0, 10)) + '" data-category="' + esc(it.category || '') + '">' +
        esc(it.category) + (hint ? ' · ' + esc(hint) : '') + '</span>';
    }).join('');
    bar.innerHTML = '<strong>为你推荐</strong><div style="margin-top:8px;display:flex;flex-wrap:wrap;gap:6px">' + chips + '</div>';
    bar.classList.remove('hidden');
    bar.querySelectorAll('.insight-rec-chip').forEach(function (el) {
      el.style.cursor = 'pointer';
      el.addEventListener('click', function () {
        openPreview(el.dataset.date, el.dataset.category);
      });
    });
  }

  function loadRecommendations() {
    return api('/api/v1/member/insight/recommendations').then(renderRecommendations).catch(function () {});
  }

  function loadHealthScore() {
    var bar = document.getElementById('insightHealthBar');
    if (bar) bar.textContent = '健康度加载中…';
    return api('/api/v1/member/insight/health-score').then(function (data) {
      if (!bar || !data) return;
      var label = data.band === 'at_risk' ? '建议今日查看情报' : (data.band === 'healthy' ? '活跃良好' : '保持关注');
      bar.textContent = '健康度 ' + (data.score || 0) + '/100 · ' + label;
      bar.style.color = data.at_risk ? 'var(--red, #c00)' : '';
    }).catch(function () {
      if (bar) bar.textContent = '健康度暂不可用';
    });
  }

  function renderLibrary(items) {
    var list = document.getElementById('insightLibraryList');
    var empty = document.getElementById('insightLibraryEmpty');
    if (!list) return;
    _libraryItems = items || [];
    if (!items || !items.length) {
      list.innerHTML = '';
      if (empty) empty.classList.remove('hidden');
      return;
    }
    if (empty) empty.classList.add('hidden');
    list.innerHTML = items.map(function (it) {
      var date = String(it.report_date || '').slice(0, 10);
      var cat = it.category || '';
      var stars = it.stars || 3;
      return (
        '<div class="insight-lib-item" data-date="' + esc(date) + '" data-category="' + esc(cat) + '">' +
        '<div><strong>' + esc(cat) + '</strong><div class="insight-lib-meta">' + esc(date) + ' · ★' + stars + '</div></div>' +
        '<button type="button" class="btn btn-ghost btn-xs insight-read-btn">阅读</button></div>'
      );
    }).join('');
    list.querySelectorAll('.insight-lib-item').forEach(function (row) {
      row.addEventListener('click', function (e) {
        if (e.target.closest('.insight-read-btn') || e.target === row) {
          openPreview(row.dataset.date, row.dataset.category);
        }
      });
    });
  }

  function openPreview(reportDate, category) {
    var frame = document.getElementById('insightPreviewFrame');
    var hint = document.getElementById('insightPreviewHint');
    if (!frame || !reportDate || !category) return;
    _preview = { date: String(reportDate).slice(0, 10), category: category };
    frame.src = insightViewUrl(reportDate, category) + '&t=' + Date.now();
    if (hint) hint.textContent = category + ' · ' + _preview.date;
  }

  function loadInsightTab() {
    var msg = document.getElementById('insightMsg');
    var bar = document.getElementById('insightPlanBar');
    if (bar) bar.textContent = '正在加载情报库…';
    return Promise.all([
      api('/api/v1/member/profile'),
      api('/api/v1/member/insight/library'),
    ]).then(function (res) {
      var profile = res[0];
      var lib = res[1];
      renderPlanBar(profile);
      renderLibrary(lib.items || []);
      loadRadar();
      loadRecommendations();
      loadHealthScore();
      if (msg) msg.textContent = lib.shadow_mode ? '当前为 Shadow 预生成情报（只读）' : '';
      if ((lib.items || []).length) {
        var first = lib.items[0];
        openPreview(first.report_date, first.category);
      }
    }).catch(function (e) {
      var detail = (e && e.message) ? e.message : '加载失败';
      if (bar) {
        bar.innerHTML = '<span class="insight-meta" style="color:var(--red)">情报加载失败：' + esc(detail) + '</span>';
      }
      if (msg) msg.textContent = detail;
    });
  }

  global.MemberInsight = {
    applyEntitlements: applyEntitlements,
    load: loadInsightTab,
    openPreview: openPreview,
  };
})(window);
