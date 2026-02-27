
# ── Guardian Signal Queue ──────────────────────────────
import json as _json
import os as _os

def queue_signal_for_guardian(signal_data):
    """Write signal to pending_signals.json for Trade Guardian."""
    _sig_file = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "data", "pending_signals.json")
    try:
        existing = []
        if _os.path.exists(_sig_file):
            with open(_sig_file, "r") as _f:
                existing = _json.load(_f)
        existing.append(signal_data)
        with open(_sig_file, "w") as _f:
            _json.dump(existing, _f, indent=2, default=str)
    except:
        pass
# ── End Guardian Hook ──────────────────────────────────

"""
Whilber-AI Signal Bridge v3
"""
from datetime import datetime, timezone

TRACK_SYMBOLS = [
    "AUDCAD",     "AUDCHF",     "AUDJPY",     "AUDNZD",     "AUDUSD",     "BTCUSD",
    "CADCHF",     "CADJPY",     "CHFJPY",     "EURAUD",     "EURCAD",     "EURCHF",
    "EURGBP",     "EURJPY",     "EURNZD",     "EURUSD",     "GBPAUD",     "GBPCAD",
    "GBPCHF",     "GBPJPY",     "GBPNZD",     "GBPUSD",     "NAS100",     "NZDCAD",
    "NZDCHF",     "NZDJPY",     "NZDUSD",     "US30",     "USDCAD",     "USDCHF",
    "USDJPY",     "XAGUSD",     "XAUUSD", 
]

# ═══ MT5 Symbol Mapping (broker uses + suffix and DJ30 for US30) ═══
_MT5_MAP = {
    "XAUUSD": "XAUUSD+",
    "XAGUSD": "XAGUSD+",
    "EURUSD": "EURUSD+",
    "GBPUSD": "GBPUSD+",
    "USDJPY": "USDJPY+",
    "AUDUSD": "AUDUSD+",
    "USDCAD": "USDCAD+",
    "NZDUSD": "NZDUSD+",
    "USDCHF": "USDCHF+",
    "BTCUSD": "BTCUSD",
    "NAS100": "NAS100",
    "US30": "DJ30",
}

def _mt5_name(symbol):
    """Get MT5 broker symbol name."""
    if symbol in _MT5_MAP:
        return _MT5_MAP[symbol]
    # Try with + suffix
    try:
        import MetaTrader5 as mt5
        for candidate in [symbol, symbol + "+", symbol + ".crp"]:
            info = mt5.symbol_info(candidate)
            if info:
                _MT5_MAP[symbol] = candidate  # Cache it
                return candidate
    except:
        pass
    return symbol
# ═══ END MT5 Mapping ═══

TRACK_TIMEFRAMES = ["H1"]
SIGNAL_COOLDOWN = 3600
MAX_SIGNALS_PER_CYCLE = 10  # Hard cap on signals per scan cycle

PIP = {"XAUUSD":0.1,"XAGUSD":0.01,"EURUSD":0.0001,"GBPUSD":0.0001,"AUDUSD":0.0001,"USDCAD":0.0001,"NZDUSD":0.0001,"USDCHF":0.0001,"USDJPY":0.01,"BTCUSD":1.0,"US30":1.0,"NAS100":1.0}
SL_DEFAULT = {"XAUUSD":80,"XAGUSD":50,"BTCUSD":500,"US30":100,"NAS100":100}

def scan_all_signals(state, active_strategy_ids):
    signals = []
    try:
        from backend.strategies.orchestrator import analyze_symbol
    except Exception as e:
        print(f"[BRIDGE] import error: {e}")
        return signals

    last_sigs = state.get("strategy_last_signal", {})

    for symbol in TRACK_SYMBOLS:
        for tf in TRACK_TIMEFRAMES:
            try:
                result = analyze_symbol(symbol, tf)
            except Exception:
                continue
            if not result:
                continue

            for s in result.get("strategies", []):
                sig = s.get("signal", "NEUTRAL")
                if sig not in ("BUY", "SELL"):
                    continue

                # Name: try all possible fields
                name = s.get("strategy_name") or s.get("strategy_name_fa") or s.get("name") or str(s.get("strategy_id", "strat"))
                cat = s.get("category") or s.get("category_fa") or ""
                sid = f"{s.get('strategy_id', name)}_{symbol}_{tf}".replace(" ", "_")

                if sid in active_strategy_ids:
                    continue

                # Cooldown
                lt = last_sigs.get(sid, "")
                if lt:
                    try:
                        ld = datetime.fromisoformat(lt.replace("Z","+00:00"))
                        if (datetime.now(timezone.utc) - ld).total_seconds() < SIGNAL_COOLDOWN:
                            continue
                    except Exception:
                        pass

                conf = s.get("confidence", 0) or 0
                if conf < 50:
                    continue

                # Entry from MT5
                entry = 0
                try:
                    import MetaTrader5 as mt5
                    tick = mt5.symbol_info_tick(_mt5_name(symbol))
                    if tick:
                        entry = tick.ask if sig == "BUY" else tick.bid
                except Exception:
                    pass
                if entry <= 0:
                    continue

                # SL/TP
                sl, tp = _get_sl_tp(symbol, sig, entry, s, result)
                if not sl or not tp:
                    continue

                # Validate direction
                if sig == "BUY" and (sl >= entry or tp <= entry):
                    continue
                if sig == "SELL" and (sl <= entry or tp >= entry):
                    continue

                signals.append({
                    "strategy_id": sid,
                    "strategy_name": name,
                    "category": cat,
                    "symbol": symbol,
                    "timeframe": tf,
                    "signal_type": sig,
                    "entry_price": round(entry, 6),
                    "sl_price": round(sl, 6),
                    "tp_price": round(tp, 6),
                    "tp2_price": 0,
                    "tp3_price": 0,
                    "confidence": conf,
                    "reason_fa": s.get("reason_fa", ""),
                })

                # Hard cap per cycle
                if len(signals) >= MAX_SIGNALS_PER_CYCLE:
                    return signals

    return signals

def _get_sl_tp(symbol, sig, entry, strat, result):
    # Try setup
    setup = strat.get("setup") or {}
    if setup:
        sl = setup.get("sl") or setup.get("stop_loss") or 0
        tp = setup.get("tp1") or setup.get("tp") or setup.get("take_profit") or 0
        if sl and tp:
            return float(sl), float(tp)

    # Try master setup
    try:
        from backend.strategies.setup_calculator import calculate_master_setup
        m = calculate_master_setup(result)
        if m and m.get("valid"):
            sl = m.get("sl", 0)
            tp = m.get("tp1") or m.get("tp") or 0
            if sl and tp:
                return float(sl), float(tp)
    except Exception:
        pass

    # Fallback
    pip = PIP.get(symbol, 0.0001)
    sl_pips = SL_DEFAULT.get(symbol, 30)
    tp_pips = sl_pips * 2
    if sig == "BUY":
        return round(entry - sl_pips * pip, 6), round(entry + tp_pips * pip, 6)
    else:
        return round(entry + sl_pips * pip, 6), round(entry - tp_pips * pip, 6)

def get_tracked_symbols():
    return TRACK_SYMBOLS
def set_tracked_symbols(s):
    global TRACK_SYMBOLS
    TRACK_SYMBOLS = s
def get_tracked_timeframes():
    return TRACK_TIMEFRAMES
def set_tracked_timeframes(t):
    global TRACK_TIMEFRAMES
    TRACK_TIMEFRAMES = t
