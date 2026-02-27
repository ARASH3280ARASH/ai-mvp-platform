"""
Whilber-AI — Candle Pattern Strategy Pack (10 Sub-Strategies)
==============================================================
CDL_01: Hammer / Hanging Man
CDL_02: Engulfing (Bullish / Bearish)
CDL_03: Doji (Indecision / Reversal)
CDL_04: Morning Star / Evening Star
CDL_05: Three White Soldiers / Three Black Crows
CDL_06: Piercing Line / Dark Cloud Cover
CDL_07: Harami (Bullish / Bearish)
CDL_08: Marubozu (Full Body Candle)
CDL_09: Tweezer Top / Bottom
CDL_10: Spinning Top + Trend Context
"""

import numpy as np
import pandas as pd


def _body(o, c):
    return c - o

def _body_abs(o, c):
    return abs(c - o)

def _upper_shadow(h, o, c):
    return h - max(o, c)

def _lower_shadow(o, c, l):
    return min(o, c) - l

def _is_bullish(o, c):
    return c > o

def _is_bearish(o, c):
    return c < o

def _avg_body(df, n=10):
    """Average absolute body size of last n candles."""
    bodies = (df['close'] - df['open']).abs().tail(n)
    return bodies.mean() if len(bodies) > 0 else 0

def _trend_direction(df, lookback=10):
    """Simple trend: +1 uptrend, -1 downtrend, 0 neutral."""
    close = df['close']
    if len(close) < lookback + 1:
        return 0
    change = close.iloc[-1] - close.iloc[-(lookback+1)]
    pct = change / close.iloc[-(lookback+1)] * 100
    if pct > 1:
        return 1
    elif pct < -1:
        return -1
    return 0

def _sma(series, period):
    return series.rolling(window=period, min_periods=period).mean()


# ─────────────────────────────────────────────────────
# CDL_01: Hammer / Hanging Man
# Hammer at bottom of downtrend = BUY
# Hanging Man at top of uptrend = SELL
# Shape: small body, long lower shadow (2x+ body), tiny upper shadow
# ─────────────────────────────────────────────────────
def cdl_01_hammer(df, context=None):
    o = df['open'].iloc[-1]; h = df['high'].iloc[-1]
    l = df['low'].iloc[-1]; c = df['close'].iloc[-1]
    body = _body_abs(o, c)
    lower = _lower_shadow(o, c, l)
    upper = _upper_shadow(h, o, c)
    avg = _avg_body(df, 14)
    trend = _trend_direction(df, 10)

    if avg == 0:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    is_hammer_shape = (lower >= 2 * body) and (upper <= body * 0.5) and (body > avg * 0.3)

    if not is_hammer_shape:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "الگوی چکش/مرد آویزان شناسایی نشد"}

    ratio = lower / max(body, 0.0001)
    if trend == -1:
        conf = min(82, 60 + int(ratio * 5))
        return {"signal": "BUY", "confidence": conf,
                "reason_fa": f"چکش (Hammer) در انتهای روند نزولی — سایه پایین {ratio:.1f}x بدنه"}
    elif trend == 1:
        conf = min(78, 58 + int(ratio * 5))
        return {"signal": "SELL", "confidence": conf,
                "reason_fa": f"مرد آویزان (Hanging Man) در بالای روند صعودی — سایه پایین {ratio:.1f}x بدنه"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"شکل چکش ولی بدون روند مشخص (نسبت سایه {ratio:.1f}x)"}


# ─────────────────────────────────────────────────────
# CDL_02: Engulfing (Bullish / Bearish)
# BUY:  Bearish candle followed by larger bullish candle that engulfs it
# SELL: Bullish candle followed by larger bearish candle that engulfs it
# ─────────────────────────────────────────────────────
def cdl_02_engulfing(df, context=None):
    if len(df) < 3:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    o1 = df['open'].iloc[-2]; c1 = df['close'].iloc[-2]
    o2 = df['open'].iloc[-1]; c2 = df['close'].iloc[-1]
    body1 = _body_abs(o1, c1)
    body2 = _body_abs(o2, c2)
    avg = _avg_body(df, 14)
    trend = _trend_direction(df, 10)

    # Bullish engulfing: prev bearish, current bullish, current body > prev body
    if _is_bearish(o1, c1) and _is_bullish(o2, c2) and o2 <= c1 and c2 >= o1 and body2 > body1:
        engulf_ratio = body2 / max(body1, 0.0001)
        conf = min(88, 65 + int(engulf_ratio * 8))
        if trend == -1:
            conf = min(90, conf + 5)
        return {"signal": "BUY", "confidence": conf,
                "reason_fa": f"پوشای صعودی (Bullish Engulfing) — بدنه {engulf_ratio:.1f}x کندل قبل"}

    # Bearish engulfing: prev bullish, current bearish, current body > prev body
    if _is_bullish(o1, c1) and _is_bearish(o2, c2) and o2 >= c1 and c2 <= o1 and body2 > body1:
        engulf_ratio = body2 / max(body1, 0.0001)
        conf = min(88, 65 + int(engulf_ratio * 8))
        if trend == 1:
            conf = min(90, conf + 5)
        return {"signal": "SELL", "confidence": conf,
                "reason_fa": f"پوشای نزولی (Bearish Engulfing) — بدنه {engulf_ratio:.1f}x کندل قبل"}

    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "الگوی پوشا شناسایی نشد"}


# ─────────────────────────────────────────────────────
# CDL_03: Doji (Indecision / Potential Reversal)
# Very small body relative to range
# After trend = potential reversal signal
# ─────────────────────────────────────────────────────
def cdl_03_doji(df, context=None):
    o = df['open'].iloc[-1]; h = df['high'].iloc[-1]
    l = df['low'].iloc[-1]; c = df['close'].iloc[-1]
    body = _body_abs(o, c)
    candle_range = h - l
    avg = _avg_body(df, 14)
    trend = _trend_direction(df, 10)

    if candle_range == 0:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "کندل بدون تغییر"}

    body_ratio = body / candle_range

    if body_ratio > 0.1:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "الگوی دوجی شناسایی نشد"}

    upper = _upper_shadow(h, o, c)
    lower = _lower_shadow(o, c, l)

    # Dragonfly Doji (long lower shadow, no upper) = bullish at bottom
    if lower > candle_range * 0.6 and upper < candle_range * 0.1:
        if trend == -1:
            return {"signal": "BUY", "confidence": 75,
                    "reason_fa": "دوجی سنجاقک (Dragonfly) در انتهای نزول — برگشت صعودی محتمل"}
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "دوجی سنجاقک بدون روند نزولی قبلی"}

    # Gravestone Doji (long upper shadow, no lower) = bearish at top
    if upper > candle_range * 0.6 and lower < candle_range * 0.1:
        if trend == 1:
            return {"signal": "SELL", "confidence": 75,
                    "reason_fa": "دوجی سنگ قبر (Gravestone) در بالای صعود — برگشت نزولی محتمل"}
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "دوجی سنگ قبر بدون روند صعودی قبلی"}

    # Standard Doji
    if trend == 1:
        return {"signal": "SELL", "confidence": 60,
                "reason_fa": "دوجی استاندارد بعد از صعود — بلاتکلیفی، احتمال برگشت"}
    elif trend == -1:
        return {"signal": "BUY", "confidence": 60,
                "reason_fa": "دوجی استاندارد بعد از نزول — بلاتکلیفی، احتمال برگشت"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "دوجی بدون روند مشخص — بلاتکلیفی"}


# ─────────────────────────────────────────────────────
# CDL_04: Morning Star / Evening Star
# Morning Star (3 candles): big bearish + small body + big bullish = BUY
# Evening Star (3 candles): big bullish + small body + big bearish = SELL
# ─────────────────────────────────────────────────────
def cdl_04_star(df, context=None):
    if len(df) < 4:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    o1 = df['open'].iloc[-3]; c1 = df['close'].iloc[-3]
    o2 = df['open'].iloc[-2]; c2 = df['close'].iloc[-2]
    o3 = df['open'].iloc[-1]; c3 = df['close'].iloc[-1]
    body1 = _body_abs(o1, c1)
    body2 = _body_abs(o2, c2)
    body3 = _body_abs(o3, c3)
    avg = _avg_body(df, 14)

    # Morning Star
    if (_is_bearish(o1, c1) and body1 > avg * 0.8 and
        body2 < avg * 0.5 and
        _is_bullish(o3, c3) and body3 > avg * 0.8 and
        c3 > (o1 + c1) / 2):
        conf = min(85, 65 + int((body3 / max(avg, 0.0001)) * 10))
        return {"signal": "BUY", "confidence": conf,
                "reason_fa": "ستاره صبحگاهی (Morning Star) — الگوی سه‌کندلی برگشت صعودی"}

    # Evening Star
    if (_is_bullish(o1, c1) and body1 > avg * 0.8 and
        body2 < avg * 0.5 and
        _is_bearish(o3, c3) and body3 > avg * 0.8 and
        c3 < (o1 + c1) / 2):
        conf = min(85, 65 + int((body3 / max(avg, 0.0001)) * 10))
        return {"signal": "SELL", "confidence": conf,
                "reason_fa": "ستاره شامگاهی (Evening Star) — الگوی سه‌کندلی برگشت نزولی"}

    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "الگوی ستاره شناسایی نشد"}


# ─────────────────────────────────────────────────────
# CDL_05: Three White Soldiers / Three Black Crows
# 3 consecutive bullish candles with higher closes = BUY
# 3 consecutive bearish candles with lower closes = SELL
# ─────────────────────────────────────────────────────
def cdl_05_three_soldiers(df, context=None):
    if len(df) < 4:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    avg = _avg_body(df, 14)
    candles = []
    for i in range(-3, 0):
        o = df['open'].iloc[i]; c = df['close'].iloc[i]
        candles.append({"o": o, "c": c, "body": _body_abs(o, c), "bull": _is_bullish(o, c)})

    # Three White Soldiers
    if (all(c["bull"] for c in candles) and
        all(c["body"] > avg * 0.5 for c in candles) and
        candles[1]["c"] > candles[0]["c"] and candles[2]["c"] > candles[1]["c"] and
        candles[1]["o"] > candles[0]["o"] and candles[2]["o"] > candles[1]["o"]):
        total_move = (candles[2]["c"] - candles[0]["o"]) / candles[0]["o"] * 100
        return {"signal": "BUY", "confidence": 82,
                "reason_fa": f"سه سرباز سفید (Three White Soldiers) — ۳ کندل صعودی قوی متوالی ({total_move:+.2f}%)"}

    # Three Black Crows
    if (all(not c["bull"] for c in candles) and
        all(c["body"] > avg * 0.5 for c in candles) and
        candles[1]["c"] < candles[0]["c"] and candles[2]["c"] < candles[1]["c"] and
        candles[1]["o"] < candles[0]["o"] and candles[2]["o"] < candles[1]["o"]):
        total_move = (candles[2]["c"] - candles[0]["o"]) / candles[0]["o"] * 100
        return {"signal": "SELL", "confidence": 82,
                "reason_fa": f"سه کلاغ سیاه (Three Black Crows) — ۳ کندل نزولی قوی متوالی ({total_move:+.2f}%)"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "الگوی سه سرباز/کلاغ شناسایی نشد"}


# ─────────────────────────────────────────────────────
# CDL_06: Piercing Line / Dark Cloud Cover
# Piercing: bearish + bullish that opens below low and closes above 50% of prev body = BUY
# Dark Cloud: bullish + bearish that opens above high and closes below 50% = SELL
# ─────────────────────────────────────────────────────
def cdl_06_piercing(df, context=None):
    if len(df) < 3:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    o1 = df['open'].iloc[-2]; c1 = df['close'].iloc[-2]; h1 = df['high'].iloc[-2]; l1 = df['low'].iloc[-2]
    o2 = df['open'].iloc[-1]; c2 = df['close'].iloc[-1]
    body1 = _body_abs(o1, c1)
    avg = _avg_body(df, 14)
    mid1 = (o1 + c1) / 2

    # Piercing Line
    if (_is_bearish(o1, c1) and body1 > avg * 0.7 and
        _is_bullish(o2, c2) and o2 < c1 and c2 > mid1 and c2 < o1):
        penetration = (c2 - c1) / body1 * 100
        return {"signal": "BUY", "confidence": min(80, 60 + int(penetration * 0.3)),
                "reason_fa": f"خط نفوذ (Piercing Line) — نفوذ {penetration:.0f}% در بدنه کندل قبل"}

    # Dark Cloud Cover
    if (_is_bullish(o1, c1) and body1 > avg * 0.7 and
        _is_bearish(o2, c2) and o2 > c1 and c2 < mid1 and c2 > o1):
        penetration = (c1 - c2) / body1 * 100
        return {"signal": "SELL", "confidence": min(80, 60 + int(penetration * 0.3)),
                "reason_fa": f"ابر سیاه (Dark Cloud Cover) — نفوذ {penetration:.0f}% در بدنه کندل قبل"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "الگوی خط نفوذ/ابر سیاه شناسایی نشد"}


# ─────────────────────────────────────────────────────
# CDL_07: Harami (Bullish / Bearish)
# Small candle completely inside prev large candle body
# ─────────────────────────────────────────────────────
def cdl_07_harami(df, context=None):
    if len(df) < 3:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    o1 = df['open'].iloc[-2]; c1 = df['close'].iloc[-2]
    o2 = df['open'].iloc[-1]; c2 = df['close'].iloc[-1]
    body1 = _body_abs(o1, c1)
    body2 = _body_abs(o2, c2)
    avg = _avg_body(df, 14)
    trend = _trend_direction(df, 10)

    top1 = max(o1, c1); bot1 = min(o1, c1)
    top2 = max(o2, c2); bot2 = min(o2, c2)

    # Harami: prev large, current small, current inside prev
    if body1 > avg * 0.8 and body2 < body1 * 0.5 and top2 <= top1 and bot2 >= bot1:
        ratio = body2 / max(body1, 0.0001)
        # Bullish Harami: prev bearish, current bullish (or small)
        if _is_bearish(o1, c1):
            conf = 72 if trend == -1 else 58
            return {"signal": "BUY", "confidence": conf,
                    "reason_fa": f"هارامی صعودی (Bullish Harami) — کندل کوچک داخل بدنه نزولی (نسبت {ratio:.1%})"}
        # Bearish Harami: prev bullish, current bearish (or small)
        elif _is_bullish(o1, c1):
            conf = 72 if trend == 1 else 58
            return {"signal": "SELL", "confidence": conf,
                    "reason_fa": f"هارامی نزولی (Bearish Harami) — کندل کوچک داخل بدنه صعودی (نسبت {ratio:.1%})"}

    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "الگوی هارامی شناسایی نشد"}


# ─────────────────────────────────────────────────────
# CDL_08: Marubozu (Full Body Candle — No/Tiny Shadows)
# Strong conviction candle
# ─────────────────────────────────────────────────────
def cdl_08_marubozu(df, context=None):
    o = df['open'].iloc[-1]; h = df['high'].iloc[-1]
    l = df['low'].iloc[-1]; c = df['close'].iloc[-1]
    body = _body_abs(o, c)
    upper = _upper_shadow(h, o, c)
    lower = _lower_shadow(o, c, l)
    candle_range = h - l
    avg = _avg_body(df, 14)

    if candle_range == 0 or body == 0:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "کندل بدون حرکت"}

    shadow_ratio = (upper + lower) / candle_range
    body_size = body / max(avg, 0.0001)

    # Marubozu: shadows less than 10% of range, large body
    if shadow_ratio > 0.15 or body < avg * 0.8:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "الگوی ماروبوزو شناسایی نشد"}

    if _is_bullish(o, c):
        conf = min(85, 65 + int(body_size * 8))
        return {"signal": "BUY", "confidence": conf,
                "reason_fa": f"ماروبوزو صعودی — بدنه کامل بدون سایه (اندازه {body_size:.1f}x میانگین)"}
    else:
        conf = min(85, 65 + int(body_size * 8))
        return {"signal": "SELL", "confidence": conf,
                "reason_fa": f"ماروبوزو نزولی — بدنه کامل بدون سایه (اندازه {body_size:.1f}x میانگین)"}


# ─────────────────────────────────────────────────────
# CDL_09: Tweezer Top / Bottom
# Two candles with matching highs (top) or matching lows (bottom)
# ─────────────────────────────────────────────────────
def cdl_09_tweezer(df, context=None):
    if len(df) < 3:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    h1 = df['high'].iloc[-2]; l1 = df['low'].iloc[-2]
    h2 = df['high'].iloc[-1]; l2 = df['low'].iloc[-1]
    o1 = df['open'].iloc[-2]; c1 = df['close'].iloc[-2]
    o2 = df['open'].iloc[-1]; c2 = df['close'].iloc[-1]
    avg = _avg_body(df, 14)
    trend = _trend_direction(df, 10)
    tolerance = avg * 0.1  # Match within 10% of avg body

    # Tweezer Bottom: matching lows
    if abs(l1 - l2) <= tolerance and trend == -1:
        if _is_bearish(o1, c1) and _is_bullish(o2, c2):
            return {"signal": "BUY", "confidence": 76,
                    "reason_fa": f"انبرک پایینی (Tweezer Bottom) — دو کف مشابه در انتهای نزول"}
        elif abs(l1 - l2) <= tolerance * 0.5:
            return {"signal": "BUY", "confidence": 62,
                    "reason_fa": f"انبرک پایینی — کف‌های نزدیک در نزول"}

    # Tweezer Top: matching highs
    if abs(h1 - h2) <= tolerance and trend == 1:
        if _is_bullish(o1, c1) and _is_bearish(o2, c2):
            return {"signal": "SELL", "confidence": 76,
                    "reason_fa": f"انبرک بالایی (Tweezer Top) — دو سقف مشابه در بالای صعود"}
        elif abs(h1 - h2) <= tolerance * 0.5:
            return {"signal": "SELL", "confidence": 62,
                    "reason_fa": f"انبرک بالایی — سقف‌های نزدیک در صعود"}

    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "الگوی انبرک شناسایی نشد"}


# ─────────────────────────────────────────────────────
# CDL_10: Spinning Top + Trend Context
# Small body, long shadows on both sides = indecision
# ─────────────────────────────────────────────────────
def cdl_10_spinning_top(df, context=None):
    o = df['open'].iloc[-1]; h = df['high'].iloc[-1]
    l = df['low'].iloc[-1]; c = df['close'].iloc[-1]
    body = _body_abs(o, c)
    upper = _upper_shadow(h, o, c)
    lower = _lower_shadow(o, c, l)
    candle_range = h - l
    avg = _avg_body(df, 14)
    trend = _trend_direction(df, 10)

    if candle_range == 0:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "کندل بدون تغییر"}

    body_pct = body / candle_range

    # Spinning top: small body (< 30% of range), both shadows significant
    is_spinning = (body_pct < 0.3 and
                   upper > body * 0.8 and lower > body * 0.8 and
                   body > 0)

    if not is_spinning:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "الگوی فرفره شناسایی نشد"}

    if trend == 1:
        return {"signal": "SELL", "confidence": 58,
                "reason_fa": f"فرفره (Spinning Top) بعد از صعود — بلاتکلیفی، احتمال برگشت (بدنه {body_pct:.0%})"}
    elif trend == -1:
        return {"signal": "BUY", "confidence": 58,
                "reason_fa": f"فرفره (Spinning Top) بعد از نزول — بلاتکلیفی، احتمال برگشت (بدنه {body_pct:.0%})"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"فرفره بدون روند مشخص — بلاتکلیفی خالص (بدنه {body_pct:.0%})"}


# ═══════════════════════════════════════════════════════
# REGISTRY
# ═══════════════════════════════════════════════════════

CANDLE_STRATEGIES = [
    {"id": "CDL_01", "name": "Hammer / Hanging Man", "name_fa": "چکش / مرد آویزان", "func": cdl_01_hammer},
    {"id": "CDL_02", "name": "Engulfing Pattern", "name_fa": "الگوی پوشا", "func": cdl_02_engulfing},
    {"id": "CDL_03", "name": "Doji Reversal", "name_fa": "دوجی برگشتی", "func": cdl_03_doji},
    {"id": "CDL_04", "name": "Morning/Evening Star", "name_fa": "ستاره صبح/شام", "func": cdl_04_star},
    {"id": "CDL_05", "name": "3 Soldiers / Crows", "name_fa": "۳ سرباز / ۳ کلاغ", "func": cdl_05_three_soldiers},
    {"id": "CDL_06", "name": "Piercing / Dark Cloud", "name_fa": "خط نفوذ / ابر سیاه", "func": cdl_06_piercing},
    {"id": "CDL_07", "name": "Harami Pattern", "name_fa": "الگوی هارامی", "func": cdl_07_harami},
    {"id": "CDL_08", "name": "Marubozu", "name_fa": "ماروبوزو", "func": cdl_08_marubozu},
    {"id": "CDL_09", "name": "Tweezer Top/Bottom", "name_fa": "انبرک بالا/پایین", "func": cdl_09_tweezer},
    {"id": "CDL_10", "name": "Spinning Top", "name_fa": "فرفره + روند", "func": cdl_10_spinning_top},
]
