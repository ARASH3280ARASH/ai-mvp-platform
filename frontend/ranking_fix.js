/*
 * Whilber-AI — Ranking Table Fix
 * Overrides broken ranking code with correct API handling.
 * API: /api/fast/ranking → {ranking: [...], sort_by, total}
 * Each item: {strategy_id, strategy_name, by_symbol:{...}, total, wins, win_rate, total_pnl, ...}
 */
(function(){
var API = window.location.origin;
var _allRanking = [];
var _selectedSid = null;

// Wait for page load
function waitForTable(cb) {
  var el = document.querySelector('.rank-table tbody') || document.getElementById('rankBody');
  if (el) return cb(el);
  setTimeout(function(){ waitForTable(cb); }, 500);
}

function getSymbol(item) {
  if (item.symbol && item.symbol !== 'undefined') return item.symbol;
  if (item.by_symbol) {
    var keys = Object.keys(item.by_symbol);
    if (keys.length) return keys.join(', ');
  }
  // Extract from strategy_id like "ADX_01_EURUSD_H1"
  var sid = item.strategy_id || '';
  var known = ['XAUUSD','EURUSD','GBPUSD','USDJPY','AUDUSD','USDCAD','NZDUSD','USDCHF','BTCUSD','XAGUSD','US30','NAS100'];
  for (var i = 0; i < known.length; i++) {
    if (sid.indexOf(known[i]) >= 0) return known[i];
  }
  return '-';
}

function getLast5(item) {
  var last5 = item.last_5 || [];
  if (!last5.length) return '<span style="color:#64748b;">-</span>';
  return last5.map(function(r) {
    return r === 'win' ? '<span style="color:#22c55e;">\u2705</span>' : '<span style="color:#ef4444;">\u274C</span>';
  }).join('');
}

async function loadRanking(sortBy) {
  sortBy = sortBy || 'win_rate';
  try {
    var r = await fetch(API + '/api/fast/ranking?sort=' + sortBy + '&limit=100');
    var d = await r.json();
    _allRanking = d.ranking || d.strategies || d.data || [];
    if (!Array.isArray(_allRanking)) _allRanking = [];
    renderRankingTable();
  } catch(e) {
    console.error('Ranking fetch error:', e);
  }
}

function renderRankingTable() {
  var tbody = document.querySelector('.rank-table tbody') || document.getElementById('rankBody');
  if (!tbody) return;

  if (!_allRanking.length) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:#64748b;padding:30px;font-size:11px;">\u0647\u0646\u0648\u0632 \u062F\u0627\u062F\u0647\u200C\u0627\u06CC \u0646\u06CC\u0633\u062A \u2014 \u0645\u0646\u062A\u0638\u0631 \u062A\u06A9\u0645\u06CC\u0644 \u0645\u0639\u0627\u0645\u0644\u0627\u062A \u0628\u0627\u0634\u06CC\u062F</td></tr>';
    return;
  }

  var html = '';
  _allRanking.forEach(function(s, i) {
    var wr = (s.win_rate || 0).toFixed(1);
    var wrColor = wr >= 60 ? '#22c55e' : wr >= 45 ? '#f59e0b' : '#ef4444';
    var pnl = (s.total_pnl || 0).toFixed(1);
    var pnlColor = pnl >= 0 ? '#22c55e' : '#ef4444';
    var sym = getSymbol(s);

    html += '<tr style="cursor:pointer;" onclick="window._selectStrategy(\'' + (s.strategy_id||'').replace(/'/g, "\\'") + '\')">';
    html += '<td style="color:#64748b;">' + (i + 1) + '</td>';
    html += '<td><div style="font-size:11px;font-weight:700;color:#06b6d4;">' + (s.strategy_name || s.strategy_id || '') + '</div>';
    if (s.category) html += '<div style="font-size:8px;color:#64748b;">' + s.category + '</div>';
    html += '</td>';
    html += '<td style="font-size:10px;">' + sym + '</td>';
    html += '<td style="text-align:center;">' + (s.total || 0) + ' <span style="font-size:8px;color:#64748b;">(' + (s.wins||0) + 'W/' + (s.losses||0) + 'L)</span></td>';
    html += '<td style="text-align:center;color:' + wrColor + ';font-weight:700;">' + wr + '%</td>';
    html += '<td style="text-align:center;color:' + pnlColor + ';font-weight:700;">' + (pnl >= 0 ? '+' : '') + pnl + '$</td>';
    html += '<td style="text-align:center;">' + getLast5(s) + '</td>';
    html += '</tr>';
  });

  tbody.innerHTML = html;
}

// Strategy detail view
window._selectStrategy = async function(sid) {
  if (!sid) return;
  _selectedSid = sid;

  // Try to show detail section
  var detailCard = document.getElementById('strategyDetail') || document.getElementById('detailCard');
  
  // Fetch stats
  try {
    var r = await fetch(API + '/api/tracker/records/' + encodeURIComponent(sid) + '/stats');
    var stats = await r.json();
    
    var r2 = await fetch(API + '/api/tracker/records/' + encodeURIComponent(sid));
    var rec = await r2.json();
    var trades = rec.trades || rec.records || [];

    // If detail section exists, populate it
    if (detailCard) {
      detailCard.style.display = 'block';
      var body = detailCard.querySelector('.card-body') || detailCard;
      
      var item = _allRanking.find(function(x){ return x.strategy_id === sid; }) || {};
      var sym = getSymbol(item);
      
      var h = '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:8px;">';
      h += '<div style="background:#334155;padding:6px 12px;border-radius:6px;text-align:center;flex:1;min-width:60px;"><div style="font-size:18px;font-weight:800;color:#06b6d4;">' + (stats.total||trades.length) + '</div><div style="font-size:8px;color:#64748b;">\u0645\u0639\u0627\u0645\u0644\u0627\u062A</div></div>';
      h += '<div style="background:#334155;padding:6px 12px;border-radius:6px;text-align:center;flex:1;min-width:60px;"><div style="font-size:18px;font-weight:800;color:' + ((stats.win_rate||0)>=50?'#22c55e':'#ef4444') + ';">' + ((stats.win_rate||0).toFixed(1)) + '%</div><div style="font-size:8px;color:#64748b;">Win Rate</div></div>';
      h += '<div style="background:#334155;padding:6px 12px;border-radius:6px;text-align:center;flex:1;min-width:60px;"><div style="font-size:18px;font-weight:800;color:' + ((stats.total_pnl||0)>=0?'#22c55e':'#ef4444') + ';">' + ((stats.total_pnl||0)>=0?'+':'') + ((stats.total_pnl||0).toFixed(1)) + '$</div><div style="font-size:8px;color:#64748b;">PnL</div></div>';
      h += '<div style="background:#334155;padding:6px 12px;border-radius:6px;text-align:center;flex:1;min-width:60px;"><div style="font-size:18px;font-weight:800;">' + ((stats.profit_factor||0).toFixed(2)) + '</div><div style="font-size:8px;color:#64748b;">Profit Factor</div></div>';
      h += '</div>';

      // Equity curve
      if (item.equity_curve && item.equity_curve.length > 1) {
        h += '<div style="margin:8px 0;"><canvas id="eqCanvas" width="500" height="120"></canvas></div>';
      }

      // Recent trades
      h += '<div style="font-size:10px;color:#f59e0b;margin:6px 0 3px;">\u{1F4CB} \u0622\u062E\u0631\u06CC\u0646 \u0645\u0639\u0627\u0645\u0644\u0627\u062A:</div>';
      h += '<table style="width:100%;font-size:9px;"><thead><tr><th>\u0646\u0645\u0627\u062F</th><th>\u062C\u0647\u062A</th><th>\u0648\u0631\u0648\u062F</th><th>PnL</th><th>\u0646\u062A\u06CC\u062C\u0647</th><th>\u062A\u0627\u0631\u06CC\u062E</th></tr></thead><tbody>';
      trades.slice(-10).reverse().forEach(function(t) {
        var pc = (t.pnl_usd||0) >= 0 ? '#22c55e' : '#ef4444';
        h += '<tr>';
        h += '<td>' + (t.symbol||sym) + '</td>';
        h += '<td style="color:' + (t.direction==='BUY'?'#22c55e':'#ef4444') + ';">' + (t.direction||'') + '</td>';
        h += '<td>' + (t.entry_price||'') + '</td>';
        h += '<td style="color:' + pc + ';font-weight:700;">' + ((t.pnl_usd||0)>=0?'+':'') + (t.pnl_usd||0) + '$</td>';
        h += '<td>' + (t.outcome==='win'?'\u2705':'\u274C') + '</td>';
        h += '<td>' + (t.opened_at||'').substring(0,10) + '</td>';
        h += '</tr>';
      });
      h += '</tbody></table>';

      body.innerHTML = '<h3 style="color:#f59e0b;font-size:13px;margin-bottom:8px;">' + (item.strategy_name||sid) + ' <span style="font-size:10px;color:#64748b;">(' + sym + ')</span></h3>' + h;

      // Draw equity curve
      if (item.equity_curve && item.equity_curve.length > 1) {
        setTimeout(function(){ drawEquity(item.equity_curve); }, 100);
      }

      // Scroll to detail
      detailCard.scrollIntoView({behavior:'smooth', block:'nearest'});
    }
  } catch(e) {
    console.error('Strategy detail error:', e);
  }
};

function drawEquity(curve) {
  var canvas = document.getElementById('eqCanvas');
  if (!canvas) return;
  var ctx = canvas.getContext('2d');
  var w = canvas.width, h = canvas.height;
  ctx.clearRect(0, 0, w, h);

  var min = Math.min.apply(null, curve);
  var max = Math.max.apply(null, curve);
  var range = max - min || 1;

  // Background
  ctx.fillStyle = 'rgba(255,255,255,.02)';
  ctx.fillRect(0, 0, w, h);

  // Zero line
  var zeroY = h - ((0 - min) / range) * (h - 10) - 5;
  ctx.strokeStyle = 'rgba(255,255,255,.05)';
  ctx.setLineDash([3, 3]);
  ctx.beginPath();
  ctx.moveTo(0, zeroY);
  ctx.lineTo(w, zeroY);
  ctx.stroke();
  ctx.setLineDash([]);

  // Curve
  ctx.strokeStyle = curve[curve.length-1] >= 0 ? '#22c55e' : '#ef4444';
  ctx.lineWidth = 2;
  ctx.beginPath();
  curve.forEach(function(v, i) {
    var x = (i / (curve.length - 1)) * w;
    var y = h - ((v - min) / range) * (h - 10) - 5;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // Fill
  ctx.lineTo(w, h);
  ctx.lineTo(0, h);
  ctx.closePath();
  ctx.fillStyle = curve[curve.length-1] >= 0 ? 'rgba(34,197,94,.05)' : 'rgba(239,68,68,.05)';
  ctx.fill();
}

// ══════ OVERRIDE: Replace original ranking load ══════
// Override the global functions
waitForTable(function() {
  // Override allRanking and renderTable globally
  window.allRanking = _allRanking;
  window.renderTable = renderRankingTable;
  
  // Kill any existing ranking interval and re-init
  loadRanking('win_rate');
  
  // Override loadRanking globally  
  window.loadRanking = loadRanking;
  
  // Patch sort dropdown if exists
  var sortSel = document.querySelector('#rankSort, select[onchange*="loadRanking"], select[onchange*="renderTable"]');
  if (sortSel) {
    sortSel.onchange = function() { loadRanking(this.value); };
  }
});

})();
