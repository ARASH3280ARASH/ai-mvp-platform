"""
Whilber-AI — Strategy Alert Subscription Engine
===================================================
Users subscribe to strategies → get lifecycle alerts:
  Signal detected → Entry → BE → Partial → Trailing → TP/SL
Notifications: in-app popup + email.
"""

import json
import os
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timezone
from threading import Lock
from collections import defaultdict

PROJECT_DIR = r"C:\Users\Administrator\Desktop\mvp"
SUBS_FILE = os.path.join(PROJECT_DIR, "track_records", "subscriptions.json")
NOTIF_FILE = os.path.join(PROJECT_DIR, "track_records", "notifications.json")
EMAIL_CONFIG_FILE = os.path.join(PROJECT_DIR, "email_config.json")
_lock = Lock()

# ══════ SUBSCRIPTION MANAGEMENT ══════

def _load_subs():
    try:
        if os.path.exists(SUBS_FILE):
            with open(SUBS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"subscriptions": []}


def _save_subs(data):
    with _lock:
        with open(SUBS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)


def subscribe(email, sub_config):
    """
    Subscribe to strategy alerts.
    sub_config: {
        strategy_id: str or "*" for all,
        strategy_name: str,
        symbols: [list] or ["*"],
        alert_on: {
            signal: bool,    # New signal detected
            entry: bool,     # Virtual entry confirmed
            be_move: bool,   # SL moved to break even
            partial: bool,   # Partial close executed
            trailing: bool,  # Trailing activated
            near_tp: bool,   # Near take profit
            near_sl: bool,   # Near stop loss
            closed_tp: bool, # Closed at TP
            closed_sl: bool, # Closed at SL
        },
        notify_email: bool,
        notify_app: bool,
        min_confidence: int (0-100),
    }
    """
    data = _load_subs()
    now = datetime.now(timezone.utc).isoformat()

    sub_id = now.replace(":", "").replace("-", "").replace(".", "")[:18]

    sub = {
        "id": sub_id,
        "email": email,
        "strategy_id": sub_config.get("strategy_id", "*"),
        "strategy_name": sub_config.get("strategy_name", ""),
        "symbols": sub_config.get("symbols", ["*"]),
        "alert_on": sub_config.get("alert_on", {
            "signal": True, "entry": True, "be_move": True,
            "partial": True, "trailing": True, "near_tp": True,
            "near_sl": True, "closed_tp": True, "closed_sl": True,
        }),
        "notify_email": sub_config.get("notify_email", False),
        "notify_app": sub_config.get("notify_app", True),
        "notify_desktop": sub_config.get("notify_desktop", True),
        "min_confidence": sub_config.get("min_confidence", 40),
        "active": True,
        "created_at": now,
        "alert_count": 0,
    }

    # Avoid duplicate
    for existing in data["subscriptions"]:
        if (existing["email"] == email and
            existing["strategy_id"] == sub["strategy_id"] and
            existing.get("active")):
            existing["active"] = False  # Deactivate old

    data["subscriptions"].append(sub)
    _save_subs(data)
    return {"success": True, "sub_id": sub_id}


def unsubscribe(email, sub_id):
    data = _load_subs()
    for s in data["subscriptions"]:
        if s["id"] == sub_id and s["email"] == email:
            s["active"] = False
            _save_subs(data)
            return {"success": True}
    return {"success": False, "error": "Not found"}


def get_subscriptions(email):
    data = _load_subs()
    return [s for s in data["subscriptions"]
            if s["email"] == email and s.get("active", True)]


def get_all_active_subs():
    data = _load_subs()
    return [s for s in data["subscriptions"] if s.get("active", True)]


# ══════ NOTIFICATION DISPATCH ══════

def _load_notifs():
    try:
        if os.path.exists(NOTIF_FILE):
            with open(NOTIF_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"notifications": []}


def _save_notifs(data):
    with _lock:
        data["notifications"] = data["notifications"][:2000]
        with open(NOTIF_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)


def dispatch_alert(event_type, trade, detail=""):
    """
    Called by tracker daemon when a trade event occurs.
    Matches against all subscriptions and sends notifications.
    event_type: signal, entry, be_move, partial, trailing, near_tp, near_sl, closed_tp, closed_sl
    """
    subs = get_all_active_subs()
    if not subs:
        return 0

    strategy_id = trade.get("strategy_id", "")
    strategy_name = trade.get("strategy_name", "")
    symbol = trade.get("symbol", "")
    direction = trade.get("direction", "")
    confidence = trade.get("confidence", 0)
    sent = 0

    for sub in subs:
        # Match strategy
        if sub["strategy_id"] != "*" and sub["strategy_id"] != strategy_id:
            # Also match by name
            if sub.get("strategy_name", "").lower() not in strategy_name.lower():
                continue

        # Match symbol
        if "*" not in sub.get("symbols", ["*"]) and symbol not in sub.get("symbols", []):
            continue

        # Match event type
        if not sub.get("alert_on", {}).get(event_type, False):
            continue

        # Min confidence
        if confidence < sub.get("min_confidence", 0):
            continue

        # Build notification
        notif = _build_notification(event_type, trade, detail, sub)

        # In-app notification
        if sub.get("notify_app", True):
            _store_notification(sub["email"], notif)

        # Email
        if sub.get("notify_email", False):
            _send_email(sub["email"], notif)

        # Update sub count
        sub["alert_count"] = sub.get("alert_count", 0) + 1
        sent += 1

    # Save updated subs
    if sent:
        data = _load_subs()
        for s in data["subscriptions"]:
            for sub in subs:
                if s["id"] == sub["id"]:
                    s["alert_count"] = sub["alert_count"]
        _save_subs(data)

    return sent


EVENT_ICONS = {
    "signal": "📡", "entry": "🟢", "be_move": "💛",
    "partial": "💰", "trailing": "🔄", "near_tp": "🎯",
    "near_sl": "🔴", "closed_tp": "✅", "closed_sl": "❌",
    "closed_trailing": "🔄", "closed_be": "🟡",
}

EVENT_TITLES_FA = {
    "signal": "سیگنال جدید شناسایی شد",
    "entry": "ورود به معامله",
    "be_move": "SL به Break Even رفت",
    "partial": "سیو سود انجام شد",
    "trailing": "Trailing فعال شد",
    "near_tp": "نزدیک حد سود!",
    "near_sl": "نزدیک حد ضرر!",
    "closed_tp": "معامله با سود بسته شد ✅",
    "closed_sl": "معامله با ضرر بسته شد ❌",
    "closed_trailing": "Trailing بسته شد",
    "closed_be": "در Break Even بسته شد",
}

EVENT_ACTIONS_FA = {
    "signal": "بررسی شرایط ورود کنید",
    "entry": "مانیتور معامله شروع شد — SL و TP فعال",
    "be_move": "ریسک صفر شد — بذارید ادامه بده",
    "partial": "بخشی از سود ذخیره شد — باقی ادامه",
    "trailing": "SL داره دنبال قیمت حرکت میکنه",
    "near_tp": "آماده سیو سود باشید",
    "near_sl": "به SL اعتماد کنید — جابجا نکنید!",
    "closed_tp": "تبریک! معامله موفق بود",
    "closed_sl": "درس بگیرید و ادامه بدید",
    "closed_trailing": "تریلینگ سود شما رو حفظ کرد",
    "closed_be": "بدون سود و ضرر — عملکرد درست",
}


def _build_notification(event_type, trade, detail, sub):
    icon = EVENT_ICONS.get(event_type, "🔔")
    title = EVENT_TITLES_FA.get(event_type, event_type)
    action = EVENT_ACTIONS_FA.get(event_type, "")
    now = datetime.now(timezone.utc).isoformat()

    sym = trade.get("symbol", "")
    direction = trade.get("direction", "")
    entry = trade.get("entry_price", 0)
    cp = trade.get("current_price", entry)
    pnl = trade.get("current_pnl_usd", 0)
    sl = trade.get("sl_price", 0)
    tp1 = trade.get("tp1_price", 0)

    body_fa = f"{icon} {trade.get('strategy_name','')} | {sym} {direction}\n"
    body_fa += f"📍 ورود: {entry}"
    if cp and cp != entry:
        body_fa += f" → فعلی: {cp}"
    if pnl:
        body_fa += f" | PnL: {'+'if pnl>=0 else ''}{pnl:.2f}$"
    body_fa += f"\n🎯 TP: {tp1} | 🛑 SL: {sl}"
    if detail:
        body_fa += f"\n💬 {detail}"
    body_fa += f"\n📌 {action}"

    return {
        "id": now.replace(":", "").replace("-", "")[:18],
        "event_type": event_type,
        "icon": icon,
        "title_fa": title,
        "body_fa": body_fa,
        "action_fa": action,
        "strategy_id": trade.get("strategy_id", ""),
        "strategy_name": trade.get("strategy_name", ""),
        "symbol": sym,
        "direction": direction,
        "price": cp,
        "pnl": pnl,
        "time": now,
        "read": False,
        "priority": "high" if event_type in ("near_sl", "closed_sl") else "normal",
    }


def _store_notification(email, notif):
    data = _load_notifs()
    notif["email"] = email
    data["notifications"].insert(0, notif)
    _save_notifs(data)


def get_notifications(email, limit=50, unread_only=False):
    data = _load_notifs()
    notifs = [n for n in data["notifications"] if n.get("email") == email]
    if unread_only:
        notifs = [n for n in notifs if not n.get("read")]
    return notifs[:limit]


def get_unread_count(email):
    data = _load_notifs()
    return sum(1 for n in data["notifications"]
               if n.get("email") == email and not n.get("read"))


def mark_read(email, notif_id=None):
    data = _load_notifs()
    for n in data["notifications"]:
        if n.get("email") == email:
            if notif_id is None or n.get("id") == notif_id:
                n["read"] = True
    _save_notifs(data)
    return {"success": True}


def clear_notifications(email):
    data = _load_notifs()
    data["notifications"] = [n for n in data["notifications"] if n.get("email") != email]
    _save_notifs(data)
    return {"success": True}


# ══════ EMAIL ══════

def _load_email_config():
    try:
        if os.path.exists(EMAIL_CONFIG_FILE):
            with open(EMAIL_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _send_email(to_email, notif):
    config = _load_email_config()
    if not config.get("smtp_host"):
        return False

    try:
        subject = f"Whilber-AI | {notif['icon']} {notif['title_fa']}"
        body = notif["body_fa"]

        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = config.get("from_email", "alert@whilber.ai")
        msg["To"] = to_email

        with smtplib.SMTP(config["smtp_host"], config.get("smtp_port", 587)) as server:
            if config.get("smtp_tls", True):
                server.starttls()
            if config.get("smtp_user"):
                server.login(config["smtp_user"], config.get("smtp_pass", ""))
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"[ALERT] Email error: {e}")
        return False


def save_email_config(config):
    with open(EMAIL_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    return {"success": True}


def get_email_config():
    c = _load_email_config()
    if c.get("smtp_pass"):
        c["smtp_pass"] = "***"
    return c
