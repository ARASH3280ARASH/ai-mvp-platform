"""
Whilber-AI — Multi-Timeframe Strategy Pack (4 Sub-Strategies)
==============================================================
MTF_01: Multi-EMA Timeframe (EMA20/50/200 as proxy for 3 TFs)
MTF_02: RSI Multi-Period (RSI 7/14/21 alignment)
MTF_03: MACD Multi-Speed (Fast/Medium/Slow MACD)
MTF_04: Trend Alignment Score (Multiple indicators across periods)
"""

import numpy as np
import pandas as pd


def _ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def _sma(series, period):
    return series.rolling(window=period, min_periods=period).mean()


def _rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    return 100 - (100 / (1 + rs))


def _macd_signal(close, fast, slow, sig):
    ema_f = _ema(close, fast)
    ema_s = _ema(close, slow)
    macd = ema_f - ema_s
    signal = _ema(macd, sig)
    return macd, signal


# ─────────────────────────────────────────────────────
# MTF_01: Multi-EMA Timeframe Proxy
# EMA20 = short-term, EMA50 = medium, EMA200 = long-term
# BUY:  Price > EMA20 > EMA50 > EMA200 (all aligned bullish)
# SELL: Price < EMA20 < EMA50 < EMA200 (all aligned bearish)
# ─────────────────────────────────────────────────────
def mtf_01_multi_ema(df, context=None):
    close = df['close']
    e20 = _ema(close, 20)
    e50 = _ema(close, 50)
    e200 = _ema(close, 200)

    if e200.isna().iloc[-1]:
        # Fallback: use 100 instead of 200
        e200 = _ema(close, 100)
        if e200.isna().iloc[-1]:
            return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    p = close.iloc[-1]
    v20 = e20.iloc[-1]; v50 = e50.iloc[-1]; v200 = e200.iloc[-1]

    # Previous values for cross detection
    p_p = close.iloc[-2]
    v20_p = e20.iloc[-2]; v50_p = e50.iloc[-2]; v200_p = e200.iloc[-2]

    bull_now = p > v20 > v50 > v200
    bear_now = p < v20 < v50 < v200
    bull_prev = p_p > v20_p > v50_p > v200_p
    bear_prev = p_p < v20_p < v50_p < v200_p

    # Count aligned
    bull_count = sum([p > v20, v20 > v50, v50 > v200])
    bear_count = sum([p < v20, v20 < v50, v50 < v200])

    if bull_now and not bull_prev:
        return {"signal": "BUY", "confidence": 88,
                "reason_fa": "MTF هم‌ترازی کامل صعودی — قیمت > EMA20 > EMA50 > EMA200"}
    elif bear_now and not bear_prev:
        return {"signal": "SELL", "confidence": 88,
                "reason_fa": "MTF هم‌ترازی کامل نزولی — قیمت < EMA20 < EMA50 < EMA200"}
    elif bull_now:
        return {"signal": "BUY", "confidence": 65,
                "reason_fa": "MTF صعودی ادامه‌دار — هر ۳ تایم‌فریم هم‌جهت"}
    elif bear_now:
        return {"signal": "SELL", "confidence": 65,
                "reason_fa": "MTF نزولی ادامه‌دار — هر ۳ تایم‌فریم هم‌جهت"}
    elif bull_count >= 2:
        return {"signal": "BUY", "confidence": 48,
                "reason_fa": f"MTF عمدتا صعودی ({bull_count}/3 هم‌ترازی)"}
    elif bear_count >= 2:
        return {"signal": "SELL", "confidence": 48,
                "reason_fa": f"MTF عمدتا نزولی ({bear_count}/3 هم‌ترازی)"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "MTF بدون هم‌ترازی — تایم‌فریم‌ها متناقض"}


# ─────────────────────────────────────────────────────
# MTF_02: RSI Multi-Period Alignment
# RSI(7) = fast, RSI(14) = medium, RSI(21) = slow
# BUY:  All 3 RSIs oversold or all rising from low
# SELL: All 3 RSIs overbought or all falling from high
# ─────────────────────────────────────────────────────
def mtf_02_rsi_multi(df, context=None):
    close = df['close']
    r7 = _rsi(close, 7)
    r14 = _rsi(close, 14)
    r21 = _rsi(close, 21)

    if r21.isna().iloc[-1]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    v7 = r7.iloc[-1]; v14 = r14.iloc[-1]; v21 = r21.iloc[-1]
    v7p = r7.iloc[-2]; v14p = r14.iloc[-2]; v21p = r21.iloc[-2]

    # All oversold
    all_oversold = v7 < 35 and v14 < 35 and v21 < 35
    all_overbought = v7 > 65 and v14 > 65 and v21 > 65

    # All rising
    all_rising = v7 > v7p and v14 > v14p and v21 > v21p
    all_falling = v7 < v7p and v14 < v14p and v21 < v21p

    if all_oversold and all_rising:
        return {"signal": "BUY", "confidence": 85,
                "reason_fa": f"RSI سه‌گانه اشباع فروش + صعودی — 7:{v7:.0f} 14:{v14:.0f} 21:{v21:.0f}"}
    elif all_overbought and all_falling:
        return {"signal": "SELL", "confidence": 85,
                "reason_fa": f"RSI سه‌گانه اشباع خرید + نزولی — 7:{v7:.0f} 14:{v14:.0f} 21:{v21:.0f}"}
    elif all_oversold:
        return {"signal": "BUY", "confidence": 72,
                "reason_fa": f"RSI سه‌گانه اشباع فروش — 7:{v7:.0f} 14:{v14:.0f} 21:{v21:.0f}"}
    elif all_overbought:
        return {"signal": "SELL", "confidence": 72,
                "reason_fa": f"RSI سه‌گانه اشباع خرید — 7:{v7:.0f} 14:{v14:.0f} 21:{v21:.0f}"}
    elif all_rising and v14 > 50:
        return {"signal": "BUY", "confidence": 58,
                "reason_fa": f"RSI سه‌گانه همه صعودی — 7:{v7:.0f} 14:{v14:.0f} 21:{v21:.0f}"}
    elif all_falling and v14 < 50:
        return {"signal": "SELL", "confidence": 58,
                "reason_fa": f"RSI سه‌گانه همه نزولی — 7:{v7:.0f} 14:{v14:.0f} 21:{v21:.0f}"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"RSI سه‌گانه بدون هم‌ترازی — 7:{v7:.0f} 14:{v14:.0f} 21:{v21:.0f}"}


# ─────────────────────────────────────────────────────
# MTF_03: MACD Multi-Speed
# Fast MACD (5,13,4), Medium (12,26,9), Slow (19,39,9)
# BUY:  All 3 bullish (MACD > Signal)
# SELL: All 3 bearish (MACD < Signal)
# ─────────────────────────────────────────────────────
def mtf_03_macd_multi(df, context=None):
    close = df['close']
    m_fast, s_fast = _macd_signal(close, 5, 13, 4)
    m_med, s_med = _macd_signal(close, 12, 26, 9)
    m_slow, s_slow = _macd_signal(close, 19, 39, 9)

    if m_slow.isna().iloc[-1] or s_slow.isna().iloc[-1]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    fast_bull = m_fast.iloc[-1] > s_fast.iloc[-1]
    med_bull = m_med.iloc[-1] > s_med.iloc[-1]
    slow_bull = m_slow.iloc[-1] > s_slow.iloc[-1]

    fast_prev = m_fast.iloc[-2] > s_fast.iloc[-2]
    med_prev = m_med.iloc[-2] > s_med.iloc[-2]
    slow_prev = m_slow.iloc[-2] > s_slow.iloc[-2]

    bull_count = sum([fast_bull, med_bull, slow_bull])
    all_bull_now = bull_count == 3
    all_bear_now = bull_count == 0
    all_bull_prev = sum([fast_prev, med_prev, slow_prev]) == 3
    all_bear_prev = sum([fast_prev, med_prev, slow_prev]) == 0

    if all_bull_now and not all_bull_prev:
        return {"signal": "BUY", "confidence": 86,
                "reason_fa": "MACD سه‌گانه هم‌جهت صعودی شد — سریع+متوسط+آهسته"}
    elif all_bear_now and not all_bear_prev:
        return {"signal": "SELL", "confidence": 86,
                "reason_fa": "MACD سه‌گانه هم‌جهت نزولی شد — سریع+متوسط+آهسته"}
    elif all_bull_now:
        return {"signal": "BUY", "confidence": 62,
                "reason_fa": "MACD سه‌گانه صعودی ادامه‌دار"}
    elif all_bear_now:
        return {"signal": "SELL", "confidence": 62,
                "reason_fa": "MACD سه‌گانه نزولی ادامه‌دار"}
    elif bull_count >= 2:
        return {"signal": "BUY", "confidence": 45,
                "reason_fa": f"MACD {bull_count}/3 صعودی"}
    elif bull_count <= 1:
        return {"signal": "SELL", "confidence": 45,
                "reason_fa": f"MACD {3-bull_count}/3 نزولی"}
    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "MACD سه‌گانه متناقض"}


# ─────────────────────────────────────────────────────
# MTF_04: Trend Alignment Score
# Combines EMA trend + RSI zone + MACD direction across periods
# Score from -9 to +9, signal based on score
# ─────────────────────────────────────────────────────
def mtf_04_alignment_score(df, context=None):
    close = df['close']
    p = close.iloc[-1]
    score = 0
    details = []

    # EMA alignment (3 points)
    e20 = _ema(close, 20); e50 = _ema(close, 50); e100 = _ema(close, 100)
    if not e100.isna().iloc[-1]:
        if p > e20.iloc[-1]: score += 1; details.append("EMA20+")
        else: score -= 1; details.append("EMA20-")
        if p > e50.iloc[-1]: score += 1; details.append("EMA50+")
        else: score -= 1; details.append("EMA50-")
        if p > e100.iloc[-1]: score += 1; details.append("EMA100+")
        else: score -= 1; details.append("EMA100-")

    # RSI alignment (3 points)
    r7 = _rsi(close, 7); r14 = _rsi(close, 14); r21 = _rsi(close, 21)
    if not r21.isna().iloc[-1]:
        if r7.iloc[-1] > 50: score += 1
        else: score -= 1
        if r14.iloc[-1] > 50: score += 1
        else: score -= 1
        if r21.iloc[-1] > 50: score += 1
        else: score -= 1

    # MACD alignment (3 points)
    m1, s1 = _macd_signal(close, 5, 13, 4)
    m2, s2 = _macd_signal(close, 12, 26, 9)
    m3, s3 = _macd_signal(close, 19, 39, 9)
    if not m3.isna().iloc[-1]:
        if m1.iloc[-1] > s1.iloc[-1]: score += 1
        else: score -= 1
        if m2.iloc[-1] > s2.iloc[-1]: score += 1
        else: score -= 1
        if m3.iloc[-1] > s3.iloc[-1]: score += 1
        else: score -= 1

    if score >= 8:
        return {"signal": "BUY", "confidence": 90,
                "reason_fa": f"امتیاز هم‌ترازی {score}/9 — تایید کامل صعودی"}
    elif score <= -8:
        return {"signal": "SELL", "confidence": 90,
                "reason_fa": f"امتیاز هم‌ترازی {score}/9 — تایید کامل نزولی"}
    elif score >= 6:
        return {"signal": "BUY", "confidence": 75,
                "reason_fa": f"امتیاز هم‌ترازی {score}/9 — عمدتا صعودی"}
    elif score <= -6:
        return {"signal": "SELL", "confidence": 75,
                "reason_fa": f"امتیاز هم‌ترازی {score}/9 — عمدتا نزولی"}
    elif score >= 4:
        return {"signal": "BUY", "confidence": 55,
                "reason_fa": f"امتیاز هم‌ترازی {score}/9 — نسبتا صعودی"}
    elif score <= -4:
        return {"signal": "SELL", "confidence": 55,
                "reason_fa": f"امتیاز هم‌ترازی {score}/9 — نسبتا نزولی"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"امتیاز هم‌ترازی {score}/9 — بدون جهت غالب"}


# ═══════════════════════════════════════════════════════
# REGISTRY
# ═══════════════════════════════════════════════════════

MTF_STRATEGIES = [
    {"id": "MTF_01", "name": "Multi-EMA Timeframe", "name_fa": "چند تایم‌فریم EMA", "func": mtf_01_multi_ema},
    {"id": "MTF_02", "name": "RSI Multi-Period", "name_fa": "RSI چند دوره‌ای", "func": mtf_02_rsi_multi},
    {"id": "MTF_03", "name": "MACD Multi-Speed", "name_fa": "MACD چند سرعته", "func": mtf_03_macd_multi},
    {"id": "MTF_04", "name": "Trend Alignment Score", "name_fa": "امتیاز هم‌ترازی روند", "func": mtf_04_alignment_score},
]
