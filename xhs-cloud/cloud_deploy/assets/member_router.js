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
  var hashBound = false;
  var booted = false;

  function membershipExpired() {
    try {
      var raw = localStorage.getItem('xhs_member_profile');
      if (!raw) return false;
      var m = JSON.parse(raw);
      return m && m.is_active === false;
    } catch (e) {
      return false;
    }
  }

  function normalizeHash() {
    var raw = (location.hash || '').replace(/^#/, '').trim().toLowerCase();
    if (!raw) return membershipExpired() ? 'account' : 'today';
    return ROUTES[raw] || raw;
  }

  function applyRoute(name) {
    current = name || 'today';
    if (membershipExpired() && current !== 'account' && current !== 'client') {
      current = 'account';
    }
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
    var expired = membershipExpired();

    if (dashInsight) dashInsight.classList.toggle('hidden', current !== 'today');
    if (dashArchive) dashArchive.classList.toggle('hidden', current !== 'archive');
    if (dashClient) dashClient.classList.toggle('hidden', current !== 'client');
    if (dashWatchlist) dashWatchlist.classList.toggle('hidden', current !== 'watchlist');
    if (profileCard) profileCard.classList.toggle('hidden', current !== 'account' && !expired);

    if (current === 'today' && window.MemberReader && !booted && !expired) {
      booted = true;
      MemberReader.boot().catch(function () { booted = false; });
    }
    if (current === 'today' && window.MemberInsight && typeof MemberInsight.load === 'function' && !expired) {
      MemberInsight.load();
    }
    if (current === 'archive' && window.MemberReader && !expired) {
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
    if (membershipExpired() && route !== 'account' && route !== 'client') {
      route = 'account';
    }
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
    if (!hashBound) {
      hashBound = true;
      window.addEventListener('hashchange', function () {
        applyRoute(normalizeHash());
      });
    }
  }

  return {
    go: go,
    init: init,
    current: function () { return current; },
    resetBoot: function () { booted = false; }
  };
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
