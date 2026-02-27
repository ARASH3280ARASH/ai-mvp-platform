"""
Whilber-AI — Alert Manager (Phase B — Enhanced)
===================================================
Core alert system: create, store, check, trigger, history.
Centralized hub for all alert types across all pages.

Alert Categories:
  Signal Alerts:
    - signal_change, signal_buy, signal_sell, confidence_high
    - master_active, master_change
  Price Alerts (live market):
    - price_above, price_below
  Trade Tracking Alerts:
    - tp1_hit, tp2_hit, sl_hit
    - trade_update (BE move, partial close, SL adjust, trailing)

Features:
  - Message templates with user customization
  - Multi-channel delivery (Telegram, Email, Desktop popup)
  - Edit / delete / reactivate alerts
  - Simplified setup (email + Telegram only)

Storage: JSON file (alerts.json, notifications.json, alert_templates.json)
"""

import json
import os
import hashlib
from datetime import datetime, timezone
from threading import Lock
from copy import deepcopy

PROJECT_DIR = r"C:\Users\Administrator\Desktop\mvp"
ALERTS_FILE = os.path.join(PROJECT_DIR, "alerts.json")
NOTIFS_FILE = os.path.join(PROJECT_DIR, "notifications.json")
TEMPLATES_FILE = os.path.join(PROJECT_DIR, "alert_templates.json")
USER_CONFIG_FILE = os.path.join(PROJECT_DIR, "alert_user_config.json")
_lock = Lock()


# ═══════════════════════════════════════════════════
# ALERT TYPES (expanded)
# ═══════════════════════════════════════════════════

ALERT_TYPES = {
    # ── Signal Alerts ──
    "signal_change": {
        "name_fa": "تغییر سیگنال",
        "desc_fa": "وقتی جهت سیگنال تغییر کند",
        "icon": "🔄",
        "category": "signal",
        "category_fa": "سیگنال",
    },
    "signal_buy": {
        "name_fa": "سیگنال خرید",
        "desc_fa": "وقتی سیگنال خرید فعال شود",
        "icon": "🟢",
        "category": "signal",
        "category_fa": "سیگنال",
    },
    "signal_sell": {
        "name_fa": "سیگنال فروش",
        "desc_fa": "وقتی سیگنال فروش فعال شود",
        "icon": "🔴",
        "category": "signal",
        "category_fa": "سیگنال",
    },
    "confidence_high": {
        "name_fa": "اطمینان بالا",
        "desc_fa": "وقتی اطمینان بالای ۷۵٪ شود",
        "icon": "⭐",
        "category": "signal",
        "category_fa": "سیگنال",
    },
    "master_active": {
        "name_fa": "ستاپ کلی فعال",
        "desc_fa": "وقتی ستاپ کلی معاملاتی فعال شود",
        "icon": "📋",
        "category": "signal",
        "category_fa": "سیگنال",
    },
    "master_change": {
        "name_fa": "تغییر ستاپ کلی",
        "desc_fa": "وقتی جهت ستاپ کلی عوض شود",
        "icon": "🔀",
        "category": "signal",
        "category_fa": "سیگنال",
    },
    # ── Price Alerts (live market) ──
    "price_above": {
        "name_fa": "قیمت بالاتر از",
        "desc_fa": "وقتی قیمت از سطح مشخصی بالاتر رود",
        "icon": "📈",
        "category": "price",
        "category_fa": "قیمت لحظه‌ای",
    },
    "price_below": {
        "name_fa": "قیمت پایین‌تر از",
        "desc_fa": "وقتی قیمت از سطح مشخصی پایین‌تر رود",
        "icon": "📉",
        "category": "price",
        "category_fa": "قیمت لحظه‌ای",
    },
    # ── Trade Tracking Alerts ──
    "tp1_hit": {
        "name_fa": "رسیدن به TP1",
        "desc_fa": "وقتی قیمت به هدف اول برسد",
        "icon": "✅",
        "category": "trade",
        "category_fa": "معامله",
    },
    "tp2_hit": {
        "name_fa": "رسیدن به TP2",
        "desc_fa": "وقتی قیمت به هدف دوم برسد",
        "icon": "🏆",
        "category": "trade",
        "category_fa": "معامله",
    },
    "sl_hit": {
        "name_fa": "فعال شدن حد ضرر",
        "desc_fa": "وقتی قیمت به حد ضرر برسد",
        "icon": "🛑",
        "category": "trade",
        "category_fa": "معامله",
    },
    "trade_update": {
        "name_fa": "تغییر معامله فعال",
        "desc_fa": "وقتی BE، سیو سود، تغییر SL یا trailing فعال شود",
        "icon": "🔔",
        "category": "trade",
        "category_fa": "معامله",
    },
}


# ═══════════════════════════════════════════════════
# DEFAULT MESSAGE TEMPLATES
# ═══════════════════════════════════════════════════

DEFAULT_TEMPLATES = {
    "signal_change": "{icon} تغییر سیگنال {symbol}\n{strategy}: سیگنال به {direction_fa} تغییر کرد (اطمینان {confidence}%)",
    "signal_buy": "{icon} سیگنال خرید {symbol}\n{strategy}: خرید فعال شد — اطمینان {confidence}%",
    "signal_sell": "{icon} سیگنال فروش {symbol}\n{strategy}: فروش فعال شد — اطمینان {confidence}%",
    "confidence_high": "{icon} اطمینان بالا {symbol}\n{strategy}: اطمینان {confidence}% — سیگنال {direction_fa}",
    "master_active": "{icon} ستاپ کلی فعال {symbol}\nستاپ {direction_fa} — ورود: {entry} SL: {sl} TP1: {tp1}",
    "master_change": "{icon} تغییر ستاپ کلی {symbol}\nستاپ کلی به {direction_fa} تغییر کرد — ورود: {entry}",
    "price_above": "{icon} قیمت {symbol} بالاتر از {target}\nقیمت فعلی: {price}",
    "price_below": "{icon} قیمت {symbol} پایین‌تر از {target}\nقیمت فعلی: {price}",
    "tp1_hit": "{icon} TP1 رسیده {symbol}\nقیمت {price} به هدف اول {target} رسید!",
    "tp2_hit": "{icon} TP2 رسیده {symbol}\nقیمت {price} به هدف دوم {target} رسید!",
    "sl_hit": "{icon} حد ضرر {symbol}\nقیمت {price} به حد ضرر {target} رسید!",
    "trade_update": "{icon} تغییر معامله {symbol}\n{detail}",
}


# ═══════════════════════════════════════════════════
# FILE I/O
# ═══════════════════════════════════════════════════

def _load_json(filepath, default=None):
    if default is None:
        default = {}
    try:
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return deepcopy(default) if isinstance(default, (dict, list)) else default


def _save_json(filepath, data):
    with _lock:
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


# ═══════════════════════════════════════════════════
# USER CONFIG (simplified: email + telegram)
# ═══════════════════════════════════════════════════

def save_user_config(user_email, config):
    """
    Save user delivery config. Only needs email + telegram_chat_id.
    System auto-configures everything else.
    """
    all_cfg = _load_json(USER_CONFIG_FILE, {"users": {}})
    key = user_email.lower()
    all_cfg["users"][key] = {
        "email": user_email.lower(),
        "telegram_chat_id": config.get("telegram_chat_id", ""),
        "channels": {
            "telegram": bool(config.get("telegram_chat_id", "")),
            "email": bool(user_email),
            "popup": config.get("popup", True),
        },
        "quiet_start": config.get("quiet_start", ""),
        "quiet_end": config.get("quiet_end", ""),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_json(USER_CONFIG_FILE, all_cfg)
    return {"success": True}


def get_user_config(user_email):
    """Get user delivery config."""
    all_cfg = _load_json(USER_CONFIG_FILE, {"users": {}})
    key = user_email.lower()
    return all_cfg.get("users", {}).get(key, {
        "email": user_email,
        "telegram_chat_id": "",
        "channels": {"telegram": False, "email": True, "popup": True},
        "quiet_start": "",
        "quiet_end": "",
    })


# ═══════════════════════════════════════════════════
# MESSAGE TEMPLATES
# ═══════════════════════════════════════════════════

def get_templates(user_email=None):
    """Get message templates. Returns user-customized or defaults."""
    data = _load_json(TEMPLATES_FILE, {"templates": {}, "user_templates": {}})
    defaults = deepcopy(DEFAULT_TEMPLATES)
    if user_email:
        user_tpls = data.get("user_templates", {}).get(user_email.lower(), {})
        defaults.update(user_tpls)
    return defaults


def save_template(user_email, alert_type, template_text):
    """Save a user-customized message template for an alert type."""
    if alert_type not in ALERT_TYPES:
        return {"success": False, "error": "نوع هشدار نامعتبر"}
    data = _load_json(TEMPLATES_FILE, {"templates": {}, "user_templates": {}})
    key = user_email.lower()
    if key not in data["user_templates"]:
        data["user_templates"][key] = {}
    data["user_templates"][key][alert_type] = template_text
    _save_json(TEMPLATES_FILE, data)
    return {"success": True}


def reset_template(user_email, alert_type):
    """Reset a template back to default."""
    data = _load_json(TEMPLATES_FILE, {"templates": {}, "user_templates": {}})
    key = user_email.lower()
    if key in data.get("user_templates", {}) and alert_type in data["user_templates"][key]:
        del data["user_templates"][key][alert_type]
        _save_json(TEMPLATES_FILE, data)
    return {"success": True}


def render_template(alert_type, context):
    """Render a message template with context variables."""
    user_email = context.get("user_email", "")
    templates = get_templates(user_email)
    tpl = templates.get(alert_type, DEFAULT_TEMPLATES.get(alert_type, "{icon} {symbol}"))
    try:
        return tpl.format(**context)
    except KeyError:
        # Fallback: return template with whatever we can fill
        for k, v in context.items():
            tpl = tpl.replace("{" + k + "}", str(v))
        return tpl


# ═══════════════════════════════════════════════════
# ALERT CRUD (enhanced)
# ═══════════════════════════════════════════════════

def create_alert(
    user_email,
    symbol,
    timeframe,
    alert_type,
    strategy_id=None,
    target_price=None,
    notes="",
    channels=None,
    custom_message=None,
    repeat=False,
):
    """
    Create a new alert.

    Args:
        user_email: user's email
        symbol: e.g. "XAUUSD"
        timeframe: e.g. "H1" (optional for price alerts)
        alert_type: one of ALERT_TYPES keys
        strategy_id: optional specific strategy (None = master)
        target_price: for price/TP/SL alerts
        notes: user notes
        channels: dict of delivery channels {telegram: bool, email: bool, popup: bool}
        custom_message: user-customized message text (overrides template)
        repeat: if True, alert stays active after triggering

    Returns:
        dict with alert info
    """
    if alert_type not in ALERT_TYPES:
        return {"success": False, "error": f"نوع هشدار نامعتبر: {alert_type}"}

    alert_id = hashlib.md5(
        f"{user_email}{symbol}{alert_type}{strategy_id}{datetime.now().isoformat()}".encode()
    ).hexdigest()[:10]

    type_info = ALERT_TYPES[alert_type]
    # Default channels from user config
    if channels is None:
        ucfg = get_user_config(user_email)
        channels = ucfg.get("channels", {"telegram": False, "email": True, "popup": True})

    alert = {
        "id": alert_id,
        "user_email": user_email.lower(),
        "symbol": symbol.upper(),
        "timeframe": (timeframe or "").upper(),
        "alert_type": alert_type,
        "alert_type_fa": type_info["name_fa"],
        "category": type_info.get("category", "signal"),
        "icon": type_info["icon"],
        "strategy_id": strategy_id,
        "target_price": target_price,
        "notes": notes,
        "channels": channels,
        "custom_message": custom_message,
        "repeat": repeat,
        "active": True,
        "triggered": False,
        "triggered_at": None,
        "trigger_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "last_state": None,
    }

    data = _load_json(ALERTS_FILE, {"alerts": []})
    data["alerts"].append(alert)
    _save_json(ALERTS_FILE, data)

    return {"success": True, "alert_id": alert_id, "alert": alert}


def update_alert(alert_id, user_email, updates):
    """
    Edit an existing alert.

    Args:
        alert_id: alert ID
        user_email: owner email
        updates: dict of fields to update (symbol, target_price, notes, channels, custom_message, repeat)

    Returns:
        dict with success status
    """
    data = _load_json(ALERTS_FILE, {"alerts": []})
    allowed_fields = {"symbol", "timeframe", "target_price", "notes", "channels",
                      "custom_message", "repeat", "active", "strategy_id"}

    for a in data["alerts"]:
        if a["id"] == alert_id and a["user_email"] == user_email.lower():
            for k, v in updates.items():
                if k in allowed_fields:
                    if k == "symbol" and v:
                        v = v.upper()
                    a[k] = v
            a["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save_json(ALERTS_FILE, data)
            return {"success": True, "alert": a}

    return {"success": False, "error": "هشدار پیدا نشد"}


def reactivate_alert(alert_id, user_email):
    """Re-enable a triggered alert so it can fire again."""
    data = _load_json(ALERTS_FILE, {"alerts": []})
    for a in data["alerts"]:
        if a["id"] == alert_id and a["user_email"] == user_email.lower():
            a["active"] = True
            a["triggered"] = False
            a["triggered_at"] = None
            a["last_state"] = None
            a["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save_json(ALERTS_FILE, data)
            return {"success": True, "alert": a}
    return {"success": False, "error": "هشدار پیدا نشد"}


def get_alerts(user_email=None, symbol=None, active_only=True, category=None, include_all=False):
    """Get alerts, optionally filtered."""
    data = _load_json(ALERTS_FILE, {"alerts": []})
    alerts = data.get("alerts", [])

    if user_email:
        alerts = [a for a in alerts if a["user_email"] == user_email.lower()]
    if symbol:
        alerts = [a for a in alerts if a["symbol"] == symbol.upper()]
    if active_only and not include_all:
        alerts = [a for a in alerts if a.get("active", True)]
    if category:
        alerts = [a for a in alerts if a.get("category") == category]

    return alerts


def get_alert_by_id(alert_id, user_email=None):
    """Get single alert by ID."""
    data = _load_json(ALERTS_FILE, {"alerts": []})
    for a in data.get("alerts", []):
        if a["id"] == alert_id:
            if user_email and a["user_email"] != user_email.lower():
                continue
            return a
    return None


def delete_alert(alert_id, user_email=None):
    """Delete an alert by ID."""
    data = _load_json(ALERTS_FILE, {"alerts": []})
    before = len(data["alerts"])
    data["alerts"] = [
        a for a in data["alerts"]
        if not (a["id"] == alert_id and (user_email is None or a["user_email"] == user_email.lower()))
    ]
    _save_json(ALERTS_FILE, data)
    return {"success": len(data["alerts"]) < before}


def toggle_alert(alert_id, user_email=None):
    """Toggle alert active state."""
    data = _load_json(ALERTS_FILE, {"alerts": []})
    for a in data["alerts"]:
        if a["id"] == alert_id:
            if user_email and a["user_email"] != user_email.lower():
                continue
            a["active"] = not a.get("active", True)
            a["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save_json(ALERTS_FILE, data)
            return {"success": True, "active": a["active"]}
    return {"success": False}


def get_alert_stats(user_email):
    """Get alert statistics for user."""
    all_alerts = get_alerts(user_email=user_email, active_only=False, include_all=True)
    active = [a for a in all_alerts if a.get("active")]
    triggered = [a for a in all_alerts if a.get("triggered")]
    by_cat = {}
    for a in active:
        cat = a.get("category", "signal")
        by_cat[cat] = by_cat.get(cat, 0) + 1

    notifs = get_notifications(user_email, limit=200)
    unread = sum(1 for n in notifs if not n.get("read", False))
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_count = sum(1 for n in notifs if (n.get("created_at") or "")[:10] == today)

    return {
        "total_alerts": len(all_alerts),
        "active_alerts": len(active),
        "triggered_alerts": len(triggered),
        "by_category": by_cat,
        "total_notifications": len(notifs),
        "unread": unread,
        "today": today_count,
    }


# ═══════════════════════════════════════════════════
# NOTIFICATION STORAGE
# ═══════════════════════════════════════════════════

def add_notification(user_email, alert_id, title, body, icon="🔔", data_extra=None, channels_used=None):
    """Store a triggered notification for user history."""
    notif = {
        "id": hashlib.md5(f"{alert_id}{datetime.now().isoformat()}".encode()).hexdigest()[:10],
        "user_email": user_email.lower(),
        "alert_id": alert_id,
        "title": title,
        "body": body,
        "icon": icon,
        "read": False,
        "data": data_extra or {},
        "channels_used": channels_used or [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    ndata = _load_json(NOTIFS_FILE, {"notifications": []})
    ndata["notifications"].insert(0, notif)

    # Keep last 500 per user max
    user_notifs = [n for n in ndata["notifications"] if n["user_email"] == user_email.lower()]
    if len(user_notifs) > 500:
        ids_to_keep = set(n["id"] for n in user_notifs[:500])
        ndata["notifications"] = [
            n for n in ndata["notifications"]
            if n["user_email"] != user_email.lower() or n["id"] in ids_to_keep
        ]

    _save_json(NOTIFS_FILE, ndata)
    return notif


def get_notifications(user_email, limit=50, unread_only=False):
    """Get user's notification history."""
    ndata = _load_json(NOTIFS_FILE, {"notifications": []})
    notifs = [n for n in ndata["notifications"] if n["user_email"] == user_email.lower()]
    if unread_only:
        notifs = [n for n in notifs if not n.get("read", False)]
    return notifs[:limit]


def delete_notification(user_email, notif_id):
    """Delete a single notification."""
    ndata = _load_json(NOTIFS_FILE, {"notifications": []})
    before = len(ndata["notifications"])
    ndata["notifications"] = [
        n for n in ndata["notifications"]
        if not (n["id"] == notif_id and n["user_email"] == user_email.lower())
    ]
    _save_json(NOTIFS_FILE, ndata)
    return {"success": len(ndata["notifications"]) < before}


def mark_read(user_email, notif_id=None):
    """Mark notification(s) as read. None = mark all."""
    ndata = _load_json(NOTIFS_FILE, {"notifications": []})
    count = 0
    for n in ndata["notifications"]:
        if n["user_email"] == user_email.lower():
            if notif_id is None or n["id"] == notif_id:
                if not n.get("read", False):
                    n["read"] = True
                    count += 1
    _save_json(NOTIFS_FILE, ndata)
    return {"marked": count}


def get_unread_count(user_email):
    """Get count of unread notifications."""
    ndata = _load_json(NOTIFS_FILE, {"notifications": []})
    return sum(
        1 for n in ndata["notifications"]
        if n["user_email"] == user_email.lower() and not n.get("read", False)
    )


# ═══════════════════════════════════════════════════
# ALERT CHECKER — Check & Trigger (enhanced)
# ═══════════════════════════════════════════════════

def check_price_alerts_live(prices_dict):
    """
    Check live price alerts against current market prices.
    Called periodically with {symbol: price} dict.
    Returns list of triggered notifications.
    """
    if not prices_dict:
        return []

    data = _load_json(ALERTS_FILE, {"alerts": []})
    all_alerts = data.get("alerts", [])
    triggered = []

    for alert in all_alerts:
        if not alert.get("active"):
            continue
        atype = alert["alert_type"]
        if atype not in ("price_above", "price_below"):
            continue

        sym = alert["symbol"]
        target = alert.get("target_price")
        if not target or sym not in prices_dict:
            continue

        price = prices_dict[sym]
        fire = False

        if atype == "price_above" and price >= target:
            fire = True
        elif atype == "price_below" and price <= target:
            fire = True

        if fire:
            icon = ALERT_TYPES[atype]["icon"]
            context = {
                "icon": icon, "symbol": sym, "target": target,
                "price": price, "user_email": alert["user_email"],
            }
            msg = render_template(atype, context)
            title = f"{icon} {ALERT_TYPES[atype]['name_fa']} {sym}"

            # Mark triggered
            alert["triggered"] = True
            alert["triggered_at"] = datetime.now(timezone.utc).isoformat()
            alert["trigger_count"] = alert.get("trigger_count", 0) + 1
            if not alert.get("repeat"):
                alert["active"] = False

            # Deliver via channels
            channels_used = _deliver_alert(alert, title, msg)

            notif = add_notification(
                user_email=alert["user_email"],
                alert_id=alert["id"],
                title=title,
                body=msg,
                icon=icon,
                data_extra={"symbol": sym, "price": price, "target": target, "alert_type": atype},
                channels_used=channels_used,
            )
            notif["alert"] = alert
            triggered.append(notif)

    _save_json(ALERTS_FILE, data)
    return triggered


def check_trade_updates(trade_event):
    """
    Check trade_update alerts when an active trade changes.
    trade_event: {symbol, event_sub_type, detail, user_email, ...}
    """
    symbol = trade_event.get("symbol", "")
    user_email = trade_event.get("user_email", "")
    if not symbol:
        return []

    active_alerts = get_alerts(user_email=user_email or None, symbol=symbol, active_only=True, category="trade")
    update_alerts = [a for a in active_alerts if a["alert_type"] == "trade_update"]
    if not update_alerts:
        return []

    triggered = []
    data = _load_json(ALERTS_FILE, {"alerts": []})

    for alert in update_alerts:
        icon = "🔔"
        detail = trade_event.get("detail", "تغییر در معامله فعال")
        context = {
            "icon": icon, "symbol": symbol, "detail": detail,
            "user_email": alert["user_email"],
        }
        msg = render_template("trade_update", context)
        title = f"{icon} تغییر معامله {symbol}"

        # Mark triggered
        for a in data["alerts"]:
            if a["id"] == alert["id"]:
                a["trigger_count"] = a.get("trigger_count", 0) + 1
                a["triggered_at"] = datetime.now(timezone.utc).isoformat()
                # trade_update alerts stay active (repeat by nature)
                break

        channels_used = _deliver_alert(alert, title, msg)

        notif = add_notification(
            user_email=alert["user_email"],
            alert_id=alert["id"],
            title=title,
            body=msg,
            icon=icon,
            data_extra={
                "symbol": symbol,
                "alert_type": "trade_update",
                "sub_type": trade_event.get("event_sub_type", ""),
            },
            channels_used=channels_used,
        )
        triggered.append(notif)

    _save_json(ALERTS_FILE, data)
    return triggered


def check_alerts(analysis_result):
    """
    Check all active alerts against fresh analysis results.
    Triggers notifications for matched alerts.
    """
    # ═══ ALERT VALIDATION ═══
    try:
        from backend.api.signal_validator import validate_signal
        signals = analysis_result.get("signals", analysis_result.get("strategies", []))
        if isinstance(signals, list):
            valid_signals = []
            for sig in signals:
                _s = {
                    "strategy_id": sig.get("strategy_id", sig.get("name", "")),
                    "strategy_name": sig.get("strategy_name", sig.get("name", "")),
                    "symbol": analysis_result.get("symbol", sig.get("symbol", "")),
                    "signal_type": sig.get("signal", sig.get("signal_type", sig.get("direction", ""))),
                    "entry_price": sig.get("entry_price", sig.get("entry", 0)),
                    "sl_price": sig.get("sl_price", sig.get("sl", 0)),
                    "tp_price": sig.get("tp_price", sig.get("tp", sig.get("tp1", 0))),
                    "confidence": sig.get("confidence", 50),
                }
                ok, reason = validate_signal(_s)
                if ok:
                    valid_signals.append(sig)
            if "signals" in analysis_result:
                analysis_result["signals"] = valid_signals
            elif "strategies" in analysis_result:
                analysis_result["strategies"] = valid_signals
    except ImportError:
        pass
    # ═══ END ALERT VALIDATION ═══

    symbol = analysis_result.get("symbol", "")
    tf = analysis_result.get("timeframe", "")
    price = analysis_result.get("last_close")
    overall = analysis_result.get("overall", {})
    master = analysis_result.get("master_setup", {})
    strategies = analysis_result.get("strategies", [])

    if not symbol or not price:
        return []

    active_alerts = get_alerts(symbol=symbol, active_only=True)
    if not active_alerts:
        return []

    strat_map = {}
    for s in strategies:
        strat_map[s.get("strategy_id", "")] = s

    triggered = []
    data = _load_json(ALERTS_FILE, {"alerts": []})

    for alert in active_alerts:
        # Skip price and trade_update alerts (handled by their own checkers)
        if alert.get("category") == "price" or alert["alert_type"] == "trade_update":
            continue
        if alert.get("timeframe") and alert["timeframe"] != tf:
            continue

        result = _check_single_alert(alert, price, overall, master, strat_map)

        if result:
            for a in data["alerts"]:
                if a["id"] == alert["id"]:
                    a["triggered"] = True
                    a["triggered_at"] = datetime.now(timezone.utc).isoformat()
                    a["trigger_count"] = a.get("trigger_count", 0) + 1
                    a["last_state"] = result.get("new_state")
                    if not a.get("repeat"):
                        a["active"] = False
                    break

            channels_used = _deliver_alert(alert, result["title"], result["body"])

            notif = add_notification(
                user_email=alert["user_email"],
                alert_id=alert["id"],
                title=result["title"],
                body=result["body"],
                icon=alert.get("icon", "🔔"),
                data_extra={
                    "symbol": symbol,
                    "timeframe": tf,
                    "price": price,
                    "alert_type": alert["alert_type"],
                    "strategy_id": alert.get("strategy_id"),
                },
                channels_used=channels_used,
            )
            notif["alert"] = alert
            triggered.append(notif)

    _save_json(ALERTS_FILE, data)
    return triggered


def _check_single_alert(alert, price, overall, master, strat_map):
    """Check a single alert against current data."""
    atype = alert["alert_type"]
    sid = alert.get("strategy_id")
    symbol = alert["symbol"]
    last_state = alert.get("last_state")

    # ── Strategy-specific alerts ──
    if sid and sid in strat_map:
        strat = strat_map[sid]
        sig = strat.get("signal", "NEUTRAL")
        conf = strat.get("confidence", 0)
        name_fa = strat.get("strategy_name_fa", sid)

        if atype == "signal_change":
            if last_state and sig != last_state and sig != "NEUTRAL":
                sig_fa = "خرید" if sig == "BUY" else "فروش"
                context = {"icon": "🔄", "symbol": symbol, "strategy": name_fa,
                           "direction_fa": sig_fa, "confidence": conf, "user_email": alert["user_email"]}
                return {
                    "title": f"🔄 تغییر سیگنال {symbol}",
                    "body": render_template("signal_change", context),
                    "new_state": sig,
                }
            return None

        if atype == "signal_buy" and sig == "BUY" and conf >= 50:
            if last_state != "BUY":
                context = {"icon": "🟢", "symbol": symbol, "strategy": name_fa,
                           "confidence": conf, "user_email": alert["user_email"]}
                return {
                    "title": f"🟢 سیگنال خرید {symbol}",
                    "body": render_template("signal_buy", context),
                    "new_state": sig,
                }

        if atype == "signal_sell" and sig == "SELL" and conf >= 50:
            if last_state != "SELL":
                context = {"icon": "🔴", "symbol": symbol, "strategy": name_fa,
                           "confidence": conf, "user_email": alert["user_email"]}
                return {
                    "title": f"🔴 سیگنال فروش {symbol}",
                    "body": render_template("signal_sell", context),
                    "new_state": sig,
                }

        if atype == "confidence_high" and conf >= 75:
            if last_state != "HIGH":
                sig_fa = "خرید" if sig == "BUY" else "فروش" if sig == "SELL" else "خنثی"
                context = {"icon": "⭐", "symbol": symbol, "strategy": name_fa,
                           "direction_fa": sig_fa, "confidence": conf, "user_email": alert["user_email"]}
                return {
                    "title": f"⭐ اطمینان بالا {symbol}",
                    "body": render_template("confidence_high", context),
                    "new_state": "HIGH",
                }

    # ── TP/SL alerts ──
    target = alert.get("target_price")
    if target and price:
        tolerance = price * 0.001

        if atype == "tp1_hit" and abs(price - target) < tolerance:
            context = {"icon": "✅", "symbol": symbol, "price": price, "target": target,
                       "user_email": alert["user_email"]}
            return {
                "title": f"✅ TP1 رسیده {symbol}",
                "body": render_template("tp1_hit", context),
                "new_state": "HIT",
            }

        if atype == "tp2_hit" and abs(price - target) < tolerance:
            context = {"icon": "🏆", "symbol": symbol, "price": price, "target": target,
                       "user_email": alert["user_email"]}
            return {
                "title": f"🏆 TP2 رسیده {symbol}",
                "body": render_template("tp2_hit", context),
                "new_state": "HIT",
            }

        if atype == "sl_hit" and abs(price - target) < tolerance:
            context = {"icon": "🛑", "symbol": symbol, "price": price, "target": target,
                       "user_email": alert["user_email"]}
            return {
                "title": f"🛑 حد ضرر {symbol}",
                "body": render_template("sl_hit", context),
                "new_state": "HIT",
            }

    # ── Master setup alerts ──
    if atype == "master_active":
        if master and master.get("has_setup"):
            dir_fa = master.get("direction_fa", "")
            if last_state != master.get("direction"):
                context = {"icon": "📋", "symbol": symbol, "direction_fa": dir_fa,
                           "entry": master.get("entry", ""), "sl": master.get("stop_loss", ""),
                           "tp1": master.get("tp1", ""), "user_email": alert["user_email"]}
                return {
                    "title": f"📋 ستاپ کلی فعال {symbol}",
                    "body": render_template("master_active", context),
                    "new_state": master.get("direction"),
                }

    if atype == "master_change":
        if master and master.get("has_setup"):
            new_dir = master.get("direction")
            if last_state and new_dir != last_state:
                dir_fa = master.get("direction_fa", "")
                context = {"icon": "🔀", "symbol": symbol, "direction_fa": dir_fa,
                           "entry": master.get("entry", ""), "user_email": alert["user_email"]}
                return {
                    "title": f"🔀 تغییر ستاپ کلی {symbol}",
                    "body": render_template("master_change", context),
                    "new_state": new_dir,
                }

    if atype == "signal_change" and sid and sid in strat_map:
        return None

    return None


# ═══════════════════════════════════════════════════
# DELIVERY (Telegram + Email + Popup dispatch)
# ═══════════════════════════════════════════════════

def _deliver_alert(alert, title, body):
    """Deliver alert via configured channels. Returns list of channels used."""
    channels = alert.get("channels", {})
    user_email = alert["user_email"]
    used = []

    # Telegram
    if channels.get("telegram"):
        try:
            ucfg = get_user_config(user_email)
            chat_id = ucfg.get("telegram_chat_id", "")
            if chat_id:
                from backend.api.alert_dispatcher import dispatch_event
                dispatch_event("alert_notification", {
                    "chat_id": chat_id,
                    "title": title,
                    "body": body,
                    "symbol": alert.get("symbol", ""),
                    "alert_type": alert.get("alert_type", ""),
                })
                used.append("telegram")
        except Exception:
            pass

    # Email
    if channels.get("email"):
        try:
            from backend.api.email_sender import send_email, is_configured
            if is_configured():
                send_email(user_email, alert.get("alert_type", ""), {
                    "symbol": alert.get("symbol", ""),
                    "direction": "",
                    "strategy_name": alert.get("strategy_id", "Whilber-AI"),
                    "entry_price": alert.get("target_price", ""),
                })
                used.append("email")
        except Exception:
            pass

    # Popup is handled client-side via notification polling
    if channels.get("popup", True):
        used.append("popup")

    return used


def get_alert_types():
    """Return available alert types for frontend."""
    return ALERT_TYPES
