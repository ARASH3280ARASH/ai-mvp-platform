

# ═══ AUTO-REBUILD CACHE (keeps ranking fresh) ═══
_last_rebuild = 0
_REBUILD_INTERVAL = 300  # seconds (10 min)

def _auto_rebuild_cache():
    """Rebuild ranking cache periodically — inline, reliable."""
    global _last_rebuild
    import time as _time
    now = _time.time()
    if now - _last_rebuild < _REBUILD_INTERVAL:
        return
    _last_rebuild = now
    try:
        import sys, threading
        sys.path.insert(0, r"C:\Users\Administrator\Desktop\mvp")
        def _do_rebuild():
            try:
                from scripts.rebuild_cache import rebuild
                result = rebuild()
                n = len(result.get("ranking", []))
                print(f"[TRACKER] Cache rebuilt: {n} strategies")
            except Exception as e:
                print(f"[TRACKER] Rebuild error: {e}")
        # Run in thread so it doesn't block the cycle
        t = threading.Thread(target=_do_rebuild, daemon=True)
        t.start()
        print("[TRACKER] Cache rebuild started (background thread)")
    except Exception as e:
        print(f"[TRACKER] Cache rebuild error: {e}")
# ═══ END AUTO-REBUILD ═══
"""
Whilber-AI — Tracker Daemon
================================
Background thread: every 10 seconds checks all strategies.
Detects new signals → virtual entry.
Tracks active trades → TP/SL/BE detection → exit.
Periodic disk saves + immediate save on important events.
"""

import time
import traceback
from datetime import datetime, timezone
from threading import Thread, Event

# ═══ MT5 Symbol Mapping ═══
# Broker uses "+" suffix for forex/metals, "DJ30" for US30, BTCUSD/NAS100 stay as-is
_DAEMON_MT5_MAP = {
    "BTCUSD": "BTCUSD", "NAS100": "NAS100", "US30": "DJ30",
}
_DAEMON_MT5_CACHE = {}

def _mt5_sym(s):
    if s in _DAEMON_MT5_CACHE:
        return _DAEMON_MT5_CACHE[s]
    if s in _DAEMON_MT5_MAP:
        _DAEMON_MT5_CACHE[s] = _DAEMON_MT5_MAP[s]
        return _DAEMON_MT5_MAP[s]
    # Try with + suffix (broker convention for forex/metals)
    try:
        import MetaTrader5 as _mt5_check
        if _mt5_check.symbol_info(s + "+"):
            _DAEMON_MT5_CACHE[s] = s + "+"
            return s + "+"
        if _mt5_check.symbol_info(s):
            _DAEMON_MT5_CACHE[s] = s
            return s
    except Exception:
        pass
    _DAEMON_MT5_CACHE[s] = s + "+"  # Default: add + suffix
    return s + "+"
# ═══ END ═══


_stop = Event()
_thread = None
_running = False
_cycle_interval = 30  # seconds — orchestrator needs more time


def start_tracker():
    """Start background tracker thread."""
    global _thread, _running
    if _running:
        return {"success": True, "message": "Already running"}

    _stop.clear()
    _thread = Thread(target=_tracker_loop, daemon=True, name="SignalTracker")
    _thread.start()
    _running = True

    from backend.api.tracker_engine import load_state, save_state
    state = load_state()
    state["started_at"] = datetime.now(timezone.utc).isoformat()
    # Auto-rebuild ranking cache
    try:
        _auto_rebuild_cache()
    except: pass
    save_state(state)

    print("[TRACKER] Started background tracker")
    # Also save running state to file
    try:
        state["running"] = True
        save_state(state)
    except:
        pass
    return {"success": True}


def stop_tracker():
    """Stop background tracker."""
    global _running
    _stop.set()
    _running = False
    # Save final state
    try:
        from backend.api.tracker_engine import load_active, save_active
        save_active(load_active())
    except Exception:
        pass
    print("[TRACKER] Stopped")
    return {"success": True}


def is_running():
    return _running


def _tracker_loop():
    """Main tracker loop — runs continuously, never crashes."""
    global _running
    _running = True
    consecutive_errors = 0
    
    # Recovery on first run — close trades that hit SL/TP during downtime
    try:
        from backend.api.tracker_engine import recover_after_restart
        result = recover_after_restart()
        if result and result.get("recovered", 0) > 0:
            print(f"[TRACKER] Recovered {result['recovered']} trades from downtime")
    except Exception as e:
        print(f"[TRACKER] Recovery check: {e}")
    
    while not _stop.is_set():
        try:
            _run_one_cycle()
            consecutive_errors = 0  # reset on success
        except Exception as e:
            consecutive_errors += 1
            print(f"[TRACKER] Cycle error #{consecutive_errors}: {e}")
            if consecutive_errors > 10:
                print("[TRACKER] Too many errors, sleeping 5 min...")
                _stop.wait(300)
                consecutive_errors = 0
                continue
        
        # Wait for next cycle
        _stop.wait(_cycle_interval)
    
    _running = False
    print("[TRACKER] Loop ended, final save done")

def _run_one_cycle():
    # Alert dispatcher
    try:
        from backend.api.alert_subscription import dispatch_alert as _dispatch
    except ImportError:
        _dispatch = None
    """One cycle: scan signals + track active trades."""
    from backend.api.tracker_engine import (
        load_state, save_state, load_active, save_active,
        record_entry, record_exit, _get_pip, _get_tv,
    )
    state = load_state()
    state["last_cycle"] = datetime.now(timezone.utc).isoformat()
    state["total_cycles"] = state.get("total_cycles", 0) + 1

    # MT5
    try:
        import MetaTrader5 as mt5
        from backend.mt5.mt5_connector import MT5Connector
        conn = MT5Connector.get_instance()
        if not conn.ensure_connected():
            save_state(state)
            return
    except Exception:
        save_state(state)
        return

    # ═══ PART 1: SCAN SIGNALS ═══
    try:
        from backend.api.signal_bridge import scan_all_signals
        from backend.api.signal_validator import validate_batch, reset_cycle, get_stats
        active = load_active()
        active_ids = {t.get("strategy_id","") for t in active.get("active",[])}
        new_sigs = scan_all_signals(state, active_ids)
        # ── Signal Validation ──
        reset_cycle()
        new_sigs = validate_batch(new_sigs)
        if new_sigs:
            print(f"[VALIDATOR] {len(new_sigs)} signals passed validation")
        for sig in new_sigs:
            record_entry(
                strategy_id=sig["strategy_id"],
                strategy_name=sig["strategy_name"],
                category=sig["category"],
                symbol=sig["symbol"],
                timeframe=sig["timeframe"],
                signal_type=sig["signal_type"],
                entry_price=sig["entry_price"],
                sl_price=sig["sl_price"],
                tp_price=sig["tp_price"],
                tp2_price=sig.get("tp2_price", 0),
                tp3_price=sig.get("tp3_price", 0),
                lot_size=0.01,
            )
            state["total_signals"] = state.get("total_signals", 0) + 1
            state.setdefault("strategy_last_signal", {})[sig["strategy_id"]] = datetime.now(timezone.utc).isoformat()
            if _dispatch:
                _dispatch("entry", {
                    "strategy_id": sig["strategy_id"],
                    "strategy_name": sig["strategy_name"],
                    "symbol": sig["symbol"],
                    "direction": sig["signal_type"],
                    "entry_price": sig["entry_price"],
                    "sl_price": sig["sl_price"],
                    "tp1_price": sig["tp_price"],
                    "confidence": sig.get("confidence", 0),
                }, sig.get("reason_fa", ""))
            print(f"[TRACKER] NEW: {sig['strategy_name']} {sig['signal_type']} {sig['symbol']} @ {sig['entry_price']}")
    except Exception as e:
        print(f"[TRACKER] Bridge error: {e}")
        import traceback
        traceback.print_exc()

    # ═══ PART 2: TRACK ACTIVE TRADES ═══
    try:
        from backend.api.lifecycle_manager import process_tick
    except ImportError:
        process_tick = None

    active = load_active()
    for trade in list(active.get("active", [])):
        sym = trade.get("symbol", "XAUUSD")
        direction = trade.get("direction", "BUY")
        pip = _get_pip(sym)
        tv = _get_tv(sym)
        try:
            tick = mt5.symbol_info_tick(_mt5_sym(sym))
            if not tick:
                continue
            cp = tick.ask if direction == "BUY" else tick.bid
        except Exception:
            continue

        if process_tick:
            res = process_tick(trade, cp, tick.bid, tick.ask)
            for ev in res.get("events", []):
                trade.setdefault("events", []).append(ev)
                # Dispatch alert for lifecycle event
                if _dispatch:
                    etype = ev.get("type", "")
                    alert_map = {
                        "be_activated": "be_move", "be_move": "be_move",
                        "near_be": "be_move",
                        "partial_close_1": "partial", "partial_close_2": "partial",
                        "trailing_active": "trailing",
                        "near_tp": "near_tp", "near_sl": "near_sl",
                        "in_profit": "entry",
                        "closed_tp": "closed_tp", "closed_sl": "closed_sl",
                        "closed_trailing": "closed_trailing", "closed_be": "closed_be",
                    }
                    mapped = alert_map.get(etype)
                    if mapped:
                        _dispatch(mapped, trade, ev.get("detail", ""))
            if res.get("closed"):
                record_exit(trade["id"], res["exit_price"], res["exit_reason"], pip, tv)
                continue
        else:
            entry = trade["entry_price"]
            sl = trade["sl_price"]
            tp1 = trade.get("tp1_price", 0)
            trade["current_price"] = cp
            pnl_p = (cp - entry) / pip if direction == "BUY" else (entry - cp) / pip
            trade["current_pnl_pips"] = round(pnl_p, 1)
            trade["current_pnl_usd"] = round(pnl_p * tv * trade.get("lot_size", 0.01), 2)
            if sl > 0 and ((direction == "BUY" and tick.bid <= sl) or (direction == "SELL" and tick.ask >= sl)):
                record_exit(trade["id"], sl, "sl", pip, tv)
                if _dispatch:
                    _dispatch("closed_sl", trade, f"SL hit @ {sl}")
                continue
            if tp1 > 0 and ((direction == "BUY" and tick.bid >= tp1) or (direction == "SELL" and tick.ask <= tp1)):
                record_exit(trade["id"], tp1, "tp", pip, tv)
                if _dispatch:
                    _dispatch("closed_tp", trade, f"TP hit @ {tp1}")
                continue

    save_active(active)

    # ═══ EXPIRE STALE TRADES (every 10 cycles) ═══
    if state.get("total_cycles", 0) % 10 == 0:
        try:
            from backend.api.tracker_engine import expire_stale_trades
            expire_stale_trades()
        except Exception as _exp_err:
            print(f"[TRACKER] Expire error: {_exp_err}")

    # ═══ STORAGE CLEANUP (every 500 cycles ~ every 4 hours) ═══
    if state.get("total_cycles", 0) % 500 == 0 and state.get("total_cycles", 0) > 0:
        try:
            from backend.api.tracker_engine import cleanup_storage
            cleanup_storage()
        except Exception as _clean_err:
            print(f"[TRACKER] Cleanup error: {_clean_err}")

    save_state(state)

def _full_save():
    """Full checkpoint save."""
    try:
        from backend.api.tracker_engine import load_active, save_active, load_state, save_state
        save_active(load_active())
        save_state(load_state())
    except Exception:
        pass


def _calc_sl(strategy, entry, direction, df, symbol):
    """Calculate SL from strategy exit conditions."""
    exits = strategy.get("exit_stop_loss", [])
    pip = {"XAUUSD": 0.1, "USDJPY": 0.01, "BTCUSD": 1.0, "US30": 1.0}.get(symbol, 0.0001)

    for ex in exits:
        ex_type = ex.get("type", "")
        params = ex.get("params", {})

        if ex_type == "fixed_pips":
            pips = float(params.get("pips", 50))
            return entry - pips * pip if direction == "BUY" else entry + pips * pip
        elif ex_type == "atr_multiplier":
            mult = float(params.get("multiplier", 2))
            period = int(params.get("period", 14))
            try:
                from backend.api.indicator_calc import compute_indicator
                import numpy as np
                atr = compute_indicator(df, "ATR", {"period": period})["value"]
                atr_val = atr[-1] if not np.isnan(atr[-1]) else pip * 50
                return entry - atr_val * mult if direction == "BUY" else entry + atr_val * mult
            except Exception:
                return entry - 50 * pip if direction == "BUY" else entry + 50 * pip
        elif ex_type == "percent":
            pct = float(params.get("percent", 1)) / 100
            return entry * (1 - pct) if direction == "BUY" else entry * (1 + pct)

    # Default: 80 pips for gold, 30 for forex
    default_pips = {"XAUUSD": 80, "XAGUSD": 50, "BTCUSD": 500, "US30": 100}.get(symbol, 30)
    return entry - default_pips * pip if direction == "BUY" else entry + default_pips * pip


def _calc_tp(strategy, entry, direction, sl, symbol):
    """Calculate TP from strategy exit conditions."""
    exits = strategy.get("exit_take_profit", [])
    pip = {"XAUUSD": 0.1, "USDJPY": 0.01, "BTCUSD": 1.0, "US30": 1.0}.get(symbol, 0.0001)

    for ex in exits:
        ex_type = ex.get("type", "")
        params = ex.get("params", {})

        if ex_type == "fixed_pips":
            pips = float(params.get("pips", 100))
            return entry + pips * pip if direction == "BUY" else entry - pips * pip
        elif ex_type == "risk_reward":
            rr = float(params.get("ratio", 2))
            sl_dist = abs(entry - sl)
            return entry + sl_dist * rr if direction == "BUY" else entry - sl_dist * rr

    # Default: 2x SL distance
    sl_dist = abs(entry - sl) if sl else 50 * pip
    return entry + sl_dist * 2 if direction == "BUY" else entry - sl_dist * 2


# ═══════════════════════════════════════════════════════════════
# ALERT DISPATCHER HOOKS (appended safely)
# ═══════════════════════════════════════════════════════════════

_alert_dispatch_fn = None

def _get_dispatch():
    global _alert_dispatch_fn
    if _alert_dispatch_fn is None:
        try:
            from backend.api.alert_dispatcher import dispatch_event
            _alert_dispatch_fn = dispatch_event
        except Exception:
            _alert_dispatch_fn = lambda *a, **k: None
    return _alert_dispatch_fn


# Wrap record_exit to dispatch close alerts
if 'record_exit' in dir() or True:
    try:
        _original_record_exit = record_exit

        def record_exit(trade_id, exit_price, exit_reason, pip_value=None, tick_value=None):
            """Wrapped record_exit — dispatches alert after closing trade."""
            result = _original_record_exit(trade_id, exit_price, exit_reason, pip_value, tick_value)
            try:
                # Find the closed trade data
                active = load_active()
                # Trade already moved to records, search there
                import glob as _g
                for fpath in _g.glob(os.path.join(TRACK_DIR, "rec_*.json")):
                    try:
                        with open(fpath, "r", encoding="utf-8") as _f:
                            rec = json.load(_f)
                        for t in reversed(rec.get("trades", [])):
                            if t.get("id") == trade_id:
                                etype = {
                                    "tp": "closed_tp", "sl": "closed_sl",
                                    "trailing": "closed_trailing",
                                    "break_even": "closed_be", "be": "closed_be",
                                }.get(exit_reason, "exit")
                                _get_dispatch()(etype, t)
                                return result
                    except Exception:
                        continue
            except Exception as _e:
                print(f"[ALERT_HOOK] record_exit dispatch error: {_e}")
            return result
    except NameError:
        pass


# Hook into the main tracking loop: dispatch entry + lifecycle events
_last_dispatched_events = {}  # {trade_id: set(event_types)} — avoid duplicates

def _check_and_dispatch_events(trade):
    """Check if trade has new events to dispatch."""
    tid = trade.get("id", "")
    if not tid:
        return
    
    events = trade.get("events", [])
    if not events:
        return
    
    dispatched = _last_dispatched_events.get(tid, set())
    
    for ev in events:
        ev_type = ev.get("type", "")
        ev_time = ev.get("time", "")
        ev_key = f"{ev_type}_{ev_time}"
        
        if ev_key in dispatched:
            continue
        
        # Map lifecycle event types to alert types
        alert_type = {
            "entry": "entry",
            "be_activated": "be_activated",
            "trailing_active": "trailing_active",
            "near_tp": "near_tp",
            "near_sl": "near_sl",
            "in_profit": "in_profit",
            "in_loss": "in_loss",
            "recovery": "recovery",
            "partial_close": "partial_close",
            "closed_tp": "closed_tp",
            "closed_sl": "closed_sl",
            "closed_trailing": "closed_trailing",
            "closed_be": "closed_be",
        }.get(ev_type)
        
        if alert_type:
            try:
                # ═══ ALERT VALIDATION GATE ═══
                _alert_valid = True
                try:
                    from backend.api.signal_validator import validate_signal
                    _asig = {
                        "strategy_id": trade.get("strategy_id", ""),
                        "strategy_name": trade.get("strategy_name", ""),
                        "symbol": trade.get("symbol", ""),
                        "signal_type": trade.get("direction", trade.get("signal_type", "")),
                        "entry_price": trade.get("entry_price", 0),
                        "sl_price": trade.get("sl_price", 0),
                        "tp_price": trade.get("tp1_price", trade.get("tp_price", 0)),
                        "confidence": 50,
                    }
                    _aok, _areason = validate_signal(_asig)
                    if not _aok:
                        _alert_valid = False
                        print(f"[ALERT-GATE] Blocked alert for invalid trade: {trade.get('strategy_name','')} {trade.get('symbol','')} — {_areason}")
                except ImportError:
                    pass  # No validator, allow alert
                # ═══ END ALERT GATE ═══
                if _alert_valid:
                    _get_dispatch()(alert_type, trade)
                dispatched.add(ev_key)
            except Exception:
                pass
    
    _last_dispatched_events[tid] = dispatched
    
    # Cleanup old entries (keep max 2000)
    if len(_last_dispatched_events) > 2000:
        keys = list(_last_dispatched_events.keys())
        for k in keys[:500]:
            _last_dispatched_events.pop(k, None)


# Wrap the main _tracking_cycle if it exists
try:
    if '_run_cycle' in dir():
        _original_run_cycle = _run_cycle
        
        def _run_cycle():
            _original_run_cycle()
            # After cycle, check active trades for new events
            try:
                active = load_active()
                for trade in active.get("active", []):
                    _check_and_dispatch_events(trade)
            except Exception:
                pass
except NameError:
    pass

# ═══ END ALERT HOOKS ═════════════════════════════════════════
