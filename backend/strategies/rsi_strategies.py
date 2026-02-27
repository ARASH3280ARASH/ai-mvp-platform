"""
Whilber-AI — RSI Strategy Pack (12 Sub-Strategies)
====================================================
RSI_01: Classic 30/70
RSI_02: Conservative 25/75
RSI_03: Aggressive 35/65
RSI_04: Ultra 20/80
RSI_05: Midline Cross 50
RSI_06: Fast RSI(7)
RSI_07: Slow RSI(21)
RSI_08: RSI Divergence
RSI_09: RSI Hidden Divergence
RSI_10: RSI Double Bottom/Top
RSI_11: RSI + EMA Filter
RSI_12: RSI Range Shift
"""

import numpy as np
import pandas as pd


def _rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    return 100 - (100 / (1 + rs))


def _find_peaks(series, order=5):
    """Find local highs and lows."""
    highs, lows = [], []
    arr = series.values
    for i in range(order, len(arr) - order):
        if all(arr[i] >= arr[i-j] for j in range(1, order+1)) and all(arr[i] >= arr[i+j] for j in range(1, order+1)):
            highs.append(i)
        if all(arr[i] <= arr[i-j] for j in range(1, order+1)) and all(arr[i] <= arr[i+j] for j in range(1, order+1)):
            lows.append(i)
    return highs, lows


def _ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


# ─────────────────────────────────────────────────────
# RSI_01: Classic 30/70
# BUY:  RSI(14) < 30 و سپس برگشت بالای 30
# SELL: RSI(14) > 70 و سپس برگشت زیر 70
# ─────────────────────────────────────────────────────
def rsi_01_classic(df, context=None):
    close = df['close']
    rsi = _rsi(close, 14)
    r = rsi.iloc[-1]
    r_prev = rsi.iloc[-2]

    if r_prev < 30 and r >= 30:
        conf = min(90, 60 + int((30 - rsi.iloc[-3]) * 2)) if len(rsi) > 3 else 70
        return {"signal": "BUY", "confidence": conf,
                "reason_fa": f"RSI از اشباع فروش برگشت ({r:.1f}) — کلاسیک 30/70"}
    elif r_prev > 70 and r <= 70:
        conf = min(90, 60 + int((rsi.iloc[-3] - 70) * 2)) if len(rsi) > 3 else 70
        return {"signal": "SELL", "confidence": conf,
                "reason_fa": f"RSI از اشباع خرید برگشت ({r:.1f}) — کلاسیک 30/70"}
    elif r < 30:
        return {"signal": "BUY", "confidence": 55,
                "reason_fa": f"RSI در اشباع فروش ({r:.1f}) — منتظر برگشت"}
    elif r > 70:
        return {"signal": "SELL", "confidence": 55,
                "reason_fa": f"RSI در اشباع خرید ({r:.1f}) — منتظر برگشت"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"RSI خنثی ({r:.1f})"}


# ─────────────────────────────────────────────────────
# RSI_02: Conservative 25/75
# BUY:  RSI(14) < 25 — اشباع فروش عمیق
# SELL: RSI(14) > 75 — اشباع خرید عمیق
# ─────────────────────────────────────────────────────
def rsi_02_conservative(df, context=None):
    rsi = _rsi(df['close'], 14)
    r = rsi.iloc[-1]
    r_prev = rsi.iloc[-2]

    if r_prev < 25 and r >= 25:
        return {"signal": "BUY", "confidence": 80,
                "reason_fa": f"RSI از اشباع عمیق فروش برگشت ({r:.1f}) — محافظه‌کار 25/75"}
    elif r_prev > 75 and r <= 75:
        return {"signal": "SELL", "confidence": 80,
                "reason_fa": f"RSI از اشباع عمیق خرید برگشت ({r:.1f}) — محافظه‌کار 25/75"}
    elif r < 25:
        return {"signal": "BUY", "confidence": 65,
                "reason_fa": f"RSI اشباع فروش عمیق ({r:.1f})"}
    elif r > 75:
        return {"signal": "SELL", "confidence": 65,
                "reason_fa": f"RSI اشباع خرید عمیق ({r:.1f})"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"RSI در محدوده 25-75 ({r:.1f})"}


# ─────────────────────────────────────────────────────
# RSI_03: Aggressive 35/65
# BUY:  RSI(14) < 35 — ورود زودتر
# SELL: RSI(14) > 65 — خروج زودتر
# ─────────────────────────────────────────────────────
def rsi_03_aggressive(df, context=None):
    rsi = _rsi(df['close'], 14)
    r = rsi.iloc[-1]
    r_prev = rsi.iloc[-2]

    if r_prev < 35 and r >= 35:
        return {"signal": "BUY", "confidence": 60,
                "reason_fa": f"RSI از زیر 35 برگشت ({r:.1f}) — تهاجمی"}
    elif r_prev > 65 and r <= 65:
        return {"signal": "SELL", "confidence": 60,
                "reason_fa": f"RSI از بالای 65 برگشت ({r:.1f}) — تهاجمی"}
    elif r < 35:
        return {"signal": "BUY", "confidence": 50,
                "reason_fa": f"RSI زیر 35 ({r:.1f}) — ناحیه تهاجمی خرید"}
    elif r > 65:
        return {"signal": "SELL", "confidence": 50,
                "reason_fa": f"RSI بالای 65 ({r:.1f}) — ناحیه تهاجمی فروش"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"RSI خنثی ({r:.1f})"}


# ─────────────────────────────────────────────────────
# RSI_04: Ultra 20/80
# BUY:  RSI(14) < 20 — اشباع فروش شدید
# SELL: RSI(14) > 80 — اشباع خرید شدید
# ─────────────────────────────────────────────────────
def rsi_04_ultra(df, context=None):
    rsi = _rsi(df['close'], 14)
    r = rsi.iloc[-1]
    r_prev = rsi.iloc[-2]

    if r_prev < 20 and r >= 20:
        return {"signal": "BUY", "confidence": 88,
                "reason_fa": f"RSI از اشباع شدید فروش برگشت ({r:.1f}) — سیگنال قوی!"}
    elif r_prev > 80 and r <= 80:
        return {"signal": "SELL", "confidence": 88,
                "reason_fa": f"RSI از اشباع شدید خرید برگشت ({r:.1f}) — سیگنال قوی!"}
    elif r < 20:
        return {"signal": "BUY", "confidence": 75,
                "reason_fa": f"RSI اشباع شدید ({r:.1f}) — احتمال بازگشت بالا"}
    elif r > 80:
        return {"signal": "SELL", "confidence": 75,
                "reason_fa": f"RSI اشباع شدید ({r:.1f}) — احتمال ریزش بالا"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"RSI نرمال ({r:.1f})"}


# ─────────────────────────────────────────────────────
# RSI_05: Midline Cross 50
# BUY:  RSI(14) از زیر 50 به بالای 50 قطع کند
# SELL: RSI(14) از بالای 50 به زیر 50 قطع کند
# ─────────────────────────────────────────────────────
def rsi_05_midline(df, context=None):
    rsi = _rsi(df['close'], 14)
    r = rsi.iloc[-1]
    r_prev = rsi.iloc[-2]
    r_prev2 = rsi.iloc[-3] if len(rsi) > 3 else r_prev

    if r_prev < 50 and r >= 50:
        momentum = r - r_prev2
        conf = min(75, 55 + int(momentum * 2))
        return {"signal": "BUY", "confidence": max(50, conf),
                "reason_fa": f"RSI خط میانی 50 را صعودی قطع کرد ({r:.1f})"}
    elif r_prev > 50 and r <= 50:
        momentum = r_prev2 - r
        conf = min(75, 55 + int(momentum * 2))
        return {"signal": "SELL", "confidence": max(50, conf),
                "reason_fa": f"RSI خط میانی 50 را نزولی قطع کرد ({r:.1f})"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"RSI بدون تقاطع خط 50 ({r:.1f})"}


# ─────────────────────────────────────────────────────
# RSI_06: Fast RSI(7)
# BUY:  RSI(7) < 30 + برگشت
# SELL: RSI(7) > 70 + برگشت
# ─────────────────────────────────────────────────────
def rsi_06_fast(df, context=None):
    rsi = _rsi(df['close'], 7)
    r = rsi.iloc[-1]
    r_prev = rsi.iloc[-2]

    if r_prev < 30 and r >= 30:
        return {"signal": "BUY", "confidence": 65,
                "reason_fa": f"RSI سریع(7) از اشباع فروش برگشت ({r:.1f})"}
    elif r_prev > 70 and r <= 70:
        return {"signal": "SELL", "confidence": 65,
                "reason_fa": f"RSI سریع(7) از اشباع خرید برگشت ({r:.1f})"}
    elif r < 25:
        return {"signal": "BUY", "confidence": 55,
                "reason_fa": f"RSI سریع(7) اشباع فروش ({r:.1f})"}
    elif r > 75:
        return {"signal": "SELL", "confidence": 55,
                "reason_fa": f"RSI سریع(7) اشباع خرید ({r:.1f})"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"RSI سریع(7) خنثی ({r:.1f})"}


# ─────────────────────────────────────────────────────
# RSI_07: Slow RSI(21)
# BUY:  RSI(21) < 30 — سیگنال بلندمدت‌تر
# SELL: RSI(21) > 70 — سیگنال بلندمدت‌تر
# ─────────────────────────────────────────────────────
def rsi_07_slow(df, context=None):
    rsi = _rsi(df['close'], 21)
    r = rsi.iloc[-1]
    r_prev = rsi.iloc[-2]

    if r_prev < 30 and r >= 30:
        return {"signal": "BUY", "confidence": 75,
                "reason_fa": f"RSI آهسته(21) از اشباع فروش برگشت ({r:.1f}) — سیگنال معتبر"}
    elif r_prev > 70 and r <= 70:
        return {"signal": "SELL", "confidence": 75,
                "reason_fa": f"RSI آهسته(21) از اشباع خرید برگشت ({r:.1f}) — سیگنال معتبر"}
    elif r < 30:
        return {"signal": "BUY", "confidence": 60,
                "reason_fa": f"RSI آهسته(21) اشباع فروش ({r:.1f})"}
    elif r > 70:
        return {"signal": "SELL", "confidence": 60,
                "reason_fa": f"RSI آهسته(21) اشباع خرید ({r:.1f})"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"RSI آهسته(21) خنثی ({r:.1f})"}


# ─────────────────────────────────────────────────────
# RSI_08: RSI Regular Divergence
# BUY:  قیمت کف پایین‌تر + RSI کف بالاتر (واگرایی مثبت)
# SELL: قیمت سقف بالاتر + RSI سقف پایین‌تر (واگرایی منفی)
# ─────────────────────────────────────────────────────
def rsi_08_divergence(df, context=None):
    close = df['close']
    rsi = _rsi(close, 14)
    if len(rsi) < 30:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    highs_idx, lows_idx = _find_peaks(close, order=5)
    rsi_highs, rsi_lows = _find_peaks(rsi, order=5)

    # Bullish divergence: price lower low + RSI higher low
    if len(lows_idx) >= 2 and len(rsi_lows) >= 2:
        p1, p2 = lows_idx[-2], lows_idx[-1]
        r1, r2 = rsi_lows[-2], rsi_lows[-1]
        if close.iloc[p2] < close.iloc[p1] and rsi.iloc[r2] > rsi.iloc[r1]:
            if rsi.iloc[-1] < 40:
                return {"signal": "BUY", "confidence": 78,
                        "reason_fa": f"واگرایی مثبت RSI — قیمت کف پایین‌تر ولی RSI کف بالاتر"}

    # Bearish divergence: price higher high + RSI lower high
    if len(highs_idx) >= 2 and len(rsi_highs) >= 2:
        p1, p2 = highs_idx[-2], highs_idx[-1]
        r1, r2 = rsi_highs[-2], rsi_highs[-1]
        if close.iloc[p2] > close.iloc[p1] and rsi.iloc[r2] < rsi.iloc[r1]:
            if rsi.iloc[-1] > 60:
                return {"signal": "SELL", "confidence": 78,
                        "reason_fa": f"واگرایی منفی RSI — قیمت سقف بالاتر ولی RSI سقف پایین‌تر"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"بدون واگرایی RSI ({rsi.iloc[-1]:.1f})"}


# ─────────────────────────────────────────────────────
# RSI_09: RSI Hidden Divergence
# BUY:  قیمت کف بالاتر + RSI کف پایین‌تر (ادامه روند صعودی)
# SELL: قیمت سقف پایین‌تر + RSI سقف بالاتر (ادامه روند نزولی)
# ─────────────────────────────────────────────────────
def rsi_09_hidden_div(df, context=None):
    close = df['close']
    rsi = _rsi(close, 14)
    if len(rsi) < 30:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    highs_idx, lows_idx = _find_peaks(close, order=5)
    rsi_highs, rsi_lows = _find_peaks(rsi, order=5)

    # Hidden bullish: price higher low + RSI lower low
    if len(lows_idx) >= 2 and len(rsi_lows) >= 2:
        p1, p2 = lows_idx[-2], lows_idx[-1]
        r1, r2 = rsi_lows[-2], rsi_lows[-1]
        if close.iloc[p2] > close.iloc[p1] and rsi.iloc[r2] < rsi.iloc[r1]:
            return {"signal": "BUY", "confidence": 72,
                    "reason_fa": "واگرایی مخفی مثبت RSI — ادامه روند صعودی محتمل"}

    # Hidden bearish: price lower high + RSI higher high
    if len(highs_idx) >= 2 and len(rsi_highs) >= 2:
        p1, p2 = highs_idx[-2], highs_idx[-1]
        r1, r2 = rsi_highs[-2], rsi_highs[-1]
        if close.iloc[p2] < close.iloc[p1] and rsi.iloc[r2] > rsi.iloc[r1]:
            return {"signal": "SELL", "confidence": 72,
                    "reason_fa": "واگرایی مخفی منفی RSI — ادامه روند نزولی محتمل"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "بدون واگرایی مخفی RSI"}


# ─────────────────────────────────────────────────────
# RSI_10: RSI Double Bottom / Double Top
# BUY:  RSI دو بار به زیر 30 رفته و برگشته (W شکل)
# SELL: RSI دو بار به بالای 70 رفته و برگشته (M شکل)
# ─────────────────────────────────────────────────────
def rsi_10_double_pattern(df, context=None):
    rsi = _rsi(df['close'], 14)
    if len(rsi) < 30:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    recent = rsi.iloc[-30:]

    # Double bottom in oversold
    oversold_zones = []
    in_zone = False
    for i in range(len(recent)):
        if recent.iloc[i] < 30:
            if not in_zone:
                in_zone = True
                oversold_zones.append(i)
        else:
            in_zone = False

    if len(oversold_zones) >= 2 and (oversold_zones[-1] - oversold_zones[-2]) > 3:
        if rsi.iloc[-1] > 30 and rsi.iloc[-1] < 50:
            return {"signal": "BUY", "confidence": 76,
                    "reason_fa": "دو کف RSI در اشباع فروش (W Pattern) — سیگنال برگشت"}

    # Double top in overbought
    overbought_zones = []
    in_zone = False
    for i in range(len(recent)):
        if recent.iloc[i] > 70:
            if not in_zone:
                in_zone = True
                overbought_zones.append(i)
        else:
            in_zone = False

    if len(overbought_zones) >= 2 and (overbought_zones[-1] - overbought_zones[-2]) > 3:
        if rsi.iloc[-1] < 70 and rsi.iloc[-1] > 50:
            return {"signal": "SELL", "confidence": 76,
                    "reason_fa": "دو سقف RSI در اشباع خرید (M Pattern) — سیگنال ریزش"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"بدون الگوی دوگانه RSI ({rsi.iloc[-1]:.1f})"}


# ─────────────────────────────────────────────────────
# RSI_11: RSI + EMA Filter
# BUY:  RSI(14) < 30 + قیمت بالای EMA50 (pullback در روند صعودی)
# SELL: RSI(14) > 70 + قیمت زیر EMA50 (pullback در روند نزولی)
# ─────────────────────────────────────────────────────
def rsi_11_ema_filter(df, context=None):
    close = df['close']
    rsi = _rsi(close, 14)
    ema50 = _ema(close, 50)
    r = rsi.iloc[-1]
    price = close.iloc[-1]
    ema_val = ema50.iloc[-1]

    if r < 30 and price > ema_val:
        return {"signal": "BUY", "confidence": 82,
                "reason_fa": f"RSI اشباع فروش ({r:.1f}) + قیمت بالای EMA50 — pullback صعودی"}
    elif r > 70 and price < ema_val:
        return {"signal": "SELL", "confidence": 82,
                "reason_fa": f"RSI اشباع خرید ({r:.1f}) + قیمت زیر EMA50 — pullback نزولی"}
    elif r < 35 and price > ema_val:
        return {"signal": "BUY", "confidence": 60,
                "reason_fa": f"RSI نزدیک اشباع ({r:.1f}) + روند صعودی"}
    elif r > 65 and price < ema_val:
        return {"signal": "SELL", "confidence": 60,
                "reason_fa": f"RSI نزدیک اشباع ({r:.1f}) + روند نزولی"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"RSI+EMA بدون سیگنال (RSI:{r:.1f})"}


# ─────────────────────────────────────────────────────
# RSI_12: RSI Range Shift (Andrew Cardwell)
# BUY:  RSI regime 40-80 (بازار گاوی) + RSI برگشت از 40-50
# SELL: RSI regime 20-60 (بازار خرسی) + RSI برگشت از 50-60
# ─────────────────────────────────────────────────────
def rsi_12_range_shift(df, context=None):
    rsi = _rsi(df['close'], 14)
    if len(rsi) < 50:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    recent_50 = rsi.iloc[-50:]
    rsi_min = recent_50.min()
    rsi_max = recent_50.max()
    r = rsi.iloc[-1]
    r_prev = rsi.iloc[-2]

    # Bullish regime: RSI stays mostly 40-80
    if rsi_min > 35 and rsi_max < 85:
        if r_prev < 45 and r >= 45:
            return {"signal": "BUY", "confidence": 74,
                    "reason_fa": f"رژیم صعودی RSI — برگشت از حمایت 40-45 ({r:.1f})"}
        elif r > 75:
            return {"signal": "NEUTRAL", "confidence": 0,
                    "reason_fa": f"رژیم صعودی — RSI بالا ولی هنوز صعودی ({r:.1f})"}

    # Bearish regime: RSI stays mostly 20-60
    if rsi_min > 15 and rsi_max < 65:
        if r_prev > 55 and r <= 55:
            return {"signal": "SELL", "confidence": 74,
                    "reason_fa": f"رژیم نزولی RSI — برگشت از مقاومت 55-60 ({r:.1f})"}
        elif r < 25:
            return {"signal": "NEUTRAL", "confidence": 0,
                    "reason_fa": f"رژیم نزولی — RSI پایین ولی هنوز نزولی ({r:.1f})"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"بدون رژیم مشخص RSI ({r:.1f})"}


# ═══════════════════════════════════════════════════════
# REGISTRY
# ═══════════════════════════════════════════════════════

RSI_STRATEGIES = [
    {"id": "RSI_01", "name": "RSI Classic 30/70", "name_fa": "RSI کلاسیک ۳۰/۷۰", "func": rsi_01_classic},
    {"id": "RSI_02", "name": "RSI Conservative 25/75", "name_fa": "RSI محافظه‌کار ۲۵/۷۵", "func": rsi_02_conservative},
    {"id": "RSI_03", "name": "RSI Aggressive 35/65", "name_fa": "RSI تهاجمی ۳۵/۶۵", "func": rsi_03_aggressive},
    {"id": "RSI_04", "name": "RSI Ultra 20/80", "name_fa": "RSI فوق‌العاده ۲۰/۸۰", "func": rsi_04_ultra},
    {"id": "RSI_05", "name": "RSI Midline Cross", "name_fa": "RSI تقاطع خط ۵۰", "func": rsi_05_midline},
    {"id": "RSI_06", "name": "RSI Fast(7)", "name_fa": "RSI سریع (۷)", "func": rsi_06_fast},
    {"id": "RSI_07", "name": "RSI Slow(21)", "name_fa": "RSI آهسته (۲۱)", "func": rsi_07_slow},
    {"id": "RSI_08", "name": "RSI Divergence", "name_fa": "واگرایی RSI", "func": rsi_08_divergence},
    {"id": "RSI_09", "name": "RSI Hidden Divergence", "name_fa": "واگرایی مخفی RSI", "func": rsi_09_hidden_div},
    {"id": "RSI_10", "name": "RSI Double Pattern", "name_fa": "الگوی دوگانه RSI", "func": rsi_10_double_pattern},
    {"id": "RSI_11", "name": "RSI + EMA Filter", "name_fa": "RSI + فیلتر EMA", "func": rsi_11_ema_filter},
    {"id": "RSI_12", "name": "RSI Range Shift", "name_fa": "تغییر رژیم RSI", "func": rsi_12_range_shift},
]
