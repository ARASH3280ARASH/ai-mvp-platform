"""
Whilber-AI — Donchian Channel Strategy Pack (5 Sub-Strategies)
================================================================
DON_01: Classic Donchian Breakout (20-period high/low break)
DON_02: Donchian Middle Line Cross (price crosses midline)
DON_03: Donchian Squeeze (channel narrows → breakout)
DON_04: Donchian + ATR Filter (breakout with volatility confirm)
DON_05: Turtle Trading System (20/55 dual channel)
"""

import numpy as np

CATEGORY_ID = "DON"
CATEGORY_NAME = "Donchian Channel"
CATEGORY_FA = "کانال دونچیان"
ICON = "📊"
COLOR = "#00bcd4"


def _donchian(high, low, period=20):
    """Calculate Donchian Channel."""
    if len(high) < period:
        return None, None, None
    upper = np.array([np.max(high[max(0,i-period+1):i+1]) for i in range(len(high))])
    lower = np.array([np.min(low[max(0,i-period+1):i+1]) for i in range(len(high))])
    middle = (upper + lower) / 2
    return upper, lower, middle


def _atr(high, low, close, period=14):
    """Calculate ATR."""
    if len(high) < period + 1:
        return None
    tr = np.maximum(high[1:] - low[1:],
         np.maximum(abs(high[1:] - close[:-1]), abs(low[1:] - close[:-1])))
    atr = np.zeros(len(tr))
    atr[period-1] = np.mean(tr[:period])
    for i in range(period, len(tr)):
        atr[i] = (atr[i-1] * (period-1) + tr[i]) / period
    return np.concatenate([[0], atr])


def _make_setup(direction, entry, atr_val, pip, rr_min=1.5):
    """Build setup dict with SL/TP, enforce R:R >= 1.5."""
    if atr_val is None or atr_val <= 0:
        return None
    sl_dist = atr_val * 1.5
    tp1_dist = sl_dist * rr_min
    tp2_dist = sl_dist * 3.0

    if direction == "BUY":
        sl = entry - sl_dist
        tp1 = entry + tp1_dist
        tp2 = entry + tp2_dist
    else:
        sl = entry + sl_dist
        tp1 = entry - tp1_dist
        tp2 = entry - tp2_dist

    rr1 = tp1_dist / sl_dist if sl_dist > 0 else 0
    rr2 = tp2_dist / sl_dist if sl_dist > 0 else 0

    if rr1 < rr_min:
        return None

    return {
        "has_setup": True,
        "direction": direction,
        "direction_fa": "خرید" if direction == "BUY" else "فروش",
        "entry": round(entry, 6),
        "stop_loss": round(sl, 6),
        "tp1": round(tp1, 6),
        "tp2": round(tp2, 6),
        "rr1": round(rr1, 2),
        "rr2": round(rr2, 2),
        "sl_pips": round(sl_dist / pip, 1) if pip > 0 else 0,
        "tp1_pips": round(tp1_dist / pip, 1) if pip > 0 else 0,
    }


def _pip_size(symbol):
    """Get pip size for symbol."""
    s = symbol.upper()
    if "JPY" in s: return 0.01
    if "XAU" in s: return 0.1
    if "XAG" in s: return 0.01
    if "BTC" in s: return 1.0
    if s in ("NAS100","US30","SPX500","GER40","UK100"): return 1.0
    return 0.0001


def _neutral(reason_fa):
    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": reason_fa,
            "setup": {"has_setup": False}}


# ── DON_01: Classic Donchian Breakout ──
def don_01(df, indicators, symbol, timeframe):
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(c) < 25:
        return _neutral("داده کافی نیست")

    upper, lower, middle = _donchian(h, l, 20)
    atr = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]
    prev = c[-2]

    if upper is None:
        return _neutral("محاسبه دونچیان ناموفق")

    # Breakout above upper
    if price > upper[-2] and prev <= upper[-3]:
        setup = _make_setup("BUY", price, atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 75,
                    "reason_fa": f"شکست صعودی کانال دونچیان ۲۰ — قیمت {price:.5f} بالای سقف {upper[-2]:.5f}",
                    "setup": setup}

    # Breakout below lower
    if price < lower[-2] and prev >= lower[-3]:
        setup = _make_setup("SELL", price, atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 75,
                    "reason_fa": f"شکست نزولی کانال دونچیان ۲۰ — قیمت {price:.5f} زیر کف {lower[-2]:.5f}",
                    "setup": setup}

    return _neutral("شکست کانال دونچیان شناسایی نشد")


# ── DON_02: Middle Line Cross ──
def don_02(df, indicators, symbol, timeframe):
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(c) < 25:
        return _neutral("داده کافی نیست")

    upper, lower, middle = _donchian(h, l, 20)
    atr = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]
    prev = c[-2]

    if middle is None:
        return _neutral("محاسبه خط میانی ناموفق")

    # Cross above middle
    if price > middle[-1] and prev <= middle[-2]:
        width = upper[-1] - lower[-1]
        if width > 0:
            conf = min(70, 40 + int(width / (atr[-1] if atr is not None and atr[-1] > 0 else 1) * 10))
            setup = _make_setup("BUY", price, atr[-1] if atr is not None else None, pip)
            if setup:
                return {"signal": "BUY", "confidence": conf,
                        "reason_fa": f"عبور صعودی از خط میانی دونچیان — قیمت بالای {middle[-1]:.5f}",
                        "setup": setup}

    # Cross below middle
    if price < middle[-1] and prev >= middle[-2]:
        setup = _make_setup("SELL", price, atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 60,
                    "reason_fa": f"عبور نزولی از خط میانی دونچیان — قیمت زیر {middle[-1]:.5f}",
                    "setup": setup}

    return _neutral("عبور خط میانی دونچیان شناسایی نشد")


# ── DON_03: Donchian Squeeze ──
def don_03(df, indicators, symbol, timeframe):
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(c) < 30:
        return _neutral("داده کافی نیست")

    upper, lower, middle = _donchian(h, l, 20)
    atr = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]

    if upper is None:
        return _neutral("محاسبه دونچیان ناموفق")

    # Channel width
    width_now = upper[-1] - lower[-1]
    width_avg = np.mean(upper[-20:] - lower[-20:])

    # Squeeze: current width < 50% of average
    if width_now < width_avg * 0.5:
        # Direction from price position
        pos_in_channel = (price - lower[-1]) / width_now if width_now > 0 else 0.5

        if pos_in_channel > 0.7:
            setup = _make_setup("BUY", price, atr[-1] if atr is not None else None, pip)
            if setup:
                return {"signal": "BUY", "confidence": 65,
                        "reason_fa": f"فشردگی کانال دونچیان + قیمت نزدیک سقف — آماده شکست صعودی",
                        "setup": setup}
        elif pos_in_channel < 0.3:
            setup = _make_setup("SELL", price, atr[-1] if atr is not None else None, pip)
            if setup:
                return {"signal": "SELL", "confidence": 65,
                        "reason_fa": f"فشردگی کانال دونچیان + قیمت نزدیک کف — آماده شکست نزولی",
                        "setup": setup}

    return _neutral("فشردگی کانال دونچیان شناسایی نشد")


# ── DON_04: Donchian + ATR Filter ──
def don_04(df, indicators, symbol, timeframe):
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(c) < 25:
        return _neutral("داده کافی نیست")

    upper, lower, middle = _donchian(h, l, 20)
    atr = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]
    prev = c[-2]

    if upper is None or atr is None:
        return _neutral("محاسبه ناموفق")

    atr_val = atr[-1]
    atr_prev = np.mean(atr[-20:-1]) if len(atr) > 20 else atr_val

    # Breakout + ATR expanding (volatility confirms)
    atr_expanding = atr_val > atr_prev * 1.2

    if price > upper[-2] and prev <= upper[-3] and atr_expanding:
        setup = _make_setup("BUY", price, atr_val, pip)
        if setup:
            return {"signal": "BUY", "confidence": 80,
                    "reason_fa": f"شکست دونچیان + ATR در حال افزایش — تایید نوسان",
                    "setup": setup}

    if price < lower[-2] and prev >= lower[-3] and atr_expanding:
        setup = _make_setup("SELL", price, atr_val, pip)
        if setup:
            return {"signal": "SELL", "confidence": 80,
                    "reason_fa": f"شکست نزولی دونچیان + ATR در حال افزایش — تایید نوسان",
                    "setup": setup}

    return _neutral("شکست دونچیان + فیلتر ATR شناسایی نشد")


# ── DON_05: Turtle Trading System (20/55 dual) ──
def don_05(df, indicators, symbol, timeframe):
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(c) < 60:
        return _neutral("داده کافی نیست — حداقل ۶۰ کندل")

    upper20, lower20, _ = _donchian(h, l, 20)
    upper55, lower55, _ = _donchian(h, l, 55)
    atr = _atr(h, l, c, 20)
    pip = _pip_size(symbol)
    price = c[-1]
    prev = c[-2]

    if upper55 is None:
        return _neutral("محاسبه کانال ۵۵ ناموفق")

    # System 1: 20-period breakout
    sys1_buy = price > upper20[-2] and prev <= upper20[-3]
    sys1_sell = price < lower20[-2] and prev >= lower20[-3]

    # System 2: 55-period breakout (stronger)
    sys2_buy = price > upper55[-2] and prev <= upper55[-3]
    sys2_sell = price < lower55[-2] and prev >= lower55[-3]

    if sys2_buy:
        setup = _make_setup("BUY", price, atr[-1] * 2 if atr is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 85,
                    "reason_fa": f"سیستم لاک‌پشت ۵۵ — شکست صعودی بلندمدت | سیگنال قوی",
                    "setup": setup}
    elif sys1_buy:
        setup = _make_setup("BUY", price, atr[-1] * 1.5 if atr is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 70,
                    "reason_fa": f"سیستم لاک‌پشت ۲۰ — شکست صعودی کوتاه‌مدت",
                    "setup": setup}

    if sys2_sell:
        setup = _make_setup("SELL", price, atr[-1] * 2 if atr is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 85,
                    "reason_fa": f"سیستم لاک‌پشت ۵۵ — شکست نزولی بلندمدت | سیگنال قوی",
                    "setup": setup}
    elif sys1_sell:
        setup = _make_setup("SELL", price, atr[-1] * 1.5 if atr is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 70,
                    "reason_fa": f"سیستم لاک‌پشت ۲۰ — شکست نزولی کوتاه‌مدت",
                    "setup": setup}

    return _neutral("سیگنال سیستم لاک‌پشت شناسایی نشد")


DON_STRATEGIES = [
    {"id": "DON_01", "name": "Classic Breakout", "name_fa": "شکست کلاسیک دونچیان", "func": don_01},
    {"id": "DON_02", "name": "Middle Line Cross", "name_fa": "عبور خط میانی", "func": don_02},
    {"id": "DON_03", "name": "Squeeze Breakout", "name_fa": "فشردگی دونچیان", "func": don_03},
    {"id": "DON_04", "name": "ATR Filter Breakout", "name_fa": "شکست + فیلتر ATR", "func": don_04},
    {"id": "DON_05", "name": "Turtle Trading", "name_fa": "سیستم لاک‌پشت", "func": don_05},
]
