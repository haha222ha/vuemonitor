/**
 * PR-2：会员中心 AI 选品情报 Tab
 * ES5 兼容（避免旧 WebView / 扩展干扰解析）
 */
(function (global) {
  'use strict';

  var STORAGE = { token: 'xhs_member_token' };

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
    var ent = (m && m.entitlements) || {};
    var limit = ent.insight_categories_per_day || 0;
    bar.innerHTML =
      '<span class="insight-badge">' + esc(m.plan_label || m.plan_code || '会员') + '</span>' +
      '<span class="insight-meta">情报额度 ' + esc(limit) + ' 类目/日</span>' +
      (ent.insight_compare ? '<span class="insight-meta">对比 ✓</span>' : '') +
      (ent.insight_timeline_days > 0 ? '<span class="insight-meta">时间轴 ' + esc(ent.insight_timeline_days) + ' 天</span>' : '');
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
      return '<span class="insight-badge">' + esc(it.category) + ' ★' + esc(it.blue_ocean_score || it.stars || '') + '</span>';
    }).join('');
    bar.innerHTML = '<strong>今日机会雷达</strong> · ' + esc(msg) + (chips ? '<div style="margin-top:8px;display:flex;flex-wrap:wrap;gap:6px">' + chips + '</div>' : '');
    bar.classList.remove('hidden');
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

  function renderLibrary(items) {
    var list = document.getElementById('insightLibraryList');
    var empty = document.getElementById('insightLibraryEmpty');
    if (!list) return;
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
    frame.src = insightViewUrl(reportDate, category) + '&t=' + Date.now();
    if (hint) hint.textContent = category + ' · ' + reportDate;
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
