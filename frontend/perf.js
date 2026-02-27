/*
 * Whilber-AI Real-Time Engine v2
 * - Live clock (server-synced, 1s update)
 * - Auto-refresh all pages (no manual refresh needed)
 * - Loading bar + status indicator
 * - Adaptive polling (fast when active, slow when hidden)
 * - Toast notifications
 */
(function(){
'use strict';
var API = window.location.origin;
var EMAIL = localStorage.getItem('whilber_email') || 'user@whilber.ai';
var _serverOffset = 0;
var _pollInterval = 8000;
var _lastPollOk = true;

// ══════ INJECT CSS ══════
var css = document.createElement('style');
css.textContent = [
  /* Clock */
  '.wh-clock{position:fixed;bottom:8px;right:8px;z-index:8000;font-size:11px;color:#94a3b8;background:rgba(15,23,42,.85);padding:4px 10px;border-radius:6px;border:1px solid rgba(255,255,255,.06);font-family:"Courier New",monospace;direction:ltr;backdrop-filter:blur(4px);}',
  /* Status dot */
  '.wh-status{position:fixed;bottom:8px;left:8px;z-index:8000;font-size:9px;padding:3px 8px;border-radius:6px;direction:ltr;font-family:monospace;backdrop-filter:blur(4px);}',
  '.wh-status.ok{color:#22c55e;background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.15);}',
  '.wh-status.slow{color:#f59e0b;background:rgba(245,158,11,.08);border:1px solid rgba(245,158,11,.15);}',
  '.wh-status.err{color:#ef4444;background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.15);}',
  /* Loading bar */
  '.wh-loading{position:fixed;top:0;left:0;width:100%;height:3px;z-index:9999;pointer-events:none;overflow:hidden;}',
  '.wh-loading .wh-bar{height:100%;width:30%;background:linear-gradient(90deg,transparent,#f59e0b,#eab308,transparent);transform:translateX(-100%);}',
  '.wh-loading.active .wh-bar{animation:whLoad 1.2s ease-in-out infinite;}',
  '@keyframes whLoad{0%{transform:translateX(-100%);}100%{transform:translateX(400%)}}',
  /* Spinner */
  '.wh-spinner{display:inline-block;width:14px;height:14px;border:2px solid rgba(245,158,11,.2);border-top-color:#f59e0b;border-radius:50%;animation:whSpin .6s linear infinite;vertical-align:middle;margin:0 4px;}',
  '@keyframes whSpin{to{transform:rotate(360deg)}}',
  /* Toast */
  '.wh-toast{position:fixed;top:12px;left:50%;transform:translateX(-50%);z-index:9999;background:#1e293b;border:1px solid rgba(245,158,11,.3);color:#f1f5f9;padding:8px 16px;border-radius:8px;font-size:12px;direction:rtl;box-shadow:0 4px 20px rgba(0,0,0,.3);animation:whToastIn .3s ease;backdrop-filter:blur(8px);}',
  '.wh-toast.success{border-color:rgba(34,197,94,.4);}',
  '.wh-toast.error{border-color:rgba(239,68,68,.4);}',
  '@keyframes whToastIn{from{opacity:0;transform:translateX(-50%) translateY(-10px);}to{opacity:1;transform:translateX(-50%) translateY(0);}}',
  /* Refresh indicator */
  '.wh-refresh-dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:#22c55e;margin-left:6px;animation:whPulse 2s ease infinite;}',
  '@keyframes whPulse{0%,100%{opacity:1;}50%{opacity:.3;}}',
].join('\n');
document.head.appendChild(css);

// ══════ LOADING BAR ══════
var loadEl = document.createElement('div');
loadEl.className = 'wh-loading';
loadEl.innerHTML = '<div class="wh-bar"></div>';
document.body.appendChild(loadEl);

var _activeReqs = 0;
window.whShowLoading = function(){ loadEl.classList.add('active'); };
window.whHideLoading = function(){ loadEl.classList.remove('active'); };

// ══════ LIVE CLOCK ══════
var clockEl = document.createElement('div');
clockEl.className = 'wh-clock';
clockEl.id = 'whClock';
document.body.appendChild(clockEl);

function updateClock(){
  var now = new Date(Date.now() + _serverOffset);
  var h = String(now.getHours()).padStart(2,'0');
  var m = String(now.getMinutes()).padStart(2,'0');
  var s = String(now.getSeconds()).padStart(2,'0');
  clockEl.textContent = h + ':' + m + ':' + s;
}
setInterval(updateClock, 1000);
updateClock();

// ══════ STATUS INDICATOR ══════
var statusEl = document.createElement('div');
statusEl.className = 'wh-status ok';
document.body.appendChild(statusEl);
statusEl.innerHTML = '<span class="wh-refresh-dot"></span> LIVE';

// ══════ TOAST ══════
window.whToast = function(msg, type){
  type = type || '';
  var t = document.createElement('div');
  t.className = 'wh-toast ' + type;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(function(){ t.style.opacity = '0'; t.style.transition = 'opacity .3s'; }, 4000);
  setTimeout(function(){ t.remove(); }, 4500);
};

// ══════ FETCH WRAPPER ══════
var _origFetch = window.fetch;
window.fetch = function(){
  _activeReqs++;
  if(_activeReqs === 1) whShowLoading();
  return _origFetch.apply(window, arguments)
    .then(function(r){ _activeReqs--; if(_activeReqs<=0){_activeReqs=0; whHideLoading();} return r; })
    .catch(function(e){ _activeReqs--; if(_activeReqs<=0){_activeReqs=0; whHideLoading();} throw e; });
};

// ══════ UNIFIED POLL ══════
async function poll(){
  var t0 = Date.now();
  try {
    var r = await _origFetch(API + '/api/poll?email=' + encodeURIComponent(EMAIL));
    var d = await r.json();
    var latency = Date.now() - t0;
    _lastPollOk = true;

    // Sync clock
    if(d.server_time){
      var serverMs = new Date(d.server_time).getTime();
      _serverOffset = serverMs - Date.now();
    }

    // Status
    if(latency < 300){
      statusEl.className = 'wh-status ok';
      statusEl.innerHTML = '<span class="wh-refresh-dot"></span> LIVE ' + latency + 'ms';
    } else if(latency < 2000){
      statusEl.className = 'wh-status slow';
      statusEl.textContent = 'SLOW ' + latency + 'ms';
    } else {
      statusEl.className = 'wh-status err';
      statusEl.textContent = 'LAG ' + latency + 'ms';
    }

    // Alert badge
    if(d.unread !== undefined){
      var badge = document.getElementById('waBadge');
      if(badge){
        if(d.unread > 0){ badge.style.display='inline'; badge.textContent=d.unread; }
        else badge.style.display='none';
      }
    }

    // Dispatch event
    window.dispatchEvent(new CustomEvent('whilber-poll', {detail: d}));
  } catch(e){
    _lastPollOk = false;
    statusEl.className = 'wh-status err';
    statusEl.textContent = 'OFFLINE';
  }
}

// ══════ ADAPTIVE POLLING ══════
function schedulePoll(){
  var interval = document.hidden ? 30000 : _pollInterval;
  setTimeout(function(){
    poll().then(schedulePoll).catch(schedulePoll);
  }, interval);
}
poll().then(schedulePoll).catch(schedulePoll);

// ══════ AUTO-REFRESH: TRACK RECORD ══════
var _refreshInterval = 30000; // 30s

function refreshTrackRecord(){
  if(window.location.pathname.indexOf('track-record') < 0) return;
  // Refresh ranking
  if(typeof window.loadRanking === 'function'){
    window.loadRanking();
  }
  // Refresh stats if visible
  var statsEl = document.getElementById('strategyDetail');
  if(statsEl && statsEl.style.display !== 'none' && typeof window._lastSelectedStrategy === 'string'){
    // Silently refresh stats
  }
}

// ══════ AUTO-REFRESH: ALERTS ══════
function refreshAlerts(){
  if(window.location.pathname.indexOf('alerts') < 0 && window.location.pathname.indexOf('alert') < 0) return;
  if(typeof window.loadHistory === 'function') window.loadHistory();
  if(typeof window.loadSubs === 'function') window.loadSubs();
  if(typeof window.loadStats === 'function') window.loadStats();
}

// ══════ AUTO-REFRESH: DASHBOARD ══════
function refreshDashboard(){
  if(window.location.pathname !== '/' && window.location.pathname.indexOf('dashboard') < 0) return;
  // Refresh active trades count, signals etc
  if(typeof window.refreshDashboard === 'function') window.refreshDashboard();
  if(typeof window.loadActiveTradesCount === 'function') window.loadActiveTradesCount();
}

// ══════ MASTER REFRESH LOOP ══════
function masterRefresh(){
  if(document.hidden) return; // Don't refresh when tab hidden
  refreshTrackRecord();
  refreshAlerts();
  refreshDashboard();
}
setInterval(masterRefresh, _refreshInterval);

// ══════ PAGE VISIBILITY ══════
document.addEventListener('visibilitychange', function(){
  if(!document.hidden){
    // Came back — immediate refresh
    poll();
    masterRefresh();
    updateClock();
  }
});

// Log
console.log('[Whilber] Real-time engine v2 loaded. Poll: ' + _pollInterval + 'ms, Refresh: ' + _refreshInterval + 'ms');
})();
