/* ═══════════════════════════════════════════════════════════════
   Whilber-AI Chart Engine — Sprint 1.1
   TradingView Lightweight Charts + Strategy Trade Markers
   ═══════════════════════════════════════════════════════════════ */

(function(){
"use strict";

// ── State ──
let chart = null;
let candleSeries = null;
let volumeSeries = null;
let tradeMarkers = [];
let slLine = null;
let tpLine = null;
let entryLine = null;
let currentSymbol = "";
let currentTF = "";
let chartContainer = null;
let isLoading = false;
let autoRefreshTimer = null;
let _lastCandleData = [];

// ── Colors ──
const C = {
  bg: "#0a0c10", grid: "#1a1e2a", border: "#2a2f42",
  text: "#8892a8", textLight: "#e8ecf4",
  green: "#22c55e", red: "#ef4444", cyan: "#06b6d4",
  yellow: "#f59e0b", purple: "#a855f7",
  greenAlpha: "rgba(34,197,94,0.15)", redAlpha: "rgba(239,68,68,0.15)",
  volGreen: "rgba(34,197,94,0.3)", volRed: "rgba(239,68,68,0.3)",
};

// ═══ INIT ═══
window.WhilberChart = {
  init: initChart,
  update: updateChart,
  destroy: destroyChart,
  loadTrades: loadTrades,
  setLines: setLines,
  getState: () => ({ symbol: currentSymbol, tf: currentTF, candleSeries, chart, lastData: _lastCandleData }),
};

function initChart(containerId, symbol, tf) {
  chartContainer = document.getElementById(containerId);
  if (!chartContainer) { console.error("Chart container not found:", containerId); return; }
  
  // Load library if not loaded
  if (typeof LightweightCharts === "undefined") {
    const s = document.createElement("script");
    s.src = "https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js";
    s.onload = () => _createChart(symbol, tf);
    s.onerror = () => {
      // Fallback CDN
      const s2 = document.createElement("script");
      s2.src = "https://cdn.jsdelivr.net/npm/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js";
      s2.onload = () => _createChart(symbol, tf);
      document.head.appendChild(s2);
    };
    document.head.appendChild(s);
  } else {
    _createChart(symbol, tf);
  }
}

function _createChart(symbol, tf) {
  if (chart) chart.remove();
  
  const w = chartContainer.clientWidth || 800;
  const h = Math.min(chartContainer.clientHeight || 350, 400);
  
  chart = LightweightCharts.createChart(chartContainer, {
    width: w, height: h,
    layout: {
      background: { type: "solid", color: C.bg },
      textColor: C.text,
      fontSize: 11,
      fontFamily: "'JetBrains Mono', 'Vazirmatn', monospace",
    },
    grid: {
      vertLines: { color: C.grid, style: 1 },
      horzLines: { color: C.grid, style: 1 },
    },
    crosshair: {
      mode: 0,
      vertLine: { color: C.cyan, width: 1, style: 2, labelBackgroundColor: C.cyan },
      horzLine: { color: C.cyan, width: 1, style: 2, labelBackgroundColor: C.cyan },
    },
    rightPriceScale: {
      borderColor: C.border,
      scaleMargins: { top: 0.05, bottom: 0.18 },
    },
    timeScale: {
      borderColor: C.border,
      timeVisible: true,
      secondsVisible: false,
      rightOffset: 5,
      barSpacing: 8,
    },
    watermark: {
      visible: true,
      text: "",
      fontSize: 18,
      color: "rgba(0,212,255,0.08)",
    },
  });
  
  // Candle series
  candleSeries = chart.addCandlestickSeries({
    upColor: C.green, downColor: C.red,
    borderUpColor: C.green, borderDownColor: C.red,
    wickUpColor: C.green, wickDownColor: C.red,
  });
  
  // Volume series
  volumeSeries = chart.addHistogramSeries({
    priceFormat: { type: "volume" },
    priceScaleId: "vol",
    scaleMargins: { top: 0.85, bottom: 0 },
  });
  chart.priceScale("vol").applyOptions({
    scaleMargins: { top: 0.85, bottom: 0 },
  });
  
  // Responsive
  const ro = new ResizeObserver(entries => {
    for (let e of entries) {
      const { width, height } = e.contentRect;
      if (width > 0 && height > 0) chart.resize(width, height);
    }
  });
  ro.observe(chartContainer);
  
  updateChart(symbol, tf);
}

// ═══ UPDATE CHART ═══
async function updateChart(symbol, tf) {
  if (!chart || !candleSeries) return; if (isLoading) { setTimeout(function(){ updateChart(symbol, tf); }, 500); return; }
  symbol = (symbol || currentSymbol || '').toUpperCase(); if (!symbol) return;
  if (!tf) tf = currentTF;
  if (!symbol) return;
  
  isLoading = true;
  currentSymbol = symbol.toUpperCase();
  currentTF = tf.toUpperCase();
  
  // Update watermark
  chart.applyOptions({
    watermark: { text: currentSymbol + " · " + currentTF, visible: true }
  });
  
  // Show loading
  _showLoading(true);
  
  try {
    const resp = await fetch(`/api/candles/${currentSymbol}/${currentTF}?limit=500`);
    const data = await resp.json();
    
    if (data.candles && data.candles.length > 0) {
      _lastCandleData = data.candles;
      candleSeries.setData(data.candles);

      // Volume with colors
      const volData = data.candles.map(c => ({
        time: c.time,
        value: c.volume,
        color: c.close >= c.open ? C.volGreen : C.volRed,
      }));
      volumeSeries.setData(volData);
      
      // Fit content
      chart.timeScale().fitContent();
      
      // Load trades for this symbol
      loadTrades(currentSymbol, currentTF);
    }
  } catch(e) {
    console.error("Chart load error:", e);
  }
  
  _showLoading(false);
  isLoading = false;
  
  // Auto-refresh
  _startAutoRefresh();
}

// ═══ AUTO REFRESH (new candles) ═══
function _startAutoRefresh() {
  if (autoRefreshTimer) clearInterval(autoRefreshTimer);
  
  // Refresh interval based on TF
  const intervals = { M1:10000, M5:15000, M15:30000, M30:45000, H1:60000, H4:120000, D1:300000 };
  const ms = intervals[currentTF] || 60000;
  
  autoRefreshTimer = setInterval(async () => {
    if (!currentSymbol || isLoading) return;
    try {
      const resp = await fetch(`/api/candles/${currentSymbol}/${currentTF}?limit=5`);
      const data = await resp.json();
      if (data.candles && data.candles.length > 0) {
        // Update only last candles
        for (const c of data.candles) {
          candleSeries.update(c);
          volumeSeries.update({
            time: c.time, value: c.volume,
            color: c.close >= c.open ? C.volGreen : C.volRed,
          });
        }
      }
    } catch(e) {}
  }, ms);
}

// ═══ LOAD STRATEGY TRADES ═══
async function loadTrades(symbol, tf) {
  if (!candleSeries) return;
  
  try {
    let url = `/api/trades/${symbol}?limit=50`;
    if (tf) url += `&tf=${tf}`;
    
    const resp = await fetch(url);
    const data = await resp.json();
    
    // Remove old markers
    _clearTradeMarkers();
    
    if (!data.trades || data.trades.length === 0) return;
    
    const markers = [];
    
    for (const t of data.trades) {
      if (!t.entry_time) continue;
      
      const isBuy = t.direction === "BUY";
      const isWin = t.win || t.result === "win" || t.result === "tp" || (t.pnl && t.pnl > 0);
      
      // Entry marker
      markers.push({
        time: t.entry_time,
        position: isBuy ? "belowBar" : "aboveBar",
        color: isBuy ? C.green : C.red,
        shape: isBuy ? "arrowUp" : "arrowDown",
        text: (t.strategy || "").substring(0, 15) + " " + t.direction,
      });
      
      // Exit marker
      if (t.exit_time && t.exit_time > 0) {
        markers.push({
          time: t.exit_time,
          position: isBuy ? "aboveBar" : "belowBar",
          color: isWin ? C.cyan : C.yellow,
          shape: "circle",
          text: isWin ? "✓ Win" : "✗ Loss",
        });
      }
    }
    
    // Sort by time (required by library)
    markers.sort((a, b) => a.time - b.time);
    
    if (markers.length > 0) {
      candleSeries.setMarkers(markers);
      tradeMarkers = markers;
    }
    
    // Show SL/TP of most recent active trade
    const recent = data.trades[0];
    if (recent && recent.entry_price) {
      setLines(recent.entry_price, recent.sl, recent.tp, recent.direction);
    }
    
    // Update trade count badge
    _updateTradeBadge(data.trades.length);
    
  } catch(e) {
    console.error("Load trades error:", e);
  }
}

// ═══ PRICE LINES (SL/TP/Entry) ═══
function setLines(entry, sl, tp, direction) {
  // Remove old lines
  if (entryLine) { candleSeries.removePriceLine(entryLine); entryLine = null; }
  if (slLine) { candleSeries.removePriceLine(slLine); slLine = null; }
  if (tpLine) { candleSeries.removePriceLine(tpLine); tpLine = null; }
  
  if (entry && entry > 0) {
    entryLine = candleSeries.createPriceLine({
      price: entry, color: C.cyan, lineWidth: 2, lineStyle: 0,
      axisLabelVisible: true,
      title: "⮕ ورود " + (entry || ""),
    });
  }
  
  if (sl && sl > 0) {
    slLine = candleSeries.createPriceLine({
      price: sl, color: C.red, lineWidth: 1, lineStyle: 2,
      axisLabelVisible: true,
      title: "🛑 SL",
    });
  }
  
  if (tp && tp > 0) {
    tpLine = candleSeries.createPriceLine({
      price: tp, color: C.green, lineWidth: 1, lineStyle: 2,
      axisLabelVisible: true,
      title: "✅ TP",
    });
  }
}

// ═══ HELPERS ═══
function _clearTradeMarkers() {
  if (candleSeries) candleSeries.setMarkers([]);
  tradeMarkers = [];
  if (entryLine) { candleSeries.removePriceLine(entryLine); entryLine = null; }
  if (slLine) { candleSeries.removePriceLine(slLine); slLine = null; }
  if (tpLine) { candleSeries.removePriceLine(tpLine); tpLine = null; }
}

function _showLoading(show) {
  let el = document.getElementById("wChartLoading");
  if (!el && chartContainer) {
    el = document.createElement("div");
    el.id = "wChartLoading";
    el.style.cssText = "position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);background:rgba(10,12,16,0.9);color:#00d4ff;padding:12px 24px;border-radius:10px;font-size:13px;font-weight:600;z-index:10;pointer-events:none;display:none;";
    el.textContent = "⏳ بارگذاری چارت...";
    chartContainer.style.position = "relative";
    chartContainer.appendChild(el);
  }
  if (el) el.style.display = show ? "block" : "none";
}

function _updateTradeBadge(count) {
  let badge = document.getElementById("wChartTradeBadge");
  if (badge) {
    badge.textContent = count > 0 ? count + " معامله" : "";
    badge.style.display = count > 0 ? "inline-block" : "none";
  }
}

function destroyChart() {
  if (autoRefreshTimer) clearInterval(autoRefreshTimer);
  if (chart) { chart.remove(); chart = null; }
  candleSeries = null;
  volumeSeries = null;
}



// ═══ MA OVERLAY LINES ═══
let ema20Series = null;
let ema50Series = null;
let ema200Series = null;
let showMAs = true;
let currentPriceLine = null;

window.WhilberChart.loadMAs = loadMAs;
window.WhilberChart.toggleMAs = toggleMAs;
window.WhilberChart.showSignalZone = showSignalZone;
window.WhilberChart.showSetup = showSetup;
window.WhilberChart.updateCurrentPrice = updateCurrentPrice;

async function loadMAs(symbol, tf) {
  if (!chart || !symbol) return;
  symbol = symbol || currentSymbol;
  tf = tf || currentTF;
  
  // Remove old
  if (ema20Series) { chart.removeSeries(ema20Series); ema20Series = null; }
  if (ema50Series) { chart.removeSeries(ema50Series); ema50Series = null; }
  if (ema200Series) { chart.removeSeries(ema200Series); ema200Series = null; }
  
  if (!showMAs) return;
  
  try {
    const resp = await fetch(`/api/indicators/${symbol}/${tf}?limit=500`);
    const data = await resp.json();
    
    if (data.ema20 && data.ema20.length > 0) {
      ema20Series = chart.addLineSeries({
        color: "rgba(0,212,255,0.6)", lineWidth: 1,
        priceLineVisible: false, lastValueVisible: false,
        crosshairMarkerVisible: false,
      });
      ema20Series.setData(data.ema20);
    }
    
    if (data.ema50 && data.ema50.length > 0) {
      ema50Series = chart.addLineSeries({
        color: "rgba(168,85,250,0.6)", lineWidth: 1,
        priceLineVisible: false, lastValueVisible: false,
        crosshairMarkerVisible: false,
      });
      ema50Series.setData(data.ema50);
    }
    
    if (data.ema200 && data.ema200.length > 0) {
      ema200Series = chart.addLineSeries({
        color: "rgba(245,158,11,0.5)", lineWidth: 2, lineStyle: 2,
        priceLineVisible: false, lastValueVisible: false,
        crosshairMarkerVisible: false,
      });
      ema200Series.setData(data.ema200);
    }
  } catch(e) {
    console.error("MA load error:", e);
  }
}

function toggleMAs() {
  showMAs = !showMAs;
  if (showMAs) {
    loadMAs(currentSymbol, currentTF);
  } else {
    if (ema20Series) { chart.removeSeries(ema20Series); ema20Series = null; }
    if (ema50Series) { chart.removeSeries(ema50Series); ema50Series = null; }
    if (ema200Series) { chart.removeSeries(ema200Series); ema200Series = null; }
  }
}

// ═══ SIGNAL ZONE (highlight buy/sell zone on chart) ═══
function showSignalZone(signal, confidence, price) {
  // Update watermark with signal
  if (!chart) return;
  
  var sigText = signal === "BUY" ? "🟢 خرید" : signal === "SELL" ? "🔴 فروش" : "⚪ خنثی";
  var confText = confidence ? " (" + confidence + "%)" : "";
  
  chart.applyOptions({
    watermark: {
      text: currentSymbol + " · " + currentTF + "  " + sigText + confText,
      visible: true,
      fontSize: 18,
      color: signal === "BUY" ? "rgba(34,197,94,0.12)" : signal === "SELL" ? "rgba(239,68,68,0.12)" : "rgba(0,212,255,0.08)",
    }
  });
  
  // Update header badge
  var symEl = document.getElementById("wChartSymbol");
  if (symEl) {
    symEl.style.color = signal === "BUY" ? "#22c55e" : signal === "SELL" ? "#ef4444" : "#00d4ff";
  }
}

// ═══ SHOW SETUP (entry/SL/TP from strategy) ═══
function showSetup(setup) {
  if (!setup || !candleSeries) return;
  
  // Clear old lines
  if (entryLine) { candleSeries.removePriceLine(entryLine); entryLine = null; }
  if (slLine) { candleSeries.removePriceLine(slLine); slLine = null; }
  if (tpLine) { candleSeries.removePriceLine(tpLine); tpLine = null; }
  
  var isBuy = (setup.direction || "").toUpperCase() === "BUY";
  
  if (setup.entry && setup.entry > 0) {
    entryLine = candleSeries.createPriceLine({
      price: setup.entry, color: isBuy ? "#22c55e" : "#ef4444",
      lineWidth: 2, lineStyle: 0,
      axisLabelVisible: true,
      title: "⮕ " + (setup.strategy || "ورود") + " " + (setup.entry || ""),
    });
  }
  
  if (setup.sl && setup.sl > 0) {
    slLine = candleSeries.createPriceLine({
      price: setup.sl, color: "#ef4444",
      lineWidth: 1, lineStyle: 2,
      axisLabelVisible: true,
      title: "🛑 SL " + setup.sl,
    });
  }
  
  if (setup.tp && setup.tp > 0) {
    tpLine = candleSeries.createPriceLine({
      price: setup.tp, color: "#22c55e",
      lineWidth: 1, lineStyle: 2,
      axisLabelVisible: true,
      title: "✅ TP " + setup.tp,
    });
  }
  
  // Also show TP2, TP3 if present
  if (setup.tp2 && setup.tp2 > 0) {
    candleSeries.createPriceLine({
      price: setup.tp2, color: "rgba(34,197,94,0.5)",
      lineWidth: 1, lineStyle: 3,
      axisLabelVisible: true,
      title: "TP2 " + setup.tp2,
    });
  }
  
  // Update setup info panel
  _updateSetupPanel(setup);
}

function _updateSetupPanel(setup) {
  var panel = document.getElementById("wSetupInfo");
  if (!panel) return;
  
  var isBuy = (setup.direction || "").toUpperCase() === "BUY";
  var dir = isBuy ? "🟢 خرید" : "🔴 فروش";
  var dirClass = isBuy ? "buy" : "sell";
  var rr = "";
  
  if (setup.entry && setup.sl && setup.tp) {
    var risk = Math.abs(setup.entry - setup.sl);
    var reward = Math.abs(setup.tp - setup.entry);
    if (risk > 0) rr = "1:" + (reward / risk).toFixed(1);
  }
  
  panel.innerHTML = 
    '<div class="wsetup-card ' + dirClass + '">' +
    '<div class="wsetup-row">' +
    '<span class="wsetup-strat">' + (setup.strategy || "—") + '</span>' +
    '<span class="wsetup-dir">' + dir + '</span>' +
    '</div>' +
    '<div class="wsetup-prices">' +
    '<div><span class="label">ورود</span><span class="val entry">' + (setup.entry || "—") + '</span></div>' +
    '<div><span class="label">🛑 SL</span><span class="val sl">' + (setup.sl || "—") + '</span></div>' +
    '<div><span class="label">✅ TP</span><span class="val tp">' + (setup.tp || "—") + '</span></div>' +
    (rr ? '<div><span class="label">R:R</span><span class="val rr">' + rr + '</span></div>' : '') +
    (setup.confidence ? '<div><span class="label">اطمینان</span><span class="val conf">' + setup.confidence + '%</span></div>' : '') +
    (setup.win_rate ? '<div><span class="label">WR</span><span class="val wr">' + setup.win_rate + '%</span></div>' : '') +
    '</div>' +
    '</div>';
  
  panel.style.display = "block";
}

// ═══ CURRENT PRICE LINE (live) ═══
function updateCurrentPrice(price) {
  if (!candleSeries || !price) return;
  
  if (currentPriceLine) {
    candleSeries.removePriceLine(currentPriceLine);
  }
  
  currentPriceLine = candleSeries.createPriceLine({
    price: price,
    color: "rgba(255,255,255,0.4)",
    lineWidth: 1,
    lineStyle: 3,
    axisLabelVisible: true,
    title: "",
  });
}

})();
