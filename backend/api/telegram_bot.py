"""
Whilber-AI — Telegram Bot (Phase 5)
═════════════════════════════════════
Interactive menus, public channel, personal alerts.
"""

import os, json, time, threading, sqlite3
import urllib.request, urllib.error
from datetime import datetime, timezone

# ── Config ──
_BOT_TOKEN = None
_CHANNEL_ID = None
_lock = threading.Lock()
_last_sent = {}
_MAX_PER_MINUTE = 30
_polling_thread = None
_polling_active = False


def _get_token():
    global _BOT_TOKEN, _CHANNEL_ID
    if _BOT_TOKEN:
        return _BOT_TOKEN
    env_file = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            for line in f:
                if line.strip().startswith("TELEGRAM_BOT_TOKEN="):
                    _BOT_TOKEN = line.strip().split("=", 1)[1].strip()
                elif line.strip().startswith("TELEGRAM_CHANNEL_ID="):
                    _CHANNEL_ID = line.strip().split("=", 1)[1].strip()
    _BOT_TOKEN = _BOT_TOKEN or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    return _BOT_TOKEN


def _get_channel():
    global _CHANNEL_ID
    if _CHANNEL_ID:
        return _CHANNEL_ID
    _get_token()
    return _CHANNEL_ID


def _api(method, data=None, timeout=10):
    token = _get_token()
    if not token:
        return {"ok": False, "description": "No token"}
    url = f"https://api.telegram.org/bot{token}/{method}"
    if data:
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    else:
        req = urllib.request.Request(url)
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try: return json.loads(raw)
        except: return {"ok": False, "description": raw[:200]}
    except Exception as e:
        return {"ok": False, "description": str(e)[:200]}


# ══════════════════════════════════════════════════════════════
# SENDING
# ══════════════════════════════════════════════════════════════

def send_message(chat_id, text, parse_mode="HTML", reply_markup=None, disable_notification=False):
    now = time.time()
    with _lock:
        times = _last_sent.get(chat_id, [])
        times = [t for t in times if now - t < 60]
        if len(times) >= _MAX_PER_MINUTE:
            return {"ok": False, "description": "Rate limited"}
        times.append(now)
        _last_sent[chat_id] = times
    
    data = {
        "chat_id": chat_id, "text": text, "parse_mode": parse_mode,
        "disable_notification": disable_notification, "disable_web_page_preview": True,
    }
    if reply_markup:
        data["reply_markup"] = reply_markup
    return _api("sendMessage", data)


def send_to_channel(text, parse_mode="HTML"):
    """Send message to public channel."""
    ch = _get_channel()
    if not ch:
        return {"ok": False, "description": "Channel not configured"}
    return send_message(ch, text, parse_mode)


EVENT_ICONS = {
    "entry": "🟢", "exit": "🔴", "closed_tp": "✅", "closed_sl": "❌",
    "closed_trailing": "🔄", "closed_be": "🟡", "be_activated": "🛡️",
    "trailing_active": "📈", "partial_close": "✂️", "near_tp": "🎯",
    "near_sl": "⚠️", "in_profit": "💚", "in_loss": "💔", "recovery": "🔄",
}
EVENT_TITLES = {
    "entry": "سیگنال جدید", "exit": "خروج", "closed_tp": "بسته شد — TP",
    "closed_sl": "بسته شد — SL", "closed_trailing": "بسته شد — Trailing",
    "closed_be": "بسته شد — BE", "be_activated": "Break Even فعال",
    "trailing_active": "Trailing فعال", "partial_close": "بسته شدن جزئی",
    "near_tp": "نزدیک TP", "near_sl": "نزدیک SL",
    "in_profit": "وارد سود", "in_loss": "وارد ضرر", "recovery": "بازگشت",
}

def format_alert(event_type, t):
    icon = EVENT_ICONS.get(event_type, "📌")
    title = EVENT_TITLES.get(event_type, event_type)
    sym = t.get("symbol", "?")
    dir = t.get("direction", "?")
    strat = t.get("strategy_name", t.get("strategy_id", "?"))
    tf = t.get("timeframe", "H1")
    dir_icon = "🟩" if dir == "BUY" else "🟥"
    
    msg = f"{icon} <b>{title}</b> — {sym} {dir_icon} {dir}\n\n"
    msg += f"📊 <b>استراتژی:</b> {strat}\n⏱ <b>تایم‌فریم:</b> {tf}\n"
    
    if event_type == "entry":
        if t.get("entry_price"): msg += f"💰 <b>ورود:</b> {t['entry_price']}\n"
        if t.get("tp1_price"): msg += f"🎯 <b>TP:</b> {t['tp1_price']}\n"
        if t.get("sl_price"): msg += f"🛑 <b>SL:</b> {t['sl_price']}\n"
    elif event_type.startswith("closed_") or event_type == "exit":
        msg += f"💰 <b>ورود:</b> {t.get('entry_price',0)} → <b>خروج:</b> {t.get('exit_price',t.get('current_price',0))}\n"
        pnl = t.get("pnl_usd", 0); pips = t.get("pnl_pips", 0)
        msg += f"{'📈' if pnl>=0 else '📉'} <b>سود:</b> {'+' if pips>=0 else ''}{pips} pips (${pnl})\n"
        if t.get("duration_minutes"): msg += f"⏱ <b>مدت:</b> {int(t['duration_minutes'])} دقیقه\n"
        if t.get("sl_moved_to_be"): msg += "🛡️ BE فعال بود\n"
        if t.get("trailing_active"): msg += "📈 Trailing فعال بود\n"
    elif event_type == "be_activated":
        msg += f"💰 <b>ورود:</b> {t.get('entry_price',0)}\n🛑 <b>SL جدید:</b> {t.get('entry_price',0)} (= ورود)\n"
    elif event_type == "trailing_active":
        msg += f"📈 <b>سود:</b> {t.get('current_pnl_pips',0)} pips\n🛑 <b>SL:</b> {t.get('sl_price',0)}\n"
    else:
        if t.get("current_price"): msg += f"📊 <b>قیمت:</b> {t['current_price']}\n"
        if t.get("current_pnl_pips"): msg += f"📈 {t['current_pnl_pips']} pips\n"
    
    msg += f"\n⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    return msg


def send_alert(chat_id, event_type, trade_data):
    return send_message(chat_id, format_alert(event_type, trade_data))


# ══════════════════════════════════════════════════════════════
# INTERACTIVE MENU (Inline Keyboards)
# ══════════════════════════════════════════════════════════════

def _main_menu_keyboard():
    ch = _get_channel()
    buttons = [
        [{"text": "📊 وضعیت آلرت‌ها", "callback_data": "menu_status"},
         {"text": "⚙️ تنظیمات", "callback_data": "menu_settings"}],
        [{"text": "🧪 آلرت آزمایشی", "callback_data": "menu_test"},
         {"text": "📖 راهنما", "callback_data": "menu_help"}],
        [{"text": "🔔 آلرت شخصی من", "callback_data": "menu_personal"},
         {"text": "🔕 غیرفعال", "callback_data": "menu_stop"}],
    ]
    if ch:
        buttons.insert(2, [{"text": "📢 عضویت کانال عمومی", "url": f"https://t.me/{ch.replace('@','')}"} ])
    return {"inline_keyboard": buttons}


def _settings_keyboard():
    return {"inline_keyboard": [
        [{"text": "📊 تغییر نمادها", "callback_data": "set_symbols"},
         {"text": "🔔 تغییر رویدادها", "callback_data": "set_events"}],
        [{"text": "📧 تنظیم ایمیل", "callback_data": "set_email"},
         {"text": "🌙 ساعات سکوت", "callback_data": "set_quiet"}],
        [{"text": "🔙 منوی اصلی", "callback_data": "menu_main"}],
    ]}


def _events_keyboard(current_events):
    all_evts = [
        ("entry", "🟢 ورود"), ("closed_tp", "✅ TP"), ("closed_sl", "❌ SL"),
        ("be_activated", "🛡️ BE"), ("trailing_active", "📈 Trail"),
        ("closed_trailing", "🔄 Trail Close"), ("near_tp", "🎯 نزدیک TP"),
        ("near_sl", "⚠️ نزدیک SL"), ("in_profit", "💚 سود"), ("recovery", "🔄 ریکاوری"),
    ]
    buttons = []
    row = []
    for eid, elbl in all_evts:
        check = "✅" if current_events == "*" or eid in (current_events if isinstance(current_events, list) else []) else "⬜"
        row.append({"text": f"{check} {elbl}", "callback_data": f"toggle_evt_{eid}"})
        if len(row) == 2:
            buttons.append(row); row = []
    if row: buttons.append(row)
    buttons.append([{"text": "✅ همه", "callback_data": "evt_all"}, {"text": "❌ هیچ", "callback_data": "evt_none"}])
    buttons.append([{"text": "💾 ذخیره", "callback_data": "evt_save"}, {"text": "🔙 برگشت", "callback_data": "menu_settings"}])
    return {"inline_keyboard": buttons}


def _symbols_keyboard(current_symbols):
    syms = ["EURUSD","GBPUSD","USDJPY","XAUUSD","BTCUSD","NAS100","AUDUSD","USDCAD","NZDUSD","USDCHF","XAGUSD","US30"]
    buttons = []
    row = []
    for s in syms:
        check = "✅" if current_symbols == "*" or s in (current_symbols if isinstance(current_symbols, list) else []) else "⬜"
        row.append({"text": f"{check} {s}", "callback_data": f"toggle_sym_{s}"})
        if len(row) == 3:
            buttons.append(row); row = []
    if row: buttons.append(row)
    buttons.append([{"text": "✅ همه", "callback_data": "sym_all"}, {"text": "❌ هیچ", "callback_data": "sym_none"}])
    buttons.append([{"text": "💾 ذخیره", "callback_data": "sym_save"}, {"text": "🔙 برگشت", "callback_data": "menu_settings"}])
    return {"inline_keyboard": buttons}


def _personal_keyboard():
    return {"inline_keyboard": [
        [{"text": "📋 آخرین آلرت‌های من", "callback_data": "personal_recent"}],
        [{"text": "📊 آمار آلرت‌ها", "callback_data": "personal_stats"}],
        [{"text": "🔙 منوی اصلی", "callback_data": "menu_main"}],
    ]}


# ══════════════════════════════════════════════════════════════
# COMMAND HANDLERS
# ══════════════════════════════════════════════════════════════

def _handle_command(message):
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()
    user = message.get("from", {})
    if not chat_id or not text: return
    cmd = text.split()[0].lower().split("@")[0]
    
    if cmd == "/start":
        _save_chat_id(chat_id, user)
        first = user.get("first_name", "")
        send_message(chat_id,
            f"🎉 <b>خوش آمدید {first}!</b>\n\n"
            f"✅ به <b>Whilber-AI Alerts</b> متصل شدید.\n"
            f"🔔 شناسه: <code>{chat_id}</code>\n\n"
            f"از منوی زیر استفاده کنید:",
            reply_markup=_main_menu_keyboard())
    elif cmd == "/menu":
        send_message(chat_id, "📋 <b>منوی اصلی</b>", reply_markup=_main_menu_keyboard())
    elif cmd == "/stop":
        _deactivate_chat(chat_id)
        send_message(chat_id, "🔕 <b>آلرت‌ها غیرفعال شد.</b>\n\n/start برای فعال‌سازی مجدد")
    elif cmd == "/status":
        _show_status(chat_id)
    elif cmd == "/settings":
        send_message(chat_id, "⚙️ <b>تنظیمات</b>", reply_markup=_settings_keyboard())
    elif cmd == "/test":
        _handle_test(chat_id)
    elif cmd == "/help":
        _show_help(chat_id)
    elif cmd == "/personal":
        send_message(chat_id, "🔔 <b>آلرت شخصی من</b>", reply_markup=_personal_keyboard())
    else:
        send_message(chat_id, "📋 <b>منوی اصلی</b>", reply_markup=_main_menu_keyboard())


def _handle_callback(callback_query):
    """Handle inline keyboard button presses."""
    chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
    msg_id = callback_query.get("message", {}).get("message_id")
    data = callback_query.get("data", "")
    cb_id = callback_query.get("id")
    
    if not chat_id: return
    
    # Answer callback to remove loading indicator
    _api("answerCallbackQuery", {"callback_query_id": cb_id})
    
    settings = _get_user_settings(chat_id) or {}
    
    if data == "menu_main":
        _edit_or_send(chat_id, msg_id, "📋 <b>منوی اصلی</b>", _main_menu_keyboard())
    
    elif data == "menu_status":
        _show_status(chat_id, msg_id)
    
    elif data == "menu_settings":
        _edit_or_send(chat_id, msg_id, "⚙️ <b>تنظیمات</b>\n\nاز دکمه‌های زیر استفاده کنید:", _settings_keyboard())
    
    elif data == "menu_test":
        _handle_test(chat_id)
    
    elif data == "menu_help":
        _show_help(chat_id)
    
    elif data == "menu_stop":
        _deactivate_chat(chat_id)
        _edit_or_send(chat_id, msg_id, "🔕 <b>آلرت‌ها غیرفعال شد.</b>\n\n/start برای فعال‌سازی", None)
    
    elif data == "menu_personal":
        _edit_or_send(chat_id, msg_id, "🔔 <b>آلرت شخصی من</b>\n\nآلرت‌ها بر اساس تنظیمات شما ارسال می‌شوند.", _personal_keyboard())
    
    elif data == "personal_recent":
        _show_recent_alerts(chat_id)
    
    elif data == "personal_stats":
        _show_alert_stats(chat_id)
    
    elif data == "set_symbols":
        syms = settings.get("symbols", "*")
        if isinstance(syms, str) and syms != "*":
            try: syms = json.loads(syms)
            except: syms = "*"
        _edit_or_send(chat_id, msg_id, "📊 <b>انتخاب نمادها</b>\n\nروی هر نماد بزنید:", _symbols_keyboard(syms))
    
    elif data == "set_events":
        evts = settings.get("events", "*")
        if isinstance(evts, str) and evts != "*":
            try: evts = json.loads(evts)
            except: evts = "*"
        _edit_or_send(chat_id, msg_id, "🔔 <b>انتخاب رویدادها</b>\n\nروی هر رویداد بزنید:", _events_keyboard(evts))
    
    elif data == "set_email":
        send_message(chat_id, "📧 <b>تنظیم ایمیل</b>\n\nاز پنل وب استفاده کنید:\n🌐 /alerts-settings",
                     reply_markup={"inline_keyboard": [[{"text": "🌐 پنل وب", "callback_data": "menu_settings"},
                                                         {"text": "🔙 برگشت", "callback_data": "menu_settings"}]]})
    
    elif data == "set_quiet":
        send_message(chat_id, "🌙 <b>ساعات سکوت</b>\n\nاز پنل وب تنظیم کنید:\n🌐 /alerts-settings",
                     reply_markup={"inline_keyboard": [[{"text": "🌐 پنل وب", "callback_data": "menu_settings"},
                                                         {"text": "🔙 برگشت", "callback_data": "menu_settings"}]]})
    
    elif data.startswith("toggle_sym_"):
        sym = data[11:]
        _toggle_setting(chat_id, "symbols", sym, msg_id)
    
    elif data.startswith("toggle_evt_"):
        evt = data[11:]
        _toggle_setting(chat_id, "events", evt, msg_id)
    
    elif data == "sym_all":
        _set_all(chat_id, "symbols", True, msg_id)
    elif data == "sym_none":
        _set_all(chat_id, "symbols", False, msg_id)
    elif data == "evt_all":
        _set_all(chat_id, "events", True, msg_id)
    elif data == "evt_none":
        _set_all(chat_id, "events", False, msg_id)
    
    elif data == "sym_save" or data == "evt_save":
        _api("answerCallbackQuery", {"callback_query_id": cb_id, "text": "✅ ذخیره شد!", "show_alert": False})
        _edit_or_send(chat_id, msg_id, "⚙️ <b>تنظیمات</b>\n\n✅ تغییرات ذخیره شد.", _settings_keyboard())


def _edit_or_send(chat_id, msg_id, text, keyboard):
    if msg_id:
        data = {"chat_id": chat_id, "message_id": msg_id, "text": text, "parse_mode": "HTML"}
        if keyboard: data["reply_markup"] = keyboard
        r = _api("editMessageText", data)
        if not r.get("ok"):
            send_message(chat_id, text, reply_markup=keyboard)
    else:
        send_message(chat_id, text, reply_markup=keyboard)


def _toggle_setting(chat_id, field, value, msg_id):
    settings = _get_user_settings(chat_id) or {}
    current = settings.get(field, "*")
    if isinstance(current, str):
        try: current = json.loads(current) if current != "*" else []
        except: current = []
    if current == "*" or not isinstance(current, list):
        current = []
    if value in current:
        current.remove(value)
    else:
        current.append(value)
    _update_field(chat_id, field, json.dumps(current) if current else "*")
    # Refresh keyboard
    if field == "symbols":
        _edit_or_send(chat_id, msg_id, "📊 <b>انتخاب نمادها</b>", _symbols_keyboard(current or "*"))
    else:
        _edit_or_send(chat_id, msg_id, "🔔 <b>انتخاب رویدادها</b>", _events_keyboard(current or "*"))


def _set_all(chat_id, field, select_all, msg_id):
    if select_all:
        _update_field(chat_id, field, "*")
        val = "*"
    else:
        _update_field(chat_id, field, "[]")
        val = []
    if field == "symbols":
        _edit_or_send(chat_id, msg_id, "📊 <b>انتخاب نمادها</b>", _symbols_keyboard(val))
    else:
        _edit_or_send(chat_id, msg_id, "🔔 <b>انتخاب رویدادها</b>", _events_keyboard(val))


def _show_status(chat_id, msg_id=None):
    s = _get_user_settings(chat_id)
    if not s:
        send_message(chat_id, "⚠️ ثبت‌نام نشدید. /start بزنید.")
        return
    tg_st = "✅ فعال" if s.get("telegram_active") else "🔕 غیرفعال"
    em_st = "✅ فعال" if s.get("email_active") else "🔕 غیرفعال"
    syms = s.get("symbols","*")
    sym_txt = "همه" if syms=="*" else (", ".join(json.loads(syms)) if isinstance(syms,str) and syms!="*" else str(syms))
    evts = s.get("events","*")
    evt_txt = "همه" if evts=="*" else f"{len(json.loads(evts)) if isinstance(evts,str) else 0} رویداد"
    quiet = f"{s.get('quiet_start','-')} تا {s.get('quiet_end','-')}" if s.get("quiet_start") else "غیرفعال"
    
    text = (f"📊 <b>وضعیت آلرت‌ها</b>\n\n"
            f"📱 تلگرام: {tg_st}\n📧 ایمیل: {em_st}\n\n"
            f"📊 نمادها: {sym_txt}\n🔔 رویدادها: {evt_txt}\n🌙 ساعات سکوت: {quiet}")
    kb = {"inline_keyboard": [[{"text":"⚙️ تنظیمات","callback_data":"menu_settings"},{"text":"🔙 منو","callback_data":"menu_main"}]]}
    _edit_or_send(chat_id, msg_id, text, kb)


def _show_help(chat_id):
    send_message(chat_id,
        "📖 <b>راهنمای Whilber-AI Alerts</b>\n\n"
        "🤖 این بات آلرت‌های معاملاتی ارسال می‌کند.\n\n"
        "<b>📋 منو:</b> /menu\n"
        "<b>📊 وضعیت:</b> /status\n"
        "<b>⚙️ تنظیمات:</b> /settings\n"
        "<b>🧪 تست:</b> /test\n"
        "<b>🔔 شخصی:</b> /personal\n"
        "<b>🔕 غیرفعال:</b> /stop\n\n"
        "<b>🔔 انواع آلرت:</b>\n"
        "🟢 ورود | ✅ TP | ❌ SL | 🛡️ BE\n"
        "📈 Trailing | ✂️ جزئی | 🎯 نزدیک TP\n"
        "⚠️ نزدیک SL | 💚 سود | 🔄 ریکاوری\n\n"
        "<b>⚙️ تنظیمات دقیق:</b>\n"
        "از منوی تنظیمات نمادها و رویدادها را انتخاب کنید.\n"
        "تنظیمات پیشرفته از پنل وب:\n"
        "🌐 /alerts-settings",
        reply_markup=_main_menu_keyboard())


def _handle_test(chat_id):
    test_trade = {"symbol":"EURUSD","direction":"BUY","strategy_name":"Test Strategy",
                  "strategy_id":"TEST","timeframe":"H1","entry_price":1.08540,
                  "sl_price":1.08340,"tp1_price":1.08740}
    r = send_alert(chat_id, "entry", test_trade)
    if r.get("ok"):
        time.sleep(0.5)
        send_message(chat_id, "✅ آلرت آزمایشی ارسال شد!", reply_markup=_main_menu_keyboard())


def _show_recent_alerts(chat_id):
    try:
        db = _get_db_path()
        conn = sqlite3.connect(db); conn.row_factory = sqlite3.Row; c = conn.cursor()
        c.execute("SELECT * FROM alert_log WHERE chat_id=? ORDER BY id DESC LIMIT 10", (str(chat_id),))
        rows = [dict(r) for r in c.fetchall()]; conn.close()
        if not rows:
            send_message(chat_id, "📋 هنوز آلرتی ارسال نشده.", reply_markup=_personal_keyboard())
            return
        msg = "📋 <b>آخرین آلرت‌ها</b>\n\n"
        for r in rows:
            icon = EVENT_ICONS.get(r.get("event_type",""),"📌")
            msg += f"{icon} {r.get('event_type','')} | {r.get('symbol','')} | {r.get('created_at','')[:16]}\n"
        send_message(chat_id, msg, reply_markup=_personal_keyboard())
    except Exception as e:
        send_message(chat_id, f"❌ خطا: {str(e)[:50]}")


def _show_alert_stats(chat_id):
    try:
        db = _get_db_path()
        conn = sqlite3.connect(db); c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM alert_log WHERE chat_id=?", (str(chat_id),))
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM alert_log WHERE chat_id=? AND status='sent'", (str(chat_id),))
        sent = c.fetchone()[0]
        c.execute("SELECT event_type, COUNT(*) FROM alert_log WHERE chat_id=? GROUP BY event_type ORDER BY COUNT(*) DESC LIMIT 5", (str(chat_id),))
        top = c.fetchall(); conn.close()
        msg = f"📊 <b>آمار آلرت‌ها</b>\n\nکل: {total}\nموفق: {sent}\n\n"
        if top:
            msg += "<b>بیشترین:</b>\n"
            for t in top:
                msg += f"  {EVENT_ICONS.get(t[0],'📌')} {t[0]}: {t[1]}\n"
        send_message(chat_id, msg, reply_markup=_personal_keyboard())
    except Exception as e:
        send_message(chat_id, f"❌ خطا: {str(e)[:50]}")


# ══════════════════════════════════════════════════════════════
# DATABASE
# ══════════════════════════════════════════════════════════════

def _get_db_path():
    return os.path.join(os.path.dirname(__file__), "..", "..", "data", "whilber.db")

def _save_chat_id(chat_id, user):
    conn = sqlite3.connect(_get_db_path()); c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS user_alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_chat_id TEXT UNIQUE,
        telegram_username TEXT DEFAULT '', telegram_first_name TEXT DEFAULT '',
        telegram_active INTEGER DEFAULT 1, email_active INTEGER DEFAULT 0,
        email_address TEXT DEFAULT '', strategies TEXT DEFAULT '*',
        symbols TEXT DEFAULT '*', events TEXT DEFAULT '*',
        min_pnl REAL DEFAULT 0, quiet_start TEXT DEFAULT '', quiet_end TEXT DEFAULT '',
        created_at TEXT DEFAULT '', updated_at TEXT DEFAULT '')""")
    now = datetime.now(timezone.utc).isoformat()
    c.execute("""INSERT INTO user_alerts (telegram_chat_id,telegram_username,telegram_first_name,telegram_active,created_at,updated_at)
                 VALUES (?,?,?,1,?,?) ON CONFLICT(telegram_chat_id) DO UPDATE SET
                 telegram_active=1,telegram_username=?,telegram_first_name=?,updated_at=?""",
              (str(chat_id),user.get("username",""),user.get("first_name",""),now,now,
               user.get("username",""),user.get("first_name",""),now))
    conn.commit(); conn.close()

def _deactivate_chat(chat_id):
    conn = sqlite3.connect(_get_db_path()); c = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    c.execute("UPDATE user_alerts SET telegram_active=0,updated_at=? WHERE telegram_chat_id=?",(now,str(chat_id)))
    conn.commit(); conn.close()

def _get_user_settings(chat_id):
    conn = sqlite3.connect(_get_db_path()); conn.row_factory = sqlite3.Row; c = conn.cursor()
    c.execute("SELECT * FROM user_alerts WHERE telegram_chat_id=?",(str(chat_id),))
    row = c.fetchone(); conn.close()
    return dict(row) if row else None

def _update_field(chat_id, field, value):
    conn = sqlite3.connect(_get_db_path()); c = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    c.execute(f"UPDATE user_alerts SET {field}=?,updated_at=? WHERE telegram_chat_id=?",(value,now,str(chat_id)))
    conn.commit(); conn.close()

def get_subscribed_users(strategy_id, symbol, event_type):
    from backend.api.alert_dispatcher import _get_subscribers
    return _get_subscribers(strategy_id, symbol, event_type)


# ══════════════════════════════════════════════════════════════
# POLLING
# ══════════════════════════════════════════════════════════════

def start_polling():
    global _polling_thread, _polling_active
    if _polling_active: return {"status": "already_running"}
    _polling_active = True
    _polling_thread = threading.Thread(target=_polling_loop, daemon=True)
    _polling_thread.start()
    print(f"[TELEGRAM] Polling started")
    return {"status": "started"}

def stop_polling():
    global _polling_active
    _polling_active = False
    return {"status": "stopped"}

def _polling_loop():
    global _polling_active
    offset = None
    while _polling_active:
        try:
            r = _api("getUpdates", {"offset": offset, "timeout": 30, "allowed_updates": ["message","callback_query"]}, timeout=35)
            if r.get("ok"):
                for u in r.get("result", []):
                    offset = u["update_id"] + 1
                    if u.get("message") and u["message"].get("text","").startswith("/"):
                        _handle_command(u["message"])
                    elif u.get("callback_query"):
                        _handle_callback(u["callback_query"])
        except Exception as e:
            print(f"[TELEGRAM] Poll error: {e}")
            time.sleep(5)

def get_bot_info():
    return _api("getMe")

def init():
    info = get_bot_info()
    if info.get("ok"):
        print(f"[TELEGRAM] Bot: @{info['result'].get('username')}")
        return True
    print(f"[TELEGRAM] FAILED: {info.get('description','?')}")
    return False
