"""
Whilber-AI — Strategy Monitor & Alerts
==========================================
Monitors saved strategies for live signals.
Generates alerts when entry conditions are met.
"""

import json
import os
import time
from datetime import datetime, timezone
from threading import Thread, Lock

from backend.api.indicator_calc import compute_indicator

PROJECT_DIR = r"C:\Users\Administrator\Desktop\mvp"
ALERTS_FILE = os.path.join(PROJECT_DIR, "strategy_alerts.json")
_lock = Lock()
_monitor_thread = None
_running = False


def _load_alerts():
    try:
        if os.path.exists(ALERTS_FILE):
            with open(ALERTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"alerts": [], "monitors": []}


def _save_alerts(data):
    with _lock:
        with open(ALERTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def _check_cond(ct, val, cmp, pv=None, pc=None):
    if val is None or cmp is None:
        return False
    try:
        val = float(val)
        cmp = float(cmp)
    except (TypeError, ValueError):
        return False
    if ct == "is_above":
        return val > cmp
    elif ct == "is_below":
        return val < cmp
    elif ct == "crosses_above":
        if pv is None:
            return False
        return float(pv) <= float(pc) and val > cmp
    elif ct == "crosses_below":
        if pv is None:
            return False
        return float(pv) >= float(pc) and val < cmp
    elif ct == "is_rising":
        return pv is not None and val > float(pv)
    elif ct == "is_falling":
        return pv is not None and val < float(pv)
    elif ct == "is_overbought":
        return val > cmp
    elif ct == "is_oversold":
        return val < cmp
    return False


def add_monitor(user_email, strategy_id, strategy):
    """Add a strategy to monitoring list."""
    data = _load_alerts()
    # Remove existing
    data["monitors"] = [m for m in data["monitors"]
                        if not (m["email"] == user_email and m["strategy_id"] == strategy_id)]
    data["monitors"].append({
        "email": user_email,
        "strategy_id": strategy_id,
        "strategy_name": strategy.get("name", ""),
        "symbol": strategy.get("symbol", "XAUUSD"),
        "timeframe": strategy.get("timeframe", "H1"),
        "strategy": strategy,
        "active": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_check": None,
        "last_signal": None,
    })
    _save_alerts(data)
    return {"success": True, "message": "Monitor added"}


def remove_monitor(user_email, strategy_id):
    """Remove strategy from monitoring."""
    data = _load_alerts()
    before = len(data["monitors"])
    data["monitors"] = [m for m in data["monitors"]
                        if not (m["email"] == user_email and m["strategy_id"] == strategy_id)]
    if len(data["monitors"]) < before:
        _save_alerts(data)
        return {"success": True}
    return {"success": False, "error": "Monitor not found"}


def toggle_monitor(user_email, strategy_id):
    """Toggle monitor active/inactive."""
    data = _load_alerts()
    for m in data["monitors"]:
        if m["email"] == user_email and m["strategy_id"] == strategy_id:
            m["active"] = not m["active"]
            _save_alerts(data)
            return {"success": True, "active": m["active"]}
    return {"success": False}


def get_monitors(user_email):
    """Get all monitors for a user."""
    data = _load_alerts()
    return [m for m in data["monitors"] if m["email"] == user_email]


def get_alerts(user_email, limit=50):
    """Get recent alerts for a user."""
    data = _load_alerts()
    user_alerts = [a for a in data["alerts"] if a["email"] == user_email]
    user_alerts.sort(key=lambda x: x.get("time", ""), reverse=True)
    return user_alerts[:limit]


def clear_alerts(user_email):
    """Clear all alerts for a user."""
    data = _load_alerts()
    data["alerts"] = [a for a in data["alerts"] if a["email"] != user_email]
    _save_alerts(data)
    return {"success": True}


def check_strategy_signal(df, strategy):
    """Check if strategy conditions are met on current data."""
    import numpy as np
    n = len(df)
    if n < 10:
        return {"signal": False}

    c = df["close"].values
    entry_conds = strategy.get("entry_conditions", [])
    entry_logic = strategy.get("entry_logic", "AND")

    ind_cache = {}
    results = []
    details = []

    for cond in entry_conds:
        ind_id = cond.get("indicator", "")
        params = cond.get("indicator_params", {})
        key = f"{ind_id}_{hash(str(sorted(params.items())))}"
        if key not in ind_cache and ind_id:
            ind_cache[key] = compute_indicator(df, ind_id, params)

        output = cond.get("output", "value")
        vals = ind_cache.get(key, {}).get(output, np.full(n, np.nan))
        v = vals[-1] if not np.isnan(vals[-1]) else None
        vp = vals[-2] if n > 1 and not np.isnan(vals[-2]) else None

        cmp_to = cond.get("compare_to", "fixed_value")
        if cmp_to == "fixed_value":
            cv = float(cond.get("compare_value", 0))
            cvp = cv
        elif cmp_to == "indicator":
            cid = cond.get("compare_indicator", "")
            cp = cond.get("compare_indicator_params", {})
            ck2 = f"{cid}_{hash(str(sorted(cp.items())))}"
            if ck2 not in ind_cache and cid:
                ind_cache[ck2] = compute_indicator(df, cid, cp)
            co = cond.get("compare_output", "value")
            cvs = ind_cache.get(ck2, {}).get(co, np.full(n, np.nan))
            cv = cvs[-1] if not np.isnan(cvs[-1]) else None
            cvp = cvs[-2] if n > 1 and not np.isnan(cvs[-2]) else cv
        else:
            cv = c[-1]
            cvp = c[-2] if n > 1 else c[-1]

        met = _check_cond(cond.get("condition", ""), v, cv, vp, cvp)
        results.append(met)
        details.append({
            "indicator": ind_id,
            "value": round(float(v), 4) if v is not None else None,
            "met": met,
        })

    if results:
        signal = all(results) if entry_logic == "AND" else any(results)
    else:
        signal = False

    # Direction
    direction = strategy.get("direction", "both")
    sig_type = "NONE"
    if signal:
        if direction == "buy_only":
            sig_type = "BUY"
        elif direction == "sell_only":
            sig_type = "SELL"
        else:
            sma = compute_indicator(df, "SMA", {"period": min(50, n - 1)})["value"]
            sig_type = "BUY" if (not np.isnan(sma[-1]) and c[-1] > sma[-1]) else "SELL"

    return {
        "signal": signal,
        "type": sig_type,
        "price": round(float(c[-1]), 5),
        "conditions": details,
    }


def run_monitor_check():
    """Check all active monitors once."""
    data = _load_alerts()
    active = [m for m in data["monitors"] if m.get("active", True)]
    new_alerts = []

    for mon in active:
        strategy = mon.get("strategy", {})
        symbol = mon.get("symbol", "XAUUSD")
        timeframe = mon.get("timeframe", "H1")

        try:
            from backend.mt5.mt5_connector import MT5Connector
            import MetaTrader5 as mt5
            import pandas as pd

            connector = MT5Connector.get_instance()
            if not connector.ensure_connected():
                continue

            tf_map = {
                "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5,
                "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
                "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
                "D1": mt5.TIMEFRAME_D1, "W1": mt5.TIMEFRAME_W1,
            }
            tf = tf_map.get(timeframe.upper(), mt5.TIMEFRAME_H1)
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, 100)
            if rates is None or len(rates) < 10:
                continue

            df = pd.DataFrame(rates)
            df["time"] = pd.to_datetime(df["time"], unit="s")

            result = check_strategy_signal(df, strategy)
            now = datetime.now(timezone.utc).isoformat()
            mon["last_check"] = now

            if result["signal"]:
                # Avoid duplicate alerts (same signal within 1 hour)
                if mon.get("last_signal") and mon["last_signal"] == result["type"]:
                    continue

                mon["last_signal"] = result["type"]
                alert = {
                    "email": mon["email"],
                    "strategy_id": mon["strategy_id"],
                    "strategy_name": mon.get("strategy_name", ""),
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "signal_type": result["type"],
                    "price": result["price"],
                    "time": now,
                    "read": False,
                }
                data["alerts"].insert(0, alert)
                new_alerts.append(alert)
            else:
                mon["last_signal"] = None

        except Exception:
            continue

    # Keep last 200 alerts
    data["alerts"] = data["alerts"][:200]
    _save_alerts(data)
    return new_alerts


def get_alert_count(user_email):
    """Get unread alert count."""
    data = _load_alerts()
    return sum(1 for a in data["alerts"]
               if a["email"] == user_email and not a.get("read", True))


def mark_alerts_read(user_email):
    """Mark all alerts as read."""
    data = _load_alerts()
    for a in data["alerts"]:
        if a["email"] == user_email:
            a["read"] = True
    _save_alerts(data)
    return {"success": True}
