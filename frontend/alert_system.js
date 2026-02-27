/*
 * Whilber-AI Alert System v4
 * 3 notification channels:
 *   1. Bell badge (count on 🔔 icon)
 *   2. Desktop push notification (browser Notification API)
 *   3. In-page popup toast
 * + Email (handled server-side)
 * 
 * Full lifecycle: entry → BE → partial → trailing → near TP/SL → closed
 */
(function(){
var API = window.location.origin;
var EMAIL = localStorage.getItem('whilber_email') || 'user@whilber.ai';
var SYMS = ['XAUUSD','EURUSD','GBPUSD','USDJPY','AUDUSD','USDCAD','NZDUSD','USDCHF','BTCUSD','XAGUSD','US30','NAS100'];
var EVENTS = [
  {id:'signal',icon:'\u{1F4E1}',name:'\u0633\u06CC\u06AF\u0646\u0627\u0644 \u062C\u062F\u06CC\u062F',desc:'\u0648\u0642\u062A\u06CC \u0633\u062A\u0627\u067E \u0634\u0646\u0627\u0633\u0627\u06CC\u06CC \u0634\u062F'},
  {id:'entry',icon:'\u{1F7E2}',name:'\u0648\u0631\u0648\u062F \u0628\u0647 \u0645\u0639\u0627\u0645\u0644\u0647',desc:'\u0642\u06CC\u0645\u062A \u0628\u0647 \u0646\u0642\u0637\u0647 \u0648\u0631\u0648\u062F \u0631\u0633\u06CC\u062F'},
  {id:'be_move',icon:'\u{1F49B}',name:'SL \u0628\u0647 Break Even',desc:'SL \u0628\u0647 \u0646\u0642\u0637\u0647 \u0648\u0631\u0648\u062F \u0631\u0641\u062A'},
  {id:'partial',icon:'\u{1F4B0}',name:'\u0633\u06CC\u0648 \u0633\u0648\u062F',desc:'\u0628\u062E\u0634\u06CC \u0627\u0632 \u0633\u0648\u062F \u0630\u062E\u06CC\u0631\u0647 \u0634\u062F'},
  {id:'trailing',icon:'\u{1F504}',name:'Trailing \u0641\u0639\u0627\u0644',desc:'SL \u062F\u0646\u0628\u0627\u0644 \u0642\u06CC\u0645\u062A'},
  {id:'near_tp',icon:'\u{1F3AF}',name:'\u0646\u0632\u062F\u06CC\u06A9 TP',desc:'\u0646\u0632\u062F\u06CC\u06A9 \u062D\u062F \u0633\u0648\u062F'},
  {id:'near_sl',icon:'\u{1F534}',name:'\u0646\u0632\u062F\u06CC\u06A9 SL',desc:'\u0647\u0634\u062F\u0627\u0631! \u0646\u0632\u062F\u06CC\u06A9 \u062D\u062F \u0636\u0631\u0631'},
  {id:'closed_tp',icon:'\u2705',name:'\u0628\u0633\u062A\u0647 \u0634\u062F \u2014 TP',desc:'\u0645\u0639\u0627\u0645\u0644\u0647 \u0628\u0627 \u0633\u0648\u062F \u0628\u0633\u062A\u0647 \u0634\u062F'},
  {id:'closed_sl',icon:'\u274C',name:'\u0628\u0633\u062A\u0647 \u0634\u062F \u2014 SL',desc:'\u0645\u0639\u0627\u0645\u0644\u0647 \u0628\u0627 \u0636\u0631\u0631 \u0628\u0633\u062A\u0647 \u0634\u062F'},
];
var _subSid='', _subName='', _lastCount=0, _desktopEnabled=false;

// ══════ CSS ══════
var style = document.createElement('style');
style.textContent = '\
.wa-bell{position:fixed;top:8px;left:8px;z-index:9000;cursor:pointer;font-size:20px;background:#1e293b;border:1px solid rgba(245,158,11,.3);border-radius:50%;width:38px;height:38px;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 12px rgba(0,0,0,.4);transition:.2s;}\
.wa-bell:hover{border-color:#f59e0b;transform:scale(1.1);}\
.wa-bell .wa-badge{position:absolute;top:-3px;right:-5px;background:#ef4444;color:#fff;font-size:8px;font-weight:800;padding:1px 4px;border-radius:8px;min-width:14px;text-align:center;display:none;}\
.wa-panel{position:fixed;top:52px;left:8px;width:360px;max-height:65vh;background:#1e293b;border:1px solid rgba(245,158,11,.2);border-radius:12px;z-index:9001;overflow:hidden;display:none;box-shadow:0 8px 30px rgba(0,0,0,.5);}\
.wa-panel.show{display:block;}\
.wa-phead{padding:8px 12px;border-bottom:1px solid rgba(255,255,255,.05);display:flex;align-items:center;justify-content:space-between;}\
.wa-phead h4{font-size:12px;color:#f59e0b;font-weight:700;margin:0;}\
.wa-plist{max-height:55vh;overflow-y:auto;padding:4px 0;}\
.wa-ni{padding:8px 12px;border-bottom:1px solid rgba(255,255,255,.02);display:flex;gap:8px;}\
.wa-ni.unread{background:rgba(245,158,11,.04);border-right:3px solid #f59e0b;}\
.wa-btn{display:inline-flex;align-items:center;gap:2px;padding:2px 7px;border-radius:4px;background:rgba(245,158,11,.08);border:1px solid rgba(245,158,11,.2);color:#f59e0b;font-size:10px;font-weight:700;cursor:pointer;transition:.15s;margin-left:4px;}\
.wa-btn:hover{background:rgba(245,158,11,.18);border-color:#f59e0b;}\
.wa-overlay{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,.7);z-index:9999;align-items:center;justify-content:center;}\
.wa-overlay.show{display:flex;}\
.wa-modal{background:#0f172a;border:1px solid rgba(245,158,11,.2);border-radius:14px;width:92%;max-width:460px;max-height:80vh;overflow-y:auto;padding:16px;}\
.wa-modal h3{color:#f59e0b;font-size:14px;margin:0 0 10px 0;}\
.wa-evt{display:flex;align-items:center;justify-content:space-between;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.03);}\
.wa-evt label{font-size:11px;display:flex;align-items:center;gap:6px;color:#e2e8f0;}\
.wa-evt .desc{font-size:8px;color:#64748b;}\
.wa-tgl{position:relative;width:34px;height:18px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);border-radius:9px;cursor:pointer;transition:.2s;flex-shrink:0;}\
.wa-tgl.on{background:rgba(34,197,94,.15);border-color:#22c55e;}\
.wa-tgl::after{content:"";position:absolute;top:2px;right:2px;width:12px;height:12px;border-radius:50%;background:#64748b;transition:.2s;}\
.wa-tgl.on::after{right:auto;left:2px;background:#22c55e;}\
.wa-syms{display:flex;flex-wrap:wrap;gap:3px;margin:4px 0;}\
.wa-sym{padding:2px 7px;border-radius:4px;border:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.03);color:#94a3b8;font-size:9px;cursor:pointer;transition:.15s;}\
.wa-sym.sel{background:rgba(6,182,212,.1);border-color:#06b6d4;color:#06b6d4;}\
.wa-save{width:100%;padding:9px;margin-top:10px;background:linear-gradient(135deg,#f59e0b,#d97706);border:none;border-radius:8px;color:#000;font-weight:800;font-size:12px;cursor:pointer;}\
.wa-save:hover{filter:brightness(1.1);}\
.wa-ghost{background:transparent;border:1px solid rgba(255,255,255,.08);color:#94a3b8;padding:2px 6px;border-radius:4px;font-size:9px;cursor:pointer;}\
.wa-toast-box{position:fixed;top:10px;left:50px;z-index:9500;display:flex;flex-direction:column;gap:6px;max-width:380px;pointer-events:none;}\
.wa-toast{background:#1e293b;border:1px solid rgba(245,158,11,.25);border-radius:10px;padding:10px 14px;display:flex;gap:8px;align-items:flex-start;animation:waIn .3s ease;pointer-events:auto;box-shadow:0 4px 20px rgba(0,0,0,.4);}\
.wa-toast.out{animation:waOut .3s ease forwards;}\
@keyframes waIn{from{opacity:0;transform:translateY(-20px);}to{opacity:1;transform:translateY(0);}}\
@keyframes waOut{to{opacity:0;transform:translateY(-20px);}}\
';
document.head.appendChild(style);

// ══════ DESKTOP NOTIFICATION PERMISSION ══════
function requestDesktopPermission() {
  if (!('Notification' in window)) return;
  if (Notification.permission === 'granted') {
    _desktopEnabled = true;
  } else if (Notification.permission !== 'denied') {
    Notification.requestPermission().then(function(p) {
      _desktopEnabled = (p === 'granted');
    });
  }
}

function showDesktopNotif(notif) {
  if (!_desktopEnabled || !('Notification' in window) || Notification.permission !== 'granted') return;
  try {
    var title = (notif.icon||'') + ' ' + (notif.title_fa||'Whilber-AI');
    var body = (notif.strategy_name||'') + ' | ' + (notif.symbol||'') + ' ' + (notif.direction||'');
    if (notif.action_fa) body += '\n' + notif.action_fa;
    if (notif.pnl) body += '\nPnL: ' + (notif.pnl>=0?'+':'') + notif.pnl + '$';
    var n = new Notification(title, {
      body: body,
      icon: '/favicon.ico',
      tag: 'whilber-' + (notif.id||Date.now()),
      requireInteraction: false,
      silent: false,
    });
    n.onclick = function() { window.focus(); n.close(); };
    setTimeout(function(){ n.close(); }, 10000);
  } catch(e) {}
}

// ══════ TOAST POPUP ══════
var toastBox = document.createElement('div');
toastBox.className = 'wa-toast-box';
document.body.appendChild(toastBox);

function showToast(notif) {
  var div = document.createElement('div');
  div.className = 'wa-toast';
  var pnlHtml = '';
  if (notif.pnl) {
    var pc = notif.pnl >= 0 ? '#22c55e' : '#ef4444';
    pnlHtml = '<div style="font-size:9px;font-weight:800;color:'+pc+';">PnL: '+(notif.pnl>=0?'+':'')+notif.pnl+'$</div>';
  }
  div.innerHTML = '<span style="font-size:18px;">'+(notif.icon||'\u{1F514}')+'</span>'
    +'<div style="flex:1;min-width:0;">'
    +'<div style="font-size:11px;font-weight:700;color:#f59e0b;">'+(notif.title_fa||'')+'</div>'
    +'<div style="font-size:9px;color:#94a3b8;">'+(notif.strategy_name||'')+' | '+(notif.symbol||'')+' '+(notif.direction||'')+'</div>'
    +(notif.action_fa?'<div style="font-size:8px;color:#64748b;">'+notif.action_fa+'</div>':'')
    +pnlHtml
    +'</div>'
    +'<span onclick="this.parentElement.classList.add(\'out\');setTimeout(function(){this.parentElement.remove()}.bind(this),300);" style="cursor:pointer;color:#64748b;font-size:12px;pointer-events:auto;">\u2715</span>';
  toastBox.appendChild(div);
  setTimeout(function(){ if(div.parentElement){div.classList.add('out');setTimeout(function(){if(div.parentElement)div.remove();},300);} }, 8000);
}

// ══════ BELL ══════
var bell = document.createElement('div');
bell.className = 'wa-bell';
bell.innerHTML = '\u{1F514}<span class="wa-badge" id="waBadge">0</span>';
bell.onclick = function(){ var p=document.getElementById('waPanel'); p.classList.toggle('show'); if(p.classList.contains('show'))refreshList(); };
document.body.appendChild(bell);

// ══════ PANEL ══════
var panel = document.createElement('div');
panel.className = 'wa-panel';
panel.id = 'waPanel';
panel.innerHTML = '<div class="wa-phead"><h4>\u{1F514} \u0647\u0634\u062F\u0627\u0631\u0647\u0627</h4><div><button class="wa-ghost" onclick="waMarkAll()">\u062E\u0648\u0627\u0646\u062F\u0647</button> <button class="wa-ghost" onclick="waClear()">\u067E\u0627\u06A9</button> <span onclick="document.getElementById(\'waPanel\').classList.remove(\'show\')" style="cursor:pointer;color:#64748b;margin-left:4px;">\u2715</span></div></div><div class="wa-plist" id="waPlist"><div style="text-align:center;color:#64748b;padding:20px;font-size:11px;">\u0628\u062F\u0648\u0646 \u0647\u0634\u062F\u0627\u0631</div></div>';
document.body.appendChild(panel);

// ══════ MODAL ══════
var overlay = document.createElement('div');
overlay.className = 'wa-overlay';
overlay.id = 'waOverlay';
overlay.onclick = function(e){ if(e.target===overlay) overlay.classList.remove('show'); };
overlay.innerHTML = '<div class="wa-modal" id="waModal"></div>';
document.body.appendChild(overlay);

// ══════ OPEN SUBSCRIBE ══════
window.waOpenSub = function(sid, name) {
  _subSid = sid || '*';
  _subName = name || '\u0647\u0645\u0647';
  var m = document.getElementById('waModal');
  var h = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">';
  h += '<h3>\u{1F514} \u062A\u0646\u0638\u06CC\u0645 \u0647\u0634\u062F\u0627\u0631</h3>';
  h += '<span onclick="document.getElementById(\'waOverlay\').classList.remove(\'show\')" style="cursor:pointer;color:#64748b;border:1px solid rgba(255,255,255,.08);padding:3px 8px;border-radius:6px;">\u2715</span></div>';
  h += '<div style="padding:6px 8px;background:rgba(6,182,212,.06);border:1px solid rgba(6,182,212,.12);border-radius:6px;margin-bottom:8px;font-size:12px;color:#06b6d4;font-weight:700;">' + _subName + '</div>';

  h += '<div style="font-size:10px;color:#94a3b8;margin-bottom:3px;">\u{1F4CD} \u0646\u0645\u0627\u062F\u0647\u0627:</div><div class="wa-syms" id="waSyms">';
  h += '<div class="wa-sym sel" data-s="*" onclick="waTogSym(this)">\u0647\u0645\u0647</div>';
  SYMS.forEach(function(s){ h += '<div class="wa-sym" data-s="'+s+'" onclick="waTogSym(this)">'+s+'</div>'; });
  h += '</div>';

  h += '<div style="font-size:10px;color:#94a3b8;margin:8px 0 3px;">\u26A1 \u0645\u0631\u0627\u062D\u0644 \u0647\u0634\u062F\u0627\u0631 (\u0648\u0631\u0648\u062F \u062A\u0627 \u062E\u0631\u0648\u062C):</div>';
  EVENTS.forEach(function(e){
    h += '<div class="wa-evt"><label><span style="font-size:14px;">'+e.icon+'</span> '+e.name+'<br><span class="desc">'+e.desc+'</span></label>';
    h += '<div class="wa-tgl on" data-e="'+e.id+'" onclick="this.classList.toggle(\'on\')"></div></div>';
  });

  // 3 notification channels
  h += '<div style="font-size:10px;color:#f59e0b;margin:10px 0 4px;font-weight:700;">\u{1F4E3} \u06A9\u0627\u0646\u0627\u0644 \u0647\u0634\u062F\u0627\u0631:</div>';
  h += '<div class="wa-evt"><label>\u{1F514} \u0646\u0645\u0627\u062F \u0632\u0646\u06AF\u0648\u0644\u0647 (\u0647\u0645\u06CC\u0634\u0647 \u0641\u0639\u0627\u0644)</label><div class="wa-tgl on" style="opacity:.5;pointer-events:none;"></div></div>';
  h += '<div class="wa-evt"><label>\u{1F4BB} \u067E\u0627\u067E\u200C\u0627\u067E \u062F\u0633\u06A9\u062A\u0627\u067E<br><span class="desc">\u0646\u0648\u062A\u06CC\u0641\u06CC\u06A9\u06CC\u0634\u0646 \u0645\u0631\u0648\u0631\u06AF\u0631 + \u0635\u0641\u062D\u0647</span></label><div class="wa-tgl on" id="waDesktopT" onclick="this.classList.toggle(\'on\')"></div></div>';
  h += '<div class="wa-evt"><label>\u{1F4E7} \u0627\u06CC\u0645\u06CC\u0644<br><span class="desc">\u0627\u0631\u0633\u0627\u0644 \u0628\u0647 \u0627\u06CC\u0645\u06CC\u0644 \u062B\u0628\u062A\u200C\u0634\u062F\u0647</span></label><div class="wa-tgl" id="waEmailT" onclick="this.classList.toggle(\'on\')"></div></div>';

  h += '<div style="margin-top:6px;display:flex;align-items:center;gap:4px;"><label style="font-size:10px;color:#94a3b8;">\u062D\u062F\u0627\u0642\u0644 \u0627\u0639\u062A\u0645\u0627\u062F:</label>';
  h += '<input type="number" id="waMinConf" value="40" min="0" max="100" style="width:45px;padding:2px 4px;border-radius:4px;border:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.03);color:#e2e8f0;font-size:10px;">';
  h += '<span style="font-size:9px;color:#64748b;">%</span></div>';

  h += '<button class="wa-save" onclick="waSaveSub()">\u2705 \u0641\u0639\u0627\u0644\u200C\u0633\u0627\u0632\u06CC \u0647\u0634\u062F\u0627\u0631</button>';
  h += '<div id="waResult" style="margin-top:4px;font-size:11px;text-align:center;"></div>';
  h += '<div style="margin-top:8px;border-top:1px solid rgba(255,255,255,.03);padding-top:6px;"><div style="font-size:9px;color:#64748b;margin-bottom:4px;">\u{1F4CB} \u0627\u0634\u062A\u0631\u0627\u06A9\u200C\u0647\u0627:</div><div id="waSubList"></div></div>';

  m.innerHTML = h;
  loadSubs();
  document.getElementById('waOverlay').classList.add('show');

  // Request desktop permission when opening modal
  requestDesktopPermission();
};

window.waTogSym = function(el) {
  if (el.dataset.s==='*') {document.querySelectorAll('#waSyms .wa-sym').forEach(function(t){t.classList.remove('sel');});el.classList.add('sel');}
  else {document.querySelector('#waSyms [data-s="*"]').classList.remove('sel');el.classList.toggle('sel');}
};

window.waSaveSub = async function() {
  // Show loading state
  var saveBtn = document.querySelector('.wa-save');
  if (saveBtn) {
    saveBtn.disabled = true;
    saveBtn._origText = saveBtn.textContent;
    saveBtn.innerHTML = '<span class="wh-spinner"></span> \u062F\u0631 \u062D\u0627\u0644 \u067E\u0631\u062F\u0627\u0632\u0634...';
    saveBtn.style.opacity = '0.7';
  }
  document.getElementById('waResult').innerHTML = '<span style="color:#94a3b8;">\u26F3 \u0644\u0637\u0641\u0627\u064B \u0635\u0628\u0631 \u06A9\u0646\u06CC\u062F...</span>';

  // Show loading state
  var saveBtn = document.querySelector('.wa-save');
  if (saveBtn) {
    saveBtn.disabled = true;
    saveBtn._origText = saveBtn.textContent;
    saveBtn.innerHTML = '<span class="wh-spinner"></span> \u062F\u0631 \u062D\u0627\u0644 \u067E\u0631\u062F\u0627\u0632\u0634...';
    saveBtn.style.opacity = '0.7';
  }
  document.getElementById('waResult').innerHTML = '<span style="color:#94a3b8;">\u26F3 \u0644\u0637\u0641\u0627\u064B \u0635\u0628\u0631 \u06A9\u0646\u06CC\u062F...</span>';

  var evts = {};
  document.querySelectorAll('.wa-tgl[data-e]').forEach(function(t){evts[t.dataset.e]=t.classList.contains('on');});
  var syms = [];
  document.querySelectorAll('#waSyms .wa-sym.sel').forEach(function(t){syms.push(t.dataset.s);});
  if (!syms.length) syms=['*'];
  var cfg = {
    strategy_id:_subSid, strategy_name:_subName, symbols:syms, alert_on:evts,
    notify_email: document.getElementById('waEmailT').classList.contains('on'),
    notify_app: true,  // always on (bell)
    notify_desktop: document.getElementById('waDesktopT').classList.contains('on'),
    min_confidence: parseInt(document.getElementById('waMinConf').value)||40
  };
  try {
    var r = await fetch(API+'/api/alert/subscribe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:EMAIL,config:cfg})});
    var d = await r.json();
    document.getElementById('waResult').innerHTML = d.success
      ? '<span style="color:#22c55e;">\u2705 \u0647\u0634\u062F\u0627\u0631 \u0641\u0639\u0627\u0644 \u0634\u062F!</span>'
      : '<span style="color:#ef4444;">\u062E\u0637\u0627</span>';
    if (d.success) {
      if (saveBtn) { saveBtn.disabled = false; saveBtn.innerHTML = saveBtn._origText || '\u2705 \u0641\u0639\u0627\u0644\u200C\u0633\u0627\u0632\u06CC \u0647\u0634\u062F\u0627\u0631'; saveBtn.style.opacity = '1'; }
      loadSubs();
      if (document.getElementById('waDesktopT').classList.contains('on')) requestDesktopPermission();
    }
  } catch(e) {document.getElementById('waResult').innerHTML='<span style="color:#ef4444;">\u062E\u0637\u0627</span>';}
};

async function loadSubs() {
  try {
    var r = await fetch(API+'/api/alert/subscriptions?email='+encodeURIComponent(EMAIL));
    var d = await r.json();
    var box = document.getElementById('waSubList');
    if (!box) return;
    var subs = d.subscriptions||[];
    if (!subs.length) {box.innerHTML='<div style="color:#64748b;font-size:9px;">\u0647\u0646\u0648\u0632 \u0627\u0634\u062A\u0631\u0627\u06A9\u06CC \u0646\u062F\u0627\u0631\u06CC\u062F</div>';return;}
    var h = '';
    subs.forEach(function(s) {
      var channels = [];
      if (s.notify_app) channels.push('\u{1F514}');
      if (s.notify_desktop) channels.push('\u{1F4BB}');
      if (s.notify_email) channels.push('\u{1F4E7}');
      h += '<div style="display:flex;align-items:center;justify-content:space-between;padding:3px 0;border-bottom:1px solid rgba(255,255,255,.02);font-size:10px;">';
      h += '<div><b style="color:#06b6d4;">'+(s.strategy_name||'\u0647\u0645\u0647')+'</b> | '+(s.symbols||[]).join(',')+' | '+channels.join('')+' | '+(s.alert_count||0)+'x</div>';
      h += '<button onclick="waRemoveSub(\''+s.id+'\')" style="background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.12);color:#ef4444;padding:1px 5px;border-radius:3px;font-size:8px;cursor:pointer;">\u062D\u0630\u0641</button></div>';
    });
    box.innerHTML = h;
  } catch(e) {}
}

window.waRemoveSub = async function(id) {
  try {await fetch(API+'/api/alert/unsubscribe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:EMAIL,sub_id:id})});loadSubs();} catch(e) {}
};
window.alertCloseModal = function() {document.getElementById('waOverlay').classList.remove('show');};

// ══════ POLL + DISPATCH ══════
async function refreshCount() {
  try {
    var r = await fetch(API+'/api/alert/unread-count?email='+encodeURIComponent(EMAIL));
    var d = await r.json();
    var cnt = d.count||0;
    var b = document.getElementById('waBadge');
    if (cnt>0) {b.style.display='inline';b.textContent=cnt;} else b.style.display='none';

    // New notifications arrived → show toast + desktop
    if (cnt > _lastCount && _lastCount >= 0) {
      var diff = cnt - _lastCount;
      if (diff > 10) diff = 10; // max 10 at once
      var r2 = await fetch(API+'/api/alert/notifications?email='+encodeURIComponent(EMAIL)+'&limit='+diff+'&unread=true');
      var d2 = await r2.json();
      (d2.notifications||[]).forEach(function(n) {
        showToast(n);        // In-page popup
        showDesktopNotif(n); // Browser desktop notification
      });
    }
    _lastCount = cnt;
  } catch(e) {}
}

async function refreshList() {
  try {
    var r = await fetch(API+'/api/alert/notifications?email='+encodeURIComponent(EMAIL)+'&limit=50');
    var d = await r.json();
    var list = document.getElementById('waPlist');
    var ns = d.notifications||[];
    if (!ns.length) {list.innerHTML='<div style="text-align:center;color:#64748b;padding:20px;font-size:11px;">\u0628\u062F\u0648\u0646 \u0647\u0634\u062F\u0627\u0631</div>';return;}
    var h = '';
    ns.forEach(function(n) {
      h += '<div class="wa-ni '+(n.read?'':'unread')+'" onclick="waMarkOne(\''+n.id+'\')">';
      h += '<span style="font-size:16px;">'+(n.icon||'\u{1F514}')+'</span>';
      h += '<div style="flex:1;min-width:0;"><div style="font-size:11px;font-weight:700;">'+(n.title_fa||'')+'</div>';
      h += '<div style="font-size:9px;color:#06b6d4;">'+(n.strategy_name||'')+' | '+(n.symbol||'')+' '+(n.direction||'')+'</div>';
      if (n.action_fa) h += '<div style="font-size:9px;color:#64748b;">'+n.action_fa+'</div>';
      if (n.pnl) h += '<div style="font-size:9px;font-weight:700;color:'+(n.pnl>=0?'#22c55e':'#ef4444')+';">PnL: '+(n.pnl>=0?'+':'')+n.pnl+'$</div>';
      h += '<div style="font-size:8px;color:#475569;">'+(n.time||'').substring(11,19)+'</div>';
      h += '</div></div>';
    });
    list.innerHTML = h;
  } catch(e) {}
}

window.waMarkOne = async function(id) {
  try {await fetch(API+'/api/alert/mark-read',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:EMAIL,notif_id:id})});refreshCount();refreshList();} catch(e) {}
};
window.waMarkAll = async function() {
  try {await fetch(API+'/api/alert/mark-read',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:EMAIL})});refreshCount();refreshList();} catch(e) {}
};
window.waClear = async function() {
  try {await fetch(API+'/api/alert/clear',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:EMAIL})});refreshCount();refreshList();} catch(e) {}
};

// ══════ AUTO-INJECT BUTTONS ══════
function injectButtons() {
  document.querySelectorAll('table tbody tr').forEach(function(row) {
    if (row.querySelector('.wa-btn')) return;
    var cells = row.querySelectorAll('td');
    if (cells.length<3) return;
    var nameCell = cells[1];
    var nameText = (nameCell.textContent||'').trim().split('\n')[0].trim();
    if (!nameText||nameText.length<2) return;
    if (nameText==='\u0647\u0646\u0648\u0632'||nameText==='\u0627\u0633\u062A\u0631\u0627\u062A\u0698\u06CC') return;
    var btn = document.createElement('button');
    btn.className = 'wa-btn';
    btn.textContent = '\u{1F514}';
    btn.title = '\u062A\u0646\u0638\u06CC\u0645 \u0647\u0634\u062F\u0627\u0631';
    (function(n){btn.onclick=function(e){e.stopPropagation();waOpenSub(n.replace(/\s+/g,'_'),n);};})(nameText);
    var lastCell = cells[cells.length-1];
    lastCell.appendChild(btn);
  });
  if (!document.getElementById('waGlobalBtn')) {
    var area = document.querySelector('.adv-panel')||document.querySelector('.filter-bar');
    if (area) {
      var gb = document.createElement('button');
      gb.id = 'waGlobalBtn';
      gb.className = 'wa-btn';
      gb.style.cssText = 'padding:4px 10px;font-size:11px;margin:4px;';
      gb.innerHTML = '\u{1F514} \u0627\u0634\u062A\u0631\u0627\u06A9 \u0647\u0645\u0647';
      gb.onclick = function(){waOpenSub('*','\u0647\u0645\u0647 \u0627\u0633\u062A\u0631\u0627\u062A\u0698\u06CC\u200C\u0647\u0627');};
      area.appendChild(gb);
    }
  }
}

var observer = new MutationObserver(function(){setTimeout(injectButtons,300);});
observer.observe(document.body,{childList:true,subtree:true});

// ══════ INIT ══════
requestDesktopPermission();
refreshCount();
setInterval(refreshCount, 8000);
setTimeout(injectButtons, 1500);
setInterval(injectButtons, 5000);

})();


// ══════ LOADING STATE FOR ALERT ACTIONS ══════
(function(){
  // Wrap waSaveSub with loading state
  var _origSave = window.waSaveSub;
  if(_origSave){
    window.waSaveSub = async function(){
      var btn = document.querySelector('.wa-save, .wa-btn-save, button[onclick*="waSaveSub"]');
      var resultEl = document.getElementById('waResult');
      if(btn){
        btn.disabled = true;
        btn._orig = btn.innerHTML;
        btn.innerHTML = '<span class="wh-spinner"></span> \u062F\u0631 \u062D\u0627\u0644 \u067E\u0631\u062F\u0627\u0632\u0634...';
        btn.style.opacity = '.6';
      }
      if(resultEl) resultEl.innerHTML = '<span style="color:#94a3b8">\u26F3 \u0644\u0637\u0641\u0627\u064B \u0635\u0628\u0631 \u06A9\u0646\u06CC\u062F...</span>';
      try {
        await _origSave();
        if(typeof whToast === 'function') whToast('\u2705 \u0647\u0634\u062F\u0627\u0631 \u0641\u0639\u0627\u0644 \u0634\u062F!', 'success');
      } catch(e) {
        if(resultEl) resultEl.innerHTML = '<span style="color:#ef4444">\u274C \u062E\u0637\u0627 \u062F\u0631 \u0641\u0639\u0627\u0644\u200C\u0633\u0627\u0632\u06CC</span>';
        if(typeof whToast === 'function') whToast('\u274C \u062E\u0637\u0627 \u062F\u0631 \u0641\u0639\u0627\u0644\u200C\u0633\u0627\u0632\u06CC', 'error');
      }
      if(btn){ btn.disabled = false; btn.innerHTML = btn._orig || '\u2705 \u0641\u0639\u0627\u0644\u200C\u0633\u0627\u0632\u06CC \u0647\u0634\u062F\u0627\u0631'; btn.style.opacity = '1'; }
    };
  }

  // Wrap waRemoveSub
  var _origRemove = window.waRemoveSub;
  if(_origRemove){
    window.waRemoveSub = async function(sid){
      if(typeof whToast === 'function') whToast('\u062F\u0631 \u062D\u0627\u0644 \u062D\u0630\u0641...', '');
      try {
        await _origRemove(sid);
        if(typeof whToast === 'function') whToast('\u2705 \u0647\u0634\u062F\u0627\u0631 \u062D\u0630\u0641 \u0634\u062F', 'success');
      } catch(e) {
        if(typeof whToast === 'function') whToast('\u274C \u062E\u0637\u0627', 'error');
      }
    };
  }
})();
// ══════ END LOADING STATE ══════
