"""
Whilber-AI — Portfolio Risk & Alert Engine
=============================================
Risk Score (0-100), exposure tracking, correlation detection,
real-time price alerts, position summary dashboard.
"""

import json
import os
import math
from datetime import datetime, timezone
from threading import Lock
from collections import defaultdict

PROJECT_DIR = r"C:\Users\Administrator\Desktop\mvp"
ALERTS_FILE = os.path.join(PROJECT_DIR, "risk_alerts.json")
_lock = Lock()

# Import shared market data from risk_engine
try:
    from backend.api.risk_engine import MARKET_SPECS, DEFAULT_SPEC
    MARKET_PIPS = {k: v["pip"] for k, v in MARKET_SPECS.items()}
    TICK_VALUES = {k: v["tick_value_per_lot"] for k, v in MARKET_SPECS.items()}
except ImportError:
    MARKET_PIPS = {"XAUUSD": 0.1, "EURUSD": 0.0001, "GBPUSD": 0.0001, "USDJPY": 0.01, "BTCUSD": 1.0}
    TICK_VALUES = {"XAUUSD": 1.0, "EURUSD": 10.0, "GBPUSD": 10.0, "USDJPY": 6.5, "BTCUSD": 1.0}

# Symbol correlation groups
CORRELATION_GROUPS = {
    "usd_majors": ["EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCHF", "USDCAD"],
    "jpy_pairs": ["USDJPY", "EURJPY", "GBPJPY", "AUDJPY", "CADJPY"],
    "eur_crosses": ["EURGBP", "EURAUD", "EURCAD", "EURCHF", "EURJPY"],
    "gbp_crosses": ["GBPJPY", "GBPAUD", "GBPCAD", "EURGBP"],
    "metals": ["XAUUSD", "XAGUSD"],
    "us_indices": ["US30", "NAS100", "US500"],
    "crypto": ["BTCUSD", "ETHUSD", "SOLUSD"],
}


def _load_alerts():
    try:
        if os.path.exists(ALERTS_FILE):
            with open(ALERTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"alerts": [], "price_alerts": []}


def _save_alerts(data):
    with _lock:
        with open(ALERTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# ══════ RISK SCORE ══════

def calculate_risk_score(profile, active_trades, prices=None):
    """
    Calculate portfolio risk score 0-100.
    0 = extremely risky, 100 = very safe.
    """
    balance = float(profile.get("balance", 10000))
    max_dd = float(profile.get("max_daily_dd_pct", 5))
    max_open = int(profile.get("max_open_trades", 3))
    risk_pct = float(profile.get("risk_pct", 2))
    prices = prices or {}

    if not active_trades:
        return {
            "score": 100, "grade": "A+", "color": "#22c55e",
            "label_fa": "بدون ریسک",
            "details": [], "warnings": [],
        }

    score = 100
    details = []
    warnings = []

    # 1. Number of open trades vs max
    n_open = len(active_trades)
    open_ratio = n_open / max(max_open, 1)
    if open_ratio > 1.0:
        score -= 25
        warnings.append({"type": "critical", "text_fa": f"⛔ {n_open} معامله باز — بیش از حد مجاز ({max_open})"})
    elif open_ratio > 0.8:
        score -= 10
        warnings.append({"type": "warning", "text_fa": f"⚠️ {n_open}/{max_open} معامله باز — نزدیک حد مجاز"})
    details.append({"name_fa": "معاملات باز", "value": f"{n_open}/{max_open}", "score_impact": -int(open_ratio * 15)})

    # 2. Total exposure (risk)
    total_risk = 0
    total_pnl = 0
    by_symbol = defaultdict(lambda: {"count": 0, "direction": [], "risk": 0, "pnl": 0})

    for t in active_trades:
        sym = t.get("symbol", "XAUUSD")
        direction = t.get("direction", "BUY")
        entry = float(t.get("entry_price", 0))
        sl = float(t.get("sl_price", 0))
        lot = float(t.get("lot_size", 0.01))
        pip = MARKET_PIPS.get(sym, 0.0001)
        tv = TICK_VALUES.get(sym, 10.0)

        sl_pips = abs(entry - sl) / pip if sl > 0 and pip > 0 else 50
        risk = sl_pips * tv * lot
        total_risk += risk

        # Live PnL
        cp = prices.get(sym, entry)
        if direction == "BUY":
            pnl = (cp - entry) / pip * tv * lot
        else:
            pnl = (entry - cp) / pip * tv * lot
        total_pnl += pnl

        by_symbol[sym]["count"] += 1
        by_symbol[sym]["direction"].append(direction)
        by_symbol[sym]["risk"] += risk
        by_symbol[sym]["pnl"] += pnl

    risk_pct_actual = total_risk / balance * 100 if balance > 0 else 0
    if risk_pct_actual > max_dd:
        score -= 30
        warnings.append({"type": "critical", "text_fa": f"⛔ ریسک کل {risk_pct_actual:.1f}% — بیش از حد افت روزانه ({max_dd}%)"})
    elif risk_pct_actual > max_dd * 0.7:
        score -= 15
        warnings.append({"type": "warning", "text_fa": f"⚠️ ریسک کل {risk_pct_actual:.1f}% — نزدیک حد مجاز"})
    details.append({"name_fa": "ریسک کل", "value": f"${total_risk:.0f} ({risk_pct_actual:.1f}%)", "score_impact": -int(risk_pct_actual * 3)})

    # 3. Correlation check
    correlated_count = 0
    for group_name, group_syms in CORRELATION_GROUPS.items():
        matching = [s for s in by_symbol if s in group_syms]
        if len(matching) >= 2:
            dirs = []
            for s in matching:
                dirs.extend(by_symbol[s]["direction"])
            same_dir = all(d == dirs[0] for d in dirs)
            if same_dir:
                correlated_count += 1
                score -= 10
                warnings.append({"type": "warning", "text_fa": f"⚠️ معاملات هم‌جهت در گروه {group_name}: {', '.join(matching)}"})

    details.append({"name_fa": "همبستگی", "value": f"{correlated_count} گروه", "score_impact": -correlated_count * 10})

    # 4. Drawdown check
    dd_pct = -total_pnl / balance * 100 if total_pnl < 0 and balance > 0 else 0
    if dd_pct > max_dd * 0.8:
        score -= 20
        warnings.append({"type": "critical", "text_fa": f"⛔ افت فعلی {dd_pct:.1f}% — خیلی نزدیک حد مجاز!"})
    elif dd_pct > max_dd * 0.5:
        score -= 10
        warnings.append({"type": "warning", "text_fa": f"⚠️ افت فعلی {dd_pct:.1f}%"})
    details.append({"name_fa": "افت فعلی", "value": f"{dd_pct:.1f}%", "score_impact": -int(dd_pct * 2)})

    # 5. Single-symbol concentration
    for sym, info in by_symbol.items():
        if info["count"] >= 2:
            warnings.append({"type": "info", "text_fa": f"ℹ️ {info['count']} معامله روی {sym} — تمرکز بالا"})
            score -= 5

    score = max(0, min(100, score))

    if score >= 80:
        grade, color, label = "A", "#22c55e", "امن"
    elif score >= 60:
        grade, color, label = "B", "#f59e0b", "قابل قبول"
    elif score >= 40:
        grade, color, label = "C", "#f97316", "هشدار"
    elif score >= 20:
        grade, color, label = "D", "#ef4444", "خطرناک"
    else:
        grade, color, label = "F", "#dc2626", "بحرانی"

    # Exposure by symbol
    exposure = []
    for sym, info in sorted(by_symbol.items(), key=lambda x: -x[1]["risk"]):
        exposure.append({
            "symbol": sym,
            "count": info["count"],
            "directions": list(set(info["direction"])),
            "risk": round(info["risk"], 2),
            "risk_pct": round(info["risk"] / balance * 100, 2) if balance > 0 else 0,
            "pnl": round(info["pnl"], 2),
        })

    return {
        "score": score,
        "grade": grade,
        "color": color,
        "label_fa": label,
        "total_risk": round(total_risk, 2),
        "total_risk_pct": round(risk_pct_actual, 2),
        "total_pnl": round(total_pnl, 2),
        "open_trades": n_open,
        "exposure": exposure,
        "details": details,
        "warnings": warnings,
    }


# ══════ PRICE ALERTS ══════

def add_price_alert(email, alert):
    """Add a price alert for trade management."""
    data = _load_alerts()
    now = datetime.now(timezone.utc).isoformat()
    alert_entry = {
        "id": now.replace(":", "").replace("-", "")[:18],
        "email": email,
        "trade_id": alert.get("trade_id", ""),
        "symbol": alert.get("symbol", "XAUUSD"),
        "type": alert.get("type", "price_above"),  # price_above, price_below, be_reached, tp_near, sl_near
        "trigger_price": float(alert.get("trigger_price", 0)),
        "message_fa": alert.get("message_fa", ""),
        "action_fa": alert.get("action_fa", ""),
        "priority": alert.get("priority", "medium"),
        "active": True,
        "triggered": False,
        "created_at": now,
    }
    data["price_alerts"].append(alert_entry)
    _save_alerts(data)
    return {"success": True, "alert_id": alert_entry["id"]}


def check_price_alerts(email, prices):
    """Check all active alerts against current prices. Return triggered ones."""
    data = _load_alerts()
    triggered = []

    for alert in data["price_alerts"]:
        if alert["email"] != email or not alert["active"] or alert["triggered"]:
            continue

        sym = alert["symbol"]
        cp = prices.get(sym, 0)
        if cp <= 0:
            continue

        trigger = False
        if alert["type"] == "price_above" and cp >= alert["trigger_price"]:
            trigger = True
        elif alert["type"] == "price_below" and cp <= alert["trigger_price"]:
            trigger = True
        elif alert["type"] == "be_reached":
            trigger = cp >= alert["trigger_price"] if alert.get("direction") == "BUY" else cp <= alert["trigger_price"]
        elif alert["type"] == "tp_near":
            dist = abs(cp - alert["trigger_price"])
            pip = MARKET_PIPS.get(sym, 0.0001)
            if dist / pip <= 20:  # Within 20 pips
                trigger = True
        elif alert["type"] == "sl_near":
            dist = abs(cp - alert["trigger_price"])
            pip = MARKET_PIPS.get(sym, 0.0001)
            if dist / pip <= 15:
                trigger = True

        if trigger:
            alert["triggered"] = True
            alert["triggered_at"] = datetime.now(timezone.utc).isoformat()
            alert["triggered_price"] = cp
            triggered.append(alert)

            # Dispatch to Telegram
            try:
                from backend.api.alert_dispatcher import dispatch_event
                dispatch_event("risk_alert", {
                    "symbol": sym,
                    "alert_type": alert["type"],
                    "message_fa": alert.get("message_fa", ""),
                    "action_fa": alert.get("action_fa", ""),
                    "price": cp,
                    "priority": alert.get("priority", "medium"),
                })
            except Exception:
                pass

            # Add to main alerts
            data["alerts"].insert(0, {
                "email": email,
                "type": "price_alert",
                "priority": alert["priority"],
                "symbol": sym,
                "message_fa": alert["message_fa"],
                "action_fa": alert["action_fa"],
                "price": cp,
                "time": datetime.now(timezone.utc).isoformat(),
                "read": False,
            })

    data["alerts"] = data["alerts"][:300]
    _save_alerts(data)
    return triggered


def auto_create_trade_alerts(email, trade):
    """Auto-create alerts for a trade (BE, near TP, near SL)."""
    sym = trade.get("symbol", "XAUUSD")
    direction = trade.get("direction", "BUY")
    entry = float(trade.get("entry_price", 0))
    sl = float(trade.get("sl_price", 0))
    tp1 = float(trade.get("tp1_price", 0) or trade.get("tp_price", 0) or 0)
    trade_id = trade.get("id", "")
    pip = MARKET_PIPS.get(sym, 0.0001)

    alerts_to_add = []

    # Break Even alert
    if direction == "BUY":
        sl_dist = (entry - sl) / pip
        be_price = entry + sl_dist * 0.5 * pip
    else:
        sl_dist = (sl - entry) / pip
        be_price = entry - sl_dist * 0.5 * pip

    alerts_to_add.append({
        "trade_id": trade_id, "symbol": sym,
        "type": "be_reached", "trigger_price": round(be_price, 6),
        "direction": direction,
        "message_fa": f"🟡 {sym}: قیمت به نقطه Break Even رسید!",
        "action_fa": "SL را به قیمت ورود منتقل کنید.",
        "priority": "high",
    })

    # Near TP alert
    if tp1 > 0:
        alerts_to_add.append({
            "trade_id": trade_id, "symbol": sym,
            "type": "tp_near", "trigger_price": tp1,
            "message_fa": f"🎯 {sym}: نزدیک TP1!",
            "action_fa": "آماده سیو سود باشید.",
            "priority": "high",
        })

    # Near SL alert
    alerts_to_add.append({
        "trade_id": trade_id, "symbol": sym,
        "type": "sl_near", "trigger_price": sl,
        "message_fa": f"🔴 {sym}: نزدیک SL!",
        "action_fa": "SL را جابجا نکنید! به پلن اعتماد کنید.",
        "priority": "critical",
    })

    results = []
    for a in alerts_to_add:
        r = add_price_alert(email, a)
        results.append(r)
    return {"success": True, "alerts_created": len(results)}


def get_risk_alerts(email, limit=50):
    data = _load_alerts()
    user_alerts = [a for a in data["alerts"] if a["email"] == email]
    user_alerts.sort(key=lambda x: x.get("time", ""), reverse=True)
    return user_alerts[:limit]


def get_active_price_alerts(email):
    data = _load_alerts()
    return [a for a in data["price_alerts"]
            if a["email"] == email and a["active"] and not a["triggered"]]


def clear_risk_alerts(email):
    data = _load_alerts()
    data["alerts"] = [a for a in data["alerts"] if a["email"] != email]
    data["price_alerts"] = [a for a in data["price_alerts"] if a["email"] != email]
    _save_alerts(data)
    return {"success": True}


def mark_risk_alerts_read(email):
    data = _load_alerts()
    for a in data["alerts"]:
        if a["email"] == email:
            a["read"] = True
    _save_alerts(data)
    return {"success": True}


def get_unread_count(email):
    data = _load_alerts()
    return sum(1 for a in data["alerts"] if a["email"] == email and not a.get("read", True))


# ══════ PORTFOLIO SUMMARY ══════

def portfolio_summary(profile, active_trades, prices=None):
    """Complete portfolio summary for dashboard widget."""
    prices = prices or {}
    balance = float(profile.get("balance", 10000))

    risk_data = calculate_risk_score(profile, active_trades, prices)

    # PnL breakdown
    total_pnl = 0
    winning = 0
    losing = 0
    trades_info = []

    for t in active_trades:
        sym = t.get("symbol", "XAUUSD")
        direction = t.get("direction", "BUY")
        entry = float(t.get("entry_price", 0))
        lot = float(t.get("lot_size", 0.01))
        pip = MARKET_PIPS.get(sym, 0.0001)
        tv = TICK_VALUES.get(sym, 10.0)
        cp = prices.get(sym, entry)

        if direction == "BUY":
            pnl_pips = (cp - entry) / pip
        else:
            pnl_pips = (entry - cp) / pip
        pnl = pnl_pips * tv * lot
        total_pnl += pnl

        if pnl >= 0:
            winning += 1
        else:
            losing += 1

        trades_info.append({
            "id": t.get("id", ""),
            "symbol": sym,
            "direction": direction,
            "entry": entry,
            "current_price": cp,
            "lot_size": lot,
            "pnl_pips": round(pnl_pips, 1),
            "pnl": round(pnl, 2),
            "strategy_name": t.get("strategy_name", ""),
        })

    trades_info.sort(key=lambda x: x["pnl"], reverse=True)

    return {
        "risk_score": risk_data,
        "balance": balance,
        "equity": round(balance + total_pnl, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl / balance * 100, 2) if balance > 0 else 0,
        "winning_trades": winning,
        "losing_trades": losing,
        "trades": trades_info,
    }
