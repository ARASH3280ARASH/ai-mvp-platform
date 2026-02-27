"""
Whilber-AI — Executor Daemon v2.0
====================================
Background loop that:
1. Reads whitelist (top strategies from ranking)
2. Scans signals from signal_bridge
3. Opens positions on MT5 for qualifying signals
4. Manages open positions (BE move, trailing stop)
5. Logs everything

Runs alongside tracker_daemon (tracker = virtual, executor = real).
"""

import json
import os
import time
import sys
from datetime import datetime, timezone, timedelta
from threading import Thread, Event, Lock

PROJECT = r"C:\Users\Administrator\Desktop\mvp"
sys.path.insert(0, PROJECT)

WHITELIST_PATH = os.path.join(PROJECT, "data", "analysis", "whitelist.json")
EXECUTOR_STATE_PATH = os.path.join(PROJECT, "data", "analysis", "executor_state.json")

_stop_event = Event()
_daemon_thread = None
_is_running = False


def load_whitelist():
    """Load whitelist of approved strategies for live trading."""
    try:
        if os.path.exists(WHITELIST_PATH):
            with open(WHITELIST_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    # Default: empty (no strategies approved)
    return {"strategies": [], "updated": None}


def save_executor_state(state):
    """Save executor state."""
    try:
        with open(EXECUTOR_STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def load_executor_state():
    """Load executor state."""
    try:
        if os.path.exists(EXECUTOR_STATE_PATH):
            with open(EXECUTOR_STATE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {
        "started": datetime.now(timezone.utc).isoformat(),
        "cycles": 0,
        "orders_sent": 0,
        "orders_failed": 0,
        "last_cycle": None,
        "daily_loss_usd": 0,
        "daily_loss_reset": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "recent_signals": [],
        "cooldowns": {},
    }


def _run_one_cycle(state):
    """One execution cycle."""
    from backend.executor.mt5_executor import (
        ensure_connected, get_account_info, get_open_positions,
        open_position, modify_position, check_safety,
        move_to_breakeven, calculate_lot, close_all,
    )

    if not ensure_connected():
        print("[EXEC] MT5 not connected, skipping cycle")
        return

    # ── Daily loss reset ──
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if state.get("daily_loss_reset") != today:
        state["daily_loss_usd"] = 0
        state["daily_loss_reset"] = today

    # ── Safety check ──
    safe, reason = check_safety()
    if not safe:
        print(f"[EXEC] SAFETY BLOCK: {reason}")
        if "Drawdown" in reason:
            print("[EXEC] EMERGENCY: Closing all positions!")
            close_all("max_drawdown")
        return

    # ── Load whitelist ──
    whitelist = load_whitelist()
    approved = set(s.get("strategy_id", "") for s in whitelist.get("strategies", []))
    if not approved:
        # No whitelist yet = don't trade
        return

    # ── Get current open positions ──
    open_pos = get_open_positions()
    open_strategy_ids = set()
    for p in open_pos:
        # Extract strategy_id from comment
        cmt = p.get("comment", "")
        if "|" in cmt:
            open_strategy_ids.add(cmt.split("|")[0])

    # ── Scan signals ──
    try:
        from backend.api.signal_bridge import scan_all_signals
        # We pass an empty state dict; bridge uses its own cooldowns
        bridge_state = {}
        signals = scan_all_signals(bridge_state, open_strategy_ids)
    except Exception as e:
        print(f"[EXEC] Bridge error: {e}")
        signals = []

    # ── Filter: only whitelisted + not already open ──
    for sig in signals:
        sid = sig.get("strategy_id", "")
        symbol = sig.get("symbol", "")

        if sid not in approved:
            continue
        if sid in open_strategy_ids:
            continue

        # Cooldown: don't re-enter same strategy+symbol within 4h
        cooldown_key = f"{sid}_{symbol}"
        last_entry = state.get("cooldowns", {}).get(cooldown_key)
        if last_entry:
            try:
                last_dt = datetime.fromisoformat(last_entry)
                if datetime.now(timezone.utc) - last_dt < timedelta(hours=4):
                    continue
            except Exception:
                pass

        # ── Execute! ──
        sl = sig.get("sl_price", 0)
        tp = sig.get("tp_price", sig.get("tp1_price", 0))
        direction = sig.get("signal_type", sig.get("direction", ""))

        if not sl or not tp or not direction:
            continue

        comment = f"{sid}|{direction[:1]}"

        result = open_position(
            symbol=symbol,
            direction=direction,
            sl_price=sl,
            tp_price=tp,
            strategy_id=sid,
            comment=comment,
        )

        if result.get("success"):
            state["orders_sent"] = state.get("orders_sent", 0) + 1
            state["cooldowns"][cooldown_key] = datetime.now(timezone.utc).isoformat()
            print(f"[EXEC] OPENED: {sid} {direction} {symbol} lot={result['lot']} "
                  f"@ {result['price']} SL={sl} TP={tp} RR={result['rr']}")
        else:
            state["orders_failed"] = state.get("orders_failed", 0) + 1
            print(f"[EXEC] FAILED: {sid} {symbol}: {result.get('error', '?')}")

    # ── Manage open positions (BE move) ──
    for pos in open_pos:
        entry = pos["open_price"]
        sl = pos["sl"]
        tp = pos["tp"]
        current_profit = pos["profit"]
        direction = pos["type"]

        # Skip if already at BE or better
        if direction == "BUY" and sl >= entry:
            continue
        if direction == "SELL" and sl > 0 and sl <= entry:
            continue

        # Move to BE when profit reaches 50% of SL distance
        import MetaTrader5 as mt5
        tick = mt5.symbol_info_tick(pos["symbol"])
        if not tick:
            continue

        cp = tick.bid if direction == "BUY" else tick.ask
        sl_dist = abs(entry - sl) if sl > 0 else 0

        if sl_dist > 0:
            if direction == "BUY":
                profit_dist = cp - entry
            else:
                profit_dist = entry - cp

            if profit_dist >= sl_dist * 0.5:
                move_to_breakeven(pos["ticket"])
                print(f"[EXEC] BE MOVE: {pos['symbol']} ticket={pos['ticket']}")

    # ── Update state ──
    state["cycles"] = state.get("cycles", 0) + 1
    state["last_cycle"] = datetime.now(timezone.utc).isoformat()
    save_executor_state(state)


def _daemon_loop():
    """Main daemon loop — runs every 5 seconds."""
    global _is_running
    _is_running = True
    state = load_executor_state()
    print("[EXEC] Executor daemon started")
    print(f"[EXEC] Whitelist: {WHITELIST_PATH}")

    while not _stop_event.is_set():
        try:
            _run_one_cycle(state)
        except Exception as e:
            print(f"[EXEC] Cycle error: {e}")
            import traceback
            traceback.print_exc()

        _stop_event.wait(5)  # 5-second interval

    _is_running = False
    save_executor_state(state)
    print("[EXEC] Executor daemon stopped")


def start_executor():
    """Start executor daemon in background thread."""
    global _daemon_thread, _is_running
    if _is_running:
        return {"status": "already_running"}

    _stop_event.clear()
    _daemon_thread = Thread(target=_daemon_loop, daemon=True, name="executor_daemon")
    _daemon_thread.start()
    return {"status": "started"}


def stop_executor():
    """Stop executor daemon."""
    global _is_running
    _stop_event.set()
    if _daemon_thread:
        _daemon_thread.join(timeout=10)
    _is_running = False
    return {"status": "stopped"}


def get_executor_status():
    """Get executor status for API."""
    from backend.executor.mt5_executor import get_open_positions, get_account_info
    state = load_executor_state()
    positions = get_open_positions()
    acct = get_account_info()
    whitelist = load_whitelist()

    return {
        "running": _is_running,
        "cycles": state.get("cycles", 0),
        "orders_sent": state.get("orders_sent", 0),
        "orders_failed": state.get("orders_failed", 0),
        "last_cycle": state.get("last_cycle"),
        "open_positions": len(positions),
        "positions": positions,
        "balance": acct["balance"] if acct else 0,
        "equity": acct["equity"] if acct else 0,
        "profit": acct["profit"] if acct else 0,
        "whitelist_count": len(whitelist.get("strategies", [])),
    }
