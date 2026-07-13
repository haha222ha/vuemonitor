/**
 * 会员站 AI 阅读器 — ES5
 * 依赖：MemberCore.api / global.api
 */
var MemberReader = (function () {
  'use strict';

  var apiFn = function (path, opts) {
    if (typeof window.api === 'function') return window.api(path, opts);
    if (window.MemberCore && window.MemberCore.api) return window.MemberCore.api(path, opts);
    return Promise.reject(new Error('api 未加载'));
  };

  var escFn = function (s) {
    if (typeof window.esc === 'function') return window.esc(s);
    if (window.MemberCore && window.MemberCore.esc) return window.MemberCore.esc(s);
    return String(s || '');
  };

  var getToken = function () {
    if (window.MemberCore && window.MemberCore.getToken) return window.MemberCore.getToken();
    try { return localStorage.getItem('xhs_member_token') || ''; } catch (e) { return ''; }
  };

  var state = 'IDLE';
  var current = { date: '', node: null };
  var dashboard = null;
  var archiveItems = [];

  function setState(s) {
    state = s;
    document.body.dataset.readerState = s;
  }

  function el(id) {
    return document.getElementById(id);
  }

  function renderEmptyWaiting(msg) {
    var body = el('readerBody');
    var frameWrap = el('readerFrameWrap');
    if (frameWrap) frameWrap.classList.add('hidden');
    if (body) {
      body.classList.remove('hidden');
      body.innerHTML = '<div class="reader-empty">' + escFn(msg || '今日 AI 分析尚未发布，请稍后再来。类目情报将在右侧树中展示。') + '</div>';
    }
    var chrome = el('readerChrome');
    if (chrome) chrome.innerHTML = '<h2>今日分析</h2><p>等待云端发布…</p>';
    setState('IDLE');
  }

  function renderSidebar(today) {
    var side = el('readerSidebar');
    if (!side) return;
    today = today || {};
    var html = '';
    var date = today.report_date || '';

    if (today.overview) {
      html += '<div class="reader-tree-group"><div class="reader-tree-title">今日简报</div>';
      html += '<button type="button" class="reader-tree-item" data-node="overview" data-date="' + escFn(date) + '">'
        + escFn(today.overview.title || '市场观察')
        + '<span class="rt-meta">' + escFn((today.overview.summary || '').slice(0, 60)) + '</span></button></div>';
    }

    if (today.directions && today.directions.length) {
      html += '<div class="reader-tree-group"><div class="reader-tree-title">方向解读</div>';
      for (var i = 0; i < today.directions.length; i++) {
        var d = today.directions[i];
        html += '<button type="button" class="reader-tree-item" data-node="direction" data-key="' + escFn(d.key) + '" data-date="' + escFn(date) + '">'
          + escFn(d.title || d.key)
          + '<span class="rt-meta">' + escFn((d.summary || '').slice(0, 50)) + '</span></button>';
      }
      html += '</div>';
    }

    if (today.insights && today.insights.length) {
      html += '<div class="reader-tree-group"><div class="reader-tree-title">类目情报</div>';
      for (var j = 0; j < today.insights.length; j++) {
        var ins = today.insights[j];
        html += '<button type="button" class="reader-tree-item" data-node="insight" data-category="' + escFn(ins.category) + '" data-date="' + escFn(ins.report_date || date) + '">'
          + escFn(ins.category || '类目')
          + '<span class="rt-meta">★' + escFn(ins.stars || 0) + ' · ' + escFn((ins.summary || '').slice(0, 40)) + '</span></button>';
      }
      html += '</div>';
    }

    if (!html) {
      html = '<div class="reader-empty" style="padding:16px">暂无今日内容</div>';
    }
    side.innerHTML = html;

    var buttons = side.querySelectorAll('.reader-tree-item');
    for (var b = 0; b < buttons.length; b++) {
      buttons[b].onclick = function () {
        var nodeType = this.getAttribute('data-node');
        var node = {
          type: nodeType,
          date: this.getAttribute('data-date') || '',
          key: this.getAttribute('data-key') || '',
          category: this.getAttribute('data-category') || ''
        };
        selectNode(node);
      };
    }
  }

  function highlightTree(node) {
    var side = el('readerSidebar');
    if (!side) return;
    var items = side.querySelectorAll('.reader-tree-item');
    for (var i = 0; i < items.length; i++) {
      var btn = items[i];
      var match = btn.getAttribute('data-node') === node.type
        && (btn.getAttribute('data-date') || '') === (node.date || '');
      if (node.type === 'direction') match = match && btn.getAttribute('data-key') === node.key;
      if (node.type === 'insight') match = match && btn.getAttribute('data-category') === node.category;
      btn.classList.toggle('active', match);
    }
  }

  function updateChrome(title, subtitle) {
    var chrome = el('readerChrome');
    if (!chrome) return;
    chrome.innerHTML = '<h2>' + escFn(title || 'AI 选品分析') + '</h2>'
      + (subtitle ? '<p>' + escFn(subtitle) + '</p>' : '');
  }

  function renderMarkdownArticle(data, node) {
    var body = el('readerBody');
    var frameWrap = el('readerFrameWrap');
    if (frameWrap) frameWrap.classList.add('hidden');
    if (!body) return;

    var html = '';
    var title = '';
    if (data.daily_overview) {
      title = data.daily_overview.title || '今日市场观察';
      html = data.daily_overview.content || data.daily_overview.summary || '';
    } else if (data.content) {
      title = data.title || '分析';
      html = data.content;
    } else if (data.title) {
      title = data.title;
      html = data.summary || '';
    }

    updateChrome(title, node && node.date ? '报告日期 ' + node.date : '');
    body.classList.remove('hidden');
    body.innerHTML = '<article class="advisor-prose">' + escFn(html) + '</article>'
      + '<footer class="advisor-disclaimer">仅供参考，不构成投资建议。数据基于公开信息与系统计算，存在延迟与误差。</footer>';
    setState('READING');
  }

  function loadInsightIframe(url) {
    var body = el('readerBody');
    var frameWrap = el('readerFrameWrap');
    var frame = el('readerFrame');
    if (body) body.classList.add('hidden');
    if (frameWrap) frameWrap.classList.remove('hidden');
    if (frame) {
      var t = getToken();
      frame.src = url + (url.indexOf('?') >= 0 ? '&' : '?') + 'access_token=' + encodeURIComponent(t);
    }
    setState('READING');
  }

  function loadAdvisorHtml(date) {
    var body = el('readerBody');
    var frameWrap = el('readerFrameWrap');
    var frame = el('readerFrame');
    if (body) body.classList.add('hidden');
    if (frameWrap) frameWrap.classList.remove('hidden');
    if (frame) {
      var t = getToken();
      frame.src = '/api/v1/member/advisor/' + encodeURIComponent(date) + '/view?access_token=' + encodeURIComponent(t);
    }
    updateChrome('AI 选品顾问', date);
    setState('READING');
  }

  function handleError(err) {
    var locked = el('readerLocked');
    var errEl = el('readerError');
    if (err && err.status === 402) {
      setState('LOCKED');
      if (locked) locked.style.display = 'flex';
      if (errEl) errEl.style.display = 'none';
      return;
    }
    if (err && err.status === 401) {
      setState('ERROR');
      if (locked) locked.style.display = 'none';
      if (errEl) {
        errEl.style.display = 'block';
        errEl.textContent = '登录已失效，请退出后重新登录';
      }
      return;
    }
    setState('ERROR');
    if (locked) locked.style.display = 'none';
    if (errEl) {
      errEl.style.display = 'block';
      errEl.textContent = (err && err.message) || '加载失败';
    }
  }

  function selectNode(node) {
    current.node = node;
    current.date = node.date || '';
    setState('LOADING');
    highlightTree(node);

    var locked = el('readerLocked');
    var errEl = el('readerError');
    if (locked) locked.style.display = 'none';
    if (errEl) errEl.style.display = 'none';

    if (node.type === 'insight') {
      updateChrome(node.category, node.date);
      var insUrl = '/api/v1/member/insight/' + encodeURIComponent(node.date) + '/' + encodeURIComponent(node.category) + '/view';
      loadInsightIframe(insUrl);
      return;
    }

    if (node.type === 'overview' && node.date) {
      apiFn('/api/v1/member/advisor/' + encodeURIComponent(node.date), { auth: true })
        .then(function (data) { renderMarkdownArticle(data, node); })
        .catch(function (e) {
          if (e && e.status === 404) loadAdvisorHtml(node.date);
          else handleError(e);
        });
      return;
    }

    if (node.type === 'direction' && node.date && node.key) {
      apiFn('/api/v1/member/advisor/' + encodeURIComponent(node.date) + '/articles/' + encodeURIComponent(node.key), { auth: true })
        .then(function (data) { renderMarkdownArticle(data, node); })
        .catch(handleError);
      return;
    }

    if (node.type === 'archive' && node.date) {
      apiFn('/api/v1/member/advisor/' + encodeURIComponent(node.date), { auth: true })
        .then(function (data) { renderMarkdownArticle(data, node); })
        .catch(function (e) {
          if (e && e.status === 404) loadAdvisorHtml(node.date);
          else handleError(e);
        });
      return;
    }

    renderEmptyWaiting();
  }

  function loadDashboard() {
    setState('LOADING');
    return apiFn('/api/v1/member/advisor/dashboard', { auth: true }).then(function (data) {
      dashboard = data;
      renderSidebar(data.today || {});
      var today = data.today || {};
      if (today.overview) {
        selectNode({ type: 'overview', date: today.report_date || '' });
      } else if (today.insights && today.insights.length) {
        selectNode({
          type: 'insight',
          date: today.insights[0].report_date || today.report_date,
          category: today.insights[0].category
        });
      } else if (today.report_date && today.status === 'published') {
        selectNode({ type: 'overview', date: today.report_date });
      } else {
        renderEmptyWaiting();
      }
      return data;
    }).catch(handleError);
  }

  function loadArchive() {
    var host = el('archiveList');
    if (!host) return Promise.resolve();
    host.innerHTML = '<div class="reader-empty">加载中…</div>';
    return apiFn('/api/v1/member/advisor/library', { auth: true }).then(function (data) {
      archiveItems = data.items || [];
      if (!archiveItems.length) {
        host.innerHTML = '<div class="reader-empty">暂无历史 AI 顾问报告。类目情报请从「今日分析」阅读。</div>';
        return;
      }
      var html = '<div class="archive-list">';
      for (var i = 0; i < archiveItems.length; i++) {
        var it = archiveItems[i];
        html += '<div class="archive-item" data-date="' + escFn(it.report_date) + '">'
          + '<div><div class="ai-date">' + escFn(it.report_date) + '</div>'
          + '<div class="ai-summary">' + escFn(it.summary || 'AI 选品顾问报告') + '</div></div>'
          + '<span style="color:var(--reader-accent);font-size:13px">阅读 →</span></div>';
      }
      html += '</div>';
      host.innerHTML = html;
      var rows = host.querySelectorAll('.archive-item');
      for (var j = 0; j < rows.length; j++) {
        rows[j].onclick = function () {
          var d = this.getAttribute('data-date');
          if (window.MemberRouter) MemberRouter.go('today');
          selectNode({ type: 'archive', date: d });
        };
      }
    }).catch(function (e) {
      host.innerHTML = '<div class="reader-empty">' + escFn(e.message || '加载失败') + '</div>';
    });
  }

  function boot() {
    return loadDashboard();
  }

  return {
    boot: boot,
    loadDashboard: loadDashboard,
    loadArchive: loadArchive,
    selectNode: selectNode,
    getDashboard: function () { return dashboard; }
  };
})();
