"""
Whilber-AI — Bollinger Bands Strategy Pack (10 Sub-Strategies)
===============================================================
BB_01: Bounce (touch lower/upper band)
BB_02: Squeeze → Breakout
BB_03: %B Overbought/Oversold
BB_04: Width Expansion
BB_05: Band Walk (riding upper/lower)
BB_06: BB + RSI Combo
BB_07: Double Bottom at Lower Band
BB_08: Mean Reversion (return to middle)
BB_09: Tight BB (1.5 SD)
BB_10: Wide BB (2.5 SD)
"""

import numpy as np
import pandas as pd


def _bb(close, period=20, std_dev=2.0):
    sma = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    upper = sma + std_dev * std
    lower = sma - std_dev * std
    width = (upper - lower) / sma * 100
    pct_b = (close - lower) / (upper - lower + 1e-10) * 100
    return sma, upper, lower, width, pct_b


def _rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    return 100 - (100 / (1 + rs))


# ─────────────────────────────────────────────────────
# BB_01: Bounce (touch lower/upper band)
# BUY:  قیمت باند پایین را لمس یا قطع کرده و برگشته
# SELL: قیمت باند بالا را لمس یا قطع کرده و برگشته
# ─────────────────────────────────────────────────────
def bb_01_bounce(df, context=None):
    close = df['close']
    sma, upper, lower, _, pct_b = _bb(close, 20, 2.0)
    c = close.iloc[-1]
    c_prev = close.iloc[-2]
    low_val = df['low'].iloc[-2]
    high_val = df['high'].iloc[-2]
    lb = lower.iloc[-1]
    ub = upper.iloc[-1]

    # Previous candle touched lower band and current bounced up
    if low_val <= lower.iloc[-2] and c > c_prev:
        return {"signal": "BUY", "confidence": 72,
                "reason_fa": f"قیمت باند پایین بولینگر را لمس کرد و برگشت — %B: {pct_b.iloc[-1]:.0f}%"}
    # Previous candle touched upper band and current fell
    elif high_val >= upper.iloc[-2] and c < c_prev:
        return {"signal": "SELL", "confidence": 72,
                "reason_fa": f"قیمت باند بالای بولینگر را لمس کرد و برگشت — %B: {pct_b.iloc[-1]:.0f}%"}
    # Currently at lower band
    elif c <= lb * 1.002:
        return {"signal": "BUY", "confidence": 55,
                "reason_fa": f"قیمت نزدیک باند پایین بولینگر — %B: {pct_b.iloc[-1]:.0f}%"}
    elif c >= ub * 0.998:
        return {"signal": "SELL", "confidence": 55,
                "reason_fa": f"قیمت نزدیک باند بالای بولینگر — %B: {pct_b.iloc[-1]:.0f}%"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"قیمت بین باندهای بولینگر (%B: {pct_b.iloc[-1]:.0f}%)"}


# ─────────────────────────────────────────────────────
# BB_02: Squeeze → Breakout
# BUY:  BB عرض کم (squeeze) + شکست صعودی باند بالا
# SELL: BB عرض کم (squeeze) + شکست نزولی باند پایین
# ─────────────────────────────────────────────────────
def bb_02_squeeze(df, context=None):
    close = df['close']
    sma, upper, lower, width, _ = _bb(close, 20, 2.0)
    if len(width) < 30:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    w = width.iloc[-1]
    w_min_20 = width.iloc[-20:].min()
    c = close.iloc[-1]

    # Is in squeeze? (width near 20-bar minimum)
    is_squeeze = w < w_min_20 * 1.15

    if is_squeeze and c > upper.iloc[-1]:
        return {"signal": "BUY", "confidence": 82,
                "reason_fa": f"شکست صعودی بعد از Squeeze بولینگر — حرکت انفجاری!"}
    elif is_squeeze and c < lower.iloc[-1]:
        return {"signal": "SELL", "confidence": 82,
                "reason_fa": f"شکست نزولی بعد از Squeeze بولینگر — حرکت انفجاری!"}
    elif is_squeeze:
        return {"signal": "NEUTRAL", "confidence": 30,
                "reason_fa": f"بولینگر در حالت Squeeze — آماده شکست (عرض: {w:.2f})"}

    # Expanding after squeeze
    w_prev = width.iloc[-5:].min()
    if w > w_prev * 1.5 and c > sma.iloc[-1]:
        return {"signal": "BUY", "confidence": 60,
                "reason_fa": "باند بولینگر در حال باز شدن + قیمت بالای میانگین"}
    elif w > w_prev * 1.5 and c < sma.iloc[-1]:
        return {"signal": "SELL", "confidence": 60,
                "reason_fa": "باند بولینگر در حال باز شدن + قیمت زیر میانگین"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"بدون Squeeze بولینگر (عرض: {w:.2f})"}


# ─────────────────────────────────────────────────────
# BB_03: %B Overbought/Oversold
# BUY:  %B < 0 (زیر باند پایین) + برگشت بالای 0
# SELL: %B > 100 (بالای باند بالا) + برگشت زیر 100
# ─────────────────────────────────────────────────────
def bb_03_pctb(df, context=None):
    close = df['close']
    _, _, _, _, pct_b = _bb(close, 20, 2.0)
    b = pct_b.iloc[-1]
    b_prev = pct_b.iloc[-2]

    if b_prev < 0 and b >= 0:
        return {"signal": "BUY", "confidence": 78,
                "reason_fa": f"%B از زیر صفر برگشت ({b:.0f}%) — خرید قوی"}
    elif b_prev > 100 and b <= 100:
        return {"signal": "SELL", "confidence": 78,
                "reason_fa": f"%B از بالای ۱۰۰ برگشت ({b:.0f}%) — فروش قوی"}
    elif b < 5:
        return {"signal": "BUY", "confidence": 60,
                "reason_fa": f"%B بسیار پایین ({b:.0f}%) — اشباع فروش بولینگر"}
    elif b > 95:
        return {"signal": "SELL", "confidence": 60,
                "reason_fa": f"%B بسیار بالا ({b:.0f}%) — اشباع خرید بولینگر"}
    elif b < 20:
        return {"signal": "BUY", "confidence": 45,
                "reason_fa": f"%B پایین ({b:.0f}%) — نزدیک اشباع فروش"}
    elif b > 80:
        return {"signal": "SELL", "confidence": 45,
                "reason_fa": f"%B بالا ({b:.0f}%) — نزدیک اشباع خرید"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"%B بولینگر خنثی ({b:.0f}%)"}


# ─────────────────────────────────────────────────────
# BB_04: Width Expansion (ورود به روند)
# BUY:  عرض BB از حداقل ۲۰ کندل قبل ۵۰٪ بیشتر + قیمت بالای SMA
# SELL: عرض BB از حداقل ۲۰ کندل قبل ۵۰٪ بیشتر + قیمت زیر SMA
# ─────────────────────────────────────────────────────
def bb_04_width_expansion(df, context=None):
    close = df['close']
    sma, upper, lower, width, _ = _bb(close, 20, 2.0)
    if len(width) < 25:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    w = width.iloc[-1]
    w_min = width.iloc[-20:-1].min()
    expansion = (w / (w_min + 1e-10) - 1) * 100
    c = close.iloc[-1]
    mid = sma.iloc[-1]

    if expansion > 50 and c > mid:
        conf = min(80, 55 + int(expansion / 10))
        return {"signal": "BUY", "confidence": conf,
                "reason_fa": f"باند بولینگر {expansion:.0f}% باز شده + قیمت بالای SMA — روند صعودی"}
    elif expansion > 50 and c < mid:
        conf = min(80, 55 + int(expansion / 10))
        return {"signal": "SELL", "confidence": conf,
                "reason_fa": f"باند بولینگر {expansion:.0f}% باز شده + قیمت زیر SMA — روند نزولی"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"عرض باند بولینگر تغییر خاصی نکرده ({expansion:.0f}%)"}


# ─────────────────────────────────────────────────────
# BB_05: Band Walk (riding upper/lower band)
# BUY:  ۳ کندل متوالی بالای SMA و نزدیک باند بالا (Walking the band)
# SELL: ۳ کندل متوالی زیر SMA و نزدیک باند پایین
# ─────────────────────────────────────────────────────
def bb_05_band_walk(df, context=None):
    close = df['close']
    sma, upper, lower, _, pct_b = _bb(close, 20, 2.0)
    if len(pct_b) < 5:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    b3 = [pct_b.iloc[-i] for i in range(1, 4)]

    # Walking upper band: 3 candles with %B > 70
    if all(b > 70 for b in b3):
        return {"signal": "BUY", "confidence": 68,
                "reason_fa": f"قیمت ۳ کندل روی باند بالای بولینگر حرکت — Band Walk صعودی"}
    # Walking lower band: 3 candles with %B < 30
    elif all(b < 30 for b in b3):
        return {"signal": "SELL", "confidence": 68,
                "reason_fa": f"قیمت ۳ کندل روی باند پایین بولینگر حرکت — Band Walk نزولی"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"بدون Band Walk (%B: {pct_b.iloc[-1]:.0f}%)"}


# ─────────────────────────────────────────────────────
# BB_06: BB + RSI Combo
# BUY:  قیمت زیر باند پایین + RSI < 30 (تایید دوگانه)
# SELL: قیمت بالای باند بالا + RSI > 70 (تایید دوگانه)
# ─────────────────────────────────────────────────────
def bb_06_rsi_combo(df, context=None):
    close = df['close']
    _, upper, lower, _, pct_b = _bb(close, 20, 2.0)
    rsi = _rsi(close, 14)
    c = close.iloc[-1]
    r = rsi.iloc[-1]
    b = pct_b.iloc[-1]

    if c <= lower.iloc[-1] and r < 30:
        conf = min(90, 75 + int((30 - r) / 2))
        return {"signal": "BUY", "confidence": conf,
                "reason_fa": f"قیمت زیر باند پایین + RSI({r:.0f}) اشباع فروش — تایید دوگانه!"}
    elif c >= upper.iloc[-1] and r > 70:
        conf = min(90, 75 + int((r - 70) / 2))
        return {"signal": "SELL", "confidence": conf,
                "reason_fa": f"قیمت بالای باند بالا + RSI({r:.0f}) اشباع خرید — تایید دوگانه!"}
    elif b < 10 and r < 35:
        return {"signal": "BUY", "confidence": 60,
                "reason_fa": f"BB+RSI نزدیک اشباع فروش (%B:{b:.0f} RSI:{r:.0f})"}
    elif b > 90 and r > 65:
        return {"signal": "SELL", "confidence": 60,
                "reason_fa": f"BB+RSI نزدیک اشباع خرید (%B:{b:.0f} RSI:{r:.0f})"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"BB+RSI بدون سیگنال (%B:{b:.0f} RSI:{r:.0f})"}


# ─────────────────────────────────────────────────────
# BB_07: Double Bottom at Lower Band
# BUY:  دو برخورد به باند پایین در ۲۰ کندل اخیر + برگشت (W شکل)
# SELL: دو برخورد به باند بالا + برگشت (M شکل)
# ─────────────────────────────────────────────────────
def bb_07_double_pattern(df, context=None):
    close = df['close']
    _, upper, lower, _, pct_b = _bb(close, 20, 2.0)
    if len(pct_b) < 25:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    recent = pct_b.iloc[-20:]

    # Count touches of lower band (%B < 5)
    lower_touches = []
    in_touch = False
    for i in range(len(recent)):
        if recent.iloc[i] < 5:
            if not in_touch:
                lower_touches.append(i)
                in_touch = True
        else:
            in_touch = False

    if len(lower_touches) >= 2 and (lower_touches[-1] - lower_touches[-2]) > 3:
        if pct_b.iloc[-1] > 20:
            return {"signal": "BUY", "confidence": 77,
                    "reason_fa": "الگوی W — دو لمس باند پایین بولینگر و برگشت صعودی"}

    # Count touches of upper band (%B > 95)
    upper_touches = []
    in_touch = False
    for i in range(len(recent)):
        if recent.iloc[i] > 95:
            if not in_touch:
                upper_touches.append(i)
                in_touch = True
        else:
            in_touch = False

    if len(upper_touches) >= 2 and (upper_touches[-1] - upper_touches[-2]) > 3:
        if pct_b.iloc[-1] < 80:
            return {"signal": "SELL", "confidence": 77,
                    "reason_fa": "الگوی M — دو لمس باند بالای بولینگر و برگشت نزولی"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "بدون الگوی دوگانه بولینگر"}


# ─────────────────────────────────────────────────────
# BB_08: Mean Reversion (return to middle band)
# BUY:  قیمت از باند پایین به سمت SMA حرکت + هنوز زیر SMA
# SELL: قیمت از باند بالا به سمت SMA حرکت + هنوز بالای SMA
# ─────────────────────────────────────────────────────
def bb_08_mean_reversion(df, context=None):
    close = df['close']
    sma, upper, lower, _, pct_b = _bb(close, 20, 2.0)
    c = close.iloc[-1]
    mid = sma.iloc[-1]
    b = pct_b.iloc[-1]
    b_prev5_min = pct_b.iloc[-6:-1].min()
    b_prev5_max = pct_b.iloc[-6:-1].max()

    # Was near lower band, now moving toward middle
    if b_prev5_min < 10 and 20 < b < 50:
        return {"signal": "BUY", "confidence": 65,
                "reason_fa": f"بازگشت به میانگین — از باند پایین به سمت SMA (%B: {b:.0f}%)"}
    # Was near upper band, now moving toward middle
    elif b_prev5_max > 90 and 50 < b < 80:
        return {"signal": "SELL", "confidence": 65,
                "reason_fa": f"بازگشت به میانگین — از باند بالا به سمت SMA (%B: {b:.0f}%)"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"بدون بازگشت به میانگین (%B: {b:.0f}%)"}


# ─────────────────────────────────────────────────────
# BB_09: Tight BB (1.5 SD) — حساس‌تر
# BUY:  قیمت زیر باند پایین (1.5 SD) + برگشت
# SELL: قیمت بالای باند بالا (1.5 SD) + برگشت
# ─────────────────────────────────────────────────────
def bb_09_tight(df, context=None):
    close = df['close']
    sma, upper, lower, _, pct_b = _bb(close, 20, 1.5)
    c = close.iloc[-1]
    c_prev = close.iloc[-2]
    b = pct_b.iloc[-1]

    if c_prev <= lower.iloc[-2] and c > lower.iloc[-1]:
        return {"signal": "BUY", "confidence": 60,
                "reason_fa": f"قیمت از باند پایین تنگ (1.5σ) برگشت — حساس‌تر"}
    elif c_prev >= upper.iloc[-2] and c < upper.iloc[-1]:
        return {"signal": "SELL", "confidence": 60,
                "reason_fa": f"قیمت از باند بالای تنگ (1.5σ) برگشت — حساس‌تر"}
    elif b < 5:
        return {"signal": "BUY", "confidence": 50,
                "reason_fa": f"قیمت زیر باند تنگ (1.5σ) — %B: {b:.0f}%"}
    elif b > 95:
        return {"signal": "SELL", "confidence": 50,
                "reason_fa": f"قیمت بالای باند تنگ (1.5σ) — %B: {b:.0f}%"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"BB تنگ (1.5σ) بدون سیگنال (%B: {b:.0f}%)"}


# ─────────────────────────────────────────────────────
# BB_10: Wide BB (2.5 SD) — فیلتر قوی‌تر
# BUY:  قیمت زیر باند پایین (2.5 SD) — اشباع فروش شدید
# SELL: قیمت بالای باند بالا (2.5 SD) — اشباع خرید شدید
# ─────────────────────────────────────────────────────
def bb_10_wide(df, context=None):
    close = df['close']
    sma, upper, lower, _, pct_b = _bb(close, 20, 2.5)
    c = close.iloc[-1]
    c_prev = close.iloc[-2]
    b = pct_b.iloc[-1]

    if c_prev <= lower.iloc[-2] and c > lower.iloc[-1]:
        return {"signal": "BUY", "confidence": 85,
                "reason_fa": f"قیمت از باند پایین عریض (2.5σ) برگشت — اشباع شدید!"}
    elif c_prev >= upper.iloc[-2] and c < upper.iloc[-1]:
        return {"signal": "SELL", "confidence": 85,
                "reason_fa": f"قیمت از باند بالای عریض (2.5σ) برگشت — اشباع شدید!"}
    elif c <= lower.iloc[-1]:
        return {"signal": "BUY", "confidence": 72,
                "reason_fa": f"قیمت زیر باند عریض (2.5σ) — اشباع فروش شدید"}
    elif c >= upper.iloc[-1]:
        return {"signal": "SELL", "confidence": 72,
                "reason_fa": f"قیمت بالای باند عریض (2.5σ) — اشباع خرید شدید"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"BB عریض (2.5σ) بدون سیگنال (%B: {b:.0f}%)"}


# ═══════════════════════════════════════════════════════
# REGISTRY
# ═══════════════════════════════════════════════════════

BB_STRATEGIES = [
    {"id": "BB_01", "name": "BB Bounce", "name_fa": "بولینگر برگشتی", "func": bb_01_bounce},
    {"id": "BB_02", "name": "BB Squeeze Breakout", "name_fa": "شکست Squeeze بولینگر", "func": bb_02_squeeze},
    {"id": "BB_03", "name": "BB %B", "name_fa": "بولینگر %B", "func": bb_03_pctb},
    {"id": "BB_04", "name": "BB Width Expansion", "name_fa": "باز شدن باند بولینگر", "func": bb_04_width_expansion},
    {"id": "BB_05", "name": "BB Band Walk", "name_fa": "حرکت روی باند بولینگر", "func": bb_05_band_walk},
    {"id": "BB_06", "name": "BB + RSI Combo", "name_fa": "بولینگر + RSI ترکیبی", "func": bb_06_rsi_combo},
    {"id": "BB_07", "name": "BB Double Pattern", "name_fa": "الگوی W/M بولینگر", "func": bb_07_double_pattern},
    {"id": "BB_08", "name": "BB Mean Reversion", "name_fa": "بازگشت به میانگین بولینگر", "func": bb_08_mean_reversion},
    {"id": "BB_09", "name": "BB Tight (1.5σ)", "name_fa": "بولینگر تنگ (1.5σ)", "func": bb_09_tight},
    {"id": "BB_10", "name": "BB Wide (2.5σ)", "name_fa": "بولینگر عریض (2.5σ)", "func": bb_10_wide},
]
