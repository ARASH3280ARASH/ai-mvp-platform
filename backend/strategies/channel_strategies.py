"""
Whilber-AI — Channel Strategies
=================================
CH_01: Donchian Breakout
CH_02: Donchian Middle
CH_03: Price Channel Bounce
CH_04: Keltner Squeeze
CH_05: Keltner Band Walking
CH_06: Envelope
"""

import numpy as np


def _ema(data, period):
    if len(data) < period:
        return None
    e = np.zeros(len(data))
    e[0] = np.mean(data[:period])
    m = 2 / (period + 1)
    for i in range(1, len(data)):
        e[i] = data[i] * m + e[i-1] * (1 - m)
    return e


def _atr(high, low, close, period=14):
    if len(high) < period + 1:
        return None
    tr = np.maximum(high[1:] - low[1:],
         np.maximum(np.abs(high[1:] - close[:-1]), np.abs(low[1:] - close[:-1])))
    atr = np.zeros(len(tr))
    atr[period-1] = np.mean(tr[:period])
    for i in range(period, len(tr)):
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
    return atr


# -- CH_01: Donchian Breakout
def channel_donchian_break(df, context=None):
    """Donchian شکست — شکست سقف/کف ۲۰ بار"""
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(h) < 22:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "دانچیان — داده کافی نیست"}
    period = 20
    upper = np.max(h[-period-1:-1])
    lower = np.min(l[-period-1:-1])
    price = c[-1]

    if price > upper:
        return {"signal": "BUY", "confidence": 68,
                "reason_fa": f"دانچیان شکست بالا — قیمت {price:.5g} > سقف {upper:.5g} | ادامه صعود"}
    elif price < lower:
        return {"signal": "SELL", "confidence": 68,
                "reason_fa": f"دانچیان شکست پایین — قیمت {price:.5g} < کف {lower:.5g} | ادامه نزول"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"دانچیان — داخل کانال | سقف={upper:.5g} کف={lower:.5g}"}


# -- CH_02: Donchian Middle
def channel_donchian_mid(df, context=None):
    """Donchian خط وسط — عبور از میانه کانال"""
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(h) < 22:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "دانچیان Mid — داده کافی نیست"}
    period = 20
    upper = np.max(h[-period-1:-1])
    lower = np.min(l[-period-1:-1])
    mid = (upper + lower) / 2
    price = c[-1]
    prev = c[-2]

    if prev <= mid and price > mid:
        return {"signal": "BUY", "confidence": 55,
                "reason_fa": f"دانچیان عبور بالای میانه {mid:.5g} | مومنتوم صعودی"}
    elif prev >= mid and price < mid:
        return {"signal": "SELL", "confidence": 55,
                "reason_fa": f"دانچیان عبور پایین میانه {mid:.5g} | مومنتوم نزولی"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"دانچیان — بدون عبور میانه={mid:.5g}"}


# -- CH_03: Price Channel Bounce
def channel_price_bounce(df, context=None):
    """Price Channel بانس — برگشت از سقف/کف کانال"""
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(h) < 22:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "کانال قیمتی — داده کافی نیست"}
    period = 20
    upper = np.max(h[-period-1:-1])
    lower = np.min(l[-period-1:-1])
    rng = upper - lower
    if rng == 0:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "کانال — رنج صفر"}
    price = c[-1]
    pos = (price - lower) / rng

    if pos < 0.10 and c[-1] > c[-2]:
        return {"signal": "BUY", "confidence": 60,
                "reason_fa": f"بانس از کف کانال — قیمت نزدیک {lower:.5g} و برگشت | خرید"}
    elif pos > 0.90 and c[-1] < c[-2]:
        return {"signal": "SELL", "confidence": 60,
                "reason_fa": f"ریجکت از سقف کانال — قیمت نزدیک {upper:.5g} و برگشت | فروش"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"کانال — موقعیت {pos:.0%} | نه کف نه سقف"}


# -- CH_04: Keltner Squeeze
def channel_keltner_squeeze(df, context=None):
    """Keltner فشردگی — BB داخل Keltner = فشردگی"""
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(c) < 25:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "کلتنر — داده کافی نیست"}

    ema20 = _ema(c, 20)
    atr_val = _atr(h, l, c, 14)
    if ema20 is None or atr_val is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "کلتنر — محاسبه نشد"}

    # Keltner bands
    k_upper = ema20[-1] + 2 * atr_val[-1]
    k_lower = ema20[-1] - 2 * atr_val[-1]

    # Bollinger bands
    sma20 = np.mean(c[-20:])
    std20 = np.std(c[-20:])
    bb_upper = sma20 + 2 * std20
    bb_lower = sma20 - 2 * std20

    # Squeeze: BB inside Keltner
    squeeze = bb_upper < k_upper and bb_lower > k_lower
    price = c[-1]

    if squeeze:
        # Direction hint from EMA slope
        slope = ema20[-1] - ema20[-3] if len(ema20) > 3 else 0
        if slope > 0:
            return {"signal": "BUY", "confidence": 58,
                    "reason_fa": f"فشردگی کلتنر — BB داخل Keltner + شیب صعودی | آماده شکست بالا"}
        elif slope < 0:
            return {"signal": "SELL", "confidence": 58,
                    "reason_fa": f"فشردگی کلتنر — BB داخل Keltner + شیب نزولی | آماده شکست پایین"}
        return {"signal": "NEUTRAL", "confidence": 45,
                "reason_fa": f"فشردگی کلتنر — منتظر جهت شکست"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"کلتنر — بدون فشردگی"}


# -- CH_05: Keltner Band Walking
def channel_keltner_walk(df, context=None):
    """Keltner واکینگ — قیمت روی باند = روند قوی"""
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(c) < 22:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "کلتنر Walk — داده کافی نیست"}

    ema20 = _ema(c, 20)
    atr_val = _atr(h, l, c, 14)
    if ema20 is None or atr_val is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "کلتنر — محاسبه نشد"}

    k_upper = ema20[-1] + 2 * atr_val[-1]
    k_lower = ema20[-1] - 2 * atr_val[-1]
    price = c[-1]

    # Count how many of last 5 bars touched upper/lower band
    touch_upper = sum(1 for i in range(-5, 0) if c[i] > ema20[i] + 1.8 * atr_val[i])
    touch_lower = sum(1 for i in range(-5, 0) if c[i] < ema20[i] - 1.8 * atr_val[i])

    if touch_upper >= 3 and price > k_upper * 0.998:
        return {"signal": "BUY", "confidence": 65,
                "reason_fa": f"کلتنر واکینگ صعودی — {touch_upper}/5 بار روی باند بالا | روند قوی"}
    elif touch_lower >= 3 and price < k_lower * 1.002:
        return {"signal": "SELL", "confidence": 65,
                "reason_fa": f"کلتنر واکینگ نزولی — {touch_lower}/5 بار روی باند پایین | روند قوی"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"کلتنر — بدون واکینگ"}


# -- CH_06: Envelope
def channel_envelope(df, context=None):
    """Envelope — پاکت MA اشباع خرید/فروش"""
    c = df["close"].values
    if len(c) < 22:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "Envelope — داده کافی نیست"}

    sma20 = np.mean(c[-20:])
    pct = 0.02  # 2% envelope
    upper = sma20 * (1 + pct)
    lower = sma20 * (1 - pct)
    price = c[-1]

    if price < lower and c[-1] > c[-2]:
        return {"signal": "BUY", "confidence": 58,
                "reason_fa": f"Envelope اشباع فروش — قیمت زیر {lower:.5g} و برگشت | خرید"}
    elif price > upper and c[-1] < c[-2]:
        return {"signal": "SELL", "confidence": 58,
                "reason_fa": f"Envelope اشباع خرید — قیمت بالای {upper:.5g} و برگشت | فروش"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"Envelope — داخل پاکت | بالا={upper:.5g} پایین={lower:.5g}"}


CH_STRATEGIES = [
    {"id": "CH_01", "name": "Donchian Breakout", "name_fa": "دانچیان: شکست", "func": channel_donchian_break},
    {"id": "CH_02", "name": "Donchian Middle", "name_fa": "دانچیان: خط میانی", "func": channel_donchian_mid},
    {"id": "CH_03", "name": "Price Channel Bounce", "name_fa": "کانال: بانس", "func": channel_price_bounce},
    {"id": "CH_04", "name": "Keltner Squeeze", "name_fa": "کلتنر: فشردگی", "func": channel_keltner_squeeze},
    {"id": "CH_05", "name": "Keltner Walk", "name_fa": "کلتنر: واکینگ", "func": channel_keltner_walk},
    {"id": "CH_06", "name": "Envelope", "name_fa": "Envelope: پاکت MA", "func": channel_envelope},
]
