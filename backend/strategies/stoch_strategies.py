"""
Whilber-AI — Stochastic Strategy Pack (8 Sub-Strategies)
=========================================================
STOCH_01: Classic 20/80 (14,3,3)
STOCH_02: Fast (5,3,3)
STOCH_03: Slow (21,7,7)
STOCH_04: Conservative 25/75
STOCH_05: %K/%D Cross
STOCH_06: Stoch Divergence
STOCH_07: Stoch + RSI Double Confirm
STOCH_08: Stoch Pop (George Lane)
"""

import numpy as np
import pandas as pd


def _stoch(df, k_period=14, d_period=3, smooth=3):
    low_min = df['low'].rolling(window=k_period).min()
    high_max = df['high'].rolling(window=k_period).max()
    raw_k = 100 * (df['close'] - low_min) / (high_max - low_min + 1e-10)
    k = raw_k.rolling(window=smooth).mean()
    d = k.rolling(window=d_period).mean()
    return k, d


def _rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    return 100 - (100 / (1 + rs))


def _find_peaks(series, order=5):
    highs, lows = [], []
    arr = series.values
    for i in range(order, len(arr) - order):
        if all(arr[i] >= arr[i-j] for j in range(1, order+1)) and all(arr[i] >= arr[i+j] for j in range(1, order+1)):
            highs.append(i)
        if all(arr[i] <= arr[i-j] for j in range(1, order+1)) and all(arr[i] <= arr[i+j] for j in range(1, order+1)):
            lows.append(i)
    return highs, lows


# ─────────────────────────────────────────────────────
# STOCH_01: Classic 20/80 (14,3,3)
# BUY:  %K < 20 و سپس %K از %D رو به بالا قطع کند (اشباع فروش)
# SELL: %K > 80 و سپس %K از %D رو به پایین قطع کند (اشباع خرید)
# ─────────────────────────────────────────────────────
def stoch_01_classic(df, context=None):
    k, d = _stoch(df, 14, 3, 3)
    k0, d0 = k.iloc[-1], d.iloc[-1]
    k1, d1 = k.iloc[-2], d.iloc[-2]

    if k0 < 20 and k1 <= d1 and k0 > d0:
        return {"signal": "BUY", "confidence": 75,
                "reason_fa": f"استوکاستیک تقاطع صعودی در اشباع فروش (K:{k0:.0f} D:{d0:.0f})"}
    elif k0 > 80 and k1 >= d1 and k0 < d0:
        return {"signal": "SELL", "confidence": 75,
                "reason_fa": f"استوکاستیک تقاطع نزولی در اشباع خرید (K:{k0:.0f} D:{d0:.0f})"}
    elif k0 < 20:
        return {"signal": "BUY", "confidence": 50,
                "reason_fa": f"استوکاستیک در اشباع فروش (K:{k0:.0f}) — منتظر تقاطع"}
    elif k0 > 80:
        return {"signal": "SELL", "confidence": 50,
                "reason_fa": f"استوکاستیک در اشباع خرید (K:{k0:.0f}) — منتظر تقاطع"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"استوکاستیک خنثی (K:{k0:.0f})"}


# ─────────────────────────────────────────────────────
# STOCH_02: Fast Stochastic (5,3,3)
# BUY:  %K(5) < 20 + تقاطع صعودی — واکنش سریع
# SELL: %K(5) > 80 + تقاطع نزولی — واکنش سریع
# ─────────────────────────────────────────────────────
def stoch_02_fast(df, context=None):
    k, d = _stoch(df, 5, 3, 3)
    k0, d0 = k.iloc[-1], d.iloc[-1]
    k1, d1 = k.iloc[-2], d.iloc[-2]

    if k0 < 25 and k1 <= d1 and k0 > d0:
        return {"signal": "BUY", "confidence": 62,
                "reason_fa": f"استوکاستیک سریع(5) تقاطع صعودی (K:{k0:.0f})"}
    elif k0 > 75 and k1 >= d1 and k0 < d0:
        return {"signal": "SELL", "confidence": 62,
                "reason_fa": f"استوکاستیک سریع(5) تقاطع نزولی (K:{k0:.0f})"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"استوکاستیک سریع بدون سیگنال (K:{k0:.0f})"}


# ─────────────────────────────────────────────────────
# STOCH_03: Slow Stochastic (21,7,7)
# BUY:  %K(21) < 20 + تقاطع صعودی — فیلتر نویز بیشتر
# SELL: %K(21) > 80 + تقاطع نزولی
# ─────────────────────────────────────────────────────
def stoch_03_slow(df, context=None):
    k, d = _stoch(df, 21, 7, 7)
    k0, d0 = k.iloc[-1], d.iloc[-1]
    k1, d1 = k.iloc[-2], d.iloc[-2]

    if k0 < 20 and k1 <= d1 and k0 > d0:
        return {"signal": "BUY", "confidence": 78,
                "reason_fa": f"استوکاستیک آهسته(21) تقاطع صعودی (K:{k0:.0f}) — سیگنال معتبر"}
    elif k0 > 80 and k1 >= d1 and k0 < d0:
        return {"signal": "SELL", "confidence": 78,
                "reason_fa": f"استوکاستیک آهسته(21) تقاطع نزولی (K:{k0:.0f}) — سیگنال معتبر"}
    elif k0 < 25:
        return {"signal": "BUY", "confidence": 55,
                "reason_fa": f"استوکاستیک آهسته اشباع فروش (K:{k0:.0f})"}
    elif k0 > 75:
        return {"signal": "SELL", "confidence": 55,
                "reason_fa": f"استوکاستیک آهسته اشباع خرید (K:{k0:.0f})"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"استوکاستیک آهسته خنثی (K:{k0:.0f})"}


# ─────────────────────────────────────────────────────
# STOCH_04: Conservative 25/75
# BUY:  %K < 25 + %D < 25 (هر دو اشباع فروش)
# SELL: %K > 75 + %D > 75 (هر دو اشباع خرید)
# ─────────────────────────────────────────────────────
def stoch_04_conservative(df, context=None):
    k, d = _stoch(df, 14, 3, 3)
    k0, d0 = k.iloc[-1], d.iloc[-1]
    k1 = k.iloc[-2]

    if k0 < 25 and d0 < 25 and k0 > k1:
        return {"signal": "BUY", "confidence": 70,
                "reason_fa": f"استوکاستیک محافظه‌کار: K و D هر دو زیر ۲۵ + صعودی"}
    elif k0 > 75 and d0 > 75 and k0 < k1:
        return {"signal": "SELL", "confidence": 70,
                "reason_fa": f"استوکاستیک محافظه‌کار: K و D هر دو بالای ۷۵ + نزولی"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"استوکاستیک محافظه‌کار بدون سیگنال (K:{k0:.0f} D:{d0:.0f})"}


# ─────────────────────────────────────────────────────
# STOCH_05: %K/%D Cross (anywhere)
# BUY:  %K از %D رو به بالا قطع (در هر ناحیه)
# SELL: %K از %D رو به پایین قطع (در هر ناحیه)
# ─────────────────────────────────────────────────────
def stoch_05_kd_cross(df, context=None):
    k, d = _stoch(df, 14, 3, 3)
    k0, d0 = k.iloc[-1], d.iloc[-1]
    k1, d1 = k.iloc[-2], d.iloc[-2]

    if k1 <= d1 and k0 > d0:
        # Stronger if in oversold zone
        zone_bonus = 15 if k0 < 30 else 5 if k0 < 50 else 0
        conf = 55 + zone_bonus
        return {"signal": "BUY", "confidence": conf,
                "reason_fa": f"استوکاستیک %K از %D صعودی قطع (K:{k0:.0f})"}
    elif k1 >= d1 and k0 < d0:
        zone_bonus = 15 if k0 > 70 else 5 if k0 > 50 else 0
        conf = 55 + zone_bonus
        return {"signal": "SELL", "confidence": conf,
                "reason_fa": f"استوکاستیک %K از %D نزولی قطع (K:{k0:.0f})"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"بدون تقاطع K/D (K:{k0:.0f} D:{d0:.0f})"}


# ─────────────────────────────────────────────────────
# STOCH_06: Stochastic Divergence
# BUY:  قیمت کف پایین‌تر + %K کف بالاتر (واگرایی مثبت)
# SELL: قیمت سقف بالاتر + %K سقف پایین‌تر (واگرایی منفی)
# ─────────────────────────────────────────────────────
def stoch_06_divergence(df, context=None):
    close = df['close']
    k, _ = _stoch(df, 14, 3, 3)
    if len(k) < 30:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    p_highs, p_lows = _find_peaks(close, order=5)
    k_highs, k_lows = _find_peaks(k, order=3)

    # Bullish divergence
    if len(p_lows) >= 2 and len(k_lows) >= 2:
        if close.iloc[p_lows[-1]] < close.iloc[p_lows[-2]] and k.iloc[k_lows[-1]] > k.iloc[k_lows[-2]]:
            if k.iloc[-1] < 40:
                return {"signal": "BUY", "confidence": 75,
                        "reason_fa": "واگرایی مثبت استوکاستیک — سیگنال برگشت صعودی"}

    # Bearish divergence
    if len(p_highs) >= 2 and len(k_highs) >= 2:
        if close.iloc[p_highs[-1]] > close.iloc[p_highs[-2]] and k.iloc[k_highs[-1]] < k.iloc[k_highs[-2]]:
            if k.iloc[-1] > 60:
                return {"signal": "SELL", "confidence": 75,
                        "reason_fa": "واگرایی منفی استوکاستیک — سیگنال ریزش"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "بدون واگرایی استوکاستیک"}


# ─────────────────────────────────────────────────────
# STOCH_07: Stoch + RSI Double Confirm
# BUY:  %K < 20 + RSI < 35 (هر دو اشباع فروش)
# SELL: %K > 80 + RSI > 65 (هر دو اشباع خرید)
# ─────────────────────────────────────────────────────
def stoch_07_rsi_combo(df, context=None):
    k, d = _stoch(df, 14, 3, 3)
    rsi = _rsi(df['close'], 14)
    k0 = k.iloc[-1]
    r = rsi.iloc[-1]
    k1 = k.iloc[-2]

    if k0 < 20 and r < 35:
        conf = min(88, 70 + int((35 - r) + (20 - k0) / 2))
        return {"signal": "BUY", "confidence": conf,
                "reason_fa": f"استوکاستیک({k0:.0f}) + RSI({r:.0f}) هر دو اشباع فروش — سیگنال قوی!"}
    elif k0 > 80 and r > 65:
        conf = min(88, 70 + int((r - 65) + (k0 - 80) / 2))
        return {"signal": "SELL", "confidence": conf,
                "reason_fa": f"استوکاستیک({k0:.0f}) + RSI({r:.0f}) هر دو اشباع خرید — سیگنال قوی!"}
    elif k0 < 25 and r < 40:
        return {"signal": "BUY", "confidence": 60,
                "reason_fa": f"استوکاستیک + RSI نزدیک اشباع فروش"}
    elif k0 > 75 and r > 60:
        return {"signal": "SELL", "confidence": 60,
                "reason_fa": f"استوکاستیک + RSI نزدیک اشباع خرید"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"Stoch+RSI بدون هم‌پوشانی (K:{k0:.0f} RSI:{r:.0f})"}


# ─────────────────────────────────────────────────────
# STOCH_08: Stochastic Pop (George Lane)
# BUY:  %K از زیر 20 به بالای 80 پرش کند (حرکت انفجاری صعودی)
# SELL: %K از بالای 80 به زیر 20 سقوط کند (حرکت انفجاری نزولی)
# ─────────────────────────────────────────────────────
def stoch_08_pop(df, context=None):
    k, _ = _stoch(df, 14, 3, 3)
    if len(k) < 10:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    recent_10 = k.iloc[-10:]
    k0 = k.iloc[-1]

    # Check if was below 20 recently and now above 80
    was_below_20 = any(recent_10.iloc[:-2] < 20)
    was_above_80 = any(recent_10.iloc[:-2] > 80)

    if was_below_20 and k0 > 75:
        return {"signal": "BUY", "confidence": 80,
                "reason_fa": f"Stochastic Pop صعودی! از زیر 20 به {k0:.0f} پرش — مومنتوم قوی"}
    elif was_above_80 and k0 < 25:
        return {"signal": "SELL", "confidence": 80,
                "reason_fa": f"Stochastic Pop نزولی! از بالای 80 به {k0:.0f} سقوط — فشار فروش"}

    # Partial pop
    was_below_30 = any(recent_10.iloc[:-2] < 30)
    was_above_70 = any(recent_10.iloc[:-2] > 70)

    if was_below_30 and k0 > 60:
        return {"signal": "BUY", "confidence": 58,
                "reason_fa": f"استوکاستیک در حال پرش صعودی ({k0:.0f})"}
    elif was_above_70 and k0 < 40:
        return {"signal": "SELL", "confidence": 58,
                "reason_fa": f"استوکاستیک در حال سقوط ({k0:.0f})"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"بدون Pop استوکاستیک (K:{k0:.0f})"}


# ═══════════════════════════════════════════════════════
# REGISTRY
# ═══════════════════════════════════════════════════════

STOCH_STRATEGIES = [
    {"id": "STOCH_01", "name": "Stoch Classic 20/80", "name_fa": "استوکاستیک کلاسیک", "func": stoch_01_classic},
    {"id": "STOCH_02", "name": "Stoch Fast (5,3,3)", "name_fa": "استوکاستیک سریع", "func": stoch_02_fast},
    {"id": "STOCH_03", "name": "Stoch Slow (21,7,7)", "name_fa": "استوکاستیک آهسته", "func": stoch_03_slow},
    {"id": "STOCH_04", "name": "Stoch Conservative 25/75", "name_fa": "استوکاستیک محافظه‌کار", "func": stoch_04_conservative},
    {"id": "STOCH_05", "name": "Stoch K/D Cross", "name_fa": "تقاطع K/D استوکاستیک", "func": stoch_05_kd_cross},
    {"id": "STOCH_06", "name": "Stoch Divergence", "name_fa": "واگرایی استوکاستیک", "func": stoch_06_divergence},
    {"id": "STOCH_07", "name": "Stoch + RSI Combo", "name_fa": "استوکاستیک + RSI ترکیبی", "func": stoch_07_rsi_combo},
    {"id": "STOCH_08", "name": "Stoch Pop", "name_fa": "پرش استوکاستیک (Lane)", "func": stoch_08_pop},
]
