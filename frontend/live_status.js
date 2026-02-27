/*
 * Whilber-AI — Live Trade Status Overlay
 * Shows real-time trade status on each strategy card in dashboard.
 * "30 min ago entered → waiting TP1" / "trailing active, +$12"
 */
(function(){
var API = window.location.origin;
var _activeTrades = [];
var _tradeMap = {};  // strategy_name -> trade info

var STATUS_FA = {
  'signal_detected': {icon:'\u{1F4E1}',text:'\u0633\u06CC\u06AF\u0646\u0627\u0644 \u0634\u0646\u0627\u0633\u0627\u06CC\u06CC',color:'#06b6d4'},
  'entry_confirmed': {icon:'\u{1F7E2}',text:'\u0648\u0631\u0648\u062F \u0627\u0646\u062C\u0627\u0645 \u0634\u062F',color:'#22c55e'},
  'in_loss':         {icon:'\u{1F534}',text:'\u062F\u0631 \u0636\u0631\u0631',color:'#ef4444'},
  'near_be':         {icon:'\u{1F49B}',text:'\u0646\u0632\u062F\u06CC\u06A9 BE',color:'#f59e0b'},
  'be_activated':    {icon:'\u{1F49B}',text:'SL \u0628\u0647 BE \u0631\u0641\u062A',color:'#f59e0b'},
  'in_profit':       {icon:'\u{1F4B0}',text:'\u062F\u0631 \u0633\u0648\u062F',color:'#22c55e'},
  'partial_close_1': {icon:'\u{1F4B0}',text:'\u0633\u06CC\u0648 \u0633\u0648\u062F \u06F1',color:'#22c55e'},
  'partial_close_2': {icon:'\u{1F4B0}',text:'\u0633\u06CC\u0648 \u0633\u0648\u062F \u06F2',color:'#22c55e'},
  'trailing_active': {icon:'\u{1F504}',text:'Trailing \u0641\u0639\u0627\u0644',color:'#a855f7'},
  'near_tp':         {icon:'\u{1F3AF}',text:'\u0646\u0632\u062F\u06CC\u06A9 TP!',color:'#22c55e'},
  'near_sl':         {icon:'\u{1F534}',text:'\u0646\u0632\u062F\u06CC\u06A9 SL!',color:'#ef4444'},
};

// CSS
var style = document.createElement('style');
style.textContent = '\
.live-status{display:flex;align-items:center;gap:4px;padding:3px 8px;border-radius:6px;font-size:9px;font-weight:700;margin-top:4px;animation:livePulse 2s infinite;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.04);}\
.live-status .ls-icon{font-size:12px;}\
.live-status .ls-text{flex:1;line-height:1.2;}\
.live-status .ls-pnl{font-weight:800;font-size:10px;}\
.live-status .ls-time{font-size:7px;color:#64748b;}\
@keyframes livePulse{0%,100%{opacity:1;}50%{opacity:.85;}}\
.ls-link{font-size:8px;color:#06b6d4;cursor:pointer;text-decoration:underline;margin-top:1px;}\
';
document.head.appendChild(style);

function timeAgo(isoStr){
  if(!isoStr) return '';
  try{
    var d=new Date(isoStr);
    var now=new Date();
    var diff=Math.floor((now-d)/1000);
    if(diff<60) return diff+'\u062B';
    if(diff<3600) return Math.floor(diff/60)+'\u062F';
    if(diff<86400) return Math.floor(diff/3600)+'\u0633';
    return Math.floor(diff/86400)+'\u0631';
  }catch(e){return '';}
}

async function fetchActiveTrades(){
  try{
    var r = await fetch(API+'/api/tracker/active');
    var d = await r.json();
    _activeTrades = d.active || d || [];
    if(!Array.isArray(_activeTrades)) _activeTrades=[];

    _tradeMap = {};
    _activeTrades.forEach(function(t){
      var name = (t.strategy_name||'').toLowerCase().trim();
      if(name) _tradeMap[name] = t;
      // Also map by ID
      var sid = (t.strategy_id||'');
      if(sid) _tradeMap[sid.toLowerCase()] = t;
    });
  }catch(e){}
}

function getTradeStatus(trade){
  // Determine current stage from events
  var stage = trade.stage || trade.current_stage || 'entry_confirmed';
  var events = trade.events || [];
  if(events.length){
    var last = events[events.length-1];
    stage = last.stage || last.type || stage;
  }

  var info = STATUS_FA[stage] || {icon:'\u{1F7E2}',text:'\u0641\u0639\u0627\u0644',color:'#22c55e'};

  // Calculate PnL
  var pnl = trade.current_pnl_usd || 0;
  var pnlPips = trade.current_pnl_pips || 0;
  var direction = trade.direction || 'BUY';
  var entry = trade.entry_price || 0;
  var current = trade.current_price || entry;
  var sl = trade.sl_price || 0;
  var tp1 = trade.tp1_price || trade.tp_price || 0;

  // What's next
  var nextAction = '';
  if(stage==='entry_confirmed'||stage==='in_loss') nextAction='\u0645\u0646\u062A\u0638\u0631 BE';
  else if(stage==='be_activated'||stage==='in_profit') nextAction='\u0645\u0646\u062A\u0638\u0631 TP1';
  else if(stage==='partial_close_1') nextAction='\u0645\u0646\u062A\u0638\u0631 TP2';
  else if(stage==='trailing_active') nextAction='Trailing \u062F\u0631 \u062D\u0627\u0644 \u062D\u0631\u06A9\u062A';
  else if(stage==='near_tp') nextAction='\u0622\u0645\u0627\u062F\u0647 \u0633\u06CC\u0648!';
  else if(stage==='near_sl') nextAction='\u0645\u0631\u0627\u0642\u0628 \u0628\u0627\u0634\u06CC\u062F!';

  return {
    icon: info.icon,
    text: info.text,
    color: info.color,
    pnl: pnl,
    pnlPips: pnlPips,
    nextAction: nextAction,
    direction: direction,
    entry: entry,
    current: current,
    sl: sl,
    tp1: tp1,
    timeAgo: timeAgo(trade.opened_at),
    symbol: trade.symbol||'',
  };
}

function injectLiveStatus(){
  // Find strategy cards/setups on dashboard
  var cards = document.querySelectorAll('.signal-card, .strategy-card, .setup-card, [data-signal], [data-strategy-id], [data-name]');
  
  cards.forEach(function(card){
    if(card.querySelector('.live-status')) return; // Already has

    // Find strategy name
    var name = '';
    if(card.dataset.name) name = card.dataset.name;
    else if(card.dataset.strategyId) name = card.dataset.strategyId;
    else{
      // Try to find from card header text
      var header = card.querySelector('h3, h4, .card-title, .signal-name, b, strong');
      if(header) name = header.textContent.trim();
    }
    if(!name) return;

    // Match against active trades
    var nameLower = name.toLowerCase().trim();
    var trade = _tradeMap[nameLower];

    // Try partial match
    if(!trade){
      for(var key in _tradeMap){
        if(key.indexOf(nameLower)>=0 || nameLower.indexOf(key)>=0){
          trade = _tradeMap[key];
          break;
        }
      }
    }

    if(!trade) return;

    var s = getTradeStatus(trade);
    var div = document.createElement('div');
    div.className = 'live-status';
    div.style.borderColor = s.color+'33';

    var pnlColor = s.pnl>=0 ? '#22c55e' : '#ef4444';
    var pnlSign = s.pnl>=0 ? '+' : '';

    div.innerHTML = '<span class="ls-icon">'+s.icon+'</span>'
      +'<div class="ls-text">'
      +'<div style="color:'+s.color+';">'+s.text+(s.nextAction?' \u2192 '+s.nextAction:'')+'</div>'
      +'<div class="ls-time">'+s.direction+' '+s.symbol+' | '+s.timeAgo+' \u067E\u06CC\u0634 | '+s.entry+' \u2192 '+s.current+'</div>'
      +'</div>'
      +'<span class="ls-pnl" style="color:'+pnlColor+';">'+pnlSign+s.pnl+'$</span>';

    // Find best place to insert
    var body = card.querySelector('.card-body, .signal-body, .setup-body');
    if(body) body.appendChild(div);
    else card.appendChild(div);
  });
}

// Also add live status to setup tables
function injectSetupStatus(){
  document.querySelectorAll('table tbody tr').forEach(function(row){
    if(row.querySelector('.live-status')) return;
    var cells = row.querySelectorAll('td');
    if(cells.length<3) return;
    var nameCell = cells[1] || cells[0];
    var name = (nameCell.textContent||'').trim().split('\n')[0].trim().toLowerCase();
    if(!name || name.length<2) return;

    var trade = _tradeMap[name];
    if(!trade){
      for(var key in _tradeMap){
        if(key.indexOf(name)>=0 || name.indexOf(key)>=0){
          trade = _tradeMap[key];
          break;
        }
      }
    }
    if(!trade) return;

    var s = getTradeStatus(trade);
    var badge = document.createElement('div');
    badge.className = 'live-status';
    badge.style.cssText = 'display:inline-flex;padding:1px 5px;margin-top:2px;border-color:'+s.color+'33;';
    badge.innerHTML = '<span class="ls-icon" style="font-size:10px;">'+s.icon+'</span><span style="font-size:8px;color:'+s.color+';">'+s.text+'</span><span class="ls-pnl" style="font-size:8px;color:'+(s.pnl>=0?'#22c55e':'#ef4444')+';">'+(s.pnl>=0?'+':'')+s.pnl+'$</span>';
    nameCell.appendChild(badge);
  });
}

// Poll
async function update(){
  await fetchActiveTrades();
  injectLiveStatus();
  injectSetupStatus();
}

setTimeout(update, 2000);
setInterval(update, 15000);

})();
