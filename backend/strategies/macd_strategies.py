"""
Whilber-AI — MACD Strategy Pack (10 Sub-Strategies)
=====================================================
MACD_01: Classic Signal Cross (12,26,9)
MACD_02: Fast Signal Cross (8,21,5)
MACD_03: Scalp Signal Cross (5,13,3)
MACD_04: Zero Line Cross
MACD_05: Histogram Reversal
MACD_06: Histogram Divergence
MACD_07: Double Cross (signal + zero)
MACD_08: Momentum (histogram slope)
MACD_09: MACD + RSI Combo
MACD_10: MACD Hidden Divergence
"""

import numpy as np
import pandas as pd


def _ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def _macd(close, fast=12, slow=26, signal=9):
    ema_fast = _ema(close, fast)
    ema_slow = _ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


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
# MACD_01: Classic Signal Cross (12,26,9)
# BUY:  MACD خط سیگنال را از پایین به بالا قطع کند
# SELL: MACD خط سیگنال را از بالا به پایین قطع کند
# ─────────────────────────────────────────────────────
def macd_01_classic(df, context=None):
    macd, signal, hist = _macd(df['close'], 12, 26, 9)
    h = hist.iloc[-1]
    h_prev = hist.iloc[-2]

    if h_prev <= 0 and h > 0:
        strength = abs(h) / (abs(macd.iloc[-1]) + 1e-10) * 100
        conf = min(85, 60 + int(strength))
        return {"signal": "BUY", "confidence": conf,
                "reason_fa": f"MACD سیگنال را صعودی قطع کرد — کلاسیک (12,26,9)"}
    elif h_prev >= 0 and h < 0:
        strength = abs(h) / (abs(macd.iloc[-1]) + 1e-10) * 100
        conf = min(85, 60 + int(strength))
        return {"signal": "SELL", "confidence": conf,
                "reason_fa": f"MACD سیگنال را نزولی قطع کرد — کلاسیک (12,26,9)"}

    if h > 0 and h > h_prev:
        return {"signal": "BUY", "confidence": 45,
                "reason_fa": "MACD صعودی و در حال تقویت"}
    elif h < 0 and h < h_prev:
        return {"signal": "SELL", "confidence": 45,
                "reason_fa": "MACD نزولی و در حال تقویت"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"MACD بدون تقاطع سیگنال"}


# ─────────────────────────────────────────────────────
# MACD_02: Fast Signal Cross (8,21,5)
# BUY:  MACD(8,21,5) خط سیگنال را صعودی قطع
# SELL: MACD(8,21,5) خط سیگنال را نزولی قطع
# ─────────────────────────────────────────────────────
def macd_02_fast(df, context=None):
    macd, signal, hist = _macd(df['close'], 8, 21, 5)
    h = hist.iloc[-1]
    h_prev = hist.iloc[-2]

    if h_prev <= 0 and h > 0:
        return {"signal": "BUY", "confidence": 62,
                "reason_fa": "MACD سریع (8,21,5) تقاطع صعودی — واکنش سریع‌تر"}
    elif h_prev >= 0 and h < 0:
        return {"signal": "SELL", "confidence": 62,
                "reason_fa": "MACD سریع (8,21,5) تقاطع نزولی — واکنش سریع‌تر"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "MACD سریع بدون تقاطع"}


# ─────────────────────────────────────────────────────
# MACD_03: Scalp Signal Cross (5,13,3)
# BUY:  MACD(5,13,3) تقاطع صعودی — برای اسکالپ
# SELL: MACD(5,13,3) تقاطع نزولی — برای اسکالپ
# ─────────────────────────────────────────────────────
def macd_03_scalp(df, context=None):
    macd, signal, hist = _macd(df['close'], 5, 13, 3)
    h = hist.iloc[-1]
    h_prev = hist.iloc[-2]

    if h_prev <= 0 and h > 0:
        return {"signal": "BUY", "confidence": 55,
                "reason_fa": "MACD اسکالپ (5,13,3) تقاطع صعودی — بسیار سریع"}
    elif h_prev >= 0 and h < 0:
        return {"signal": "SELL", "confidence": 55,
                "reason_fa": "MACD اسکالپ (5,13,3) تقاطع نزولی — بسیار سریع"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "MACD اسکالپ بدون تقاطع"}


# ─────────────────────────────────────────────────────
# MACD_04: Zero Line Cross
# BUY:  MACD line از زیر صفر به بالای صفر عبور کند
# SELL: MACD line از بالای صفر به زیر صفر عبور کند
# ─────────────────────────────────────────────────────
def macd_04_zero_cross(df, context=None):
    macd, signal, hist = _macd(df['close'], 12, 26, 9)
    m = macd.iloc[-1]
    m_prev = macd.iloc[-2]

    if m_prev <= 0 and m > 0:
        return {"signal": "BUY", "confidence": 72,
                "reason_fa": f"MACD خط صفر را صعودی قطع کرد — تایید روند صعودی"}
    elif m_prev >= 0 and m < 0:
        return {"signal": "SELL", "confidence": 72,
                "reason_fa": f"MACD خط صفر را نزولی قطع کرد — تایید روند نزولی"}
    elif m > 0:
        return {"signal": "BUY", "confidence": 40,
                "reason_fa": "MACD بالای صفر — روند صعودی"}
    elif m < 0:
        return {"signal": "SELL", "confidence": 40,
                "reason_fa": "MACD زیر صفر — روند نزولی"}
    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "MACD روی خط صفر"}


# ─────────────────────────────────────────────────────
# MACD_05: Histogram Reversal
# BUY:  هیستوگرام منفی بوده و شروع به کم شدن کرده (میله‌ها کوتاه‌تر)
# SELL: هیستوگرام مثبت بوده و شروع به کم شدن کرده
# ─────────────────────────────────────────────────────
def macd_05_hist_reversal(df, context=None):
    _, _, hist = _macd(df['close'], 12, 26, 9)
    if len(hist) < 5:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    h0, h1, h2 = hist.iloc[-1], hist.iloc[-2], hist.iloc[-3]

    # Bearish histogram shrinking → bullish reversal
    if h2 < h1 < 0 and h0 > h1:
        shrink_pct = abs(h0 - h1) / (abs(h1) + 1e-10) * 100
        conf = min(75, 55 + int(shrink_pct / 5))
        return {"signal": "BUY", "confidence": conf,
                "reason_fa": "هیستوگرام MACD منفی در حال کوتاه شدن — برگشت صعودی"}

    # Bullish histogram shrinking → bearish reversal
    if h2 > h1 > 0 and h0 < h1:
        shrink_pct = abs(h1 - h0) / (abs(h1) + 1e-10) * 100
        conf = min(75, 55 + int(shrink_pct / 5))
        return {"signal": "SELL", "confidence": conf,
                "reason_fa": "هیستوگرام MACD مثبت در حال کوتاه شدن — برگشت نزولی"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "هیستوگرام MACD بدون الگوی برگشت"}


# ─────────────────────────────────────────────────────
# MACD_06: Histogram Divergence
# BUY:  قیمت کف پایین‌تر + هیستوگرام کف بالاتر (واگرایی مثبت)
# SELL: قیمت سقف بالاتر + هیستوگرام سقف پایین‌تر (واگرایی منفی)
# ─────────────────────────────────────────────────────
def macd_06_hist_divergence(df, context=None):
    close = df['close']
    _, _, hist = _macd(close, 12, 26, 9)
    if len(hist) < 30:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    p_highs, p_lows = _find_peaks(close, order=5)
    h_highs, h_lows = _find_peaks(hist, order=3)

    # Bullish: price lower low + hist higher low
    if len(p_lows) >= 2 and len(h_lows) >= 2:
        if close.iloc[p_lows[-1]] < close.iloc[p_lows[-2]] and hist.iloc[h_lows[-1]] > hist.iloc[h_lows[-2]]:
            return {"signal": "BUY", "confidence": 76,
                    "reason_fa": "واگرایی مثبت هیستوگرام MACD — سیگنال برگشت صعودی"}

    # Bearish: price higher high + hist lower high
    if len(p_highs) >= 2 and len(h_highs) >= 2:
        if close.iloc[p_highs[-1]] > close.iloc[p_highs[-2]] and hist.iloc[h_highs[-1]] < hist.iloc[h_highs[-2]]:
            return {"signal": "SELL", "confidence": 76,
                    "reason_fa": "واگرایی منفی هیستوگرام MACD — سیگنال ریزش"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "بدون واگرایی هیستوگرام MACD"}


# ─────────────────────────────────────────────────────
# MACD_07: Double Cross (Signal + Zero)
# BUY:  MACD تقاطع صعودی سیگنال + بالای صفر (هر دو تایید)
# SELL: MACD تقاطع نزولی سیگنال + زیر صفر (هر دو تایید)
# ─────────────────────────────────────────────────────
def macd_07_double_cross(df, context=None):
    macd, signal, hist = _macd(df['close'], 12, 26, 9)
    m = macd.iloc[-1]
    h = hist.iloc[-1]
    h_prev = hist.iloc[-2]

    # Signal cross bullish AND above zero
    if h_prev <= 0 and h > 0 and m > 0:
        return {"signal": "BUY", "confidence": 85,
                "reason_fa": "MACD تقاطع صعودی سیگنال + بالای خط صفر — سیگنال دوگانه قوی!"}

    # Signal cross bearish AND below zero
    if h_prev >= 0 and h < 0 and m < 0:
        return {"signal": "SELL", "confidence": 85,
                "reason_fa": "MACD تقاطع نزولی سیگنال + زیر خط صفر — سیگنال دوگانه قوی!"}

    # Only signal cross (weaker)
    if h_prev <= 0 and h > 0:
        return {"signal": "BUY", "confidence": 55,
                "reason_fa": "MACD تقاطع صعودی سیگنال ولی زیر صفر — ضعیف"}
    if h_prev >= 0 and h < 0:
        return {"signal": "SELL", "confidence": 55,
                "reason_fa": "MACD تقاطع نزولی سیگنال ولی بالای صفر — ضعیف"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "MACD بدون تقاطع دوگانه"}


# ─────────────────────────────────────────────────────
# MACD_08: Momentum (Histogram Slope)
# BUY:  ۳ هیستوگرام متوالی صعودی (هر کدام بزرگتر از قبلی)
# SELL: ۳ هیستوگرام متوالی نزولی (هر کدام کوچکتر از قبلی)
# ─────────────────────────────────────────────────────
def macd_08_momentum(df, context=None):
    _, _, hist = _macd(df['close'], 12, 26, 9)
    if len(hist) < 5:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    h0, h1, h2, h3 = hist.iloc[-1], hist.iloc[-2], hist.iloc[-3], hist.iloc[-4]

    # 3 consecutive rising histograms
    if h0 > h1 > h2 > h3:
        slope = (h0 - h3) / 3
        conf = min(78, 55 + int(abs(slope) * 500))
        if h0 > 0:
            return {"signal": "BUY", "confidence": conf,
                    "reason_fa": "مومنتوم MACD صعودی — ۳ میله متوالی افزایشی"}
        else:
            return {"signal": "BUY", "confidence": max(50, conf - 10),
                    "reason_fa": "مومنتوم MACD در حال بهبود — ۳ میله متوالی بهتر"}

    # 3 consecutive falling histograms
    if h0 < h1 < h2 < h3:
        slope = (h3 - h0) / 3
        conf = min(78, 55 + int(abs(slope) * 500))
        if h0 < 0:
            return {"signal": "SELL", "confidence": conf,
                    "reason_fa": "مومنتوم MACD نزولی — ۳ میله متوالی کاهشی"}
        else:
            return {"signal": "SELL", "confidence": max(50, conf - 10),
                    "reason_fa": "مومنتوم MACD در حال تضعیف — ۳ میله متوالی بدتر"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "MACD بدون مومنتوم مشخص"}


# ─────────────────────────────────────────────────────
# MACD_09: MACD + RSI Combo
# BUY:  MACD تقاطع صعودی + RSI < 40 (هم‌زمان)
# SELL: MACD تقاطع نزولی + RSI > 60 (هم‌زمان)
# ─────────────────────────────────────────────────────
def macd_09_rsi_combo(df, context=None):
    close = df['close']
    _, _, hist = _macd(close, 12, 26, 9)
    rsi = _rsi(close, 14)
    h = hist.iloc[-1]
    h_prev = hist.iloc[-2]
    r = rsi.iloc[-1]

    if h_prev <= 0 and h > 0 and r < 40:
        conf = min(88, 70 + int((40 - r)))
        return {"signal": "BUY", "confidence": conf,
                "reason_fa": f"MACD تقاطع صعودی + RSI پایین ({r:.0f}) — ترکیب قوی خرید!"}
    elif h_prev >= 0 and h < 0 and r > 60:
        conf = min(88, 70 + int((r - 60)))
        return {"signal": "SELL", "confidence": conf,
                "reason_fa": f"MACD تقاطع نزولی + RSI بالا ({r:.0f}) — ترکیب قوی فروش!"}

    if h_prev <= 0 and h > 0:
        return {"signal": "BUY", "confidence": 52,
                "reason_fa": f"MACD تقاطع صعودی ولی RSI تایید نکرد ({r:.0f})"}
    if h_prev >= 0 and h < 0:
        return {"signal": "SELL", "confidence": 52,
                "reason_fa": f"MACD تقاطع نزولی ولی RSI تایید نکرد ({r:.0f})"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"MACD+RSI بدون سیگنال (RSI:{r:.0f})"}


# ─────────────────────────────────────────────────────
# MACD_10: MACD Hidden Divergence
# BUY:  قیمت کف بالاتر + MACD کف پایین‌تر (ادامه صعودی)
# SELL: قیمت سقف پایین‌تر + MACD سقف بالاتر (ادامه نزولی)
# ─────────────────────────────────────────────────────
def macd_10_hidden_div(df, context=None):
    close = df['close']
    macd, _, _ = _macd(close, 12, 26, 9)
    if len(macd) < 30:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    p_highs, p_lows = _find_peaks(close, order=5)
    m_highs, m_lows = _find_peaks(macd, order=3)

    # Hidden bullish: price higher low + MACD lower low
    if len(p_lows) >= 2 and len(m_lows) >= 2:
        if close.iloc[p_lows[-1]] > close.iloc[p_lows[-2]] and macd.iloc[m_lows[-1]] < macd.iloc[m_lows[-2]]:
            return {"signal": "BUY", "confidence": 74,
                    "reason_fa": "واگرایی مخفی مثبت MACD — ادامه روند صعودی محتمل"}

    # Hidden bearish: price lower high + MACD higher high
    if len(p_highs) >= 2 and len(m_highs) >= 2:
        if close.iloc[p_highs[-1]] < close.iloc[p_highs[-2]] and macd.iloc[m_highs[-1]] > macd.iloc[m_highs[-2]]:
            return {"signal": "SELL", "confidence": 74,
                    "reason_fa": "واگرایی مخفی منفی MACD — ادامه روند نزولی محتمل"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "بدون واگرایی مخفی MACD"}


# ═══════════════════════════════════════════════════════
# REGISTRY
# ═══════════════════════════════════════════════════════

MACD_STRATEGIES = [
    {"id": "MACD_01", "name": "MACD Classic (12,26,9)", "name_fa": "MACD کلاسیک", "func": macd_01_classic},
    {"id": "MACD_02", "name": "MACD Fast (8,21,5)", "name_fa": "MACD سریع", "func": macd_02_fast},
    {"id": "MACD_03", "name": "MACD Scalp (5,13,3)", "name_fa": "MACD اسکالپ", "func": macd_03_scalp},
    {"id": "MACD_04", "name": "MACD Zero Cross", "name_fa": "MACD تقاطع صفر", "func": macd_04_zero_cross},
    {"id": "MACD_05", "name": "MACD Hist Reversal", "name_fa": "برگشت هیستوگرام MACD", "func": macd_05_hist_reversal},
    {"id": "MACD_06", "name": "MACD Hist Divergence", "name_fa": "واگرایی هیستوگرام MACD", "func": macd_06_hist_divergence},
    {"id": "MACD_07", "name": "MACD Double Cross", "name_fa": "MACD تقاطع دوگانه", "func": macd_07_double_cross},
    {"id": "MACD_08", "name": "MACD Momentum", "name_fa": "مومنتوم MACD", "func": macd_08_momentum},
    {"id": "MACD_09", "name": "MACD + RSI Combo", "name_fa": "MACD + RSI ترکیبی", "func": macd_09_rsi_combo},
    {"id": "MACD_10", "name": "MACD Hidden Divergence", "name_fa": "واگرایی مخفی MACD", "func": macd_10_hidden_div},
]
