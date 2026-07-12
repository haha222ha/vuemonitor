/**
 * PR-2：会员中心 AI 选品情报 Tab（骨架）
 * 依赖 member_portal.html 同源 api()/STORAGE（通过 window 暴露）
 */
(function (global) {
  'use strict';

  const STORAGE = { token: 'xhs_member_token' };

  function loadStored(key) {
    try { return localStorage.getItem(key) || ''; } catch (_) { return ''; }
  }

  function esc(s) {
    return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
  }

  function api(path, opts) {
    opts = opts || {};
    const headers = Object.assign({}, opts.headers || {});
    const t = loadStored(STORAGE.token);
    if (t) headers.Authorization = 'Bearer ' + t;
    return fetch(path, Object.assign({}, opts, { credentials: 'include', headers }))
      .then(function (r) {
        return r.text().then(function (text) {
          var data = {};
          if (text) {
            try { data = JSON.parse(text); } catch (_) {}
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

    var banner = document.getElementById('insightPreviewBanner');
    if (banner) {
      banner.classList.toggle('hidden', !(ent.insight_preview || m.portal_route === 'legacy_with_preview'));
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
    return Promise.all([
      api('/api/v1/member/profile'),
      api('/api/v1/member/insight/library'),
    ]).then(function (res) {
      var profile = res[0];
      var lib = res[1];
      renderPlanBar(profile);
      renderLibrary(lib.items || []);
      if (msg) msg.textContent = lib.shadow_mode ? '当前为 Shadow 预生成情报（只读）' : '';
      if ((lib.items || []).length) {
        var first = lib.items[0];
        openPreview(first.report_date, first.category);
      }
    }).catch(function (e) {
      if (msg) msg.textContent = e.message || '加载失败';
    });
  }

  global.MemberInsight = {
    applyEntitlements: applyEntitlements,
    load: loadInsightTab,
    openPreview: openPreview,
  };
})(window);
