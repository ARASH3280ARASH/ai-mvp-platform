"""
Whilber-AI — Smart Profit & Trailing Engine
================================================
6 profit-taking methods, 4 trailing models.
Market-specific adaptive rules.
Post-trade report with analysis & lessons.
"""

import math

# ══════ PROFIT-TAKING METHODS ══════

PROFIT_METHODS = {
    "half_rr1": {
        "id": "half_rr1",
        "name_fa": "½ در R:R=1 + باقی R:R=2",
        "icon": "💰",
        "desc_fa": "وقتی سود به اندازه ریسک شد (R:R=1)، نصف ببندید و SL بقیه به ورود برود. باقی تا R:R=2.",
        "guide_fa": "بهترین برای مبتدیان. ریسک سریع صفر می‌شود و فرصت سود بیشتر باقی می‌ماند.",
        "difficulty": "beginner",
    },
    "thirds": {
        "id": "thirds",
        "name_fa": "⅓ + ⅓ + ⅓ پلکانی",
        "icon": "📊",
        "desc_fa": "سه هدف تعریف کنید. در هر هدف ⅓ ببندید و SL را جابجا کنید.",
        "guide_fa": "نیاز به ۳ TP دارد. مناسب سوینگ تریدرها که اهداف بزرگ دارند.",
        "difficulty": "intermediate",
    },
    "be_50": {
        "id": "be_50",
        "name_fa": "۵۰% در Break Even",
        "icon": "🟡",
        "desc_fa": "وقتی قیمت به اندازه ۵۰% SL سود رفت، نصف ببندید. SL باقی به ورود.",
        "guide_fa": "محافظه‌کارانه‌ترین روش. سریع‌ترین سیو سود. مناسب بازارهای پرنوسان.",
        "difficulty": "beginner",
    },
    "step_pips": {
        "id": "step_pips",
        "name_fa": "سیو پلکانی (هر X پیپ)",
        "icon": "📐",
        "desc_fa": "هر مقدار مشخص پیپ سود، بخشی ببندید. مثلاً هر ۵۰ پیپ ۲۵% ببندید.",
        "guide_fa": "مناسب طلا و شاخص‌ها. نوسان بالا = سیو مکرر.",
        "difficulty": "intermediate",
    },
    "session_based": {
        "id": "session_based",
        "name_fa": "سیو بر اساس سشن",
        "icon": "🕐",
        "desc_fa": "در پایان هر سشن معاملاتی بخشی ببندید. مثلاً انتهای لندن ۵۰% ببند.",
        "guide_fa": "مناسب فارکس. نقدینگی در تغییر سشن کاهش می‌یابد.",
        "difficulty": "advanced",
    },
    "reversal_signal": {
        "id": "reversal_signal",
        "name_fa": "سیو با سیگنال برگشت",
        "icon": "🔄",
        "desc_fa": "وقتی اندیکاتورها سیگنال برگشت دادند، کل ببندید.",
        "guide_fa": "پیشرفته. نیاز به تسلط بر اندیکاتورها. بیشترین سود اما بیشترین ریسک.",
        "difficulty": "advanced",
    },
}

# ══════ TRAILING MODELS ══════

TRAILING_MODELS = {
    "fixed": {
        "id": "fixed",
        "name_fa": "تریلینگ فاصله ثابت",
        "icon": "📏",
        "desc_fa": "SL را با فاصله ثابت (مثلاً ۵۰ پیپ) پشت قیمت حرکت دهید.",
        "guide_fa": "ساده‌ترین روش. SL همیشه X پیپ عقب‌تر از بهترین قیمت است.",
        "when_fa": "وقتی معامله به R:R=1 رسید فعال کنید.",
        "params": {"distance_pips": "فاصله ثابت (پیپ)"},
        "difficulty": "beginner",
    },
    "atr": {
        "id": "atr",
        "name_fa": "تریلینگ ATR (نوسان‌محور)",
        "icon": "📈",
        "desc_fa": "SL بر اساس ATR (شاخص نوسان) تنظیم می‌شود. در بازار آرام نزدیک‌تر، در بازار شلوغ دورتر.",
        "guide_fa": "بهترین روش برای بازارهای پرنوسان مثل طلا و کریپتو. خودکار با نوسان تنظیم می‌شود.",
        "when_fa": "از ابتدا یا بعد از Break Even.",
        "params": {"atr_period": "دوره ATR (معمولاً ۱۴)", "atr_multiplier": "ضریب ATR (معمولاً ۲)"},
        "difficulty": "intermediate",
    },
    "structure": {
        "id": "structure",
        "name_fa": "تریلینگ ساختاری (سویینگ)",
        "icon": "🏗️",
        "desc_fa": "SL را زیر آخرین سویینگ لو (BUY) یا بالای آخرین سویینگ های (SELL) بگذارید.",
        "guide_fa": "حرفه‌ای‌ترین روش. SL در نقاط ساختاری بازار قرار می‌گیرد.",
        "when_fa": "وقتی روند مشخص شد و سویینگ جدید تشکیل شد.",
        "params": {"lookback_bars": "تعداد کندل برای یافتن سویینگ (معمولاً ۵-۱۰)"},
        "difficulty": "advanced",
    },
    "step": {
        "id": "step",
        "name_fa": "تریلینگ پلکانی",
        "icon": "🪜",
        "desc_fa": "هر X پیپ که قیمت جلو رفت، SL هم X پیپ جلو بیاید.",
        "guide_fa": "مناسب شاخص‌ها و روندهای قوی. SL پله‌پله جلو می‌آید.",
        "when_fa": "بعد از رسیدن به Break Even.",
        "params": {"step_pips": "اندازه هر پله (پیپ)"},
        "difficulty": "beginner",
    },
}


def get_profit_trailing_config():
    """Return all methods and models for frontend."""
    return {
        "profit_methods": PROFIT_METHODS,
        "trailing_models": TRAILING_MODELS,
    }


def calculate_profit_plan(trade, method_id, params=None):
    """
    Calculate profit-taking plan for a trade.
    trade: {entry, sl, tp1, tp2, tp3, direction, symbol, lot_size}
    """
    params = params or {}
    method = PROFIT_METHODS.get(method_id)
    if not method:
        return {"success": False, "error": "Invalid method"}

    entry = float(trade.get("entry_price", 0))
    sl = float(trade.get("sl_price", 0))
    tp1 = float(trade.get("tp_price", 0) or trade.get("tp1_price", 0) or 0)
    tp2 = float(trade.get("tp2_price", 0))
    tp3 = float(trade.get("tp3_price", 0))
    direction = trade.get("direction", "BUY")
    lot = float(trade.get("lot_size", 0.01))

    pip = _get_pip(trade.get("symbol", "XAUUSD"))
    tv = _get_tv(trade.get("symbol", "XAUUSD"))

    if direction == "BUY":
        sl_pips = (entry - sl) / pip
        tp1_pips = (tp1 - entry) / pip if tp1 > 0 else sl_pips * 2
    else:
        sl_pips = (sl - entry) / pip
        tp1_pips = (entry - tp1) / pip if tp1 > 0 else sl_pips * 2

    if sl_pips <= 0:
        return {"success": False, "error": "SL invalid"}

    steps = []

    if method_id == "half_rr1":
        rr1_price = entry + sl_pips * pip if direction == "BUY" else entry - sl_pips * pip
        rr2_price = entry + sl_pips * 2 * pip if direction == "BUY" else entry - sl_pips * 2 * pip
        steps = [
            {"trigger_price": round(rr1_price, 6), "trigger_fa": "R:R = 1.0",
             "close_pct": 50, "close_lot": round(lot * 0.5, 2),
             "new_sl": entry, "new_sl_fa": "SL → ورود (ریسک صفر)",
             "pnl": round(sl_pips * tv * lot * 0.5, 2),
             "desc_fa": "نصف حجم ببندید. SL باقی‌مانده به قیمت ورود."},
            {"trigger_price": round(rr2_price, 6), "trigger_fa": "R:R = 2.0",
             "close_pct": 50, "close_lot": round(lot * 0.5, 2),
             "new_sl": None, "new_sl_fa": "کامل بسته",
             "pnl": round(sl_pips * 2 * tv * lot * 0.5, 2),
             "desc_fa": "باقی‌مانده ببندید. یا Trailing بگذارید برای سود بیشتر."},
        ]

    elif method_id == "thirds":
        if tp1 <= 0:
            return {"success": False, "error": "حداقل TP1 لازم است"}
        levels = [tp1]
        if tp2 > 0:
            levels.append(tp2)
        if tp3 > 0:
            levels.append(tp3)
        while len(levels) < 3:
            last = levels[-1]
            nxt = last + sl_pips * pip if direction == "BUY" else last - sl_pips * pip
            levels.append(round(nxt, 6))
        pct = round(100 / len(levels))
        prev_sl = sl
        for i, lv in enumerate(levels):
            new_sl = levels[i - 1] if i > 0 else entry
            dist = abs(lv - entry) / pip
            steps.append({
                "trigger_price": round(lv, 6), "trigger_fa": f"TP{i + 1}",
                "close_pct": pct, "close_lot": round(lot * pct / 100, 2),
                "new_sl": round(new_sl, 6),
                "new_sl_fa": f"SL → {('ورود' if i == 0 else 'TP' + str(i))}",
                "pnl": round(dist * tv * lot * pct / 100, 2),
                "desc_fa": f"⅓ ببندید. SL باقی‌مانده به {'ورود' if i == 0 else 'TP' + str(i)} منتقل شود.",
            })

    elif method_id == "be_50":
        be_trigger = sl_pips * 0.5
        be_price = entry + be_trigger * pip if direction == "BUY" else entry - be_trigger * pip
        steps = [
            {"trigger_price": round(be_price, 6), "trigger_fa": "50% مسیر SL",
             "close_pct": 50, "close_lot": round(lot * 0.5, 2),
             "new_sl": entry, "new_sl_fa": "SL → ورود",
             "pnl": round(be_trigger * tv * lot * 0.5, 2),
             "desc_fa": "نصف ببندید. سریع‌ترین سیو سود. بقیه با Trailing."},
            {"trigger_price": round(tp1 if tp1 > 0 else (entry + sl_pips * 2 * pip if direction == "BUY" else entry - sl_pips * 2 * pip), 6),
             "trigger_fa": "TP1",
             "close_pct": 50, "close_lot": round(lot * 0.5, 2),
             "new_sl": None, "new_sl_fa": "کامل بسته",
             "pnl": round(tp1_pips * tv * lot * 0.5, 2) if tp1 > 0 else round(sl_pips * 2 * tv * lot * 0.5, 2),
             "desc_fa": "باقی‌مانده ببندید."},
        ]

    elif method_id == "step_pips":
        step_size = float(params.get("step_pips", 50))
        close_pct_per_step = float(params.get("close_pct", 25))
        remaining = 100
        step_n = 0
        while remaining > 0 and step_n < 6:
            step_n += 1
            dist = step_size * step_n
            price = entry + dist * pip if direction == "BUY" else entry - dist * pip
            pct = min(close_pct_per_step, remaining)
            prev_price = entry + step_size * (step_n - 1) * pip if direction == "BUY" else entry - step_size * (step_n - 1) * pip
            steps.append({
                "trigger_price": round(price, 6),
                "trigger_fa": f"+{int(dist)} پیپ",
                "close_pct": int(pct), "close_lot": round(lot * pct / 100, 2),
                "new_sl": round(prev_price, 6) if step_n > 1 else entry,
                "new_sl_fa": f"SL → +{int(step_size * (step_n - 1))} پیپ" if step_n > 1 else "SL → ورود",
                "pnl": round(dist * tv * lot * pct / 100, 2),
                "desc_fa": f"{int(pct)}% ببندید در +{int(dist)} پیپ سود.",
            })
            remaining -= pct

    elif method_id == "session_based":
        steps = [
            {"trigger_price": 0, "trigger_fa": "پایان سشن آسیا",
             "close_pct": 0, "close_lot": 0,
             "new_sl": entry, "new_sl_fa": "SL → ورود (اگر در سود)",
             "pnl": 0,
             "desc_fa": "اگر در سود هستید SL به ورود ببرید. نقدینگی کم می‌شود."},
            {"trigger_price": 0, "trigger_fa": "پایان سشن لندن",
             "close_pct": 50, "close_lot": round(lot * 0.5, 2),
             "new_sl": None, "new_sl_fa": "نصف ببند",
             "pnl": 0,
             "desc_fa": "انتهای لندن نقدینگی افت می‌کند. نصف سیو کنید."},
            {"trigger_price": 0, "trigger_fa": "پایان سشن نیویورک",
             "close_pct": 50, "close_lot": round(lot * 0.5, 2),
             "new_sl": None, "new_sl_fa": "کامل ببند",
             "pnl": 0,
             "desc_fa": "آخر روز. سواپ شبانه. بهتره ببندید مگر سوینگ باشد."},
        ]

    elif method_id == "reversal_signal":
        steps = [
            {"trigger_price": 0, "trigger_fa": "سیگنال RSI برگشت",
             "close_pct": 50, "close_lot": round(lot * 0.5, 2),
             "new_sl": entry, "new_sl_fa": "SL → ورود",
             "pnl": 0,
             "desc_fa": "وقتی RSI از اشباع خرید/فروش برگشت، نصف ببندید."},
            {"trigger_price": 0, "trigger_fa": "شکست خط روند / کراس MACD",
             "close_pct": 50, "close_lot": round(lot * 0.5, 2),
             "new_sl": None, "new_sl_fa": "کامل ببند",
             "pnl": 0,
             "desc_fa": "وقتی ساختار بازار تغییر کرد، کل ببندید."},
        ]

    # Total PnL
    total_pnl = sum(s.get("pnl", 0) for s in steps)

    return {
        "success": True,
        "method": method,
        "steps": steps,
        "total_pnl": round(total_pnl, 2),
        "total_steps": len(steps),
    }


def calculate_trailing(trade, model_id, params=None, current_price=None, highest_price=None):
    """
    Calculate trailing stop level.
    Returns new SL price and info.
    """
    params = params or {}
    model = TRAILING_MODELS.get(model_id)
    if not model:
        return {"success": False, "error": "Invalid model"}

    entry = float(trade.get("entry_price", 0))
    sl = float(trade.get("sl_price", 0))
    direction = trade.get("direction", "BUY")
    symbol = trade.get("symbol", "XAUUSD")
    pip = _get_pip(symbol)

    price = float(current_price or entry)
    best = float(highest_price or price)

    new_sl = sl
    info = ""

    if model_id == "fixed":
        dist = float(params.get("distance_pips", 50)) * pip
        if direction == "BUY":
            new_sl = max(sl, best - dist)
            info = f"فاصله ثابت {params.get('distance_pips', 50)} پیپ از بالاترین قیمت ({best})"
        else:
            lowest = float(highest_price or price)  # For sell, this tracks lowest
            new_sl = min(sl, lowest + dist) if lowest + dist < sl else sl
            info = f"فاصله ثابت {params.get('distance_pips', 50)} پیپ"

    elif model_id == "atr":
        atr_val = float(params.get("current_atr", 0))
        mult = float(params.get("atr_multiplier", 2.0))
        if atr_val <= 0:
            atr_val = _default_atr(symbol)
        dist = atr_val * mult
        if direction == "BUY":
            new_sl = max(sl, best - dist)
        else:
            new_sl = min(sl, best + dist) if sl > 0 else best + dist
        info = f"ATR={atr_val:.4f} × {mult} = فاصله {dist:.4f}"

    elif model_id == "step":
        step = float(params.get("step_pips", 30)) * pip
        if direction == "BUY":
            steps_moved = math.floor((best - entry) / step)
            if steps_moved > 0:
                new_sl = max(sl, entry + (steps_moved - 1) * step)
            info = f"{steps_moved} پله طی شده. SL = ورود + {max(0, steps_moved - 1)} پله"
        else:
            steps_moved = math.floor((entry - best) / step)
            if steps_moved > 0:
                new_sl = min(sl, entry - (steps_moved - 1) * step)
            info = f"{steps_moved} پله"

    elif model_id == "structure":
        swing = float(params.get("last_swing", 0))
        buffer = float(params.get("buffer_pips", 5)) * pip
        if swing > 0:
            if direction == "BUY":
                new_sl = max(sl, swing - buffer)
            else:
                new_sl = min(sl, swing + buffer)
            info = f"آخرین سویینگ: {swing} + بافر {params.get('buffer_pips', 5)} پیپ"
        else:
            info = "سویینگ جدیدی تشکیل نشده"

    return {
        "success": True,
        "model": model,
        "new_sl": round(new_sl, 6),
        "old_sl": sl,
        "moved": abs(new_sl - sl) > pip * 0.1,
        "info_fa": info,
    }


def recommend_for_market(symbol, sl_pips, tp_pips):
    """Recommend best profit method and trailing model for a market."""
    market = _get_market_type(symbol)

    if market == "metals":
        return {
            "profit_method": "step_pips",
            "profit_reason_fa": "طلا نوسان بالایی دارد. سیو پلکانی بهترین روش است.",
            "profit_params": {"step_pips": 50, "close_pct": 25},
            "trailing_model": "atr",
            "trailing_reason_fa": "ATR با نوسان طلا سازگار است. در بازار آرام نزدیک‌تر، در شلوغ دورتر.",
            "trailing_params": {"atr_multiplier": 2.0},
        }
    elif market == "crypto":
        return {
            "profit_method": "half_rr1",
            "profit_reason_fa": "کریپتو غیرقابل پیش‌بینی است. سریع سیو کنید.",
            "profit_params": {},
            "trailing_model": "atr",
            "trailing_reason_fa": "ATR بزرگ برای نوسان شدید کریپتو.",
            "trailing_params": {"atr_multiplier": 3.0},
        }
    elif market == "indices":
        return {
            "profit_method": "be_50",
            "profit_reason_fa": "شاخص‌ها گپ دارند. سریع سیو کنید.",
            "profit_params": {},
            "trailing_model": "step",
            "trailing_reason_fa": "شاخص‌ها روند قوی دارند. پلکانی بهترین است.",
            "trailing_params": {"step_pips": int(sl_pips * 0.5)},
        }
    else:  # forex
        if tp_pips > sl_pips * 2.5:
            return {
                "profit_method": "thirds",
                "profit_reason_fa": "TP بزرگ — سیو سود پلکانی ⅓ مناسب است.",
                "profit_params": {},
                "trailing_model": "fixed",
                "trailing_reason_fa": "فارکس با فاصله ثابت خوب کار می‌کند.",
                "trailing_params": {"distance_pips": int(sl_pips * 0.7)},
            }
        else:
            return {
                "profit_method": "half_rr1",
                "profit_reason_fa": "TP کوتاه — نصف سریع ببندید.",
                "profit_params": {},
                "trailing_model": "fixed",
                "trailing_reason_fa": "ساده و مؤثر برای فارکس.",
                "trailing_params": {"distance_pips": int(sl_pips * 0.7)},
            }


# ══════ POST-TRADE REPORT ══════

def generate_full_report(trade_input, trade_result, profit_method_used=None, trailing_used=None):
    """
    Complete post-trade report with analysis, scoring, lessons.
    """
    symbol = trade_input.get("symbol", "XAUUSD")
    direction = trade_input.get("direction", "BUY")
    entry = float(trade_input.get("entry_price", 0))
    sl = float(trade_input.get("sl_price", 0))
    tp = float(trade_input.get("tp_price", 0) or trade_input.get("tp1_price", 0) or 0)

    outcome = trade_result.get("outcome", "unknown")
    pnl = float(trade_result.get("pnl", 0))
    exit_price = float(trade_result.get("exit_price", 0))
    exit_reason = trade_result.get("exit_reason", "manual")
    followed_plan = trade_result.get("followed_plan", True)
    bars_held = int(trade_result.get("bars_held", 0))
    partials = trade_result.get("partial_closes", [])

    pip = _get_pip(symbol)
    sl_pips = abs(entry - sl) / pip if sl > 0 else 0
    tp_pips = abs(tp - entry) / pip if tp > 0 else 0
    rr = tp_pips / sl_pips if sl_pips > 0 and tp_pips > 0 else 0

    sections = []
    score = 50
    lessons = []
    grade_details = []

    # 1. Outcome
    if outcome == "win":
        score += 15
        sections.append({
            "title_fa": "✅ نتیجه: برد",
            "text_fa": f"سود ${pnl:.2f} — خروج با {_exit_text(exit_reason)}",
            "color": "green",
        })
    else:
        sections.append({
            "title_fa": "❌ نتیجه: باخت",
            "text_fa": f"ضرر ${abs(pnl):.2f} — {_exit_text(exit_reason)}",
            "color": "red",
        })

    # 2. Plan adherence
    if followed_plan:
        score += 15
        sections.append({"title_fa": "📋 رعایت پلن: بله ✓", "text_fa": "شما به پلن پایبند بودید. این مهم‌ترین عامل موفقیت بلندمدت است.", "color": "green"})
        grade_details.append("پلن: +15")
    else:
        score -= 10
        sections.append({"title_fa": "⚠️ رعایت پلن: خیر ✗", "text_fa": "عدم رعایت پلن. حتی اگر سود کردید، این عادت خطرناک است.", "color": "red"})
        lessons.append("🔑 درس اصلی: همیشه به پلن پایبند باشید. یک ضرر با پلن بهتر از یک سود بدون پلن است.")
        grade_details.append("پلن: -10")

    # 3. R:R analysis
    if rr >= 2:
        score += 10
        sections.append({"title_fa": f"🎯 R:R = {rr:.1f} — عالی", "text_fa": "نسبت ریسک/ریوارد عالی. حتی با ۴۰% نرخ برد سودآور خواهید بود.", "color": "green"})
    elif rr >= 1.5:
        score += 5
        sections.append({"title_fa": f"🎯 R:R = {rr:.1f} — مناسب", "text_fa": "قابل قبول. سعی کنید R:R=2 یا بالاتر داشته باشید.", "color": "yellow"})
    elif rr > 0:
        sections.append({"title_fa": f"⚠️ R:R = {rr:.1f} — ضعیف", "text_fa": "R:R کمتر از ۱.۵ برای سودآوری بلندمدت کافی نیست.", "color": "red"})
        lessons.append("💡 قبل از ورود، مطمئن شوید R:R حداقل ۱.۵ باشد.")

    # 4. Profit taking analysis
    if profit_method_used:
        pm = PROFIT_METHODS.get(profit_method_used, {})
        if partials:
            score += 5
            sections.append({"title_fa": f"💰 سیو سود: {pm.get('name_fa', profit_method_used)}", "text_fa": f"{len(partials)} بار سیو سود انجام شد. خوب!", "color": "green"})
        else:
            sections.append({"title_fa": "💰 سیو سود: انجام نشد", "text_fa": "سیو سود پلکانی انجام نشد. دفعه بعد حتماً طبق پلن سیو کنید.", "color": "yellow"})
            lessons.append("💰 سیو سود را فراموش نکنید. سود تا زمانی که سیو نشده واقعی نیست.")

    # 5. Trailing analysis
    if trailing_used:
        tm = TRAILING_MODELS.get(trailing_used, {})
        score += 5
        sections.append({"title_fa": f"🔄 Trailing: {tm.get('name_fa', trailing_used)}", "text_fa": "تریلینگ استفاده شد. این به حفظ سود کمک می‌کند.", "color": "green"})

    # 6. Entry quality
    if exit_reason == "sl" and bars_held <= 3:
        sections.append({"title_fa": "⚡ خروج سریع با SL", "text_fa": f"فقط {bars_held} کندل. ممکن است نقطه ورود ضعیف بوده یا SL خیلی نزدیک.", "color": "yellow"})
        lessons.append("📍 نقطه ورود را بازبینی کنید. آیا تأیید کافی داشتید؟")
    elif exit_reason == "tp" and bars_held <= 2:
        score += 5
        sections.append({"title_fa": "⚡ TP سریع!", "text_fa": "معامله سریع به TP رسید. ورود عالی!", "color": "green"})

    # 7. Market-specific
    market = _get_market_type(symbol)
    if market == "metals" and outcome == "loss" and sl_pips < 40:
        lessons.append("🥇 طلا: SL شما خیلی نزدیک بود. برای طلا حداقل ۴۰-۸۰ پیپ SL توصیه می‌شود.")
    if market == "crypto" and outcome == "loss":
        lessons.append("₿ کریپتو: حجم را کمتر بگیرید. نوسان شدید عادی است.")
    if market == "indices" and exit_reason == "sl" and bars_held <= 1:
        lessons.append("📈 شاخص: ممکن است گپ بازگشایی SL را فعال کرده. جمعه معامله جدید باز نکنید.")

    # General lessons
    if outcome == "win" and followed_plan:
        lessons.append("👏 آفرین! معامله خوبی بود. همین پلن را ادامه بدهید.")
    elif outcome == "loss" and followed_plan:
        lessons.append("💪 ضرر با رعایت پلن = معامله خوب. ضرر بخشی از تریدینگ است. ادامه بدهید.")

    # Grade
    score = min(100, max(0, score))
    if score >= 85:
        grade = "A+"
    elif score >= 75:
        grade = "A"
    elif score >= 65:
        grade = "B"
    elif score >= 50:
        grade = "C"
    elif score >= 35:
        grade = "D"
    else:
        grade = "F"

    return {
        "success": True,
        "score": score,
        "grade": grade,
        "outcome": outcome,
        "pnl": round(pnl, 2),
        "sections": sections,
        "lessons": lessons,
        "grade_details": grade_details,
        "summary_fa": f"{'برد' if outcome == 'win' else 'باخت'} ${abs(pnl):.2f} | نمره: {grade} ({score}/100) | {'با پلن ✓' if followed_plan else 'بدون پلن ✗'}",
    }


# ══════ HELPERS ══════

try:
    from backend.api.risk_engine import MARKET_SPECS, DEFAULT_SPEC
except ImportError:
    MARKET_SPECS = {}
    DEFAULT_SPEC = {"pip": 0.0001, "tick_value_per_lot": 10.0, "type": "forex", "avg_atr_h1": 0.001}

def _get_pip(symbol):
    spec = MARKET_SPECS.get(symbol, DEFAULT_SPEC)
    return spec.get("pip", 0.0001)

def _get_tv(symbol):
    spec = MARKET_SPECS.get(symbol, DEFAULT_SPEC)
    return spec.get("tick_value_per_lot", 10.0)

def _get_market_type(symbol):
    spec = MARKET_SPECS.get(symbol, DEFAULT_SPEC)
    return spec.get("type", "forex")

def _default_atr(symbol):
    spec = MARKET_SPECS.get(symbol, DEFAULT_SPEC)
    return spec.get("avg_atr_h1", 0.001)

def _exit_text(reason):
    m = {"tp": "حد سود (عالی!)", "sl": "حد ضرر (مدیریت‌شده)", "trailing": "تریلینگ (سود حفظ شد)",
         "break_even": "سربه‌سر", "time": "خروج زمانی", "manual": "خروج دستی", "partial": "سیو سود"}
    return m.get(reason, reason)
