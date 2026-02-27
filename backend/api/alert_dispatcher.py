"""
Whilber-AI — Alert Dispatcher
═══════════════════════════════
Routes trade events to subscribed users via Telegram and Email.

Usage:
    from backend.api.alert_dispatcher import dispatch_event
    dispatch_event("entry", trade_data)

Flow:
    Event → get_subscribed_users() → filter by settings → send_alert()
"""

import os
import json
import time
import sqlite3
import threading
from datetime import datetime, timezone
from collections import deque

# ── Config ──
_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "whilber.db")
_dispatch_queue = deque(maxlen=5000)  # Buffer events
_dispatch_thread = None
_dispatch_active = False
_lock = threading.Lock()

# Rate limiting per chat
_rate_limits = {}  # {chat_id: [timestamps]}
_MAX_ALERTS_PER_MINUTE = 20
_MAX_ALERTS_PER_HOUR = 200

# Stats
_stats = {"sent": 0, "failed": 0, "skipped": 0, "queued": 0}


# ══════════════════════════════════════════════════════════════
# MAIN DISPATCH FUNCTION
# ══════════════════════════════════════════════════════════════

def dispatch_event(event_type, trade_data):
    """
    Main entry point: route a trade event to all subscribed users.
    Non-blocking: adds to queue and returns immediately.
    """
    _dispatch_queue.append({
        "event_type": event_type,
        "trade_data": trade_data,
        "timestamp": time.time(),
    })
    _stats["queued"] += 1
    
    # Ensure dispatch thread is running
    _ensure_dispatch_thread()


def dispatch_event_sync(event_type, trade_data):
    """
    Synchronous dispatch — use for testing or critical alerts.
    Blocks until all alerts are sent.
    """
    subscribers = _get_subscribers(
        strategy_id=trade_data.get("strategy_id", ""),
        symbol=trade_data.get("symbol", ""),
        event_type=event_type,
    )
    
    results = []
    for sub in subscribers:
        # Check rate limit
        chat_id = sub.get("telegram_chat_id", "")
        if not _check_rate_limit(chat_id):
            _stats["skipped"] += 1
            continue
        
        # Check min PnL filter
        min_pnl = sub.get("min_pnl", 0)
        if min_pnl > 0 and event_type.startswith("closed_"):
            pnl = abs(trade_data.get("pnl_usd", 0))
            if pnl < min_pnl:
                _stats["skipped"] += 1
                continue
        
        # Send Telegram
        if sub.get("telegram_active") and chat_id:
            result = _send_telegram(chat_id, event_type, trade_data)
            _log_alert(chat_id, "telegram", event_type, trade_data, result)
            results.append(result)
        
        # Send Email
        if sub.get("email_active") and sub.get("email_address"):
            result = _send_email(sub["email_address"], event_type, trade_data)
            _log_alert(chat_id, "email", event_type, trade_data, result)
            results.append(result)
    
    return {"sent": len([r for r in results if r.get("ok")]), "total_subscribers": len(subscribers)}


# ══════════════════════════════════════════════════════════════
# BACKGROUND DISPATCH THREAD
# ══════════════════════════════════════════════════════════════

def _ensure_dispatch_thread():
    global _dispatch_thread, _dispatch_active
    if _dispatch_active and _dispatch_thread and _dispatch_thread.is_alive():
        return
    _dispatch_active = True
    _dispatch_thread = threading.Thread(target=_dispatch_loop, daemon=True, name="AlertDispatcher")
    _dispatch_thread.start()


def _dispatch_loop():
    global _dispatch_active
    print("[ALERTS] Dispatch thread started")
    
    while _dispatch_active:
        try:
            if _dispatch_queue:
                item = _dispatch_queue.popleft()
                event_type = item["event_type"]
                trade_data = item["trade_data"]
                
                # Process
                dispatch_event_sync(event_type, trade_data)
            else:
                time.sleep(0.5)  # Wait for new events
        except Exception as e:
            print(f"[ALERTS] Dispatch error: {e}")
            time.sleep(1)
    
    print("[ALERTS] Dispatch thread stopped")


def stop_dispatcher():
    global _dispatch_active
    _dispatch_active = False


# ══════════════════════════════════════════════════════════════
# SUBSCRIBER LOOKUP
# ══════════════════════════════════════════════════════════════

def _get_subscribers(strategy_id, symbol, event_type):
    """Get all users who should receive this event."""
    try:
        conn = sqlite3.connect(_DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM user_alerts WHERE telegram_active=1 OR email_active=1")
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
    except Exception as e:
        print(f"[ALERTS] DB error: {e}")
        return []
    
    now = datetime.now(timezone.utc)
    result = []
    
    for row in rows:
        # Check quiet hours
        quiet_start = row.get("quiet_start", "")
        quiet_end = row.get("quiet_end", "")
        if quiet_start and quiet_end:
            current_time = now.strftime("%H:%M")
            if _in_quiet_hours(current_time, quiet_start, quiet_end):
                continue
        
        # Check strategy filter
        strategies = row.get("strategies", "*")
        if strategies and strategies != "*":
            try:
                strats = json.loads(strategies) if isinstance(strategies, str) else strategies
                if isinstance(strats, list) and strategy_id not in strats:
                    continue
            except:
                pass
        
        # Check symbol filter
        symbols = row.get("symbols", "*")
        if symbols and symbols != "*":
            try:
                syms = json.loads(symbols) if isinstance(symbols, str) else symbols
                if isinstance(syms, list) and symbol not in syms:
                    continue
            except:
                pass
        
        # Check event filter
        events = row.get("events", "*")
        if events and events != "*":
            try:
                evts = json.loads(events) if isinstance(events, str) else events
                if isinstance(evts, list) and event_type not in evts:
                    continue
            except:
                pass
        
        result.append(row)
    
    return result


def _in_quiet_hours(current, start, end):
    """Check if current time is in quiet hours (handles midnight crossing)."""
    if start <= end:
        return start <= current <= end
    else:
        return current >= start or current <= end


# ══════════════════════════════════════════════════════════════
# RATE LIMITING
# ══════════════════════════════════════════════════════════════

def _check_rate_limit(chat_id):
    """Return True if this chat can receive more alerts."""
    now = time.time()
    with _lock:
        times = _rate_limits.get(chat_id, [])
        # Clean old entries
        times = [t for t in times if now - t < 3600]  # Keep 1 hour
        
        # Check minute limit
        recent = [t for t in times if now - t < 60]
        if len(recent) >= _MAX_ALERTS_PER_MINUTE:
            return False
        
        # Check hour limit
        if len(times) >= _MAX_ALERTS_PER_HOUR:
            return False
        
        times.append(now)
        _rate_limits[chat_id] = times
    return True


# ══════════════════════════════════════════════════════════════
# SEND TELEGRAM
# ══════════════════════════════════════════════════════════════

def _send_telegram(chat_id, event_type, trade_data):
    """Send alert via Telegram bot."""
    try:
        from backend.api.telegram_bot import send_alert
        result = send_alert(chat_id, event_type, trade_data)
        if result.get("ok"):
            _stats["sent"] += 1
        else:
            _stats["failed"] += 1
        return result
    except Exception as e:
        _stats["failed"] += 1
        return {"ok": False, "description": str(e)[:200]}


# ══════════════════════════════════════════════════════════════
# SEND EMAIL
# ══════════════════════════════════════════════════════════════

def _send_email(email_addr, event_type, trade_data):
    """Send alert via email using SMTP."""
    try:
        from backend.api.email_sender import send_email, is_configured
        if not is_configured():
            return {"ok": False, "description": "SMTP not configured"}
        return send_email(email_addr, event_type, trade_data)
    except ImportError:
        return {"ok": False, "description": "email_sender module not found"}
    except Exception as e:
        return {"ok": False, "description": str(e)[:200]}


# ══════════════════════════════════════════════════════════════
# LOGGING
# ══════════════════════════════════════════════════════════════

def _log_alert(chat_id, channel, event_type, trade_data, result):
    """Log alert to database."""
    try:
        conn = sqlite3.connect(_DB_PATH)
        c = conn.cursor()
        c.execute("""INSERT INTO alert_log (chat_id, channel, event_type, strategy_id, symbol, message, status, error, created_at)
                     VALUES (?,?,?,?,?,?,?,?,?)""",
                  (str(chat_id), channel, event_type,
                   trade_data.get("strategy_id", ""),
                   trade_data.get("symbol", ""),
                   json.dumps({"direction": trade_data.get("direction",""), "pnl": trade_data.get("pnl_usd",0)}, ensure_ascii=False),
                   "sent" if result.get("ok") else "failed",
                   result.get("description", "")[:200] if not result.get("ok") else "",
                   datetime.now(timezone.utc).isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[ALERTS] Log error: {e}")


# ══════════════════════════════════════════════════════════════
# STATS / STATUS
# ══════════════════════════════════════════════════════════════

def get_stats():
    """Return dispatcher stats."""
    return {
        "sent": _stats["sent"],
        "failed": _stats["failed"],
        "skipped": _stats["skipped"],
        "queued": _stats["queued"],
        "queue_size": len(_dispatch_queue),
        "dispatch_active": _dispatch_active,
    }
