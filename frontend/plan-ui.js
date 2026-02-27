/**
 * Whilber-AI Plan UI Module (Phase 5)
 * Shared across all pages — bootstraps plan awareness, nav updates, feature locks.
 * Loaded via <script src="/static/plan-ui.js"></script>
 */
(function(){
'use strict';

/* ═══════════════════════════════════════════
   CONSTANTS
   ═══════════════════════════════════════════ */
var PLAN_LABELS = {free:'\u0631\u0627\u06cc\u06af\u0627\u0646', pro:'\u062d\u0631\u0641\u0647\u200c\u0627\u06cc', premium:'\u0648\u06cc\u0698\u0647', enterprise:'\u0633\u0627\u0632\u0645\u0627\u0646\u06cc'};
var PLAN_COLORS = {free:'#94a3b8', pro:'#06b6d4', premium:'#a855f7', enterprise:'#f59e0b'};
var PLAN_BG     = {free:'rgba(148,163,184,.12)', pro:'rgba(6,182,212,.12)', premium:'rgba(168,85,247,.12)', enterprise:'rgba(245,158,11,.12)'};

var FREE_DEFAULTS = {
  plan: 'free',
  plan_fa: PLAN_LABELS.free,
  limits: {
    max_strategies: 32,
    symbols: ['EURUSD','GBPUSD','USDJPY','XAUUSD','BTCUSD','US30','USOIL'],
    timeframes: ['H1'],
    analyses_per_day: 5,
    max_alerts: 2,
    max_journal: 10,
    max_robots: 0,
    builder: false,
    backtest: false,
    telegram_alerts: false
  },
  usage: { analyses_today: 0, active_alerts: 0 },
  upgrade_url: '/pricing'
};

/* ═══════════════════════════════════════════
   CSS INJECTION
   ═══════════════════════════════════════════ */
var CSS = [
  /* Plan badges */
  '.uplan{display:inline-flex;align-items:center;gap:4px;padding:2px 10px;border-radius:6px;font-size:11px;font-weight:700;white-space:nowrap;direction:rtl;}',
  '.uplan-free{color:#94a3b8;background:rgba(148,163,184,.12);border:1px solid rgba(148,163,184,.2);}',
  '.uplan-pro{color:#06b6d4;background:rgba(6,182,212,.12);border:1px solid rgba(6,182,212,.25);}',
  '.uplan-premium{color:#a855f7;background:rgba(168,85,247,.12);border:1px solid rgba(168,85,247,.25);}',
  '.uplan-enterprise{color:#f59e0b;background:rgba(245,158,11,.12);border:1px solid rgba(245,158,11,.25);}',

  /* Plan lock overlay */
  '.plan-lock-overlay{position:absolute;inset:0;z-index:50;background:rgba(10,12,16,.82);backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);display:flex;align-items:center;justify-content:center;border-radius:inherit;}',
  '.plan-lock-content{text-align:center;padding:30px 20px;max-width:360px;}',
  '.plan-lock-content .pli{font-size:40px;margin-bottom:12px;display:block;}',
  '.plan-lock-content .plm{font-size:14px;color:#e2e5f0;font-weight:600;margin-bottom:6px;line-height:1.7;}',
  '.plan-lock-content .pls{font-size:12px;color:#7f849c;margin-bottom:16px;line-height:1.6;}',
  '.plan-lock-btn{display:inline-block;background:linear-gradient(135deg,#00d4ff,#a855f7);color:#000;font-weight:800;padding:10px 28px;border-radius:10px;font-size:13px;text-decoration:none;transition:all .2s;cursor:pointer;border:none;font-family:inherit;}',
  '.plan-lock-btn:hover{opacity:.88;transform:translateY(-1px);box-shadow:0 4px 16px rgba(0,212,255,.3);}',

  /* Progress bars */
  '.plan-progress{margin:6px 0;}',
  '.plan-progress-label{display:flex;justify-content:space-between;font-size:11px;color:#7f849c;margin-bottom:3px;}',
  '.plan-progress-bar{height:7px;background:#1a1e2a;border-radius:4px;overflow:hidden;}',
  '.plan-progress-fill{height:100%;border-radius:4px;transition:width .4s ease;}',

  /* Nav user info */
  '.wnav-user-info{display:flex;align-items:center;gap:8px;margin-right:6px;}',
  '.wnav-user-name{font-size:12px;color:#e2e5f0;font-weight:600;white-space:nowrap;}',
  '.wnav-usage-chip{font-size:10px;color:#7f849c;background:rgba(255,255,255,.04);padding:2px 8px;border-radius:5px;white-space:nowrap;}',
  '.wnav-upgrade{display:inline-flex;align-items:center;gap:4px;font-size:11px;font-weight:700;background:linear-gradient(135deg,#00d4ff,#a855f7);color:#000;padding:4px 12px;border-radius:7px;text-decoration:none;white-space:nowrap;transition:all .2s;}',
  '.wnav-upgrade:hover{opacity:.88;transform:translateY(-1px);}',

  /* Dashboard plan widget */
  '.plan-widget{background:#12151c;border:1px solid #2a2f42;border-radius:12px;padding:14px;margin-bottom:12px;}',
  '.plan-widget-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;}',
  '.plan-widget-head h4{font-size:13px;color:#06b6d4;font-weight:700;}',
  '.plan-widget-stats{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px;}',
  '.pw-stat{background:#1a1e2a;padding:6px 8px;border-radius:7px;text-align:center;}',
  '.pw-stat .pwv{font-size:14px;font-weight:800;color:#e2e5f0;}',
  '.pw-stat .pwl{font-size:9px;color:#565a6e;margin-top:1px;}',

  /* Restriction banner */
  '.plan-restrict-banner{background:rgba(245,158,11,.06);border:1px solid rgba(245,158,11,.25);border-radius:10px;padding:10px 16px;margin-bottom:14px;display:flex;align-items:center;gap:10px;font-size:12px;color:#f59e0b;}',
  '.plan-restrict-banner a{color:#06b6d4;font-weight:700;text-decoration:none;white-space:nowrap;}',
  '.plan-restrict-banner a:hover{text-decoration:underline;}',

  /* Dashboard controls plan badge */
  '.dash-plan-badge{display:inline-flex;align-items:center;gap:6px;margin-left:6px;}'
].join('\n');

var styleEl = document.createElement('style');
styleEl.id = 'plan-ui-css';
styleEl.textContent = CSS;
document.head.appendChild(styleEl);


/* ═══════════════════════════════════════════
   BOOTSTRAP
   ═══════════════════════════════════════════ */
function _bootstrap(){
  var token = null, userInfo = null, loggedIn = false;
  try {
    token = localStorage.getItem('userToken');
    var raw = localStorage.getItem('userInfo');
    if(raw) userInfo = JSON.parse(raw);
  } catch(e){}

  if(token){
    loggedIn = true;
    fetch('/api/plans/my-usage', {
      headers: { 'Authorization': 'Bearer ' + token }
    }).then(function(r){
      if(r.status === 401){
        // stale token
        localStorage.removeItem('userToken');
        localStorage.removeItem('userInfo');
        _finalize(FREE_DEFAULTS, null, false);
        return null;
      }
      if(!r.ok) throw new Error('fetch failed');
      return r.json();
    }).then(function(data){
      if(!data) return;
      _finalize(data, userInfo, true);
    }).catch(function(){
      // network error — use cached userInfo if available
      var plan = (userInfo && userInfo.plan) ? userInfo.plan : 'free';
      var fallback = _clone(FREE_DEFAULTS);
      fallback.plan = plan;
      fallback.plan_fa = PLAN_LABELS[plan] || PLAN_LABELS.free;
      _finalize(fallback, userInfo, true);
    });
  } else {
    _finalize(FREE_DEFAULTS, null, false);
  }
}

function _finalize(data, userInfo, loggedIn){
  var P = {
    plan:        data.plan || 'free',
    plan_fa:     data.plan_fa || PLAN_LABELS[data.plan] || PLAN_LABELS.free,
    limits:      data.limits || FREE_DEFAULTS.limits,
    usage:       data.usage || FREE_DEFAULTS.usage,
    upgrade_url: data.upgrade_url || '/pricing',
    loggedIn:    loggedIn,
    user:        userInfo || {}
  };
  window.WHILBER_PLAN = P;
  _updateNav(P);
  document.dispatchEvent(new CustomEvent('whilber-plan-ready', {detail: P}));
}

function _clone(obj){ return JSON.parse(JSON.stringify(obj)); }


/* ═══════════════════════════════════════════
   NAV UPDATE
   ═══════════════════════════════════════════ */
function _updateNav(P){
  if(!P.loggedIn) return;
  var name = P.user.name || P.user.full_name || P.user.email || '';
  var shortName = name.length > 14 ? name.substring(0,12) + '...' : name;
  var badge = planBadge(P.plan);
  var usageTxt = (P.usage.analyses_today||0) + '/' + (P.limits.analyses_per_day||'?');
  var upgradeHtml = P.plan === 'free' ? ' <a href="/pricing" class="wnav-upgrade">\u2B06 \u0627\u0631\u062A\u0642\u0627</a>' : '';

  // --- .wnav-links pages ---
  var wnavLinks = document.querySelector('.wnav-links');
  if(wnavLinks){
    // Hide login/register links
    var links = wnavLinks.querySelectorAll('a');
    for(var i=0; i<links.length; i++){
      var href = links[i].getAttribute('href');
      if(href === '/login' || href === '/register'){
        links[i].style.display = 'none';
      }
    }
    // Insert user info
    var info = document.createElement('span');
    info.className = 'wnav-user-info';
    info.innerHTML = '<span class="wnav-user-name">' + _esc(shortName) + '</span>' +
      badge +
      '<span class="wnav-usage-chip">' + usageTxt + ' \u062A\u062D\u0644\u06CC\u0644</span>' +
      upgradeHtml;
    wnavLinks.appendChild(info);
  }

  // --- Dashboard .header .controls ---
  var controls = document.querySelector('.header .controls');
  if(controls && !wnavLinks){
    var dbadge = document.createElement('span');
    dbadge.className = 'dash-plan-badge';
    dbadge.innerHTML = badge +
      '<span class="wnav-usage-chip">' + usageTxt + '</span>' +
      upgradeHtml;
    controls.appendChild(dbadge);
  }
  // Even if both exist (dashboard with wnav), add to controls
  if(controls && wnavLinks){
    var dbadge2 = document.createElement('span');
    dbadge2.className = 'dash-plan-badge';
    dbadge2.innerHTML = badge +
      '<span class="wnav-usage-chip">' + usageTxt + '</span>';
    controls.appendChild(dbadge2);
  }

  // --- Mobile nav ---
  var mob = document.querySelector('.wnav-mob');
  if(mob){
    var mobLinks = mob.querySelectorAll('a');
    for(var j=0; j<mobLinks.length; j++){
      var mhref = mobLinks[j].getAttribute('href');
      if(mhref === '/login' || mhref === '/register'){
        mobLinks[j].style.display = 'none';
      }
    }
    var mobInfo = document.createElement('div');
    mobInfo.style.cssText = 'padding:11px 14px;border-top:1px solid #1e2a45;margin-top:8px;';
    mobInfo.innerHTML = '<div style="font-size:13px;font-weight:700;color:#e8ecf4;margin-bottom:6px;">' + _esc(name) + '</div>' +
      badge + ' <span style="font-size:11px;color:#8892a8;margin-right:6px;">' + usageTxt + ' \u062A\u062D\u0644\u06CC\u0644</span>' +
      (P.plan === 'free' ? '<div style="margin-top:8px;"><a href="/pricing" class="wnav-upgrade">\u2B06 \u0627\u0631\u062A\u0642\u0627 \u067E\u0644\u0646</a></div>' : '');
    mob.appendChild(mobInfo);
  }
}

function _esc(s){
  if(!s) return '';
  var d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}


/* ═══════════════════════════════════════════
   PUBLIC UTILITIES
   ═══════════════════════════════════════════ */

/** Plan badge HTML */
function planBadge(plan){
  var p = plan || 'free';
  var label = PLAN_LABELS[p] || p;
  return '<span class="uplan uplan-' + p + '">' + label + '</span>';
}

/** Progress bar HTML */
function planProgress(used, limit, label){
  var pct = limit > 0 ? Math.min(100, Math.round((used/limit)*100)) : 0;
  var color = pct < 60 ? '#22c55e' : pct < 85 ? '#f59e0b' : '#ef4444';
  var displayLimit = limit >= 9999 ? '\u221E' : limit;
  return '<div class="plan-progress">' +
    '<div class="plan-progress-label"><span>' + (label||'') + '</span><span>' + used + ' / ' + displayLimit + '</span></div>' +
    '<div class="plan-progress-bar"><div class="plan-progress-fill" style="width:' + pct + '%;background:' + color + ';"></div></div>' +
    '</div>';
}

/** Glass lock overlay on element */
function planLock(element, message, subtitle){
  if(!element) return;
  var st = getComputedStyle(element);
  if(st.position === 'static') element.style.position = 'relative';
  var ov = document.createElement('div');
  ov.className = 'plan-lock-overlay';
  ov.innerHTML = '<div class="plan-lock-content">' +
    '<span class="pli">\uD83D\uDD12</span>' +
    '<div class="plm">' + (message || '\u0645\u062D\u062F\u0648\u062F\u06CC\u062A \u067E\u0644\u0646') + '</div>' +
    (subtitle ? '<div class="pls">' + subtitle + '</div>' : '') +
    '<a href="/pricing" class="plan-lock-btn">\u0645\u0634\u0627\u0647\u062F\u0647 \u067E\u0644\u0646\u200C\u0647\u0627</a>' +
    '</div>';
  element.appendChild(ov);
  return ov;
}

/** Check if feature is available */
function planCheck(feature){
  var P = window.WHILBER_PLAN;
  if(!P || !P.limits) return false;
  var L = P.limits;
  switch(feature){
    case 'builder':  return !!L.builder;
    case 'backtest': return !!L.backtest;
    case 'telegram': return !!L.telegram_alerts;
    default:         return true;
  }
}

/** Standard auth headers */
function getAuthHeaders(){
  var h = {};
  try {
    var t = localStorage.getItem('userToken');
    if(t) h['Authorization'] = 'Bearer ' + t;
  } catch(e){}
  return h;
}

// Expose utilities on window
window.planBadge    = planBadge;
window.planProgress = planProgress;
window.planLock     = planLock;
window.planCheck    = planCheck;
window.getAuthHeaders = window.getAuthHeaders || getAuthHeaders;
window.PLAN_LABELS  = PLAN_LABELS;
window.PLAN_COLORS  = PLAN_COLORS;


/* ═══════════════════════════════════════════
   INIT
   ═══════════════════════════════════════════ */
if(document.readyState === 'loading'){
  document.addEventListener('DOMContentLoaded', _bootstrap);
} else {
  _bootstrap();
}

})();
