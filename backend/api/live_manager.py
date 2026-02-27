"""
Whilber-AI — Live Trade Manager
===================================
Real-time trade tracking with dynamic recommendations.
Updates PnL, milestone progress, trailing suggestions on each tick.
"""

import json
import os
import math
from datetime import datetime, timezone
from threading import Lock

PROJECT_DIR = r"C:\Users\Administrator\Desktop\mvp"
ACTIVE_FILE = os.path.join(PROJECT_DIR, "active_trades.json")
_lock = Lock()


def _load_active():
    try:
        if os.path.exists(ACTIVE_FILE):
            with open(ACTIVE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"trades": []}


def _save_active(data):
    with _lock:
        with open(ACTIVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


try:
    from backend.api.risk_engine import MARKET_SPECS, DEFAULT_SPEC
    MARKET_PIPS = {k: v["pip"] for k, v in MARKET_SPECS.items()}
    TICK_VALUES = {k: v["tick_value_per_lot"] for k, v in MARKET_SPECS.items()}
except ImportError:
    MARKET_PIPS = {"XAUUSD": 0.1, "EURUSD": 0.0001, "GBPUSD": 0.0001, "USDJPY": 0.01, "BTCUSD": 1.0}
    TICK_VALUES = {"XAUUSD": 1.0, "EURUSD": 10.0, "GBPUSD": 10.0, "USDJPY": 6.5, "BTCUSD": 1.0}
    MARKET_SPECS = {}
    DEFAULT_SPEC = {"sessions": []}


# ══════ ACTIVE TRADE MANAGEMENT ══════

def open_trade(email, trade):
    """Register a new active trade for live tracking."""
    data = _load_active()
    now = datetime.now(timezone.utc).isoformat()
    tid = now.replace(":", "").replace("-", "").replace(".", "")[:20]

    entry = {
        "id": tid,
        "email": email,
        "symbol": trade.get("symbol", "XAUUSD"),
        "direction": trade.get("direction", "BUY"),
        "entry_price": float(trade.get("entry_price", 0)),
        "sl_price": float(trade.get("sl_price", 0)),
        "tp1_price": float(trade.get("tp_price", 0)),
        "tp2_price": float(trade.get("tp2_price", 0)),
        "tp3_price": float(trade.get("tp3_price", 0)),
        "lot_size": float(trade.get("lot_size", 0.01)),
        "strategy_name": trade.get("strategy_name", ""),
        "strategy_id": trade.get("strategy_id", ""),
        "opened_at": now,
        "status": "active",
        "sl_moved_to_be": False,
        "partial_closed": [],
        "notes": "",
    }
    data["trades"].insert(0, entry)
    _save_active(data)
    return {"success": True, "trade_id": tid}


def close_trade(email, trade_id, exit_price, exit_reason="manual"):
    """Close an active trade."""
    data = _load_active()
    for t in data["trades"]:
        if t["id"] == trade_id and t["email"] == email:
            t["status"] = "closed"
            t["exit_price"] = float(exit_price)
            t["exit_reason"] = exit_reason
            t["closed_at"] = datetime.now(timezone.utc).isoformat()

            pip = MARKET_PIPS.get(t["symbol"], 0.0001)
            tv = TICK_VALUES.get(t["symbol"], 10.0)
            if t["direction"] == "BUY":
                t["pnl_pips"] = round((float(exit_price) - t["entry_price"]) / pip, 1)
            else:
                t["pnl_pips"] = round((t["entry_price"] - float(exit_price)) / pip, 1)
            t["pnl"] = round(t["pnl_pips"] * tv * t["lot_size"], 2)

            _save_active(data)
            return {"success": True, "pnl": t["pnl"], "pnl_pips": t["pnl_pips"]}
    return {"success": False, "error": "Trade not found"}


def get_active_trades(email):
    data = _load_active()
    return [t for t in data["trades"] if t["email"] == email and t["status"] == "active"]


def get_trade_history(email, limit=50):
    data = _load_active()
    closed = [t for t in data["trades"] if t["email"] == email and t["status"] == "closed"]
    return closed[:limit]


def update_trade_sl(email, trade_id, new_sl):
    """Update SL (for BE move or manual adjustment)."""
    data = _load_active()
    for t in data["trades"]:
        if t["id"] == trade_id and t["email"] == email:
            t["sl_price"] = float(new_sl)
            t["sl_moved_to_be"] = True
            _save_active(data)
            return {"success": True}
    return {"success": False}


def record_partial_close(email, trade_id, pct, price):
    """Record a partial close."""
    data = _load_active()
    for t in data["trades"]:
        if t["id"] == trade_id and t["email"] == email:
            t["partial_closed"].append({
                "pct": pct, "price": float(price),
                "time": datetime.now(timezone.utc).isoformat(),
            })
            _save_active(data)
            return {"success": True}
    return {"success": False}


# ══════ LIVE CALCULATION ══════

def calculate_live(trade, current_price):
    """
    Calculate real-time management data for an active trade.
    Returns PnL, progress, recommendations, milestone status.
    """
    symbol = trade.get("symbol", "XAUUSD")
    direction = trade.get("direction", "BUY")
    entry = float(trade.get("entry_price", 0))
    sl = float(trade.get("sl_price", 0))
    tp1 = float(trade.get("tp1_price", 0) or trade.get("tp_price", 0) or 0)
    tp2 = float(trade.get("tp2_price", 0))
    tp3 = float(trade.get("tp3_price", 0))
    lot = float(trade.get("lot_size", 0.01))
    price = float(current_price)

    pip = MARKET_PIPS.get(symbol, 0.0001)
    tv = TICK_VALUES.get(symbol, 10.0)

    # PnL
    if direction == "BUY":
        pnl_pips = (price - entry) / pip
        sl_dist = (entry - sl) / pip
        tp1_dist = (tp1 - entry) / pip if tp1 > 0 else 0
        dist_to_sl = (price - sl) / pip
        dist_to_tp1 = (tp1 - price) / pip if tp1 > 0 else 0
    else:
        pnl_pips = (entry - price) / pip
        sl_dist = (sl - entry) / pip
        tp1_dist = (entry - tp1) / pip if tp1 > 0 else 0
        dist_to_sl = (sl - price) / pip
        dist_to_tp1 = (price - tp1) / pip if tp1 > 0 else 0

    pnl_usd = pnl_pips * tv * lot
    risk_usd = sl_dist * tv * lot

    # Progress toward TP (0% = at entry, 100% = at TP1)
    total_range = sl_dist + tp1_dist if tp1_dist > 0 else sl_dist * 3
    progress = 0
    if total_range > 0:
        progress = ((pnl_pips + sl_dist) / total_range) * 100
    progress = max(-50, min(150, progress))

    # R:R achieved so far
    rr_current = pnl_pips / sl_dist if sl_dist > 0 else 0

    # Status
    if pnl_pips > 0:
        if rr_current >= 2:
            status = "strong_profit"
            status_fa = "🟢 سود قوی"
            status_color = "#22c55e"
        elif rr_current >= 1:
            status = "profit"
            status_fa = "🟢 در سود"
            status_color = "#22c55e"
        else:
            status = "small_profit"
            status_fa = "🟡 سود جزئی"
            status_color = "#f59e0b"
    elif pnl_pips > -sl_dist * 0.3:
        status = "near_entry"
        status_fa = "🟡 نزدیک ورود"
        status_color = "#f59e0b"
    elif pnl_pips > -sl_dist * 0.7:
        status = "losing"
        status_fa = "🟠 در ضرر"
        status_color = "#f97316"
    else:
        status = "near_sl"
        status_fa = "🔴 نزدیک SL"
        status_color = "#ef4444"

    # Dynamic recommendations
    recommendations = _get_recommendations(
        pnl_pips, sl_dist, tp1_dist, rr_current, direction,
        entry, price, sl, tp1, tp2, tp3, pip, symbol,
        trade.get("sl_moved_to_be", False),
        trade.get("partial_closed", []),
    )

    # Milestone check
    milestones = _check_milestones(
        pnl_pips, sl_dist, tp1_dist, price, entry, sl, tp1, tp2, tp3,
        direction, pip, trade.get("sl_moved_to_be", False),
    )

    # Alert dispatch flags
    should_alert = False
    alert_type = None
    if status == "near_sl":
        should_alert = True
        alert_type = "near_sl"
    elif any(r.get("action") == "close_tp1" for r in recommendations):
        should_alert = True
        alert_type = "tp_reached"
    elif any(r.get("action") == "move_sl_be" and r.get("priority") == "critical" for r in recommendations):
        should_alert = True
        alert_type = "be_suggest"

    return {
        "current_price": price,
        "pnl_pips": round(pnl_pips, 1),
        "pnl_usd": round(pnl_usd, 2),
        "risk_usd": round(risk_usd, 2),
        "rr_current": round(rr_current, 2),
        "progress": round(progress, 1),
        "dist_to_sl": round(dist_to_sl, 1),
        "dist_to_tp1": round(dist_to_tp1, 1) if tp1 > 0 else None,
        "status": status,
        "status_fa": status_fa,
        "status_color": status_color,
        "recommendations": recommendations,
        "milestones": milestones,
        "should_alert": should_alert,
        "alert_type": alert_type,
    }


def _get_session_name(hour):
    """Map UTC hour to session name."""
    if 0 <= hour < 7:
        return "sydney"
    elif 7 <= hour < 9:
        return "tokyo"
    elif 9 <= hour < 12:
        return "london"
    elif 12 <= hour < 16:
        return "newyork"
    elif 16 <= hour < 21:
        return "newyork"
    else:
        return "sydney"


def _get_recommendations(pnl_pips, sl_dist, tp1_dist, rr, direction,
                          entry, price, sl, tp1, tp2, tp3, pip, symbol,
                          be_done, partials):
    """Generate dynamic recommendations based on current state."""
    recs = []
    pct_of_sl = pnl_pips / sl_dist * 100 if sl_dist > 0 else 0

    # Session awareness
    spec = MARKET_SPECS.get(symbol, DEFAULT_SPEC) if MARKET_SPECS else {}
    sessions = spec.get("sessions", [])
    if sessions and "24/7" not in sessions:
        utc_hour = datetime.now(timezone.utc).hour
        current_session = _get_session_name(utc_hour)
        if current_session not in sessions:
            recs.append({
                "priority": "medium",
                "icon": "🕐",
                "title_fa": "خارج از سشن فعال!",
                "detail_fa": f"سشن فعلی ({current_session}) جزو سشن‌های فعال {symbol} نیست ({', '.join(sessions)}). نقدینگی کمتر و اسپرد بالاتر.",
                "action": "wait",
            })

    # Urgency-based BE recommendation
    if not be_done and rr >= 1.5:
        recs.append({
            "priority": "critical",
            "icon": "⚡",
            "title_fa": "فوری: SL به BE ببرید!",
            "detail_fa": f"R:R = {rr:.1f} و هنوز SL جابجا نشده! سود شما در خطر است. فوراً SL به ورود ({entry}) ببرید.",
            "action": "move_sl_be",
            "action_value": entry,
        })
    elif not be_done and pct_of_sl >= 50:
        recs.append({
            "priority": "high",
            "icon": "🟡",
            "title_fa": "SL را به Break Even ببرید!",
            "detail_fa": f"شما {pnl_pips:.0f} پیپ در سود هستید (۵۰%+ فاصله SL). الان SL را به {entry} منتقل کنید تا ریسک صفر شود.",
            "action": "move_sl_be",
            "action_value": entry,
        })
    elif not be_done and pct_of_sl >= 30:
        recs.append({
            "priority": "medium",
            "icon": "💡",
            "title_fa": "نزدیک Break Even",
            "detail_fa": f"هنوز {(50 - pct_of_sl):.0f}% تا نقطه BE فاصله دارید. صبر کنید.",
            "action": "wait",
        })

    # Don't average down warning
    if pnl_pips < 0 and abs(pnl_pips) > sl_dist * 0.5:
        recs.append({
            "priority": "high",
            "icon": "⛔",
            "title_fa": "معامله جدید اضافه نکنید!",
            "detail_fa": f"ضرر فعلی {abs(pnl_pips):.0f} پیپ (بیش از ۵۰% SL). میانگین‌گیری در ضرر ریسک را دو برابر می‌کند.",
            "action": "hold",
        })

    # Partial close recommendations
    partial_pcts = sum(p.get("pct", 0) for p in partials)

    if tp1 > 0 and rr >= 1.0 and partial_pcts < 50:
        if tp2 > 0:
            recs.append({
                "priority": "high",
                "icon": "💰",
                "title_fa": "سیو سود — ⅓ ببندید!",
                "detail_fa": f"R:R به {rr:.1f} رسید. ⅓ حجم ببندید و SL باقی‌مانده به ورود ببرید.",
                "action": "partial_close",
                "action_value": 33,
            })
        else:
            recs.append({
                "priority": "high",
                "icon": "💰",
                "title_fa": "سیو سود — نصف ببندید!",
                "detail_fa": f"R:R به {rr:.1f} رسید. ½ حجم ببندید و SL باقی‌مانده به ورود ببرید.",
                "action": "partial_close",
                "action_value": 50,
            })

    if rr >= 2.0 and partial_pcts < 70:
        recs.append({
            "priority": "high",
            "icon": "🔄",
            "title_fa": "Trailing فعال کنید!",
            "detail_fa": f"R:R = {rr:.1f} عالی است! Trailing Stop فعال کنید تا سود حفظ شود.",
            "action": "activate_trailing",
        })

    # Near SL warning
    near_sl = pnl_pips < 0 and abs(pnl_pips) > sl_dist * 0.8
    if near_sl:
        recs.append({
            "priority": "critical",
            "icon": "🔴",
            "title_fa": "نزدیک حد ضرر!",
            "detail_fa": "قیمت به SL نزدیک شده. SL را جابجا نکنید! اجازه دهید پلن اجرا شود.",
            "action": "hold",
        })

    # TP reached
    tp_reached = False
    if tp1 > 0:
        if direction == "BUY" and price >= tp1:
            tp_reached = True
            recs.append({
                "priority": "critical",
                "icon": "🎯",
                "title_fa": "TP1 فعال شد!",
                "detail_fa": "قیمت به TP1 رسید. طبق پلن سیو سود کنید.",
                "action": "close_tp1",
            })
        elif direction == "SELL" and price <= tp1:
            tp_reached = True
            recs.append({
                "priority": "critical",
                "icon": "🎯",
                "title_fa": "TP1 فعال شد!",
                "detail_fa": "قیمت به TP1 رسید. طبق پلن سیو سود کنید.",
                "action": "close_tp1",
            })

    # If no specific recommendations, give status
    if not recs:
        if pnl_pips >= 0:
            recs.append({
                "priority": "low",
                "icon": "⏳",
                "title_fa": "صبر کنید",
                "detail_fa": "معامله در مسیر درست است. تغییری ندهید. به پلن پایبند باشید.",
                "action": "wait",
            })
        else:
            recs.append({
                "priority": "low",
                "icon": "⏳",
                "title_fa": "صبر — SL جابجا نکنید!",
                "detail_fa": "معامله در ضرر جزئی است. این طبیعی است. به SL اعتماد کنید.",
                "action": "wait",
            })

    # Sort by priority
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    recs.sort(key=lambda r: priority_order.get(r["priority"], 9))
    return recs


def _check_milestones(pnl_pips, sl_dist, tp1_dist, price, entry, sl, tp1, tp2, tp3, direction, pip, be_done):
    """Check which milestones have been reached."""
    ms = []
    pct = pnl_pips / sl_dist * 100 if sl_dist > 0 else 0

    ms.append({"name": "entry", "name_fa": "ورود", "reached": True, "price": entry})
    ms.append({"name": "25pct", "name_fa": "25% مسیر", "reached": pct >= 25, "price": None})
    ms.append({
        "name": "break_even", "name_fa": "Break Even",
        "reached": be_done or pct >= 50,
        "price": entry, "done": be_done,
    })
    ms.append({"name": "75pct", "name_fa": "75% مسیر", "reached": pct >= 75, "price": None})

    if tp1 > 0:
        tp1_reached = (direction == "BUY" and price >= tp1) or (direction == "SELL" and price <= tp1)
        ms.append({"name": "tp1", "name_fa": "TP1", "reached": tp1_reached, "price": tp1})
    if tp2 > 0:
        tp2_reached = (direction == "BUY" and price >= tp2) or (direction == "SELL" and price <= tp2)
        ms.append({"name": "tp2", "name_fa": "TP2", "reached": tp2_reached, "price": tp2})
    if tp3 > 0:
        tp3_reached = (direction == "BUY" and price >= tp3) or (direction == "SELL" and price <= tp3)
        ms.append({"name": "tp3", "name_fa": "TP3", "reached": tp3_reached, "price": tp3})

    sl_reached = (direction == "BUY" and price <= sl) or (direction == "SELL" and price >= sl)
    ms.append({"name": "sl", "name_fa": "SL", "reached": sl_reached, "price": sl})

    return ms
