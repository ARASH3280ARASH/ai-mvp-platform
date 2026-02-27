"""
Whilber-AI — Auto Signal Tracker Engine
===========================================
Background thread monitors ALL strategies every cycle.
Detects new signals, records virtual entries, tracks until TP/SL.
Persistent storage survives server restarts.
"""

import json
import os
import time
import copy
import shutil
from datetime import datetime, timezone
from threading import Thread, Lock, Event
from collections import defaultdict

PROJECT_DIR = r"C:\Users\Administrator\Desktop\mvp"
TRACK_DIR = os.path.join(PROJECT_DIR, "track_records")
os.makedirs(TRACK_DIR, exist_ok=True)

STATE_FILE = os.path.join(TRACK_DIR, "tracker_state.json")
ACTIVE_FILE = os.path.join(TRACK_DIR, "active_tracks.json")
STATS_CACHE = os.path.join(TRACK_DIR, "stats_cache.json")

_lock = Lock()
_stop_event = Event()
_tracker_thread = None
_is_running = False

# ══════ ANTI-MASS-TRADE LIMITS ══════
MAX_ACTIVE_TRADES = 150       # Global cap on active tracked trades
MAX_PER_SYMBOL = 8            # Max active trades per symbol
MAX_TRADE_AGE_HOURS = 168     # 7 days — auto-expire old trades
MAX_EVENTS_PER_TRADE = 30     # Cap lifecycle events to save storage

# ══════ PERSISTENT STORAGE ══════

def _safe_save(filepath, data):
    """Save JSON with temp file + retry to avoid lock conflicts."""
    import tempfile
    for attempt in range(3):
        try:
            dir_name = os.path.dirname(filepath)
            fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix='.tmp')
            try:
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    json.dump(data, f)
                if os.path.exists(filepath):
                    for _ in range(3):
                        try:
                            os.remove(filepath)
                            break
                        except PermissionError:
                            time.sleep(0.2)
                os.rename(tmp_path, filepath)
                return
            except Exception:
                if os.path.exists(tmp_path):
                    try: os.remove(tmp_path)
                    except: pass
                raise
        except (PermissionError, OSError) as e:
            if attempt < 2:
                time.sleep(0.3 * (attempt + 1))
            else:
                print(f"[TRACKER] Save error {filepath}: {e}")


def _safe_load(filepath):
    """Load JSON with retry to handle file locks."""
    for attempt in range(3):
        try:
            if not os.path.exists(filepath):
                return {}
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (PermissionError, OSError) as e:
            if attempt < 2:
                time.sleep(0.2 * (attempt + 1))
            else:
                print(f"[TRACKER] Load error {filepath}: {e}")
                return {}
        except json.JSONDecodeError:
            print(f"[TRACKER] JSON error {filepath}")
            return {}


def _record_file(strategy_id):
    """Per-strategy record file."""
    safe_id = str(strategy_id).replace("/", "_").replace("\\", "_")[:60]
    return os.path.join(TRACK_DIR, f"rec_{safe_id}.json")


def load_records(strategy_id):
    """Load all trade records for a strategy."""
    data = _safe_load(_record_file(strategy_id))
    return data if data else {"strategy_id": strategy_id, "trades": [], "stats": {}}


def save_records(strategy_id, data):
    """Save trade records for a strategy."""
    _safe_save(_record_file(strategy_id), data)


def load_active():
    """Load all currently active (open) tracked trades."""
    data = _safe_load(ACTIVE_FILE)
    return data if data else {"active": []}


def save_active(data):
    """Save active trades — called frequently."""
    _safe_save(ACTIVE_FILE, data)


def load_state():
    """Load tracker state (last check times, etc)."""
    data = _safe_load(STATE_FILE)
    if data:
        return data
    return {
        "last_cycle": None,
        "total_cycles": 0,
        "total_signals": 0,
        "total_closes": 0,
        "started_at": None,
        "strategy_last_signal": {},
    }


def save_state(state):
    _safe_save(STATE_FILE, state)


# ══════ SIGNAL DETECTION ══════

def detect_signal(df, strategy, indicator_calc_fn):
    """
    Check if strategy conditions are met on current data.
    Returns {signal: bool, type: BUY/SELL, price: float} or None.
    """
    import numpy as np
    n = len(df)
    if n < 10:
        return None

    c = df["close"].values
    entry_conds = strategy.get("entry_conditions", [])
    entry_logic = strategy.get("entry_logic", "AND")

    if not entry_conds:
        return None

    ind_cache = {}
    results = []

    for cond in entry_conds:
        ind_id = cond.get("indicator", "")
        params = cond.get("indicator_params", {})
        key = f"{ind_id}_{hash(str(sorted(params.items())))}"
        if key not in ind_cache and ind_id:
            try:
                ind_cache[key] = indicator_calc_fn(df, ind_id, params)
            except Exception:
                ind_cache[key] = {}

        output = cond.get("output", "value")
        vals = ind_cache.get(key, {}).get(output, np.full(n, np.nan))

        v = vals[-1] if len(vals) > 0 and not np.isnan(vals[-1]) else None
        vp = vals[-2] if len(vals) > 1 and not np.isnan(vals[-2]) else None

        cmp_to = cond.get("compare_to", "fixed_value")
        if cmp_to == "fixed_value":
            cv = float(cond.get("compare_value", 0))
            cvp = cv
        elif cmp_to == "indicator":
            cid = cond.get("compare_indicator", "")
            cp = cond.get("compare_indicator_params", {})
            ck2 = f"{cid}_{hash(str(sorted(cp.items())))}"
            if ck2 not in ind_cache and cid:
                try:
                    ind_cache[ck2] = indicator_calc_fn(df, cid, cp)
                except Exception:
                    ind_cache[ck2] = {}
            co = cond.get("compare_output", "value")
            cvs = ind_cache.get(ck2, {}).get(co, np.full(n, np.nan))
            cv = cvs[-1] if len(cvs) > 0 and not np.isnan(cvs[-1]) else None
            cvp = cvs[-2] if len(cvs) > 1 and not np.isnan(cvs[-2]) else cv
        else:
            cv = c[-1]
            cvp = c[-2] if n > 1 else c[-1]

        met = _check_cond(cond.get("condition", ""), v, cv, vp, cvp)
        results.append(met)

    if not results:
        return None

    signal = all(results) if entry_logic == "AND" else any(results)
    if not signal:
        return None

    direction = strategy.get("direction", "both")
    if direction == "buy_only":
        sig_type = "BUY"
    elif direction == "sell_only":
        sig_type = "SELL"
    else:
        import numpy as np
        sma_vals = indicator_calc_fn(df, "SMA", {"period": min(50, n - 1)}).get("value", np.full(n, np.nan))
        sig_type = "BUY" if (not np.isnan(sma_vals[-1]) and c[-1] > sma_vals[-1]) else "SELL"

    return {
        "signal": True,
        "type": sig_type,
        "price": round(float(c[-1]), 6),
        "time": datetime.now(timezone.utc).isoformat(),
    }


def _check_cond(ct, val, cmp, pv=None, pc=None):
    if val is None or cmp is None:
        return False
    try:
        val, cmp = float(val), float(cmp)
    except (TypeError, ValueError):
        return False
    if ct == "is_above":
        return val > cmp
    elif ct == "is_below":
        return val < cmp
    elif ct == "crosses_above":
        return pv is not None and float(pv) <= float(pc) and val > cmp
    elif ct == "crosses_below":
        return pv is not None and float(pv) >= float(pc) and val < cmp
    elif ct == "is_rising":
        return pv is not None and val > float(pv)
    elif ct == "is_falling":
        return pv is not None and val < float(pv)
    elif ct in ("is_overbought", "is_oversold"):
        return val > cmp if ct == "is_overbought" else val < cmp
    return False


# ══════ TRADE ENTRY RECORDING ══════

def expire_stale_trades():
    """Auto-close trades older than MAX_TRADE_AGE_HOURS. Returns count expired."""
    expired = 0
    now = datetime.now(timezone.utc)
    with _lock:
        active = load_active()
        still_active = []
        for trade in active.get("active", []):
            opened_at = trade.get("opened_at", "")
            try:
                opened = datetime.fromisoformat(opened_at.replace("Z", "+00:00"))
                age_hours = (now - opened).total_seconds() / 3600
                if age_hours > MAX_TRADE_AGE_HOURS:
                    # Record as expired
                    pip = _get_pip(trade.get("symbol", "XAUUSD"))
                    tv = _get_tv(trade.get("symbol", "XAUUSD"))
                    trade["status"] = "closed"
                    trade["exit_reason"] = "expired"
                    trade["closed_at"] = now.isoformat()
                    cp = trade.get("current_price", trade["entry_price"])
                    trade["exit_price"] = cp
                    direction = trade.get("direction", "BUY")
                    if direction == "BUY":
                        pnl = (cp - trade["entry_price"]) / pip
                    else:
                        pnl = (trade["entry_price"] - cp) / pip
                    trade["pnl_pips"] = round(pnl, 1)
                    trade["pnl_usd"] = round(pnl * tv * trade.get("lot_size", 0.01), 2)
                    trade["outcome"] = "win" if pnl > 0 else "loss"
                    # Save to records
                    records = load_records(trade["strategy_id"])
                    records["trades"].insert(0, trade)
                    records["trades"] = records["trades"][:500]
                    save_records(trade["strategy_id"], records)
                    expired += 1
                    continue
            except Exception:
                pass
            still_active.append(trade)
        active["active"] = still_active
        active["count"] = len(still_active)
        save_active(active)
    if expired > 0:
        print(f"[TRACKER] Expired {expired} stale trades (>{MAX_TRADE_AGE_HOURS}h old)")
    return expired


def record_entry(strategy_id, strategy_name, category, symbol, timeframe,
                 signal_type, entry_price, sl_price, tp_price,
                 tp2_price=0, tp3_price=0, lot_size=0.01):
    """Record a new virtual trade entry."""
    # ═══ HARD VALIDATION GATE ═══
    try:
        from backend.api.signal_validator import validate_signal
        _sig = {
            "strategy_id": strategy_id,
            "strategy_name": strategy_name,
            "symbol": symbol,
            "signal_type": signal_type,
            "entry_price": entry_price,
            "sl_price": sl_price,
            "tp_price": tp_price,
            "confidence": 50,
        }
        _ok, _reason = validate_signal(_sig)
        if not _ok:
            return None
    except ImportError:
        pass
    # ═══ END GATE ═══

    now = datetime.now(timezone.utc).isoformat()
    trade_id = now.replace(":", "").replace("-", "").replace(".", "")[:20]

    trade = {
        "id": trade_id,
        "strategy_id": strategy_id,
        "strategy_name": strategy_name,
        "category": category,
        "symbol": symbol,
        "timeframe": timeframe,
        "direction": signal_type,
        "entry_price": round(float(entry_price), 6),
        "sl_price": round(float(sl_price), 6),
        "tp1_price": round(float(tp_price), 6) if tp_price else 0,
        "tp2_price": round(float(tp2_price), 6) if tp2_price else 0,
        "tp3_price": round(float(tp3_price), 6) if tp3_price else 0,
        "lot_size": float(lot_size),
        "opened_at": now,
        "status": "active",
        "current_price": float(entry_price),
        "current_pnl_pips": 0,
        "current_pnl_usd": 0,
        "highest_price": float(entry_price),
        "lowest_price": float(entry_price),
        "sl_moved_to_be": False,
        "partial_closes": [],
        "events": [
            {"time": now, "type": "entry", "price": float(entry_price),
             "detail": f"{signal_type} @ {entry_price}"}
        ],
    }

    # Add to active — enforce caps
    with _lock:
        active = load_active()
        active_list = active.get("active", [])

        # ONE trade per strategy
        for existing in active_list:
            if existing.get("strategy_id") == strategy_id:
                return None

        # Global cap
        if len(active_list) >= MAX_ACTIVE_TRADES:
            return None

        # Per-symbol cap
        sym_count = sum(1 for t in active_list if t.get("symbol") == symbol)
        if sym_count >= MAX_PER_SYMBOL:
            return None

        active_list.append(trade)
        active["active"] = active_list
        active["count"] = len(active_list)
        save_active(active)

    return trade


def record_exit(trade_id, exit_price, exit_reason, pip_val=0.0001, tick_val=10.0):
    """Record trade exit and move to history."""
    now = datetime.now(timezone.utc).isoformat()

    with _lock:
        active = load_active()
        trade = None
        remaining = []
        for t in active["active"]:
            if t["id"] == trade_id:
                trade = t
            else:
                remaining.append(t)

        if not trade:
            return None

        # Calculate PnL
        entry = trade["entry_price"]
        exit_p = float(exit_price)
        direction = trade["direction"]

        if direction == "BUY":
            pnl_pips = (exit_p - entry) / pip_val
        else:
            pnl_pips = (entry - exit_p) / pip_val

        pnl_usd = pnl_pips * tick_val * trade["lot_size"]

        # Compute duration
        try:
            opened = datetime.fromisoformat(trade["opened_at"].replace("Z", "+00:00"))
            closed = datetime.fromisoformat(now.replace("Z", "+00:00"))
            duration_min = (closed - opened).total_seconds() / 60
        except Exception:
            duration_min = 0

        trade["status"] = "closed"
        trade["exit_price"] = round(exit_p, 6)
        trade["exit_reason"] = exit_reason
        trade["closed_at"] = now
        trade["pnl_pips"] = round(pnl_pips, 1)
        trade["pnl_usd"] = round(pnl_usd, 2)
        trade["outcome"] = "win" if pnl_usd >= 0 else "loss"
        trade["duration_minutes"] = round(duration_min, 1)
        trade["events"].append({
            "time": now, "type": "exit", "price": exit_p,
            "detail": f"Closed ({exit_reason}) @ {exit_p} | PnL: {pnl_usd:.2f}$"
        })

        # Save to strategy records
        records = load_records(trade["strategy_id"])
        records["trades"].insert(0, trade)
        # Keep last 200 trades per strategy
        records["trades"] = records["trades"][:MAX_TRADES_PER_RECORD]
        save_records(trade["strategy_id"], records)

        # Remove from active
        active["active"] = remaining
        save_active(active)

        # Update state
        state = load_state()
        state["total_closes"] = state.get("total_closes", 0) + 1
        save_state(state)

    return trade


def record_event(trade_id, event_type, price, detail):
    """Record a lifecycle event (BE move, partial close, etc)."""
    now = datetime.now(timezone.utc).isoformat()
    with _lock:
        active = load_active()
        for t in active["active"]:
            if t["id"] == trade_id:
                events = t.get("events", [])
                # Cap events to save storage — keep first 5 (entry) + last N
                if len(events) >= MAX_EVENTS_PER_TRADE:
                    t["events"] = events[:5] + events[-(MAX_EVENTS_PER_TRADE - 6):]
                t["events"].append({
                    "time": now, "type": event_type,
                    "price": float(price), "detail": detail,
                })
                if event_type == "be_move":
                    t["sl_moved_to_be"] = True
                    t["sl_price"] = float(price)
                elif event_type == "partial_close":
                    t["partial_closes"].append({"time": now, "price": float(price)})
                save_active(active)
                return True
    return False


def update_trade_price(trade_id, current_price):
    """Update current price and track high/low."""
    with _lock:
        active = load_active()
        for t in active["active"]:
            if t["id"] == trade_id:
                t["current_price"] = float(current_price)
                t["highest_price"] = max(t.get("highest_price", 0), float(current_price))
                t["lowest_price"] = min(t.get("lowest_price", 999999), float(current_price))
                return True
        # Don't save here — batch save in cycle
    return False


# ══════ RECOVERY (after restart) ══════

def recover_after_restart():
    """
    After server restart, check if any active trades hit TP/SL during downtime.
    Uses MT5 historical data to backfill.
    """
    active = load_active()
    if not active["active"]:
        return {"recovered": 0}

    recovered = 0
    try:
        import MetaTrader5 as mt5
        from backend.mt5.mt5_connector import MT5Connector
        connector = MT5Connector.get_instance()
        if not connector.ensure_connected():
            return {"recovered": 0, "error": "MT5 not connected"}

        _BROKER_MAP = {
            "XAUUSD": "XAUUSD+", "XAGUSD": "XAGUSD+", "EURUSD": "EURUSD+",
            "GBPUSD": "GBPUSD+", "USDJPY": "USDJPY+", "AUDUSD": "AUDUSD+",
            "USDCAD": "USDCAD+", "NZDUSD": "NZDUSD+", "USDCHF": "USDCHF+",
            "BTCUSD": "BTCUSD", "NAS100": "NAS100", "US30": "DJ30",
        }

        for trade in list(active["active"]):
            symbol = trade.get("symbol", "XAUUSD")
            broker_sym = _BROKER_MAP.get(symbol, symbol)
            opened_at = trade.get("opened_at", "")
            sl = trade.get("sl_price", 0)
            tp1 = trade.get("tp1_price", 0)
            direction = trade.get("direction", "BUY")

            # Get bars since trade opened
            try:
                from datetime import datetime as dt
                start_time = dt.fromisoformat(opened_at.replace("Z", "+00:00"))
                rates = mt5.copy_rates_from(broker_sym, mt5.TIMEFRAME_M1, start_time, 10000)
                if rates is None or len(rates) == 0:
                    continue

                for bar in rates:
                    high = bar["high"]
                    low = bar["low"]

                    # Check SL hit
                    sl_hit = False
                    tp_hit = False
                    if direction == "BUY":
                        if sl > 0 and low <= sl:
                            sl_hit = True
                        if tp1 > 0 and high >= tp1:
                            tp_hit = True
                    else:
                        if sl > 0 and high >= sl:
                            sl_hit = True
                        if tp1 > 0 and low <= tp1:
                            tp_hit = True

                    if sl_hit:
                        pip = _get_pip(symbol)
                        tv = _get_tv(symbol)
                        record_event(trade["id"], "recovery",
                                     sl, "Server was down — SL hit detected from history")
                        record_exit(trade["id"], sl, "sl_recovery", pip, tv)
                        recovered += 1
                        break
                    elif tp_hit:
                        pip = _get_pip(symbol)
                        tv = _get_tv(symbol)
                        record_event(trade["id"], "recovery",
                                     tp1, "Server was down — TP hit detected from history")
                        record_exit(trade["id"], tp1, "tp_recovery", pip, tv)
                        recovered += 1
                        break

            except Exception:
                continue

    except Exception:
        pass

    return {"recovered": recovered}


# ══════ TRACKER STATUS ══════

def get_tracker_status():
    state = load_state()
    active = load_active()
    return {
        "running": _is_running,
        "active_trades": len(active.get("active", [])),
        "total_cycles": state.get("total_cycles", 0),
        "total_signals": state.get("total_signals", 0),
        "total_closes": state.get("total_closes", 0),
        "last_cycle": state.get("last_cycle"),
        "started_at": state.get("started_at"),
    }


def get_active_tracked():
    active = load_active()
    return active.get("active", [])


def get_strategy_records(strategy_id):
    return load_records(strategy_id)


def get_all_strategy_ids():
    """List all strategies that have records."""
    ids = []
    for f in os.listdir(TRACK_DIR):
        if f.startswith("rec_") and f.endswith(".json"):
            sid = f[4:-5]
            ids.append(sid)
    return ids


# ══════ HELPERS ══════

PIP_MAP = {
    "XAUUSD": 0.1, "XAGUSD": 0.01, "EURUSD": 0.0001, "GBPUSD": 0.0001,
    "AUDUSD": 0.0001, "USDCAD": 0.0001, "NZDUSD": 0.0001, "USDCHF": 0.0001,
    "USDJPY": 0.01, "BTCUSD": 1.0, "US30": 1.0, "NAS100": 1.0,
    # Cross-pairs
    "AUDNZD": 0.0001, "EURNZD": 0.0001, "GBPNZD": 0.0001, "GBPCAD": 0.0001,
    "NZDCAD": 0.0001, "GBPAUD": 0.0001, "EURCHF": 0.0001, "EURCAD": 0.0001,
    "CADCHF": 0.0001, "NZDCHF": 0.0001, "AUDCAD": 0.0001, "GBPCHF": 0.0001,
    "EURGBP": 0.0001, "AUDCHF": 0.0001, "EURAUD": 0.0001,
    "CHFJPY": 0.01, "EURJPY": 0.01, "NZDJPY": 0.01, "GBPJPY": 0.01,
    "AUDJPY": 0.01, "CADJPY": 0.01,
}
TV_MAP = {
    "XAUUSD": 1.0, "XAGUSD": 50.0, "EURUSD": 10.0, "GBPUSD": 10.0,
    "AUDUSD": 10.0, "USDCAD": 10.0, "NZDUSD": 10.0, "USDCHF": 10.0,
    "USDJPY": 6.5, "BTCUSD": 1.0, "US30": 1.0, "NAS100": 1.0,
    # Cross-pairs (approximate, denominated in counter currency)
    "AUDNZD": 6.0, "EURNZD": 6.0, "GBPNZD": 6.0, "GBPCAD": 7.5,
    "NZDCAD": 7.5, "GBPAUD": 6.5, "EURCHF": 11.0, "EURCAD": 7.5,
    "CADCHF": 11.0, "NZDCHF": 11.0, "AUDCAD": 7.5, "GBPCHF": 11.0,
    "EURGBP": 12.5, "AUDCHF": 11.0, "EURAUD": 6.5,
    "CHFJPY": 6.5, "EURJPY": 6.5, "NZDJPY": 6.5, "GBPJPY": 6.5,
    "AUDJPY": 6.5, "CADJPY": 6.5,
}

def _get_pip(symbol):
    return PIP_MAP.get(symbol, 0.0001)

def _get_tv(symbol):
    return TV_MAP.get(symbol, 10.0)


# ══════ STORAGE CLEANUP ══════
MAX_TRADES_PER_RECORD = 200   # Per strategy file (was 500)
MAX_RECORD_FILES = 500        # Total record files to keep


def cleanup_storage():
    """Trim trade records and remove oversized files. Returns stats."""
    trimmed = 0
    removed = 0

    # 1. Trim trades per strategy to MAX_TRADES_PER_RECORD
    rec_files = [f for f in os.listdir(TRACK_DIR) if f.startswith("rec_") and f.endswith(".json")]
    for fname in rec_files:
        fpath = os.path.join(TRACK_DIR, fname)
        try:
            data = _safe_load(fpath)
            trades = data.get("trades", [])
            if len(trades) > MAX_TRADES_PER_RECORD:
                data["trades"] = trades[:MAX_TRADES_PER_RECORD]
                _safe_save(fpath, data)
                trimmed += 1
        except Exception:
            continue

    # 2. If too many record files, remove oldest/smallest ones
    if len(rec_files) > MAX_RECORD_FILES:
        # Sort by modification time (oldest first)
        full_paths = [os.path.join(TRACK_DIR, f) for f in rec_files]
        full_paths.sort(key=os.path.getmtime)
        # Remove oldest until under limit
        to_remove = full_paths[:len(rec_files) - MAX_RECORD_FILES]
        for fpath in to_remove:
            try:
                # Only remove if it has < 5 trades (not valuable)
                data = _safe_load(fpath)
                if len(data.get("trades", [])) < 5:
                    os.remove(fpath)
                    removed += 1
            except Exception:
                continue

    if trimmed or removed:
        print(f"[TRACKER] Storage cleanup: trimmed {trimmed} files, removed {removed} files")
    return {"trimmed": trimmed, "removed": removed}
