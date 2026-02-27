/*
 * Whilber-AI Alert System — Standalone
 * Load this file in any page: <script src="/static/alert_system.js"></script>
 * It creates everything from JS: bell, panel, modal, buttons.
 */
(function(){
var API = window.location.origin;
var EMAIL = localStorage.getItem('whilber_email') || 'user@whilber.ai';
var SYMS = ['XAUUSD','EURUSD','GBPUSD','USDJPY','AUDUSD','USDCAD','NZDUSD','USDCHF','BTCUSD','XAGUSD','US30','NAS100'];
var EVENTS = [
  {id:'signal',icon:'\u{1F4E1}',name:'\u0633\u06CC\u06AF\u0646\u0627\u0644 \u062C\u062F\u06CC\u062F',desc:'\u0648\u0642\u062A\u06CC \u0633\u062A\u0627\u067E \u0634\u0646\u0627\u0633\u0627\u06CC\u06CC \u0634\u062F'},
  {id:'entry',icon:'\u{1F7E2}',name:'\u0648\u0631\u0648\u062F \u0628\u0647 \u0645\u0639\u0627\u0645\u0644\u0647',desc:'\u0642\u06CC\u0645\u062A \u0628\u0647 \u0646\u0642\u0637\u0647 \u0648\u0631\u0648\u062F \u0631\u0633\u06CC\u062F'},
  {id:'be_move',icon:'\u{1F49B}',name:'SL \u0628\u0647 Break Even',desc:'\u0631\u06CC\u0633\u06A9 \u0635\u0641\u0631 \u0634\u062F'},
  {id:'partial',icon:'\u{1F4B0}',name:'\u0633\u06CC\u0648 \u0633\u0648\u062F',desc:'\u0628\u062E\u0634\u06CC \u0627\u0632 \u0633\u0648\u062F \u0630\u062E\u06CC\u0631\u0647 \u0634\u062F'},
  {id:'trailing',icon:'\u{1F504}',name:'Trailing \u0641\u0639\u0627\u0644',desc:'SL \u062F\u0646\u0628\u0627\u0644 \u0642\u06CC\u0645\u062A'},
  {id:'near_tp',icon:'\u{1F3AF}',name:'\u0646\u0632\u062F\u06CC\u06A9 TP',desc:'\u0646\u0632\u062F\u06CC\u06A9 \u062D\u062F \u0633\u0648\u062F'},
  {id:'near_sl',icon:'\u{1F534}',name:'\u0646\u0632\u062F\u06CC\u06A9 SL',desc:'\u0647\u0634\u062F\u0627\u0631!'},
  {id:'closed_tp',icon:'\u2705',name:'\u0628\u0633\u062A\u0647 \u0634\u062F \u2014 TP',desc:'\u0633\u0648\u062F'},
  {id:'closed_sl',icon:'\u274C',name:'\u0628\u0633\u062A\u0647 \u0634\u062F \u2014 SL',desc:'\u0636\u0631\u0631'},
];
var _subSid='', _subName='';

// ══════ INJECT CSS ══════
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
';
document.head.appendChild(style);

// ══════ CREATE BELL ══════
var bell = document.createElement('div');
bell.className = 'wa-bell';
bell.innerHTML = '\u{1F514}<span class="wa-badge" id="waBadge">0</span>';
bell.onclick = function(){ var p=document.getElementById('waPanel'); p.classList.toggle('show'); if(p.classList.contains('show'))refreshList(); };
document.body.appendChild(bell);

// ══════ CREATE PANEL ══════
var panel = document.createElement('div');
panel.className = 'wa-panel';
panel.id = 'waPanel';
panel.innerHTML = '<div class="wa-phead"><h4>\u{1F514} \u0647\u0634\u062F\u0627\u0631\u0647\u0627</h4><div><button class="wa-ghost" onclick="waMarkAll()">\u062E\u0648\u0627\u0646\u062F\u0647</button> <button class="wa-ghost" onclick="waClear()">\u067E\u0627\u06A9</button> <span onclick="document.getElementById(\'waPanel\').classList.remove(\'show\')" style="cursor:pointer;color:#64748b;margin-left:4px;">\u2715</span></div></div><div class="wa-plist" id="waPlist"><div style="text-align:center;color:#64748b;padding:20px;font-size:11px;">\u0628\u062F\u0648\u0646 \u0647\u0634\u062F\u0627\u0631</div></div>';
document.body.appendChild(panel);

// ══════ CREATE MODAL ══════
var overlay = document.createElement('div');
overlay.className = 'wa-overlay';
overlay.id = 'waOverlay';
overlay.onclick = function(e){ if(e.target===overlay) overlay.classList.remove('show'); };
overlay.innerHTML = '<div class="wa-modal" id="waModal"></div>';
document.body.appendChild(overlay);

// ══════ OPEN SUBSCRIBE ══════
window.waOpenSub = function(sid, name){
  _subSid = sid || '*';
  _subName = name || '\u0647\u0645\u0647';
  var m = document.getElementById('waModal');
  var h = '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">';
  h += '<h3>\u{1F514} \u062A\u0646\u0638\u06CC\u0645 \u0647\u0634\u062F\u0627\u0631</h3>';
  h += '<span onclick="document.getElementById(\'waOverlay\').classList.remove(\'show\')" style="cursor:pointer;color:#64748b;border:1px solid rgba(255,255,255,.08);padding:3px 8px;border-radius:6px;">\u2715</span></div>';
  h += '<div style="padding:6px 8px;background:rgba(6,182,212,.06);border:1px solid rgba(6,182,212,.12);border-radius:6px;margin-bottom:8px;font-size:12px;color:#06b6d4;font-weight:700;">' + _subName + '</div>';

  // Symbols
  h += '<div style="font-size:10px;color:#94a3b8;margin-bottom:3px;">\u{1F4CD} \u0646\u0645\u0627\u062F\u0647\u0627:</div><div class="wa-syms" id="waSyms">';
  h += '<div class="wa-sym sel" data-s="*" onclick="waTogSym(this)">\u0647\u0645\u0647</div>';
  SYMS.forEach(function(s){ h += '<div class="wa-sym" data-s="'+s+'" onclick="waTogSym(this)">'+s+'</div>'; });
  h += '</div>';

  // Events
  h += '<div style="font-size:10px;color:#94a3b8;margin:8px 0 3px;">\u26A1 \u0645\u0631\u0627\u062D\u0644 \u0647\u0634\u062F\u0627\u0631:</div>';
  EVENTS.forEach(function(e){
    h += '<div class="wa-evt"><label><span style="font-size:14px;">'+e.icon+'</span> '+e.name+'<br><span class="desc">'+e.desc+'</span></label>';
    h += '<div class="wa-tgl on" data-e="'+e.id+'" onclick="this.classList.toggle(\'on\')"></div></div>';
  });

  h += '<div class="wa-evt" style="margin-top:6px;"><label>\u{1F4E7} \u0627\u06CC\u0645\u06CC\u0644</label><div class="wa-tgl" id="waEmailT" onclick="this.classList.toggle(\'on\')"></div></div>';
  h += '<div class="wa-evt"><label>\u{1F514} \u0627\u067E</label><div class="wa-tgl on" id="waAppT" onclick="this.classList.toggle(\'on\')"></div></div>';

  h += '<div style="margin-top:6px;display:flex;align-items:center;gap:4px;"><label style="font-size:10px;color:#94a3b8;">\u062D\u062F\u0627\u0642\u0644 \u0627\u0639\u062A\u0645\u0627\u062F:</label>';
  h += '<input type="number" id="waMinConf" value="40" min="0" max="100" style="width:45px;padding:2px 4px;border-radius:4px;border:1px solid rgba(255,255,255,.08);background:rgba(255,255,255,.03);color:#e2e8f0;font-size:10px;">';
  h += '<span style="font-size:9px;color:#64748b;">%</span></div>';

  h += '<button class="wa-save" onclick="waSaveSub()">\u2705 \u0641\u0639\u0627\u0644\u200C\u0633\u0627\u0632\u06CC \u0647\u0634\u062F\u0627\u0631</button>';
  h += '<div id="waResult" style="margin-top:4px;font-size:11px;text-align:center;"></div>';
  h += '<div style="margin-top:8px;border-top:1px solid rgba(255,255,255,.03);padding-top:6px;"><div style="font-size:9px;color:#64748b;margin-bottom:4px;">\u{1F4CB} \u0627\u0634\u062A\u0631\u0627\u06A9\u200C\u0647\u0627\u06CC \u0641\u0639\u0627\u0644:</div><div id="waSubList"></div></div>';

  m.innerHTML = h;
  loadSubs();
  document.getElementById('waOverlay').classList.add('show');
};

window.waTogSym = function(el){
  if(el.dataset.s==='*'){document.querySelectorAll('#waSyms .wa-sym').forEach(function(t){t.classList.remove('sel');});el.classList.add('sel');}
  else{document.querySelector('#waSyms [data-s="*"]').classList.remove('sel');el.classList.toggle('sel');}
};

window.waSaveSub = async function(){
  var evts={};
  document.querySelectorAll('.wa-tgl[data-e]').forEach(function(t){evts[t.dataset.e]=t.classList.contains('on');});
  var syms=[];
  document.querySelectorAll('#waSyms .wa-sym.sel').forEach(function(t){syms.push(t.dataset.s);});
  if(!syms.length)syms=['*'];
  var cfg={strategy_id:_subSid,strategy_name:_subName,symbols:syms,alert_on:evts,
    notify_email:document.getElementById('waEmailT').classList.contains('on'),
    notify_app:document.getElementById('waAppT').classList.contains('on'),
    min_confidence:parseInt(document.getElementById('waMinConf').value)||40};
  try{
    var r=await fetch(API+'/api/alert/subscribe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:EMAIL,config:cfg})});
    var d=await r.json();
    document.getElementById('waResult').innerHTML=d.success?'<span style="color:#22c55e;">\u2705 \u0647\u0634\u062F\u0627\u0631 \u0641\u0639\u0627\u0644 \u0634\u062F!</span>':'<span style="color:#ef4444;">\u062E\u0637\u0627</span>';
    if(d.success)loadSubs();
  }catch(e){document.getElementById('waResult').innerHTML='<span style="color:#ef4444;">\u062E\u0637\u0627</span>';}
};

async function loadSubs(){
  try{
    var r=await fetch(API+'/api/alert/subscriptions?email='+encodeURIComponent(EMAIL));
    var d=await r.json();
    var box=document.getElementById('waSubList');
    if(!box)return;
    var subs=d.subscriptions||[];
    if(!subs.length){box.innerHTML='<div style="color:#64748b;font-size:9px;">\u0647\u0646\u0648\u0632 \u0627\u0634\u062A\u0631\u0627\u06A9\u06CC \u0646\u062F\u0627\u0631\u06CC\u062F</div>';return;}
    var h='';
    subs.forEach(function(s){
      h+='<div style="display:flex;align-items:center;justify-content:space-between;padding:3px 0;border-bottom:1px solid rgba(255,255,255,.02);font-size:10px;">';
      h+='<div><b style="color:#06b6d4;">'+(s.strategy_name||'\u0647\u0645\u0647')+'</b> | '+(s.symbols||[]).join(',')+' | '+(s.alert_count||0)+' \u0647\u0634\u062F\u0627\u0631</div>';
      h+='<button onclick="waRemoveSub(\''+s.id+'\')" style="background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.12);color:#ef4444;padding:1px 5px;border-radius:3px;font-size:8px;cursor:pointer;">\u062D\u0630\u0641</button></div>';
    });
    box.innerHTML=h;
  }catch(e){}
}

window.waRemoveSub = async function(id){
  try{await fetch(API+'/api/alert/unsubscribe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:EMAIL,sub_id:id})});loadSubs();}catch(e){}
};

// ══════ NOTIFICATIONS ══════
async function refreshCount(){
  try{
    var r=await fetch(API+'/api/alert/unread-count?email='+encodeURIComponent(EMAIL));
    var d=await r.json();
    var b=document.getElementById('waBadge');
    if(d.count>0){b.style.display='inline';b.textContent=d.count;}else b.style.display='none';
  }catch(e){}
}

async function refreshList(){
  try{
    var r=await fetch(API+'/api/alert/notifications?email='+encodeURIComponent(EMAIL)+'&limit=50');
    var d=await r.json();
    var list=document.getElementById('waPlist');
    var ns=d.notifications||[];
    if(!ns.length){list.innerHTML='<div style="text-align:center;color:#64748b;padding:20px;font-size:11px;">\u0628\u062F\u0648\u0646 \u0647\u0634\u062F\u0627\u0631</div>';return;}
    var h='';
    ns.forEach(function(n){
      h+='<div class="wa-ni '+(n.read?'':'unread')+'">';
      h+='<span style="font-size:16px;">'+(n.icon||'\u{1F514}')+'</span>';
      h+='<div style="flex:1;min-width:0;"><div style="font-size:11px;font-weight:700;">'+(n.title_fa||'')+'</div>';
      h+='<div style="font-size:9px;color:#94a3b8;">'+(n.strategy_name||'')+' | '+(n.symbol||'')+' '+(n.direction||'')+'</div>';
      if(n.action_fa)h+='<div style="font-size:9px;color:#64748b;">'+n.action_fa+'</div>';
      h+='<div style="font-size:8px;color:#475569;">'+(n.time||'').substring(11,19)+'</div>';
      h+='</div></div>';
    });
    list.innerHTML=h;
  }catch(e){}
}

window.waMarkAll = async function(){
  try{await fetch(API+'/api/alert/mark-read',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:EMAIL})});refreshCount();refreshList();}catch(e){}
};
window.waClear = async function(){
  try{await fetch(API+'/api/alert/clear',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:EMAIL})});refreshCount();refreshList();}catch(e){}
};

// ══════ AUTO-INJECT 🔔 BUTTONS ══════
function injectButtons(){
  // All table rows that have strategy names
  document.querySelectorAll('table tbody tr').forEach(function(row){
    if(row.querySelector('.wa-btn'))return;
    // Find cell with strategy name (usually 2nd cell)
    var cells=row.querySelectorAll('td');
    if(cells.length<3)return;
    var nameCell=cells[1];
    var nameText=(nameCell.textContent||'').trim().split('\n')[0].trim();
    if(!nameText||nameText.length<2)return;
    // Skip header-like rows
    if(nameText==='\u0647\u0646\u0648\u0632'||nameText==='\u0627\u0633\u062A\u0631\u0627\u062A\u0698\u06CC')return;

    var btn=document.createElement('button');
    btn.className='wa-btn';
    btn.textContent='\u{1F514}';
    btn.title='\u062A\u0646\u0638\u06CC\u0645 \u0647\u0634\u062F\u0627\u0631';
    (function(n){
      btn.onclick=function(e){e.stopPropagation();waOpenSub(n.replace(/\s+/g,'_'),n);};
    })(nameText);

    var lastCell=cells[cells.length-1];
    lastCell.appendChild(btn);
  });

  // Also add a global subscribe button near filter area
  if(!document.getElementById('waGlobalBtn')){
    var filterArea=document.querySelector('.adv-panel')||document.querySelector('.filter-bar');
    if(filterArea){
      var gb=document.createElement('button');
      gb.id='waGlobalBtn';
      gb.className='wa-btn';
      gb.style.cssText='padding:4px 10px;font-size:11px;margin:4px;';
      gb.innerHTML='\u{1F514} \u0627\u0634\u062A\u0631\u0627\u06A9 \u0647\u0634\u062F\u0627\u0631 \u0647\u0645\u0647';
      gb.onclick=function(){waOpenSub('*','\u0647\u0645\u0647 \u0627\u0633\u062A\u0631\u0627\u062A\u0698\u06CC\u200C\u0647\u0627');};
      filterArea.appendChild(gb);
    }
  }
}

// Observe DOM changes
var observer=new MutationObserver(function(){setTimeout(injectButtons,300);});
observer.observe(document.body,{childList:true,subtree:true});

// Init
refreshCount();
setInterval(refreshCount,10000);
setTimeout(injectButtons,1500);
setInterval(injectButtons,5000);

})();
