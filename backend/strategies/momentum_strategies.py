"""
Whilber-AI — Momentum Strategy Pack (4 Sub-Strategies)
=======================================================
MOM_01: Rate of Change (ROC)
MOM_02: Momentum Oscillator (Classic)
MOM_03: Trix Indicator (Triple EMA Momentum)
MOM_04: Awesome Oscillator (AO)
"""

import numpy as np
import pandas as pd


def _ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def _sma(series, period):
    return series.rolling(window=period, min_periods=period).mean()


# ─────────────────────────────────────────────────────
# MOM_01: Rate of Change (ROC)
# ROC = (Close - Close_n) / Close_n * 100
# BUY:  ROC crosses above 0 (momentum shifts positive)
# SELL: ROC crosses below 0 (momentum shifts negative)
# ─────────────────────────────────────────────────────
def mom_01_roc(df, context=None):
    close = df['close']
    period = 12
    if len(close) < period + 2:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    roc = (close - close.shift(period)) / close.shift(period) * 100
    r = roc.iloc[-1]
    r_prev = roc.iloc[-2]

    if r_prev <= 0 and r > 0:
        conf = min(80, 60 + int(abs(r) * 5))
        return {"signal": "BUY", "confidence": conf,
                "reason_fa": f"ROC({period}) از صفر عبور کرد (بالا) — مومنتوم مثبت شد ({r:+.2f}%)"}
    elif r_prev >= 0 and r < 0:
        conf = min(80, 60 + int(abs(r) * 5))
        return {"signal": "SELL", "confidence": conf,
                "reason_fa": f"ROC({period}) از صفر عبور کرد (پایین) — مومنتوم منفی شد ({r:+.2f}%)"}
    elif r > 3:
        return {"signal": "BUY", "confidence": 58,
                "reason_fa": f"ROC قوی مثبت ({r:+.2f}%) — مومنتوم صعودی"}
    elif r < -3:
        return {"signal": "SELL", "confidence": 58,
                "reason_fa": f"ROC قوی منفی ({r:+.2f}%) — مومنتوم نزولی"}
    elif r > 0:
        return {"signal": "BUY", "confidence": 42,
                "reason_fa": f"ROC اندکی مثبت ({r:+.2f}%)"}
    elif r < 0:
        return {"signal": "SELL", "confidence": 42,
                "reason_fa": f"ROC اندکی منفی ({r:+.2f}%)"}
    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": f"ROC صفر ({r:+.2f}%)"}


# ─────────────────────────────────────────────────────
# MOM_02: Momentum Oscillator
# Momentum = Close - Close_n (raw difference)
# BUY:  Momentum crosses above 0 + accelerating
# SELL: Momentum crosses below 0 + decelerating
# ─────────────────────────────────────────────────────
def mom_02_oscillator(df, context=None):
    close = df['close']
    period = 10
    if len(close) < period + 3:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    mom = close - close.shift(period)
    m = mom.iloc[-1]
    m_prev = mom.iloc[-2]
    m_prev2 = mom.iloc[-3]
    accel = m - m_prev
    pct = m / close.iloc[-1] * 100

    if m_prev <= 0 and m > 0:
        return {"signal": "BUY", "confidence": 74,
                "reason_fa": f"مومنتوم از صفر عبور کرد ({pct:+.2f}%) — شروع حرکت صعودی"}
    elif m_prev >= 0 and m < 0:
        return {"signal": "SELL", "confidence": 74,
                "reason_fa": f"مومنتوم از صفر عبور کرد ({pct:+.2f}%) — شروع حرکت نزولی"}
    elif m > 0 and accel > 0 and m > m_prev > m_prev2:
        return {"signal": "BUY", "confidence": 68,
                "reason_fa": f"مومنتوم مثبت و شتاب‌دار ({pct:+.2f}%) — قدرت صعودی"}
    elif m < 0 and accel < 0 and m < m_prev < m_prev2:
        return {"signal": "SELL", "confidence": 68,
                "reason_fa": f"مومنتوم منفی و شتاب‌دار ({pct:+.2f}%) — قدرت نزولی"}
    elif m > 0 and accel < 0:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"مومنتوم مثبت ولی کاهشی ({pct:+.2f}%) — ضعف صعود"}
    elif m < 0 and accel > 0:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"مومنتوم منفی ولی بهبود ({pct:+.2f}%) — ضعف نزول"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"مومنتوم خنثی ({pct:+.2f}%)"}


# ─────────────────────────────────────────────────────
# MOM_03: TRIX (Triple Smoothed EMA Rate of Change)
# BUY:  TRIX crosses above signal line
# SELL: TRIX crosses below signal line
# ─────────────────────────────────────────────────────
def mom_03_trix(df, context=None):
    close = df['close']
    period = 15
    if len(close) < period * 3 + 5:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    e1 = _ema(close, period)
    e2 = _ema(e1, period)
    e3 = _ema(e2, period)
    trix = (e3 - e3.shift(1)) / e3.shift(1) * 10000  # basis points
    signal = _ema(trix, 9)

    if trix.isna().iloc[-1] or signal.isna().iloc[-1]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    t = trix.iloc[-1]
    s = signal.iloc[-1]
    t_prev = trix.iloc[-2]
    s_prev = signal.iloc[-2]

    if t_prev <= s_prev and t > s:
        return {"signal": "BUY", "confidence": 76,
                "reason_fa": f"TRIX از سیگنال عبور کرد (بالا) — مومنتوم سه‌گانه صعودی ({t:.2f})"}
    elif t_prev >= s_prev and t < s:
        return {"signal": "SELL", "confidence": 76,
                "reason_fa": f"TRIX از سیگنال عبور کرد (پایین) — مومنتوم سه‌گانه نزولی ({t:.2f})"}
    elif t > s and t > 0:
        return {"signal": "BUY", "confidence": 52,
                "reason_fa": f"TRIX مثبت بالای سیگنال ({t:.2f})"}
    elif t < s and t < 0:
        return {"signal": "SELL", "confidence": 52,
                "reason_fa": f"TRIX منفی زیر سیگنال ({t:.2f})"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"TRIX بلاتکلیف ({t:.2f})"}


# ─────────────────────────────────────────────────────
# MOM_04: Awesome Oscillator (AO)
# AO = SMA(5, median) - SMA(34, median)
# BUY:  AO crosses above 0 OR twin peaks (saucer)
# SELL: AO crosses below 0 OR twin peaks
# ─────────────────────────────────────────────────────
def mom_04_awesome(df, context=None):
    median = (df['high'] + df['low']) / 2
    ao = _sma(median, 5) - _sma(median, 34)
    if ao.isna().iloc[-1] or len(ao.dropna()) < 5:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    a = ao.iloc[-1]
    a_prev = ao.iloc[-2]
    a_prev2 = ao.iloc[-3]

    # Zero-line cross
    if a_prev <= 0 and a > 0:
        return {"signal": "BUY", "confidence": 76,
                "reason_fa": f"AO از صفر عبور کرد (بالا) — مومنتوم صعودی ({a:.4f})"}
    elif a_prev >= 0 and a < 0:
        return {"signal": "SELL", "confidence": 76,
                "reason_fa": f"AO از صفر عبور کرد (پایین) — مومنتوم نزولی ({a:.4f})"}

    # Saucer: AO > 0, dip then rise (bullish saucer)
    if a > 0 and a_prev < a_prev2 and a > a_prev:
        return {"signal": "BUY", "confidence": 68,
                "reason_fa": f"نعلبکی صعودی AO — اصلاح و برگشت بالای صفر ({a:.4f})"}
    # Bearish saucer
    elif a < 0 and a_prev > a_prev2 and a < a_prev:
        return {"signal": "SELL", "confidence": 68,
                "reason_fa": f"نعلبکی نزولی AO — اصلاح و برگشت زیر صفر ({a:.4f})"}

    # Color change (bar color)
    if a > a_prev and a > 0:
        return {"signal": "BUY", "confidence": 45,
                "reason_fa": f"AO مثبت و افزایشی ({a:.4f})"}
    elif a < a_prev and a < 0:
        return {"signal": "SELL", "confidence": 45,
                "reason_fa": f"AO منفی و کاهشی ({a:.4f})"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"AO بلاتکلیف ({a:.4f})"}


# ═══════════════════════════════════════════════════════
# REGISTRY
# ═══════════════════════════════════════════════════════

MOM_STRATEGIES = [
    {"id": "MOM_01", "name": "Rate of Change (ROC)", "name_fa": "نرخ تغییر (ROC)", "func": mom_01_roc},
    {"id": "MOM_02", "name": "Momentum Oscillator", "name_fa": "اسیلاتور مومنتوم", "func": mom_02_oscillator},
    {"id": "MOM_03", "name": "TRIX Triple EMA", "name_fa": "تریکس سه‌گانه", "func": mom_03_trix},
    {"id": "MOM_04", "name": "Awesome Oscillator", "name_fa": "اسیلاتور عالی (AO)", "func": mom_04_awesome},
]
