/* ═══════════════════════════════════════════════════════════
   Whilber-AI — Universal Alert Modal
   Include on any page: <script src="/static/alert-modal.js">
   
   Usage: whilberAlert.open("strategy_id", "XAUUSD", "Strategy Name")
   ═══════════════════════════════════════════════════════════ */
(function(){
"use strict";

var ALL_SYMBOLS = ['XAUUSD','EURUSD','GBPUSD','USDJPY','AUDUSD','USDCAD','NZDUSD','USDCHF','BTCUSD','XAGUSD','US30','NAS100'];

var EVENTS = [
  {id:'signal',     icon:'📡', label:'سیگنال جدید',      desc:'وقتی ستاپ شناسایی شد'},
  {id:'entry',      icon:'🟢', label:'ورود به معامله',    desc:'قیمت به نقطه ورود رسید'},
  {id:'be_activated',icon:'💛', label:'SL به Break Even', desc:'SL به نقطه ورود رفت'},
  {id:'partial_close',icon:'💰',label:'سیو سود',          desc:'بخشی از سود ذخیره شد'},
  {id:'trailing_active',icon:'🔄',label:'Trailing فعال',  desc:'SL دنبال قیمت'},
  {id:'near_tp',    icon:'🎯', label:'نزدیک TP',          desc:'نزدیک حد سود'},
  {id:'near_sl',    icon:'🔴', label:'نزدیک SL',          desc:'هشدار! نزدیک حد ضرر'},
  {id:'closed_tp',  icon:'✅', label:'بسته شد — TP',      desc:'معامله با سود بسته شد'},
  {id:'closed_sl',  icon:'❌', label:'بسته شد — SL',      desc:'معامله با ضرر بسته شد'},
  {id:'closed_trailing',icon:'🔄',label:'بسته شد — Trail',desc:'با trailing بسته شد'},
  {id:'closed_be',  icon:'🟡', label:'بسته شد — BE',      desc:'در break even بسته شد'},
];

var CHANNELS = [
  {id:'telegram', icon:'📱', label:'تلگرام شخصی',   desc:'ارسال به بات تلگرام شما'},
  {id:'channel',  icon:'📢', label:'کانال عمومی',    desc:'ارسال به کانال تلگرام Whilber'},
  {id:'popup',    icon:'💻', label:'پاپ‌آپ دسکتاپ',  desc:'نوتیفیکیشن مرورگر + صفحه'},
  {id:'email',    icon:'📧', label:'ایمیل',           desc:'ارسال به ایمیل ثبت‌شده'},
  {id:'sound',    icon:'🔊', label:'صدا',             desc:'صدای آلرت در سایت'},
];

var _currentSid = '';
var _currentSym = '';
var _currentName = '';
var _selectedSymbols = new Set(['*']);
var _selectedEvents = new Set(EVENTS.map(function(e){return e.id;}));
var _selectedChannels = new Set(['telegram','popup','sound']);
var _minConfidence = 0;
var _subscriptions = [];
var _modalEl = null;
var _isAdmin = false;

// ── Check admin status ──
try {
  _isAdmin = !!localStorage.getItem('admin_token');
} catch(e){}

// ── Build modal HTML ──
function _createModal(){
  if(_modalEl) return;
  
  var overlay = document.createElement('div');
  overlay.id = 'wAlertOverlay';
  overlay.onclick = function(e){if(e.target===overlay) close();};
  
  var box = document.createElement('div');
  box.id = 'wAlertBox';
  
  box.innerHTML = [
    '<div class="wa-header">',
    '  <span class="wa-title" id="waTitle">🔔 تنظیم هشدار</span>',
    '  <span class="wa-close" onclick="whilberAlert.close()">✕</span>',
    '</div>',
    '<div class="wa-body">',
    '  <div class="wa-name" id="waName"></div>',
    '',
    '  <div class="wa-section">',
    '    <div class="wa-slbl">📍 نمادها:</div>',
    '    <div class="wa-chips" id="waSymbols"></div>',
    '  </div>',
    '',
    '  <div class="wa-section">',
    '    <div class="wa-slbl">⚡ مراحل هشدار (ورود تا خروج):</div>',
    '    <div class="wa-events" id="waEvents"></div>',
    '  </div>',
    '',
    '  <div class="wa-section">',
    '    <div class="wa-slbl">📣 کانال هشدار:</div>',
    '    <div class="wa-channels" id="waChannels"></div>',
    '  </div>',
    '',
    '  <div class="wa-section">',
    '    <div class="wa-row">',
    '      <span class="wa-slbl" style="margin:0;">حداقل اعتماد:</span>',
    '      <input type="range" id="waConf" min="0" max="100" value="0" oninput="document.getElementById(\'waConfVal\').textContent=this.value+\'%\'">',
    '      <span id="waConfVal" style="font-size:11px;color:#06b6d4;min-width:35px;">0%</span>',
    '    </div>',
    '  </div>',
    '',
    '  <div class="wa-actions">',
    '    <button class="wa-btn wa-btn-green" onclick="whilberAlert.save()">✅ فعال‌سازی هشدار</button>',
    '    <button class="wa-btn wa-btn-red" onclick="whilberAlert.disable()">🔕 غیرفعال</button>',
    '  </div>',
    '  <div id="waResult"></div>',
    '',
    '  <div class="wa-section" style="margin-top:12px;border-top:1px solid #2d3748;padding-top:10px;">',
    '    <div class="wa-slbl">📋 اشتراک‌ها:</div>',
    '    <div id="waSubs" class="wa-subs"></div>',
    '  </div>',
    '</div>',
  ].join('\n');
  
  overlay.appendChild(box);
  document.body.appendChild(overlay);
  _modalEl = overlay;
}

function _buildSymbols(){
  var el = document.getElementById('waSymbols');
  if(!el) return;
  el.innerHTML = '';
  
  // "All" chip
  var allChip = document.createElement('div');
  allChip.className = 'wa-chip' + (_selectedSymbols.has('*') ? ' on' : '');
  allChip.textContent = 'همه';
  allChip.onclick = function(){
    if(_selectedSymbols.has('*')){
      _selectedSymbols.clear();
    } else {
      _selectedSymbols.clear();
      _selectedSymbols.add('*');
    }
    _buildSymbols();
  };
  el.appendChild(allChip);
  
  ALL_SYMBOLS.forEach(function(s){
    var chip = document.createElement('div');
    var isOn = _selectedSymbols.has('*') || _selectedSymbols.has(s);
    chip.className = 'wa-chip' + (isOn ? ' on' : '');
    chip.textContent = s;
    chip.onclick = function(){
      _selectedSymbols.delete('*');
      if(_selectedSymbols.has(s)) _selectedSymbols.delete(s);
      else _selectedSymbols.add(s);
      if(_selectedSymbols.size === 0 || _selectedSymbols.size === ALL_SYMBOLS.length){
        _selectedSymbols.clear(); _selectedSymbols.add('*');
      }
      _buildSymbols();
    };
    el.appendChild(chip);
  });
}

function _buildEvents(){
  var el = document.getElementById('waEvents');
  if(!el) return;
  el.innerHTML = '';
  EVENTS.forEach(function(e){
    var row = document.createElement('div');
    var isOn = _selectedEvents.has(e.id);
    row.className = 'wa-evt-row' + (isOn ? ' on' : '');
    row.innerHTML = '<span class="wa-evt-icon">' + e.icon + '</span>' +
                    '<span class="wa-evt-label">' + e.label + '</span>' +
                    '<span class="wa-evt-desc">' + e.desc + '</span>';
    row.onclick = function(){
      if(_selectedEvents.has(e.id)) _selectedEvents.delete(e.id);
      else _selectedEvents.add(e.id);
      row.classList.toggle('on');
    };
    el.appendChild(row);
  });
}

function _buildChannels(){
  var el = document.getElementById('waChannels');
  if(!el) return;
  el.innerHTML = '';
  
  CHANNELS.forEach(function(ch){
    // Skip channel option for non-admin
    if(ch.id === 'channel' && !_isAdmin) return;
    
    var row = document.createElement('div');
    var isOn = _selectedChannels.has(ch.id);
    row.className = 'wa-ch-row' + (isOn ? ' on' : '');
    row.innerHTML = '<span class="wa-ch-icon">' + ch.icon + '</span>' +
                    '<span class="wa-ch-label">' + ch.label + '</span>' +
                    '<span class="wa-ch-desc">' + ch.desc + '</span>' +
                    '<span class="wa-ch-toggle">' + (isOn ? '✅' : '⬜') + '</span>';
    row.onclick = function(){
      if(_selectedChannels.has(ch.id)){
        _selectedChannels.delete(ch.id);
        row.classList.remove('on');
        row.querySelector('.wa-ch-toggle').textContent = '⬜';
      } else {
        _selectedChannels.add(ch.id);
        row.classList.add('on');
        row.querySelector('.wa-ch-toggle').textContent = '✅';
      }
    };
    el.appendChild(row);
  });
}

function _loadSubscriptions(){
  var el = document.getElementById('waSubs');
  if(!el) return;
  el.innerHTML = '<div style="color:#64748b;font-size:10px;">در حال بارگذاری...</div>';
  
  fetch('/api/alerts/strategy-configs').then(function(r){return r.json();}).then(function(d){
    var configs = d.configs || [];
    _subscriptions = configs;
    if(configs.length === 0){
      el.innerHTML = '<div style="color:#64748b;font-size:10px;">هنوز اشتراکی ندارید</div>';
      return;
    }
    var html = '';
    configs.forEach(function(c){
      var chIcons = '';
      if(c.telegram) chIcons += '📱';
      if(c.channel) chIcons += '📢';
      if(c.popup) chIcons += '💻';
      if(c.email) chIcons += '📧';
      var evts = c.events;
      if(evts && evts !== '*'){
        try{evts = JSON.parse(evts); evts = evts.length + ' رویداد';}catch(e){evts = c.events;}
      } else {evts = 'همه';}
      html += '<div class="wa-sub-row' + (c.strategy_id === _currentSid ? ' active' : '') + '" onclick="whilberAlert.open(\'' + c.strategy_id + '\',\'' + c.symbol + '\',\'' + c.strategy_name + '\')">';
      html += '<span class="wa-sub-name">' + (c.strategy_name || c.strategy_id) + '</span>';
      html += '<span class="wa-sub-sym">' + (c.symbol || '*') + '</span>';
      html += '<span class="wa-sub-ch">' + chIcons + '</span>';
      html += '<span class="wa-sub-evt">' + evts + '</span>';
      html += '</div>';
    });
    el.innerHTML = html;
  }).catch(function(){
    el.innerHTML = '<div style="color:#ef4444;font-size:10px;">خطا</div>';
  });
}

function _loadExisting(sid){
  // Try to load existing config for this strategy
  for(var i = 0; i < _subscriptions.length; i++){
    var c = _subscriptions[i];
    if(c.strategy_id === sid){
      _selectedChannels.clear();
      if(c.telegram) _selectedChannels.add('telegram');
      if(c.channel) _selectedChannels.add('channel');
      if(c.popup) _selectedChannels.add('popup');
      if(c.email) _selectedChannels.add('email');
      if(c.events && c.events !== '*'){
        try{
          var evts = JSON.parse(c.events);
          _selectedEvents = new Set(evts);
        }catch(e){}
      }
      _minConfidence = c.min_confidence || 0;
      return true;
    }
  }
  return false;
}

// ── Public API ──

function open(strategyId, symbol, strategyName){
  _createModal();
  _currentSid = strategyId || '';
  _currentSym = symbol || '';
  _currentName = strategyName || strategyId || '';
  
  document.getElementById('waTitle').textContent = '🔔 تنظیم هشدار';
  document.getElementById('waName').textContent = _currentName;
  document.getElementById('waResult').innerHTML = '';
  
  // Reset defaults
  _selectedSymbols = new Set(['*']);
  _selectedEvents = new Set(EVENTS.map(function(e){return e.id;}));
  _selectedChannels = new Set(['telegram','popup','sound']);
  _minConfidence = 0;
  
  // If symbol provided, pre-select it
  if(symbol && symbol !== '*'){
    _selectedSymbols = new Set([symbol]);
  }
  
  // Load existing config
  _loadExisting(strategyId);
  
  // Build UI
  _buildSymbols();
  _buildEvents();
  _buildChannels();
  document.getElementById('waConf').value = _minConfidence;
  document.getElementById('waConfVal').textContent = _minConfidence + '%';
  
  // Load subscriptions
  _loadSubscriptions();
  
  // Show
  _modalEl.classList.add('show');
}

function close(){
  if(_modalEl) _modalEl.classList.remove('show');
}

function save(){
  var syms = _selectedSymbols.has('*') ? '*' : Array.from(_selectedSymbols);
  var evts = _selectedEvents.size === EVENTS.length ? '*' : Array.from(_selectedEvents);
  var conf = parseInt(document.getElementById('waConf').value) || 0;
  
  var body = {
    strategy_id: _currentSid,
    symbol: _currentSym,
    strategy_name: _currentName,
    symbols: syms,
    events: evts,
    telegram: _selectedChannels.has('telegram'),
    channel: _selectedChannels.has('channel'),
    email: _selectedChannels.has('email'),
    popup: _selectedChannels.has('popup'),
    sound: _selectedChannels.has('sound'),
    min_confidence: conf,
  };
  
  var resEl = document.getElementById('waResult');
  resEl.innerHTML = '<div style="color:#f59e0b;font-size:10px;">⏳ ذخیره...</div>';
  
  fetch('/api/alerts/strategy-config', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body)
  }).then(function(r){return r.json();}).then(function(d){
    if(d.ok){
      resEl.innerHTML = '<div style="color:#10b981;font-size:11px;">✅ هشدار فعال شد!</div>';
      _loadSubscriptions();
      // Mark buttons on page
      var btns = document.querySelectorAll('[data-alert-sid="' + _currentSid + '"]');
      btns.forEach(function(b){b.classList.add('wa-active');});
    } else {
      resEl.innerHTML = '<div style="color:#ef4444;font-size:10px;">❌ ' + (d.error || 'خطا') + '</div>';
    }
  }).catch(function(e){
    resEl.innerHTML = '<div style="color:#ef4444;font-size:10px;">❌ ' + e.message + '</div>';
  });
}

function disable(){
  fetch('/api/alerts/strategy-config', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({strategy_id: _currentSid, disabled: true})
  }).then(function(r){return r.json();}).then(function(d){
    document.getElementById('waResult').innerHTML = '<div style="color:#f59e0b;font-size:10px;">🔕 غیرفعال شد</div>';
    _loadSubscriptions();
    var btns = document.querySelectorAll('[data-alert-sid="' + _currentSid + '"]');
    btns.forEach(function(b){b.classList.remove('wa-active');});
  });
}

// ── Inject CSS ──
var css = document.createElement('style');
css.textContent = [
  '#wAlertOverlay{position:fixed;inset:0;background:rgba(0,0,0,.75);z-index:99999;display:none;align-items:center;justify-content:center;backdrop-filter:blur(4px);}',
  '#wAlertOverlay.show{display:flex;}',
  '#wAlertBox{background:#0f1724;border:1px solid #1e3a5f;border-radius:14px;width:420px;max-width:92%;max-height:85vh;overflow-y:auto;box-shadow:0 20px 60px rgba(0,0,0,.8);direction:rtl;font-family:Tahoma,sans-serif;}',
  '.wa-header{display:flex;align-items:center;justify-content:space-between;padding:14px 16px;border-bottom:1px solid #1e293b;}',
  '.wa-title{font-size:14px;font-weight:700;color:#06b6d4;}',
  '.wa-close{cursor:pointer;color:#64748b;font-size:16px;width:24px;height:24px;display:flex;align-items:center;justify-content:center;border-radius:50%;transition:.2s;}',
  '.wa-close:hover{background:#1e293b;color:#fff;}',
  '.wa-body{padding:14px 16px;}',
  '.wa-name{font-size:13px;font-weight:700;color:#e2e8f0;margin-bottom:12px;padding:8px 10px;background:#111827;border-radius:8px;border-right:3px solid #06b6d4;}',
  '.wa-section{margin-bottom:12px;}',
  '.wa-slbl{font-size:11px;color:#94a3b8;margin-bottom:6px;font-weight:600;}',
  '.wa-chips{display:flex;flex-wrap:wrap;gap:4px;}',
  '.wa-chip{padding:3px 10px;border-radius:14px;font-size:10px;cursor:pointer;border:1px solid #2d3748;background:#111827;color:#64748b;transition:.15s;}',
  '.wa-chip.on{background:rgba(6,182,212,.15);border-color:#06b6d4;color:#06b6d4;}',
  '.wa-chip:hover{border-color:#06b6d4;}',
  '.wa-events{display:flex;flex-direction:column;gap:3px;}',
  '.wa-evt-row{display:flex;align-items:center;gap:6px;padding:5px 8px;border-radius:6px;cursor:pointer;transition:.15s;border:1px solid transparent;}',
  '.wa-evt-row:hover{background:rgba(255,255,255,.03);}',
  '.wa-evt-row.on{background:rgba(6,182,212,.08);border-color:rgba(6,182,212,.2);}',
  '.wa-evt-icon{font-size:14px;width:20px;text-align:center;}',
  '.wa-evt-label{font-size:11px;font-weight:600;color:#e2e8f0;min-width:110px;}',
  '.wa-evt-desc{font-size:9px;color:#64748b;}',
  '.wa-channels{display:flex;flex-direction:column;gap:3px;}',
  '.wa-ch-row{display:flex;align-items:center;gap:8px;padding:6px 10px;border-radius:6px;cursor:pointer;transition:.15s;border:1px solid transparent;}',
  '.wa-ch-row:hover{background:rgba(255,255,255,.03);}',
  '.wa-ch-row.on{background:rgba(16,185,129,.08);border-color:rgba(16,185,129,.2);}',
  '.wa-ch-icon{font-size:14px;width:20px;text-align:center;}',
  '.wa-ch-label{font-size:11px;font-weight:600;color:#e2e8f0;min-width:90px;}',
  '.wa-ch-desc{font-size:9px;color:#64748b;flex:1;}',
  '.wa-ch-toggle{font-size:12px;}',
  '.wa-row{display:flex;align-items:center;gap:8px;}',
  '#waConf{flex:1;accent-color:#06b6d4;}',
  '.wa-actions{display:flex;gap:8px;margin-top:12px;}',
  '.wa-btn{padding:8px 16px;border-radius:8px;border:none;cursor:pointer;font-size:11px;font-weight:700;transition:.15s;}',
  '.wa-btn:hover{opacity:.85;transform:translateY(-1px);}',
  '.wa-btn-green{background:#10b981;color:#fff;flex:1;}',
  '.wa-btn-red{background:transparent;border:1px solid #2d3748;color:#94a3b8;}',
  '.wa-subs{max-height:150px;overflow-y:auto;}',
  '.wa-sub-row{display:flex;align-items:center;gap:6px;padding:4px 8px;border-radius:4px;cursor:pointer;font-size:10px;transition:.15s;}',
  '.wa-sub-row:hover{background:rgba(255,255,255,.03);}',
  '.wa-sub-row.active{background:rgba(6,182,212,.1);border-right:2px solid #06b6d4;}',
  '.wa-sub-name{flex:1;color:#e2e8f0;font-weight:600;}',
  '.wa-sub-sym{color:#64748b;min-width:50px;}',
  '.wa-sub-ch{min-width:50px;}',
  '.wa-sub-evt{color:#64748b;}',
  '[data-alert-sid]{cursor:pointer;transition:.15s;}',
  '[data-alert-sid]:hover{transform:scale(1.2);}',
  '[data-alert-sid].wa-active{filter:drop-shadow(0 0 4px #10b981);}',
].join('\n');
document.head.appendChild(css);

// Expose
window.whilberAlert = {open: open, close: close, save: save, disable: disable};
})();
