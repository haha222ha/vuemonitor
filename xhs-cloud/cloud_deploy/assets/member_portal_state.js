/**

 * 会员中心会话状态 + 主题 + 能力矩阵导航

 */

(function (global) {

  'use strict';



  var THEME_KEY = 'xhs_member_portal_theme';

  var THEMES = ['apple', 'aurora', 'classic', 'light', 'warm'];

  var THEME_LABELS = {

    apple: 'Liquid Glass',

    aurora: 'Aurora Neon',

    classic: 'Linear Dark',

    light: 'Geist Light',

    warm: 'Sunset Bento'

  };

  var activeCap = null;



  function getToken() {

    try {

      return localStorage.getItem('xhs_member_token') || '';

    } catch (e) {

      return '';

    }

  }



  function loadProfile() {

    try {

      var raw = localStorage.getItem('xhs_member_profile');

      return raw ? JSON.parse(raw) : null;

    } catch (e) {

      return null;

    }

  }



  function resolveState(profile, hasToken) {

    if (!hasToken) return 'guest';

    if (!profile) return 'logged_in';

    if (profile.is_active === true) return 'member_active';

    if (profile.is_active === false) return 'member_expired';

    return 'logged_in';

  }



  function stateLabel(state) {

    return {

      guest: '访客',

      logged_in: '已登录',

      member_active: '有效会员',

      member_expired: '会员已过期'

    }[state] || '访客';

  }



  function stateHint(state, profile) {

    if (state === 'guest') {

      return '可预览 AI 阅读样例；开通会员后阅读最新分析与使用 PC 客户端。';

    }

    if (state === 'member_active') {

      var days = profile && profile.days_remaining != null ? profile.days_remaining : '';

      return '欢迎回来' + (profile && profile.username ? '，' + profile.username : '')

        + (days !== '' ? ' · 剩余 ' + days + ' 天' : '') + '。';

    }

    if (state === 'member_expired') {

      return '账号仍有效，但会员已过期。续费后可继续阅读 AI 分析与同步 PC。';

    }

    return '已登录，正在同步会员状态…';

  }



  function applyTheme(name) {

    var theme = THEMES.indexOf(name) >= 0 ? name : 'apple';

    document.documentElement.setAttribute('data-member-theme', theme);

    try { localStorage.setItem(THEME_KEY, theme); } catch (e) { /* ignore */ }

    var sel = document.getElementById('memberThemeSelect');

    if (sel) sel.value = theme;

    return theme;

  }



  function getTheme() {

    try {

      var stored = localStorage.getItem(THEME_KEY);

      if (stored && THEMES.indexOf(stored) >= 0) return stored;

    } catch (e) { /* ignore */ }

    return 'apple';

  }



  function highlightCapability(key) {

    activeCap = key || null;

    document.querySelectorAll('#capabilityGrid .capability-item').forEach(function (el) {

      el.classList.toggle('cap-active', !!key && el.dataset.cap === key);

    });

  }



  function navigateCapability(key) {

    var state = resolveState(loadProfile(), !!getToken());

    if (key === 'pc') {

      if (typeof global.switchTopNav === 'function') global.switchTopNav('pc');

      highlightCapability('pc');

      return;

    }

    if (typeof global.switchTopNav === 'function') global.switchTopNav('member');

    if (key === 'demo') {

      if (typeof global.switchPortal === 'function') global.switchPortal('demo');

      highlightCapability('demo');

      return;

    }

    if (key === 'custom') {

      if (typeof global.switchPortal === 'function') {

        global.switchPortal('center');

        if (typeof global.switchPricingCategory === 'function') global.switchPricingCategory('custom');

      }

      highlightCapability('custom');

      return;

    }

    if (key === 'advisor' || key === 'insight') {

      if (state === 'member_active') {

        if (typeof global.switchDash === 'function') global.switchDash('today');

        highlightCapability(key);

      } else if (state === 'guest') {

        if (typeof global.switchPortal === 'function') global.switchPortal('demo');

        highlightCapability('demo');

      } else {

        if (typeof global.switchPortal === 'function') global.switchPortal('center');

        highlightCapability('custom');

      }

      return;

    }

  }



  function renderCapabilities(state) {

    var grid = document.getElementById('capabilityGrid');

    if (!grid) return;

    var caps = [

      { key: 'demo', title: 'AI 样例', on: state === 'guest', tease: true, desc: '历史期次只读预览' },

      { key: 'advisor', title: 'AI 顾问', on: state === 'member_active', desc: '最新预生成文字报告' },

      { key: 'insight', title: '类目情报', on: state === 'member_active', desc: '单类目 AI 决策页' },

      { key: 'pc', title: 'PC 客户端', on: state === 'member_active', tease: state !== 'member_active', desc: '监控与云端同步' },

      { key: 'custom', title: '定制分析', on: state !== 'guest', tease: state === 'member_expired', desc: '会员 ¥9.9 / 非会员 ¥29.9' }

    ];

    grid.innerHTML = caps.map(function (c) {

      var cls = c.on ? 'state-on' : (c.tease ? 'state-tease' : 'state-off');

      if (activeCap === c.key) cls += ' cap-active';

      return '<div class="capability-item ' + cls + '" data-cap="' + c.key + '" role="button" tabindex="0" aria-label="' + c.title + '：' + c.desc + '">'

        + '<strong>' + c.title + '</strong>' + c.desc + '</div>';

    }).join('');

  }



  function bindCapabilityGrid() {

    var grid = document.getElementById('capabilityGrid');

    if (!grid || grid.dataset.bound) return;

    grid.dataset.bound = '1';

    grid.addEventListener('click', function (e) {

      var item = e.target.closest('.capability-item');

      if (!item || !item.dataset.cap) return;

      navigateCapability(item.dataset.cap);

    });

    grid.addEventListener('keydown', function (e) {

      if (e.key !== 'Enter' && e.key !== ' ') return;

      var item = e.target.closest('.capability-item');

      if (!item || !item.dataset.cap) return;

      e.preventDefault();

      navigateCapability(item.dataset.cap);

    });

  }



  function renderSessionBar(profile, hasToken) {

    var bar = document.getElementById('sessionStatusBar');

    if (!bar) return resolveState(profile, hasToken);

    var state = resolveState(profile, hasToken);

    bar.dataset.state = state;

    var badge = document.getElementById('sessionStatusBadge');

    var hint = document.getElementById('sessionStatusHint');

    if (badge) badge.textContent = stateLabel(state);

    if (hint) hint.textContent = stateHint(state, profile);

    renderCapabilities(state);

    renderSessionActions(state);

    return state;

  }



  function renderSessionActions(state) {

    var box = document.getElementById('sessionStatusActions');

    if (!box) return;

    if (state === 'guest') {

      box.innerHTML = '<button type="button" class="btn btn-ghost" style="min-height:32px;padding:6px 12px;font-size:13px" onclick="switchPortal(\'demo\')">看样例</button>'

        + '<button type="button" class="btn btn-ghost" style="min-height:32px;padding:6px 12px;font-size:13px" onclick="switchTopNav(\'pc\')">PC 客户端</button>'

        + '<button type="button" class="btn btn-primary" style="min-height:32px;padding:6px 12px;font-size:13px" onclick="switchPortal(\'center\')">开通会员</button>';

      return;

    }

    if (state === 'member_expired') {

      box.innerHTML = '<button type="button" class="btn btn-primary" style="min-height:32px;padding:6px 12px;font-size:13px" onclick="openBuyFromDash()">扫码续费</button>'

        + '<button type="button" class="btn btn-ghost" style="min-height:32px;padding:6px 12px;font-size:13px" onclick="switchTopNav(\'pc\')">PC 客户端</button>'

        + '<button type="button" class="btn btn-ghost" style="min-height:32px;padding:6px 12px;font-size:13px" onclick="switchDash(\'account\')">账户</button>';

      return;

    }

    if (state === 'member_active') {

      box.innerHTML = '<button type="button" class="btn btn-ghost" style="min-height:32px;padding:6px 12px;font-size:13px" onclick="switchDash(\'today\')">今日分析</button>'

        + '<button type="button" class="btn btn-ghost" style="min-height:32px;padding:6px 12px;font-size:13px" onclick="switchTopNav(\'pc\')">PC 客户端</button>'

        + '<button type="button" class="btn btn-ghost" style="min-height:32px;padding:6px 12px;font-size:13px" onclick="openBuyFromDash()">续费</button>';

      return;

    }

    box.innerHTML = '<button type="button" class="btn btn-ghost" style="min-height:32px;padding:6px 12px;font-size:13px" onclick="switchTab(\'login\')">登录</button>';

  }



  function bindThemeSelect() {

    var sel = document.getElementById('memberThemeSelect');

    if (!sel || sel.dataset.bound) return;

    sel.dataset.bound = '1';

    THEMES.forEach(function (t) {

      var opt = document.createElement('option');

      opt.value = t;

      opt.textContent = THEME_LABELS[t] || t;

      sel.appendChild(opt);

    });

    sel.value = getTheme();

    sel.addEventListener('change', function () { applyTheme(sel.value); });

  }



  function init() {

    applyTheme(getTheme());

    bindThemeSelect();

    bindCapabilityGrid();

    renderSessionBar(loadProfile(), !!getToken());

  }



  global.MemberPortalState = {

    init: init,

    applyTheme: applyTheme,

    getTheme: getTheme,

    renderSessionBar: renderSessionBar,

    resolveState: resolveState,

    loadProfile: loadProfile,

    getToken: getToken,

    navigateCapability: navigateCapability,

    highlightCapability: highlightCapability

  };



  if (document.readyState === 'loading') {

    document.addEventListener('DOMContentLoaded', init);

  } else {

    init();

  }

})(typeof window !== 'undefined' ? window : this);

