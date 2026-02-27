/*
 * Whilber-AI — Dashboard Track Record Links
 * Adds "📜 سوابق" link to each strategy card that has track record data.
 * Click → opens /track-record with strategy pre-selected.
 */
(function(){
var API = window.location.origin;
var _summary = {};

var style = document.createElement('style');
style.textContent = '\
.tr-link{display:inline-flex;align-items:center;gap:3px;padding:2px 7px;border-radius:4px;background:rgba(6,182,212,.06);border:1px solid rgba(6,182,212,.12);color:#06b6d4;font-size:9px;font-weight:700;cursor:pointer;transition:.15s;text-decoration:none;margin-top:3px;margin-left:4px;}\
.tr-link:hover{background:rgba(6,182,212,.12);border-color:#06b6d4;}\
.tr-badge{display:inline-flex;align-items:center;gap:2px;padding:1px 5px;border-radius:3px;font-size:8px;font-weight:700;}\
.tr-badge.good{background:rgba(34,197,94,.08);color:#22c55e;border:1px solid rgba(34,197,94,.1);}\
.tr-badge.mid{background:rgba(245,158,11,.08);color:#f59e0b;border:1px solid rgba(245,158,11,.1);}\
.tr-badge.bad{background:rgba(239,68,68,.08);color:#ef4444;border:1px solid rgba(239,68,68,.1);}\
';
document.head.appendChild(style);

async function loadSummary(){
  try{
    var r = await fetch(API+'/api/fast/summary');
    var d = await r.json();
    var list = d.strategies || d || [];
    if(!Array.isArray(list)) return;
    list.forEach(function(s){
      var name = (s.strategy_name||'').toLowerCase().trim();
      if(name) _summary[name] = s;
      var id = (s.strategy_id||'').toLowerCase();
      if(id) _summary[id] = s;
    });
  }catch(e){}
}

function injectLinks(){
  // Find strategy cards
  var cards = document.querySelectorAll('.signal-card, .strategy-card, .setup-card, [data-signal], [data-strategy-id], [data-name], .card');

  cards.forEach(function(card){
    if(card.querySelector('.tr-link')) return;

    var name = '';
    if(card.dataset.name) name = card.dataset.name;
    else if(card.dataset.strategyId) name = card.dataset.strategyId;
    else{
      var header = card.querySelector('h3, h4, .card-title, .signal-name, b, strong');
      if(header) name = header.textContent.trim();
    }
    if(!name || name.length < 3) return;

    var nameLower = name.toLowerCase().trim();
    var record = _summary[nameLower];

    if(!record){
      for(var key in _summary){
        if(key.indexOf(nameLower)>=0 || nameLower.indexOf(key)>=0){
          record = _summary[key];
          break;
        }
      }
    }

    if(!record || !record.total) return;

    // Build badge
    var wr = record.win_rate || 0;
    var cls = wr >= 60 ? 'good' : wr >= 45 ? 'mid' : 'bad';
    var pnl = record.total_pnl || 0;

    var link = document.createElement('a');
    link.className = 'tr-link';
    link.href = '/track-record#' + encodeURIComponent(record.strategy_id || name);
    link.target = '_blank';
    link.innerHTML = '\u{1F4DC} '
      + '<span class="tr-badge '+cls+'">' + wr + '% | ' + record.total + 'tr</span>'
      + (pnl ? ' <span style="font-size:8px;color:'+(pnl>=0?'#22c55e':'#ef4444')+';">'+(pnl>=0?'+':'')+pnl+'$</span>' : '');

    var body = card.querySelector('.card-body, .signal-body, .setup-body');
    if(body) body.appendChild(link);
    else card.appendChild(link);
  });
}

async function init(){
  await loadSummary();
  injectLinks();
  setInterval(injectLinks, 10000);
  setInterval(loadSummary, 60000);
}

setTimeout(init, 2500);
})();
