"""
Whilber-AI — Trade Journal
==============================
Manual trade logging with notes, emotions, lessons, tags.
Performance analytics per strategy.
"""

import json
import os
from datetime import datetime, timezone
from threading import Lock

PROJECT_DIR = r"C:\Users\Administrator\Desktop\mvp"
JOURNAL_DIR = os.path.join(PROJECT_DIR, "trade_journals")
os.makedirs(JOURNAL_DIR, exist_ok=True)
_lock = Lock()

EMOTIONS = [
    {"id": "confident", "name_fa": "مطمئن", "icon": "😎", "score": 2},
    {"id": "calm", "name_fa": "آرام", "icon": "😌", "score": 1},
    {"id": "neutral", "name_fa": "خنثی", "icon": "😐", "score": 0},
    {"id": "anxious", "name_fa": "مضطرب", "icon": "😰", "score": -1},
    {"id": "fomo", "name_fa": "FOMO", "icon": "😱", "score": -2},
    {"id": "greedy", "name_fa": "طمع", "icon": "🤑", "score": -2},
    {"id": "revenge", "name_fa": "انتقام", "icon": "😤", "score": -3},
    {"id": "fearful", "name_fa": "ترسیده", "icon": "😨", "score": -2},
]

TRADE_TAGS = [
    "trend", "reversal", "breakout", "scalp", "swing",
    "news", "setup_A", "setup_B", "setup_C",
    "overtrading", "early_entry", "late_entry",
    "perfect_entry", "moved_sl", "closed_early",
]

RATINGS = [
    {"id": 1, "name_fa": "خیلی بد", "icon": "⭐"},
    {"id": 2, "name_fa": "بد", "icon": "⭐⭐"},
    {"id": 3, "name_fa": "متوسط", "icon": "⭐⭐⭐"},
    {"id": 4, "name_fa": "خوب", "icon": "⭐⭐⭐⭐"},
    {"id": 5, "name_fa": "عالی", "icon": "⭐⭐⭐⭐⭐"},
]


def _user_file(email):
    safe = email.replace("@", "_at_").replace(".", "_")
    return os.path.join(JOURNAL_DIR, f"{safe}.json")


def _load(email):
    fp = _user_file(email)
    try:
        if os.path.exists(fp):
            with open(fp, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {"entries": [], "daily_notes": []}


def _save(email, data):
    with _lock:
        fp = _user_file(email)
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def add_entry(email, entry):
    """Add a trade journal entry."""
    data = _load(email)
    now = datetime.now(timezone.utc).isoformat()
    entry["id"] = now.replace(":", "").replace("-", "")[:18]
    entry["created_at"] = now
    entry.setdefault("symbol", "XAUUSD")
    entry.setdefault("type", "BUY")
    entry.setdefault("entry_price", 0)
    entry.setdefault("exit_price", 0)
    entry.setdefault("lot_size", 0.01)
    entry.setdefault("pnl", 0)
    entry.setdefault("pnl_pips", 0)
    entry.setdefault("strategy_name", "")
    entry.setdefault("timeframe", "H1")
    entry.setdefault("emotion_before", "neutral")
    entry.setdefault("emotion_after", "neutral")
    entry.setdefault("rating", 3)
    entry.setdefault("notes", "")
    entry.setdefault("lesson", "")
    entry.setdefault("tags", [])
    entry.setdefault("screenshot", "")
    entry.setdefault("followed_plan", True)
    entry.setdefault("tp_price", 0)
    entry.setdefault("sl_price", 0)

    data["entries"].insert(0, entry)
    _save(email, data)
    return {"success": True, "entry_id": entry["id"]}


def update_entry(email, entry_id, updates):
    """Update an existing entry."""
    data = _load(email)
    for e in data["entries"]:
        if e["id"] == entry_id:
            e.update(updates)
            e["updated_at"] = datetime.now(timezone.utc).isoformat()
            _save(email, data)
            return {"success": True}
    return {"success": False, "error": "Entry not found"}


def delete_entry(email, entry_id):
    data = _load(email)
    before = len(data["entries"])
    data["entries"] = [e for e in data["entries"] if e["id"] != entry_id]
    if len(data["entries"]) < before:
        _save(email, data)
        return {"success": True}
    return {"success": False, "error": "Not found"}


def get_entries(email, limit=100, symbol=None, strategy=None):
    data = _load(email)
    entries = data.get("entries", [])
    if symbol:
        entries = [e for e in entries if e.get("symbol") == symbol]
    if strategy:
        entries = [e for e in entries if e.get("strategy_name") == strategy]
    return entries[:limit]


def get_entry(email, entry_id):
    data = _load(email)
    for e in data["entries"]:
        if e["id"] == entry_id:
            return e
    return None


def add_daily_note(email, date_str, note):
    """Add/update a daily note."""
    data = _load(email)
    found = False
    for dn in data["daily_notes"]:
        if dn["date"] == date_str:
            dn["note"] = note
            dn["updated_at"] = datetime.now(timezone.utc).isoformat()
            found = True
            break
    if not found:
        data["daily_notes"].insert(0, {
            "date": date_str, "note": note,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    data["daily_notes"] = data["daily_notes"][:365]
    _save(email, data)
    return {"success": True}


def get_daily_notes(email, limit=30):
    data = _load(email)
    return data.get("daily_notes", [])[:limit]


def get_journal_analytics(email):
    """Compute analytics from journal entries."""
    data = _load(email)
    entries = data.get("entries", [])
    if not entries:
        return {"total": 0}

    wins = [e for e in entries if e.get("pnl", 0) > 0]
    losses = [e for e in entries if e.get("pnl", 0) < 0]
    pnls = [e.get("pnl", 0) for e in entries]
    total_pnl = sum(pnls)

    # By emotion
    emotion_stats = {}
    for e in entries:
        em = e.get("emotion_before", "neutral")
        if em not in emotion_stats:
            emotion_stats[em] = {"count": 0, "wins": 0, "pnl": 0}
        emotion_stats[em]["count"] += 1
        if e.get("pnl", 0) > 0:
            emotion_stats[em]["wins"] += 1
        emotion_stats[em]["pnl"] += e.get("pnl", 0)

    for k in emotion_stats:
        s = emotion_stats[k]
        s["win_rate"] = round(s["wins"] / s["count"] * 100, 1) if s["count"] else 0
        s["pnl"] = round(s["pnl"], 2)

    # By day of week
    day_stats = {}
    for e in entries:
        created = e.get("created_at", "")
        if len(created) >= 10:
            try:
                dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                day = dt.strftime("%A")
                if day not in day_stats:
                    day_stats[day] = {"count": 0, "wins": 0, "pnl": 0}
                day_stats[day]["count"] += 1
                if e.get("pnl", 0) > 0:
                    day_stats[day]["wins"] += 1
                day_stats[day]["pnl"] += e.get("pnl", 0)
            except Exception:
                pass

    # By strategy
    strat_stats = {}
    for e in entries:
        sn = e.get("strategy_name", "") or "Manual"
        if sn not in strat_stats:
            strat_stats[sn] = {"count": 0, "wins": 0, "pnl": 0}
        strat_stats[sn]["count"] += 1
        if e.get("pnl", 0) > 0:
            strat_stats[sn]["wins"] += 1
        strat_stats[sn]["pnl"] += e.get("pnl", 0)

    # Plan adherence
    followed = sum(1 for e in entries if e.get("followed_plan", True))
    not_followed = len(entries) - followed
    plan_wr = 0
    noplan_wr = 0
    fp_wins = sum(1 for e in entries if e.get("followed_plan") and e.get("pnl", 0) > 0)
    np_wins = sum(1 for e in entries if not e.get("followed_plan") and e.get("pnl", 0) > 0)
    if followed:
        plan_wr = round(fp_wins / followed * 100, 1)
    if not_followed:
        noplan_wr = round(np_wins / not_followed * 100, 1)

    # Streaks
    max_win_streak = 0
    max_loss_streak = 0
    ws = 0
    ls = 0
    for p in pnls:
        if p > 0:
            ws += 1
            ls = 0
        else:
            ls += 1
            ws = 0
        max_win_streak = max(max_win_streak, ws)
        max_loss_streak = max(max_loss_streak, ls)

    # Avg rating
    ratings = [e.get("rating", 3) for e in entries]
    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0

    return {
        "total": len(entries),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(entries) * 100, 1) if entries else 0,
        "total_pnl": round(total_pnl, 2),
        "avg_pnl": round(total_pnl / len(entries), 2) if entries else 0,
        "best_trade": round(max(pnls), 2) if pnls else 0,
        "worst_trade": round(min(pnls), 2) if pnls else 0,
        "avg_rating": avg_rating,
        "max_win_streak": max_win_streak,
        "max_loss_streak": max_loss_streak,
        "plan_adherence": round(followed / len(entries) * 100, 1) if entries else 0,
        "plan_win_rate": plan_wr,
        "noplan_win_rate": noplan_wr,
        "emotion_stats": emotion_stats,
        "day_stats": day_stats,
        "strategy_stats": strat_stats,
    }


SYMBOLS_LIST = [
    "XAUUSD","XAGUSD","EURUSD","GBPUSD","USDJPY","USDCHF","AUDUSD","NZDUSD","USDCAD",
    "EURGBP","EURJPY","GBPJPY","EURAUD","EURCAD","EURCHF","GBPAUD","GBPCAD","AUDJPY","CADJPY",
    "BTCUSD","ETHUSD","SOLUSD","US30","NAS100","US500",
]

SYMBOL_GROUPS = {
    "فلزات": ["XAUUSD","XAGUSD"],
    "فارکس — اصلی": ["EURUSD","GBPUSD","USDJPY","USDCHF","AUDUSD","NZDUSD","USDCAD"],
    "فارکس — فرعی": ["EURGBP","EURJPY","GBPJPY","EURAUD","EURCAD","EURCHF","GBPAUD","GBPCAD","AUDJPY","CADJPY"],
    "کریپتو": ["BTCUSD","ETHUSD","SOLUSD"],
    "شاخص": ["US30","NAS100","US500"],
}


def get_journal_config():
    return {
        "emotions": EMOTIONS,
        "tags": TRADE_TAGS,
        "ratings": RATINGS,
        "symbols": SYMBOLS_LIST,
        "symbol_groups": SYMBOL_GROUPS,
    }


def generate_recommendations(entry, analytics=None):
    """Generate trade recommendations/insights based on a journal entry."""
    recs = []
    pnl = entry.get("pnl", 0)
    emotion_before = entry.get("emotion_before", "neutral")
    emotion_after = entry.get("emotion_after", "neutral")
    followed_plan = entry.get("followed_plan", True)
    rating = entry.get("rating", 3)
    tags = entry.get("tags", [])
    entry_price = entry.get("entry_price", 0)
    exit_price = entry.get("exit_price", 0)
    tp_price = entry.get("tp_price", 0)
    sl_price = entry.get("sl_price", 0)
    lot_size = entry.get("lot_size", 0.01)
    trade_type = entry.get("type", "BUY")

    # Win/Loss feedback
    if pnl > 0:
        recs.append({"type": "positive", "icon": "✅", "text_fa": f"معامله موفق! سود ${round(pnl, 2)} ثبت شد."})
    elif pnl < 0:
        recs.append({"type": "warning", "icon": "⚠️", "text_fa": f"معامله با ضرر ${round(abs(pnl), 2)} بسته شد. دلایل ضرر را بررسی کنید."})
    else:
        recs.append({"type": "info", "icon": "ℹ️", "text_fa": "معامله بدون سود یا ضرر بسته شد (Break Even)."})

    # Emotion analysis
    emo_scores = {e["id"]: e["score"] for e in EMOTIONS}
    before_score = emo_scores.get(emotion_before, 0)
    after_score = emo_scores.get(emotion_after, 0)

    if before_score <= -2:
        emo_name = next((e["name_fa"] for e in EMOTIONS if e["id"] == emotion_before), emotion_before)
        recs.append({"type": "critical", "icon": "🧠", "text_fa": f"هشدار: ورود با احساس «{emo_name}» معمولاً نتایج ضعیفی دارد. قبل از ورود بعدی، آرامش خود را حفظ کنید."})
    elif before_score >= 1 and pnl > 0:
        recs.append({"type": "positive", "icon": "😎", "text_fa": "ورود با ذهن آرام و نتیجه مثبت — ادامه دهید!"})

    if after_score < before_score and pnl < 0:
        recs.append({"type": "info", "icon": "💭", "text_fa": "ضرر باعث افت روحیه شده. قبل از معامله بعدی استراحت کنید."})

    # Plan adherence
    if not followed_plan:
        if pnl > 0:
            recs.append({"type": "warning", "icon": "📐", "text_fa": "سود خارج از پلن — این تکرارپذیر نیست. به پلن خود پایبند بمانید."})
        else:
            recs.append({"type": "critical", "icon": "📐", "text_fa": "ضرر خارج از پلن! رعایت پلن مهم‌ترین عامل موفقیت بلندمدت است."})
    elif followed_plan and pnl > 0:
        recs.append({"type": "positive", "icon": "📐", "text_fa": "پلن رعایت شد و نتیجه مثبت — عالی!"})

    # Risk/Reward analysis
    if entry_price and sl_price and tp_price:
        if trade_type == "BUY":
            risk = abs(entry_price - sl_price)
            reward = abs(tp_price - entry_price)
        else:
            risk = abs(sl_price - entry_price)
            reward = abs(entry_price - tp_price)
        if risk > 0:
            rr = round(reward / risk, 2)
            if rr < 1:
                recs.append({"type": "warning", "icon": "⚖️", "text_fa": f"R:R = {rr} — ریسک به ریوارد ضعیف. حداقل 1:1.5 توصیه می‌شود."})
            elif rr >= 2:
                recs.append({"type": "positive", "icon": "⚖️", "text_fa": f"R:R = {rr} — نسبت عالی!"})
            else:
                recs.append({"type": "info", "icon": "⚖️", "text_fa": f"R:R = {rr}"})

    # Tag-based insights
    if "overtrading" in tags:
        recs.append({"type": "critical", "icon": "🛑", "text_fa": "اورتریدینگ شناسایی شد — تعداد معاملات روزانه را محدود کنید."})
    if "moved_sl" in tags:
        recs.append({"type": "warning", "icon": "🛡️", "text_fa": "SL جابجا شده — هرگز SL را به سمت ضرر بیشتر جابجا نکنید."})
    if "revenge" in tags or emotion_before == "revenge":
        recs.append({"type": "critical", "icon": "😤", "text_fa": "معامله انتقامی! بعد از ضرر حداقل ۳۰ دقیقه استراحت کنید."})
    if "perfect_entry" in tags and pnl > 0:
        recs.append({"type": "positive", "icon": "🎯", "text_fa": "ورود عالی — این ستاپ را مستندسازی کنید."})

    # Rating-based
    if rating <= 2 and pnl > 0:
        recs.append({"type": "info", "icon": "🤔", "text_fa": "سود کردید اما خودتان امتیاز پایین دادید — چرا؟ دلیل را مستند کنید."})
    if rating >= 4 and pnl < 0:
        recs.append({"type": "info", "icon": "🤔", "text_fa": "امتیاز بالا اما ضرر — ستاپ خوب بود ولی بازار مخالف بود. این طبیعی است."})

    # Analytics-based insights
    if analytics and analytics.get("total", 0) >= 5:
        wr = analytics.get("win_rate", 0)
        if wr < 40:
            recs.append({"type": "warning", "icon": "📊", "text_fa": f"نرخ برد شما {wr}% است. استراتژی و ورودهای خود را بازبینی کنید."})
        elif wr >= 60:
            recs.append({"type": "positive", "icon": "📊", "text_fa": f"نرخ برد {wr}% عالی است — ثبات را حفظ کنید."})

        # Check if specific emotion has bad record
        for em_id, em_stat in analytics.get("emotion_stats", {}).items():
            if em_stat.get("count", 0) >= 3 and em_stat.get("win_rate", 0) < 30:
                em_name = next((e["name_fa"] for e in EMOTIONS if e["id"] == em_id), em_id)
                if em_id == emotion_before:
                    recs.append({"type": "critical", "icon": "📉", "text_fa": f"در حالت «{em_name}» فقط {em_stat['win_rate']}% برد دارید. در این حالت معامله نکنید."})

    return recs


def export_entries(email, format="json"):
    """Export journal entries."""
    data = _load(email)
    entries = data.get("entries", [])
    if format == "csv":
        import csv
        import io
        output = io.StringIO()
        if entries:
            fields = ["id", "created_at", "symbol", "type", "timeframe", "strategy_name",
                       "entry_price", "exit_price", "tp_price", "sl_price", "lot_size",
                       "pnl", "pnl_pips", "emotion_before", "emotion_after", "rating",
                       "followed_plan", "tags", "notes", "lesson"]
            writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for e in entries:
                row = {k: e.get(k, "") for k in fields}
                row["tags"] = ",".join(e.get("tags", []))
                writer.writerow(row)
        return output.getvalue()
    else:
        return json.dumps(entries, ensure_ascii=False, indent=2)
