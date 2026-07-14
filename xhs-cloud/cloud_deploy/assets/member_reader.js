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
  var dashData = { today: {}, insightTree: [] }; // 全局保存 dashboard 数据，供卡片视图使用
  var readerViewMode = 'list'; // 'list' | 'cards'
  var dashboard = null;
  var archiveItems = [];

  // ===== AI 生成进度条 overlay（即使是预生成也显示，模拟实时调用） =====
  var aiGenTimers = [];
  var aiGenStageIdx = 0;
  // 阶段文案：模拟云端真实 LLM 调用流程
  var AI_GEN_STAGES = [
    { pct: 8,  sub: '正在连接云端 AI 模型…',          stage: '初始化' },
    { pct: 18, sub: '读取榜单数据（28 个维度）…',  stage: '读取数据' },
    { pct: 32, sub: '调用 DeepSeek V4 分析日销量增量榜…', stage: '榜单 1/10' },
    { pct: 42, sub: '调用 DeepSeek V4 分析低竞争机会榜…', stage: '榜单 2/10' },
    { pct: 52, sub: '调用 DeepSeek V4 分析新品动量榜…',  stage: '榜单 3/10' },
    { pct: 62, sub: '调用 DeepSeek V4 分析价格带榜单…',  stage: '榜单 4/10' },
    { pct: 72, sub: '调用 DeepSeek V4 分析类目榜单…',    stage: '榜单 5/10' },
    { pct: 82, sub: '生成跨榜综述与方向交集分析…',       stage: '跨榜综述' },
    { pct: 92, sub: '校验合规（商品 ID 拦截）…',  stage: '合规校验' },
    { pct: 98, sub: '打包发布到会员阅读区…',             stage: '发布' }
  ];

  function clearAiGenTimers() {
    for (var i = 0; i < aiGenTimers.length; i++) {
      clearTimeout(aiGenTimers[i]);
      clearInterval(aiGenTimers[i]);
    }
    aiGenTimers = [];
  }

  function showAiGenOverlay(inline) {
    var ov = el('aiGenOverlay');
    if (!ov) return;
    clearAiGenTimers();
    aiGenStageIdx = 0;
    // inline 模式：把 overlay 移入 reader-detail，只覆盖详情视图区域
    if (inline) {
      var detail = el('readerDetail');
      if (detail && detail !== ov.parentNode) {
        detail.appendChild(ov);
      }
      ov.classList.add('inline');
    } else {
      var shell = el('memberShell');
      if (shell && shell !== ov.parentNode) {
        shell.appendChild(ov);
      }
      ov.classList.remove('inline');
    }
    ov.classList.remove('hidden', 'leaving');
    // 立即显示第一帧
    updateAiGenStage(0);
    // 分阶段推进：inline 模式用更短的总时长（~0.9s），全屏模式 1.6s
    var stageDelay = inline ? 100 : 170;
    for (var i = 1; i < AI_GEN_STAGES.length; i++) {
      aiGenTimers.push(setTimeout((function (idx) {
        return function () { updateAiGenStage(idx); };
      })(i), stageDelay * i));
    }
  }

  function updateAiGenStage(idx) {
    if (idx < 0 || idx >= AI_GEN_STAGES.length) return;
    var s = AI_GEN_STAGES[idx];
    aiGenStageIdx = idx;
    var fill = el('aiGenBarFill');
    var pct = el('aiGenPct');
    var sub = el('aiGenSub');
    var stage = el('aiGenStage');
    if (fill) fill.style.width = s.pct + '%';
    if (pct) pct.textContent = s.pct + '%';
    if (sub) sub.textContent = s.sub;
    if (stage) stage.textContent = s.stage;
  }

  function hideAiGenOverlay(opts) {
    opts = opts || {};
    var ov = el('aiGenOverlay');
    if (!ov || ov.classList.contains('hidden')) return;
    // 推到 100%
    updateAiGenStage(AI_GEN_STAGES.length - 1);
    var fill = el('aiGenBarFill');
    var pct = el('aiGenPct');
    var sub = el('aiGenSub');
    var stage = el('aiGenStage');
    if (fill) fill.style.width = '100%';
    if (pct) pct.textContent = '100%';
    if (sub) sub.textContent = 'AI 选品报告已就绪';
    if (stage) stage.textContent = '完成';
    clearAiGenTimers();
    // 短暂停留再淡出
    setTimeout(function () {
      if (ov) {
        ov.classList.add('leaving');
        setTimeout(function () {
          if (ov) ov.classList.add('hidden');
          if (ov) ov.classList.remove('leaving', 'inline');
          // 恢复 overlay 到 memberShell（如果在 inline 模式下被移到了 reader-main）
          var shell = el('memberShell');
          if (shell && ov.parentNode && ov.parentNode.id !== 'memberShell') {
            shell.appendChild(ov);
          }
        }, 250);
      }
    }, opts.delay || 120);
  }

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

  function renderPendingState(today) {
    var hint = '报告生成中，预计今日 18:30 前更新。';
    if (today && today.report_date) {
      hint += ' 可先浏览侧栏类目情报或「历史归档」。';
    }
    renderEmptyWaiting(hint);
    setState('PENDING');
    var chrome = el('readerChrome');
    if (chrome) {
      var hero = chrome.getAttribute('data-hero-html') || '';
      chrome.innerHTML = hero + '<h2>今日分析</h2><p>生成中 · 预计 18:30 前更新</p>';
    }
  }

  function bindReadingProgress() {
    var bar = el('readerProgress');
    if (!bar) return;
    var span = bar.querySelector('span');
    function onScroll(target) {
      if (!target) return;
      var h = target.scrollHeight - target.clientHeight;
      var pct = h > 0 ? Math.min(100, Math.round((target.scrollTop / h) * 100)) : 0;
      if (span) span.style.width = pct + '%';
      bar.setAttribute('aria-hidden', pct <= 2 ? 'true' : 'false');
    }
    var body = el('readerBody');
    if (body) body.addEventListener('scroll', function () { onScroll(body); });
  }

  function bindReaderUX() {
    var mobileNav = el('readerMobileNav');
    if (mobileNav) {
      mobileNav.classList.remove('hidden');
      mobileNav.querySelectorAll('[data-route]').forEach(function (btn) {
        btn.onclick = function () {
          var route = btn.getAttribute('data-route') || 'today';
          // switchDash → switchAppPanel → MemberRouter.go，避免重复触发
          if (typeof switchDash === 'function') {
            switchDash(route);
          } else if (window.MemberRouter) {
            MemberRouter.go(route);
          }
          mobileNav.querySelectorAll('.reader-mobile-nav-btn').forEach(function (b) {
            b.classList.toggle('active', b === btn);
          });
        };
      });
    }
    bindReadingProgress();
  }

  function renderHero(radar, recommendations) {
    var chrome = el('readerChrome');
    if (!chrome) return;
    var parts = [];
    if (radar && radar.items && radar.items.length) {
      parts.push('<div class="reader-hero-block"><span class="reader-hero-label">机会雷达</span> ');
      for (var i = 0; i < Math.min(3, radar.items.length); i++) {
        var it = radar.items[i];
        parts.push('<button type="button" class="reader-hero-chip" data-insight-cat="' + escFn(it.category) + '" data-insight-date="' + escFn(it.report_date || '') + '">'
          + escFn(it.category || '') + '</button>');
      }
      parts.push('</div>');
    }
    if (recommendations && recommendations.items && recommendations.items.length) {
      parts.push('<div class="reader-hero-block"><span class="reader-hero-label">推荐阅读</span> ');
      for (var j = 0; j < Math.min(3, recommendations.items.length); j++) {
        var rec = recommendations.items[j];
        parts.push('<button type="button" class="reader-hero-chip" data-insight-cat="' + escFn(rec.category) + '" data-insight-date="' + escFn(rec.report_date || '') + '">'
          + escFn(rec.category || '') + '</button>');
      }
      parts.push('</div>');
    }
    var heroHtml = parts.length ? '<div class="reader-hero">' + parts.join('') + '</div>' : '';
    chrome.setAttribute('data-hero-html', heroHtml);
  }

  function applyChrome(title, subtitle) {
    var chrome = el('readerChrome');
    if (!chrome) return;
    var hero = chrome.getAttribute('data-hero-html') || '';
    chrome.innerHTML = hero + '<h2>' + escFn(title || 'AI 选品分析') + '</h2>'
      + (subtitle ? '<p>' + escFn(subtitle) + '</p>' : '');
    chrome.querySelectorAll('.reader-hero-chip').forEach(function (btn) {
      btn.onclick = function () {
        selectNode({
          type: 'insight',
          date: btn.getAttribute('data-insight-date') || '',
          category: btn.getAttribute('data-insight-cat') || ''
        });
      };
    });
  }

  // ===== 8 列等宽规整卡片网格（v2） =====
  function renderCardList(today, insightTree) {
    today = today || {};
    insightTree = insightTree || [];
    dashData.today = today;
    dashData.insightTree = insightTree;

    var body = el('readerCardListBody');
    var dateEl = el('cardListDate');
    if (!body) return;
    var date = today.report_date || '';
    if (dateEl) {
      if (today.status === 'pending') {
        dateEl.textContent = date ? ('报告日期 ' + date + ' · 生成中') : '报告生成中';
      } else if (date) {
        dateEl.textContent = '报告日期 ' + date;
      } else {
        dateEl.textContent = '暂无报告';
      }
    }

    var html = '';
    var seenInsight = {};

    // 今日简报分组
    if (today.overview) {
      html += '<div class="reader-card-group">';
      html += '<div class="reader-card-group-title">今日简报<span class="count">1</span></div>';
      html += '<div class="reader-card-grid">';
      html += buildCardCell({
        icon: '📊',
        badge: '简报',
        title: today.overview.title || '市场观察',
        tags: [{ text: 'AI 选品', cls: '' }],
        node: { type: 'overview', date: date }
      });
      html += '</div></div>';
    }

    // 方向解读分组（按虚拟/实体分类分区展示）
    if (today.directions && today.directions.length) {
      // 按 category_type 分组
      var physicalDirs = [];
      var virtualDirs = [];
      var mixedDirs = [];
      var uncatDirs = [];
      for (var di = 0; di < today.directions.length; di++) {
        var dd = today.directions[di];
        var ct = (dd.category_type || '').toLowerCase();
        if (ct === 'physical') physicalDirs.push(dd);
        else if (ct === 'virtual') virtualDirs.push(dd);
        else if (ct === 'mixed') mixedDirs.push(dd);
        else uncatDirs.push(dd);
      }

      html += '<div class="reader-card-group">';
      html += '<div class="reader-card-group-title">方向解读<span class="count">' + today.directions.length + '</span></div>';

      // 实体商品子分组
      if (physicalDirs.length) {
        html += '<div class="reader-card-subgroup">';
        html += '<div class="reader-card-subgroup-title">🏷️ 实体商品<span class="count">' + physicalDirs.length + '</span></div>';
        html += '<div class="reader-card-grid">';
        for (var pi = 0; pi < physicalDirs.length; pi++) {
          var pd = physicalDirs[pi];
          var ptags = [];
          if (pd.key) ptags.push({ text: pd.key, cls: '' });
          html += buildCardCell({
            icon: '🎯',
            badge: '实体',
            title: pd.title || pd.key,
            tags: ptags,
            node: { type: 'direction', date: date, key: pd.key }
          });
        }
        html += '</div></div>';
      }

      // 虚拟商品子分组
      if (virtualDirs.length) {
        html += '<div class="reader-card-subgroup">';
        html += '<div class="reader-card-subgroup-title">💾 虚拟商品<span class="count">' + virtualDirs.length + '</span></div>';
        html += '<div class="reader-card-grid">';
        for (var vi = 0; vi < virtualDirs.length; vi++) {
          var vd = virtualDirs[vi];
          var vtags = [];
          if (vd.key) vtags.push({ text: vd.key, cls: '' });
          html += buildCardCell({
            icon: '🎯',
            badge: '虚拟',
            title: vd.title || vd.key,
            tags: vtags,
            node: { type: 'direction', date: date, key: vd.key }
          });
        }
        html += '</div></div>';
      }

      // 混合 + 未分类子分组（合并展示，避免老报告无 category_type 时整组消失）
      var otherDirs = mixedDirs.concat(uncatDirs);
      if (otherDirs.length) {
        html += '<div class="reader-card-subgroup">';
        var otherTitle = mixedDirs.length && uncatDirs.length ? '🔄 混合 / 其他' : (mixedDirs.length ? '🔄 混合商品' : '📋 方向解读');
        html += '<div class="reader-card-subgroup-title">' + otherTitle + '<span class="count">' + otherDirs.length + '</span></div>';
        html += '<div class="reader-card-grid">';
        for (var oi = 0; oi < otherDirs.length; oi++) {
          var od = otherDirs[oi];
          var otags = [];
          if (od.key) otags.push({ text: od.key, cls: '' });
          html += buildCardCell({
            icon: '🎯',
            badge: '方向',
            title: od.title || od.key,
            tags: otags,
            node: { type: 'direction', date: date, key: od.key }
          });
        }
        html += '</div></div>';
      }

      html += '</div>'; // /reader-card-group
    }

    // 类目情报分组
    var insightItems = [];
    if (insightTree.length) {
      for (var g = 0; g < insightTree.length; g++) {
        var group = insightTree[g];
        var gdate = group.report_date || '';
        var items = group.items || [];
        for (var j = 0; j < items.length; j++) {
          var ins = items[j];
          var cat = ins.category || '';
          var key = gdate + ':' + cat;
          if (seenInsight[key]) continue;
          seenInsight[key] = true;
          insightItems.push({ ins: ins, gdate: gdate });
        }
      }
    } else if (today.insights && today.insights.length) {
      for (var k = 0; k < today.insights.length; k++) {
        insightItems.push({ ins: today.insights[k], gdate: today.insights[k].report_date || date });
      }
    }

    if (insightItems.length) {
      html += '<div class="reader-card-group">';
      html += '<div class="reader-card-group-title">类目情报<span class="count">' + insightItems.length + '</span></div>';
      html += '<div class="reader-card-grid">';
      for (var m = 0; m < insightItems.length; m++) {
        var item = insightItems[m];
        var ins2 = item.ins;
        var gdate2 = item.gdate;
        var stars = ins2.stars || 0;
        var growth = ins2.growth_rate;
        var growthStr = (growth !== null && growth !== undefined && growth !== '') ? (growth + '%') : '';
        var growthCls = growth > 0 ? 'growth-up' : (growth < 0 ? 'growth-down' : '');
        var trend = ins2.trend_label || '';
        var tags = [];
        if (stars) tags.push({ text: '★' + stars, cls: 'stars' });
        if (growthStr) tags.push({ text: (growth > 0 ? '↑' : growth < 0 ? '↓' : '') + growthStr, cls: growthCls });
        if (trend) tags.push({ text: trend, cls: '' });
        if (ins2.lifecycle_stage) tags.push({ text: ins2.lifecycle_stage, cls: '' });
        html += buildCardCell({
          icon: '📈',
          badge: stars ? ('★' + stars) : '类目',
          title: ins2.category || '类目',
          tags: tags,
          node: { type: 'insight', date: gdate2, category: ins2.category || '' }
        });
      }
      html += '</div></div>';
    }

    if (!html) {
      if (today.status === 'pending') {
        html = '<div class="reader-empty">报告生成中，预计今日 18:30 前更新。</div>';
      } else {
        html = '<div class="reader-empty">今日 AI 分析尚未发布，请稍后再来。</div>';
      }
    }
    body.innerHTML = html;

    // 绑定卡片点击
    var cells = body.querySelectorAll('.reader-card-cell');
    for (var r = 0; r < cells.length; r++) {
      cells[r].onclick = function () {
        selectNode({
          type: this.getAttribute('data-node'),
          date: this.getAttribute('data-date') || '',
          key: this.getAttribute('data-key') || '',
          category: this.getAttribute('data-category') || ''
        }, true);
      };
    }
  }

  function buildCardCell(opts) {
    var node = opts.node || {};
    return '<button type="button" class="reader-card-cell"'
      + ' data-node="' + escFn(node.type || '') + '"'
      + ' data-date="' + escFn(node.date || '') + '"'
      + (node.key ? ' data-key="' + escFn(node.key) + '"' : '')
      + (node.category ? ' data-category="' + escFn(node.category) + '"' : '')
      + '>'
      + '<div class="rcc-icon">' + opts.icon + '</div>'
      + '<div class="rcc-title">' + escFn(opts.title) + '</div>'
      + '</button>';
  }

  function highlightCard(node) {
    var body = el('readerCardListBody');
    if (!body) return;
    var cells = body.querySelectorAll('.reader-card-cell');
    for (var i = 0; i < cells.length; i++) {
      var btn = cells[i];
      var match = btn.getAttribute('data-node') === node.type
        && (btn.getAttribute('data-date') || '') === (node.date || '');
      if (node.type === 'direction') match = match && btn.getAttribute('data-key') === node.key;
      if (node.type === 'insight') match = match && btn.getAttribute('data-category') === node.category;
      btn.classList.toggle('active', match);
    }
  }

  // 切换到详情视图
  function showDetailView() {
    var list = el('readerCardList');
    var detail = el('readerDetail');
    if (list) list.classList.add('hidden');
    if (detail) detail.classList.remove('hidden');
  }

  // 返回卡片列表
  function backToCardList() {
    var list = el('readerCardList');
    var detail = el('readerDetail');
    if (detail) detail.classList.add('hidden');
    if (list) list.classList.remove('hidden');
    // 重置详情视图状态
    var frameWrap = el('readerFrameWrap');
    var body = el('readerBody');
    if (frameWrap) frameWrap.classList.add('hidden');
    if (body) body.classList.add('hidden');
    current.node = null;
    setState('IDLE');
  }

  function updateChrome(title, subtitle) {
    applyChrome(title, subtitle);
  }

  // 轻量 Markdown → HTML 渲染（ES5 兼容，支持 emoji/标题/引用/列表/加粗/代码/分隔线）
  function renderMarkdown(md) {
    if (!md) return '';
    var text = String(md);
    // 1. 转义 HTML 特殊字符
    text = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    // 2. 标题（#### ### ## #）
    text = text.replace(/^#### (.+)$/gm, '\n<h4>$1</h4>\n');
    text = text.replace(/^### (.+)$/gm, '\n<h3>$1</h3>\n');
    text = text.replace(/^## (.+)$/gm, '\n<h2>$1</h2>\n');
    text = text.replace(/^# (.+)$/gm, '\n<h1>$1</h1>\n');
    // 3. 引用块（> ...）
    text = text.replace(/^&gt; (.+)$/gm, '\n<blockquote>$1</blockquote>\n');
    // 4. 分隔线 ---
    text = text.replace(/^---+$/gm, '\n<hr>\n');
    // 5. 无序列表（- ... 或 * ...）
    text = text.replace(/^[\-\*] (.+)$/gm, '\n<li>$1</li>\n');
    // 6. 有序列表（1. ...）
    text = text.replace(/^\d+\. (.+)$/gm, '\n<li>$1</li>\n');
    // 7. 把连续 <li> 包成 <ul>
    text = text.replace(/(?:<li>[\s\S]*?<\/li>\s*)+/g, function (m) {
      return '<ul>' + m.replace(/\s+/g, ' ') + '</ul>';
    });
    // 8. 加粗 **...**
    text = text.replace(/\*\*([^\*]+?)\*\*/g, '<strong>$1</strong>');
    // 9. 行内代码 `...`
    text = text.replace(/`([^`]+?)`/g, '<code>$1</code>');
    // 10. 段落处理：按空行分块
    var blocks = text.split(/\n{2,}/);
    var out = [];
    for (var i = 0; i < blocks.length; i++) {
      var b = blocks[i].replace(/^\n+|\n+$/g, '');
      if (!b) continue;
      if (/^<(h[1-6]|ul|ol|blockquote|hr|pre|table|div|p)/.test(b)) {
        out.push(b);
      } else {
        b = b.replace(/\n/g, '<br>');
        out.push('<p>' + b + '</p>');
      }
    }
    return out.join('\n');
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
    body.innerHTML = '<article class="advisor-prose">' + renderMarkdown(html) + '</article>'
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
    // iframe 加载完成后隐藏 AI overlay（如有）
    if (frame) {
      frame.onload = function () { hideAiGenOverlay(); };
    }
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
    if (frame) {
      frame.onload = function () { hideAiGenOverlay(); };
    }
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
    if (err && err.status === 410) {
      setState('ERROR');
      var mig = '/member#today';
      try {
        var det = err.data && err.data.detail;
        if (det && typeof det === 'object' && det.migration_url) mig = det.migration_url;
      } catch (e) {}
      if (errEl) {
        errEl.style.display = 'block';
        errEl.innerHTML = '表格数据包已下线，请前往 <a href="' + escFn(mig) + '" style="color:var(--reader-accent)">AI 分析中心</a> 阅读。';
      }
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

  function selectNode(node, isUserClick) {
    current.node = node;
    current.date = node.date || '';
    setState('LOADING');
    highlightCard(node);

    // 切换到详情视图
    showDetailView();

    var locked = el('readerLocked');
    var errEl = el('readerError');
    if (locked) locked.style.display = 'none';
    if (errEl) errEl.style.display = 'none';

    // 用户点击卡片时，模拟 AI 实时生成动画（inline 模式，只覆盖详情视图区域）
    if (isUserClick) {
      showAiGenOverlay(true);
    }

    if (node.type === 'insight') {
      updateChrome(node.category, node.date);
      var insUrl = '/api/v1/member/insight/' + encodeURIComponent(node.date) + '/' + encodeURIComponent(node.category) + '/view';
      loadInsightIframe(insUrl);
      return;
    }

    if (node.type === 'overview' && node.date) {
      apiFn('/api/v1/member/advisor/' + encodeURIComponent(node.date), { auth: true })
        .then(function (data) { renderMarkdownArticle(data, node); })
        .then(function () { if (isUserClick) hideAiGenOverlay(); })
        .catch(function (e) {
          if (isUserClick) hideAiGenOverlay();
          if (e && e.status === 404) loadAdvisorHtml(node.date);
          else handleError(e);
        });
      return;
    }

    if (node.type === 'direction' && node.date && node.key) {
      apiFn('/api/v1/member/advisor/' + encodeURIComponent(node.date) + '/articles/' + encodeURIComponent(node.key), { auth: true })
        .then(function (data) { renderMarkdownArticle(data, node); })
        .then(function () { if (isUserClick) hideAiGenOverlay(); })
        .catch(function (e) {
          if (isUserClick) hideAiGenOverlay();
          handleError(e);
        });
      return;
    }

    if (node.type === 'archive' && node.date) {
      apiFn('/api/v1/member/advisor/' + encodeURIComponent(node.date), { auth: true })
        .then(function (data) { renderMarkdownArticle(data, node); })
        .then(function () { if (isUserClick) hideAiGenOverlay(); })
        .catch(function (e) {
          if (isUserClick) hideAiGenOverlay();
          if (e && e.status === 404) loadAdvisorHtml(node.date);
          else handleError(e);
        });
      return;
    }

    if (isUserClick) hideAiGenOverlay();
    renderEmptyWaiting();
  }

  function updateKPIs(data) {
    data = data || {};
    var today = data.today || {};
    var insightTree = data.insight_tree || [];
    var directions = today.directions || [];
    var insights = today.insights || [];
    // 今日榜单 = 类目情报数（优先 insight_tree 第一组的 items 数，回退 today.insights）
    var rankingCount = 0;
    if (insightTree.length && insightTree[0] && insightTree[0].items) {
      rankingCount = insightTree[0].items.length;
    } else {
      rankingCount = insights.length;
    }
    // 方向解读 = directions 数量
    var dirCount = directions.length;
    // 蓝海机会 = 高星级（≥4星）类目情报数
    var blueOcean = 0;
    var allInsights = [];
    if (insightTree.length) {
      for (var i = 0; i < insightTree.length; i++) {
        var items = (insightTree[i] || {}).items || [];
        for (var j = 0; j < items.length; j++) allInsights.push(items[j]);
      }
    } else {
      allInsights = insights;
    }
    for (var k = 0; k < allInsights.length; k++) {
      if ((allInsights[k].stars || 0) >= 4) blueOcean++;
    }
    // 报告日期
    var dateStr = today.report_date || '';
    var dateShort = dateStr ? dateStr.slice(5) : '—'; // MM-DD
    // 模式标签
    var mode = today.status === 'published' ? 'AI 已生成' : '生成中';

    var set = function (id, val) {
      var n = document.getElementById(id);
      if (n) n.textContent = val;
    };
    set('kpiRankings', rankingCount || '—');
    set('kpiDirections', dirCount || '—');
    set('kpiBlueOcean', blueOcean || '—');
    set('kpiDate', dateShort);
    set('kpiMode', mode);
    set('kpiRankingsDelta', rankingCount ? '类目情报' : '暂无');
    set('kpiDirectionsDelta', dirCount ? '个方向' : '暂无');
    // 侧栏会员标签
    var planLabel = (data.membership && (data.membership.plan_label || data.membership.plan_code)) || '会员版';
    var planNode = document.getElementById('sidebarPlanLabel');
    if (planNode) planNode.textContent = planLabel;
  }

  function loadDashboard() {
    setState('LOADING');
    // 显示 AI 生成中 overlay（即使是预生成也走这个动画，让用户感觉是实时调用）
    showAiGenOverlay();
    return Promise.all([
      apiFn('/api/v1/member/advisor/dashboard', { auth: true }),
      apiFn('/api/v1/member/insight/radar', { auth: true }).catch(function () { return null; }),
      apiFn('/api/v1/member/insight/recommendations', { auth: true }).catch(function () { return null; })
    ]).then(function (results) {
      var data = results[0];
      var radar = results[1];
      var recommend = results[2];
      dashboard = data;
      // 至少展示 1.4s，避免动画闪过；API 快的话也走完阶段
      return new Promise(function (resolve) {
        setTimeout(function () { resolve({ data: data, radar: radar, recommend: recommend }); }, 1400);
      });
    }).then(function (bundle) {
      renderHero(bundle.radar, bundle.recommend);
      // 渲染横排卡片瀑布流列表（今日简报 / 方向解读 / 类目情报）
      renderCardList(bundle.data.today || {}, bundle.data.insight_tree || []);
      var today = bundle.data.today || {};
      applyChrome('今日分析', today.report_date ? '报告日期 ' + today.report_date : '');
      updateKPIs(bundle.data);
      hideAiGenOverlay();
      return bundle.data;
    }).catch(function (err) {
      hideAiGenOverlay();
      return handleError(err);
    });
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

      // 1) 按月份分组（YYYY-MM → items[]）
      var groups = {};
      var groupOrder = [];
      for (var i = 0; i < archiveItems.length; i++) {
        var it = archiveItems[i];
        var ym = (it.report_date || '').slice(0, 7);
        if (!ym) continue;
        if (!groups[ym]) { groups[ym] = []; groupOrder.push(ym); }
        groups[ym].push(it);
      }
      groupOrder.sort().reverse(); // 最近的月份在前

      // 2) 当前月份
      var now = new Date();
      var currentYM = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0');

      // 3) 渲染月份分组
      var html = '<div class="archive-list">';
      for (var g = 0; g < groupOrder.length; g++) {
        var ym = groupOrder[g];
        var items = groups[ym];
        var isCurrent = (ym === currentYM);
        var expanded = isCurrent; // 当前月默认展开
        var ymLabel = formatMonthLabel(ym);
        var icon = expanded ? '📂' : '📁';
        var arrow = expanded ? '▼' : '▶';

        html += '<div class="archive-month-group' + (isCurrent ? ' current' : '') + '">';
        html += '<div class="archive-month-head" data-ym="' + escFn(ym) + '">';
        html += '<span class="archive-month-icon">' + icon + '</span>';
        html += '<span class="archive-month-title">' + escFn(ymLabel) + '</span>';
        html += '<span class="archive-month-count">' + items.length + ' 篇</span>';
        html += '<span class="archive-month-arrow">' + arrow + '</span>';
        html += '</div>';
        html += '<div class="archive-month-body"' + (expanded ? '' : ' style="display:none"') + '>';
        for (var k = 0; k < items.length; k++) {
          var it2 = items[k];
          var dayLabel = (it2.report_date || '').slice(5); // "07-14"
          // 虚拟/实体分类徽标
          var physicalCnt = it2.physical_count || 0;
          var virtualCnt = it2.virtual_count || 0;
          var mixedCnt = it2.mixed_count || 0;
          var badges = '';
          if (physicalCnt || virtualCnt || mixedCnt) {
            badges = '<div class="ai-cat-badges">'
              + (physicalCnt ? '<span class="cat-badge cat-physical">🏷️ 实体 ' + physicalCnt + '</span>' : '')
              + (virtualCnt ? '<span class="cat-badge cat-virtual">💾 虚拟 ' + virtualCnt + '</span>' : '')
              + (mixedCnt ? '<span class="cat-badge cat-mixed">🔄 混合 ' + mixedCnt + '</span>' : '')
              + '</div>';
          }
          html += '<div class="archive-item" data-date="' + escFn(it2.report_date) + '">'
            + '<div><div class="ai-date">' + escFn(dayLabel) + '</div>'
            + '<div class="ai-summary">' + escFn(it2.summary || 'AI 选品顾问报告') + '</div>'
            + badges + '</div>'
            + '<span class="archive-read-link">阅读 →</span></div>';
        }
        html += '</div>'; // /archive-month-body
        html += '</div>'; // /archive-month-group
      }
      html += '</div>';
      host.innerHTML = html;

      // 4) 绑定月份标题点击（展开/折叠）
      var heads = host.querySelectorAll('.archive-month-head');
      for (var h = 0; h < heads.length; h++) {
        heads[h].onclick = function () {
          toggleArchiveMonth(this);
        };
      }
      // 5) 绑定日期项点击（阅读报告）
      var rows = host.querySelectorAll('.archive-item');
      for (var j = 0; j < rows.length; j++) {
        rows[j].onclick = function (e) {
          e.stopPropagation(); // 防止冒泡到月份标题
          var d = this.getAttribute('data-date');
          if (window.MemberRouter) MemberRouter.go('today');
          selectNode({ type: 'archive', date: d });
        };
      }
    }).catch(function (e) {
      host.innerHTML = '<div class="reader-empty">' + escFn(e.message || '加载失败') + '</div>';
    });
  }

  function toggleArchiveMonth(headEl) {
    var group = headEl.parentNode;
    var body = group.querySelector('.archive-month-body');
    var arrow = headEl.querySelector('.archive-month-arrow');
    var icon = headEl.querySelector('.archive-month-icon');
    if (!body) return;
    var isOpen = body.style.display !== 'none';
    if (isOpen) {
      body.style.display = 'none';
      if (arrow) arrow.textContent = '▶';
      if (icon) icon.textContent = '📁';
    } else {
      body.style.display = '';
      if (arrow) arrow.textContent = '▼';
      if (icon) icon.textContent = '📂';
    }
  }

  function formatMonthLabel(ym) {
    var parts = ym.split('-');
    if (parts.length < 2) return ym;
    return parts[0] + '年' + parseInt(parts[1], 10) + '月';
  }

  function boot() {
    bindReaderUX();
    return loadDashboard();
  }

  // 暴露为全局，供 HTML onclick 调用
  window.backToCardList = backToCardList;
  window.selectNode = function (node, isUserClick) {
    selectNode(node, isUserClick !== undefined ? isUserClick : true);
  };

  return {
    boot: boot,
    loadDashboard: loadDashboard,
    loadArchive: loadArchive,
    selectNode: selectNode,
    backToCardList: backToCardList,
    getDashboard: function () { return dashboard; }
  };
})();
