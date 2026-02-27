/* Whilber-AI Alert Notification System */
(function(){
var _notifEnabled = true;
var _soundEnabled = true;
var _pollInterval = null;
var _lastAlertId = 0;
var _audioCtx = null;

/* Notification popup */
function showNotif(title, body, type){
  if(!_notifEnabled) return;
  
  /* Browser notification */
  if(Notification && Notification.permission === 'granted'){
    try{
      var n = new Notification(title, {body: body, icon: '/favicon.ico', tag: 'whilber-'+Date.now()});
      setTimeout(function(){n.close();}, 8000);
    }catch(e){}
  }
  
  /* In-page popup */
  var colors = {entry:'#10b981',closed_tp:'#10b981',closed_sl:'#ef4444',be_activated:'#06b6d4',trailing_active:'#06b6d4',near_tp:'#f59e0b',near_sl:'#ef4444'};
  var color = colors[type] || '#06b6d4';
  
  var el = document.createElement('div');
  el.style.cssText = 'position:fixed;top:60px;right:20px;z-index:99999;background:#111827;border:1px solid '+color+';border-right:4px solid '+color+';border-radius:8px;padding:12px 16px;max-width:320px;box-shadow:0 8px 32px rgba(0,0,0,.5);animation:slideIn .3s ease;font-family:Tahoma,sans-serif;direction:rtl;';
  el.innerHTML = '<div style="font-size:13px;font-weight:bold;color:'+color+';margin-bottom:4px;">'+title+'</div><div style="font-size:11px;color:#94a3b8;">'+body+'</div><div style="position:absolute;top:4px;left:8px;cursor:pointer;color:#64748b;font-size:14px;" onclick="this.parentNode.remove()">×</div>';
  document.body.appendChild(el);
  setTimeout(function(){if(el.parentNode) el.remove();}, 8000);
  
  /* Sound */
  if(_soundEnabled) playBeep(type);
}

function playBeep(type){
  try{
    if(!_audioCtx) _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    var osc = _audioCtx.createOscillator();
    var gain = _audioCtx.createGain();
    osc.connect(gain); gain.connect(_audioCtx.destination);
    gain.gain.value = 0.1;
    if(type && type.includes('sl')){osc.frequency.value=300;} 
    else if(type && type.includes('tp')){osc.frequency.value=800;} 
    else{osc.frequency.value=600;}
    osc.start(); osc.stop(_audioCtx.currentTime + 0.2);
  }catch(e){}
}

/* Poll for new alerts */
function pollAlerts(){
  fetch('/api/alerts/log?limit=3').then(function(r){return r.json();}).then(function(d){
    var logs = d.logs || [];
    if(logs.length > 0 && _lastAlertId > 0){
      for(var i=logs.length-1; i>=0; i--){
        var l = logs[i];
        if(l.id > _lastAlertId){
          var icons = {entry:'🟢',closed_tp:'✅',closed_sl:'❌',be_activated:'🛡️',trailing_active:'📈',near_tp:'🎯',near_sl:'⚠️'};
          var titles = {entry:'سیگنال جدید',closed_tp:'بسته شد — TP',closed_sl:'بسته شد — SL',be_activated:'BE فعال',trailing_active:'Trailing فعال',near_tp:'نزدیک TP',near_sl:'نزدیک SL'};
          var icon = icons[l.event_type] || '📌';
          var title = icon + ' ' + (titles[l.event_type] || l.event_type);
          var body = l.symbol + ' | ' + (l.message || '');
          showNotif(title, body, l.event_type);
        }
      }
    }
    if(logs.length > 0) _lastAlertId = logs[0].id;
  }).catch(function(){});
}

/* Init */
function init(){
  /* Request notification permission */
  if(Notification && Notification.permission === 'default'){
    Notification.requestPermission();
  }
  
  /* Add CSS animation */
  var style = document.createElement('style');
  style.textContent = '@keyframes slideIn{from{transform:translateX(100px);opacity:0;}to{transform:translateX(0);opacity:1;}}';
  document.head.appendChild(style);
  
  /* Start polling */
  pollAlerts();
  _pollInterval = setInterval(pollAlerts, 10000);
}

if(document.readyState === 'loading'){document.addEventListener('DOMContentLoaded', init);}
else{init();}

/* Expose */
window.whilberNotif = {show: showNotif, enable: function(v){_notifEnabled=v;}, sound: function(v){_soundEnabled=v;}};
})();
