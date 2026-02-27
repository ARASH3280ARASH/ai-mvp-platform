"""
Whilber-AI — Pivot Strategy Pack (4 Sub-Strategies)
=====================================================
PVT_01: Classic Pivot Points (S1/S2/R1/R2)
PVT_02: Fibonacci Pivot Points
PVT_03: Camarilla Pivot Points
PVT_04: Pivot + Trend Confluence
"""

import numpy as np
import pandas as pd


def _ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def _calc_classic_pivots(prev_high, prev_low, prev_close):
    pp = (prev_high + prev_low + prev_close) / 3
    r1 = 2 * pp - prev_low
    s1 = 2 * pp - prev_high
    r2 = pp + (prev_high - prev_low)
    s2 = pp - (prev_high - prev_low)
    r3 = prev_high + 2 * (pp - prev_low)
    s3 = prev_low - 2 * (prev_high - pp)
    return {"PP": pp, "R1": r1, "R2": r2, "R3": r3, "S1": s1, "S2": s2, "S3": s3}


def _calc_fib_pivots(prev_high, prev_low, prev_close):
    pp = (prev_high + prev_low + prev_close) / 3
    r = prev_high - prev_low
    r1 = pp + 0.382 * r
    r2 = pp + 0.618 * r
    r3 = pp + 1.000 * r
    s1 = pp - 0.382 * r
    s2 = pp - 0.618 * r
    s3 = pp - 1.000 * r
    return {"PP": pp, "R1": r1, "R2": r2, "R3": r3, "S1": s1, "S2": s2, "S3": s3}


def _calc_camarilla_pivots(prev_high, prev_low, prev_close):
    r = prev_high - prev_low
    r1 = prev_close + r * 1.1 / 12
    r2 = prev_close + r * 1.1 / 6
    r3 = prev_close + r * 1.1 / 4
    r4 = prev_close + r * 1.1 / 2
    s1 = prev_close - r * 1.1 / 12
    s2 = prev_close - r * 1.1 / 6
    s3 = prev_close - r * 1.1 / 4
    s4 = prev_close - r * 1.1 / 2
    pp = (prev_high + prev_low + prev_close) / 3
    return {"PP": pp, "R1": r1, "R2": r2, "R3": r3, "R4": r4,
            "S1": s1, "S2": s2, "S3": s3, "S4": s4}


def _get_prev_bar(df):
    """Get previous bar's H/L/C for pivot calculation."""
    if len(df) < 3:
        return None, None, None
    return df['high'].iloc[-2], df['low'].iloc[-2], df['close'].iloc[-2]


def _near(price, level, tolerance_pct=0.3):
    return abs(price - level) / price * 100 < tolerance_pct


# ─────────────────────────────────────────────────────
# PVT_01: Classic Pivot Points
# BUY:  Price bouncing off S1/S2 support
# SELL: Price rejecting R1/R2 resistance
# ─────────────────────────────────────────────────────
def pvt_01_classic(df, context=None):
    ph, pl, pc = _get_prev_bar(df)
    if ph is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    pivots = _calc_classic_pivots(ph, pl, pc)
    p = df['close'].iloc[-1]
    p_prev = df['close'].iloc[-2]

    # Check proximity to each level
    for level_name in ["S2", "S1"]:
        level = pivots[level_name]
        if _near(p, level, 0.3):
            if p > p_prev:
                return {"signal": "BUY", "confidence": 76,
                        "reason_fa": f"برگشت از پیوت {level_name} ({level:.4f}) — حمایت کلاسیک"}
            return {"signal": "BUY", "confidence": 60,
                    "reason_fa": f"نزدیک پیوت {level_name} ({level:.4f}) — منتظر برگشت"}

    for level_name in ["R1", "R2"]:
        level = pivots[level_name]
        if _near(p, level, 0.3):
            if p < p_prev:
                return {"signal": "SELL", "confidence": 76,
                        "reason_fa": f"ریجکت از پیوت {level_name} ({level:.4f}) — مقاومت کلاسیک"}
            return {"signal": "SELL", "confidence": 60,
                    "reason_fa": f"نزدیک پیوت {level_name} ({level:.4f}) — منتظر ریجکت"}

    # PP as reference
    pp = pivots["PP"]
    if _near(p, pp, 0.2):
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"قیمت روی محور پیوت ({pp:.4f}) — نقطه تعادل"}
    elif p > pivots["R2"]:
        return {"signal": "BUY", "confidence": 50,
                "reason_fa": f"قیمت بالای R2 — روند صعودی قوی"}
    elif p < pivots["S2"]:
        return {"signal": "SELL", "confidence": 50,
                "reason_fa": f"قیمت زیر S2 — روند نزولی قوی"}
    elif p > pp:
        return {"signal": "BUY", "confidence": 42,
                "reason_fa": f"قیمت بالای محور پیوت ({pp:.4f})"}
    else:
        return {"signal": "SELL", "confidence": 42,
                "reason_fa": f"قیمت زیر محور پیوت ({pp:.4f})"}


# ─────────────────────────────────────────────────────
# PVT_02: Fibonacci Pivot Points
# BUY:  Price at Fib S1/S2 support
# SELL: Price at Fib R1/R2 resistance
# ─────────────────────────────────────────────────────
def pvt_02_fibonacci(df, context=None):
    ph, pl, pc = _get_prev_bar(df)
    if ph is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    pivots = _calc_fib_pivots(ph, pl, pc)
    p = df['close'].iloc[-1]
    p_prev = df['close'].iloc[-2]

    for level_name in ["S2", "S1"]:
        level = pivots[level_name]
        if _near(p, level, 0.3):
            if p > p_prev:
                return {"signal": "BUY", "confidence": 78,
                        "reason_fa": f"برگشت از پیوت فیبوناچی {level_name} ({level:.4f})"}
            return {"signal": "BUY", "confidence": 62,
                    "reason_fa": f"نزدیک پیوت فیبوناچی {level_name} ({level:.4f})"}

    for level_name in ["R1", "R2"]:
        level = pivots[level_name]
        if _near(p, level, 0.3):
            if p < p_prev:
                return {"signal": "SELL", "confidence": 78,
                        "reason_fa": f"ریجکت از پیوت فیبوناچی {level_name} ({level:.4f})"}
            return {"signal": "SELL", "confidence": 62,
                    "reason_fa": f"نزدیک پیوت فیبوناچی {level_name} ({level:.4f})"}

    pp = pivots["PP"]
    if p > pp:
        return {"signal": "BUY", "confidence": 42,
                "reason_fa": f"بالای پیوت فیبوناچی ({pp:.4f})"}
    elif p < pp:
        return {"signal": "SELL", "confidence": 42,
                "reason_fa": f"زیر پیوت فیبوناچی ({pp:.4f})"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"روی محور پیوت فیبوناچی ({pp:.4f})"}


# ─────────────────────────────────────────────────────
# PVT_03: Camarilla Pivot Points
# BUY:  Price bounces off S3 (strong support) or breaks R4
# SELL: Price rejects R3 (strong resistance) or breaks S4
# ─────────────────────────────────────────────────────
def pvt_03_camarilla(df, context=None):
    ph, pl, pc = _get_prev_bar(df)
    if ph is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    pivots = _calc_camarilla_pivots(ph, pl, pc)
    p = df['close'].iloc[-1]
    p_prev = df['close'].iloc[-2]

    # S3 bounce (strong support)
    if _near(p, pivots["S3"], 0.3) and p > p_prev:
        return {"signal": "BUY", "confidence": 80,
                "reason_fa": f"برگشت از کاماریلا S3 ({pivots['S3']:.4f}) — حمایت قوی"}
    # R3 rejection (strong resistance)
    if _near(p, pivots["R3"], 0.3) and p < p_prev:
        return {"signal": "SELL", "confidence": 80,
                "reason_fa": f"ریجکت از کاماریلا R3 ({pivots['R3']:.4f}) — مقاومت قوی"}

    # R4 breakout (very strong bullish)
    if p > pivots["R4"] and p_prev <= pivots["R4"]:
        return {"signal": "BUY", "confidence": 85,
                "reason_fa": f"شکست کاماریلا R4 ({pivots['R4']:.4f}) — حرکت انفجاری صعودی"}
    # S4 breakdown (very strong bearish)
    if p < pivots["S4"] and p_prev >= pivots["S4"]:
        return {"signal": "SELL", "confidence": 85,
                "reason_fa": f"شکست کاماریلا S4 ({pivots['S4']:.4f}) — حرکت انفجاری نزولی"}

    # Range between S3-R3
    if pivots["S3"] < p < pivots["R3"]:
        mid = pivots["PP"]
        if p > mid:
            return {"signal": "NEUTRAL", "confidence": 0,
                    "reason_fa": f"بین S3-R3 کاماریلا — نیمه بالایی"}
        else:
            return {"signal": "NEUTRAL", "confidence": 0,
                    "reason_fa": f"بین S3-R3 کاماریلا — نیمه پایینی"}

    if p > pivots["R3"]:
        return {"signal": "BUY", "confidence": 55,
                "reason_fa": f"بالای کاماریلا R3 — روند صعودی"}
    else:
        return {"signal": "SELL", "confidence": 55,
                "reason_fa": f"زیر کاماریلا S3 — روند نزولی"}


# ─────────────────────────────────────────────────────
# PVT_04: Pivot + Trend Confluence
# BUY:  At pivot support + EMA confirms uptrend
# SELL: At pivot resistance + EMA confirms downtrend
# ─────────────────────────────────────────────────────
def pvt_04_trend_confluence(df, context=None):
    ph, pl, pc = _get_prev_bar(df)
    if ph is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    pivots = _calc_classic_pivots(ph, pl, pc)
    ema50 = _ema(df['close'], 50)
    if ema50.isna().iloc[-1]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    p = df['close'].iloc[-1]
    p_prev = df['close'].iloc[-2]
    above_ema = p > ema50.iloc[-1]

    # Support + uptrend
    for level_name in ["S1", "S2"]:
        level = pivots[level_name]
        if _near(p, level, 0.4) and above_ema and p > p_prev:
            return {"signal": "BUY", "confidence": 84,
                    "reason_fa": f"پیوت {level_name} + روند صعودی EMA50 — سیگنال تایید شده ({level:.4f})"}

    # Resistance + downtrend
    for level_name in ["R1", "R2"]:
        level = pivots[level_name]
        if _near(p, level, 0.4) and not above_ema and p < p_prev:
            return {"signal": "SELL", "confidence": 84,
                    "reason_fa": f"پیوت {level_name} + روند نزولی EMA50 — سیگنال تایید شده ({level:.4f})"}

    # General trend
    pp = pivots["PP"]
    if p > pp and above_ema:
        return {"signal": "BUY", "confidence": 50,
                "reason_fa": f"بالای پیوت + بالای EMA50 — تایید صعودی"}
    elif p < pp and not above_ema:
        return {"signal": "SELL", "confidence": 50,
                "reason_fa": f"زیر پیوت + زیر EMA50 — تایید نزولی"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "پیوت و EMA50 متناقض — بلاتکلیف"}


# ═══════════════════════════════════════════════════════
# REGISTRY
# ═══════════════════════════════════════════════════════

PIVOT_STRATEGIES = [
    {"id": "PVT_01", "name": "Classic Pivot Points", "name_fa": "پیوت پوینت کلاسیک", "func": pvt_01_classic},
    {"id": "PVT_02", "name": "Fibonacci Pivots", "name_fa": "پیوت فیبوناچی", "func": pvt_02_fibonacci},
    {"id": "PVT_03", "name": "Camarilla Pivots", "name_fa": "پیوت کاماریلا", "func": pvt_03_camarilla},
    {"id": "PVT_04", "name": "Pivot + Trend EMA", "name_fa": "پیوت + روند EMA", "func": pvt_04_trend_confluence},
]
