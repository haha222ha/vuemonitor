/**
 * 会员中心 hash 路由 — ES5
 */
var MemberRouter = (function () {
  'use strict';

  var ROUTES = {
    today: 'today',
    insight: 'today',
    archive: 'archive',
    watchlist: 'watchlist',
    client: 'client',
    account: 'account',
    reports: 'today'
  };

  var current = 'today';

  function normalizeHash() {
    var raw = (location.hash || '').replace(/^#/, '').trim().toLowerCase();
    if (!raw) return 'today';
    return ROUTES[raw] || raw;
  }

  function applyRoute(name) {
    current = name || 'today';
    try { localStorage.setItem('xhs_member_dash_tab', current); } catch (e) {}

    document.querySelectorAll('.dash-tab').forEach(function (t) {
      if (t.classList.contains('hidden')) return;
      var dash = t.dataset.dash;
      t.classList.toggle('active', dash === current || (current === 'today' && dash === 'insight'));
    });

    var dashInsight = document.getElementById('dashInsight');
    var dashArchive = document.getElementById('dashArchive');
    var dashClient = document.getElementById('dashClient');
    var dashWatchlist = document.getElementById('dashWatchlist');
    var profileCard = document.querySelector('#dashView > .card');

    if (dashInsight) dashInsight.classList.toggle('hidden', current !== 'today');
    if (dashArchive) dashArchive.classList.toggle('hidden', current !== 'archive');
    if (dashClient) dashClient.classList.toggle('hidden', current !== 'client');
    if (dashWatchlist) dashWatchlist.classList.toggle('hidden', current !== 'watchlist');
    if (profileCard) profileCard.classList.toggle('hidden', current !== 'account');

    if (current === 'today' && window.MemberReader) {
      MemberReader.boot();
    }
    if (current === 'today' && window.MemberInsight && typeof MemberInsight.load === 'function') {
      MemberInsight.load();
    }
    if (current === 'archive' && window.MemberReader) {
      MemberReader.loadArchive();
    }
    if (current === 'watchlist' && typeof loadWatchlist === 'function') {
      loadWatchlist();
    }
    if (current === 'client' && typeof loadClientDownload === 'function') {
      loadClientDownload();
    }
  }

  function go(name, replace) {
    var route = ROUTES[name] || name || 'today';
    var hash = '#' + route;
    if (replace) {
      history.replaceState(null, '', location.pathname + location.search + hash);
    } else if (location.hash !== hash) {
      location.hash = hash;
    }
    applyRoute(route);
  }

  function init() {
    var route = normalizeHash();
    if (location.hash === '#reports' || location.hash === '#insight') {
      history.replaceState(null, '', location.pathname + location.search + '#' + (route === 'today' ? 'today' : route));
    }
    applyRoute(route);
    window.addEventListener('hashchange', function () {
      applyRoute(normalizeHash());
    });
  }

  return { go: go, init: init, current: function () { return current; } };
})();

function switchDash(name) {
  var map = { insight: 'today', reports: 'today' };
  var route = map[name] || name || 'today';
  if (window.MemberRouter) {
    MemberRouter.go(route);
    return;
  }
  if (typeof currentDash !== 'undefined') currentDash = route;
}
