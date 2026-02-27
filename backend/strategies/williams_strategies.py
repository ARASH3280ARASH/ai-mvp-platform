"""
Whilber-AI — Williams %R Strategy Pack (3 Sub-Strategies)
==========================================================
WR_01: Classic Williams %R Overbought/Oversold (-20/-80)
WR_02: Williams %R Failure Swing
WR_03: Williams %R + Trend Filter
"""

import numpy as np
import pandas as pd


def _williams_r(df, period=14):
    high_roll = df['high'].rolling(period).max()
    low_roll = df['low'].rolling(period).min()
    wr = -100 * (high_roll - df['close']) / (high_roll - low_roll).replace(0, 1e-10)
    return wr


def _ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


# ─────────────────────────────────────────────────────
# WR_01: Classic Williams %R OB/OS
# BUY:  %R crosses above -80 from below (leaving oversold)
# SELL: %R crosses below -20 from above (leaving overbought)
# ─────────────────────────────────────────────────────
def wr_01_classic(df, context=None):
    wr = _williams_r(df, 14)
    if wr.isna().iloc[-1]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    w = wr.iloc[-1]
    w_prev = wr.iloc[-2]

    if w_prev < -80 and w >= -80:
        return {"signal": "BUY", "confidence": 76,
                "reason_fa": f"Williams %R از اشباع فروش برگشت ({w:.1f}) — عبور از -80"}
    elif w_prev > -20 and w <= -20:
        return {"signal": "SELL", "confidence": 76,
                "reason_fa": f"Williams %R از اشباع خرید برگشت ({w:.1f}) — عبور از -20"}
    elif w < -80:
        return {"signal": "BUY", "confidence": 55,
                "reason_fa": f"Williams %R در اشباع فروش ({w:.1f})"}
    elif w > -20:
        return {"signal": "SELL", "confidence": 55,
                "reason_fa": f"Williams %R در اشباع خرید ({w:.1f})"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"Williams %R خنثی ({w:.1f})"}


# ─────────────────────────────────────────────────────
# WR_02: Williams %R Failure Swing
# BUY:  %R enters oversold, bounces, dips again but higher, then rises
# SELL: %R enters overbought, drops, rises again but lower, then falls
# ─────────────────────────────────────────────────────
def wr_02_failure_swing(df, context=None):
    wr = _williams_r(df, 14)
    if wr.isna().iloc[-1] or len(wr.dropna()) < 10:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    recent = wr.dropna().tail(10).values
    w = recent[-1]

    # Bullish failure swing: look for pattern in last 10 bars
    # dip below -80, bounce, higher dip (still near -80), then rise above -80
    for i in range(2, len(recent)-2):
        if recent[i-2] < -80 and recent[i] > -80 and recent[i+1] < -60 and recent[i+1] > recent[i-2]:
            if w > -50:
                return {"signal": "BUY", "confidence": 80,
                        "reason_fa": f"نوسان شکست‌خورده صعودی %R — کف بالاتر در اشباع فروش ({w:.1f})"}

    # Bearish failure swing
    for i in range(2, len(recent)-2):
        if recent[i-2] > -20 and recent[i] < -20 and recent[i+1] > -40 and recent[i+1] < recent[i-2]:
            if w < -50:
                return {"signal": "SELL", "confidence": 80,
                        "reason_fa": f"نوسان شکست‌خورده نزولی %R — سقف پایین‌تر در اشباع خرید ({w:.1f})"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"نوسان شکست‌خورده %R شناسایی نشد ({w:.1f})"}


# ─────────────────────────────────────────────────────
# WR_03: Williams %R + Trend Filter (EMA 50)
# BUY:  %R oversold + above EMA50
# SELL: %R overbought + below EMA50
# ─────────────────────────────────────────────────────
def wr_03_trend_filter(df, context=None):
    wr = _williams_r(df, 14)
    ema50 = _ema(df['close'], 50)
    if wr.isna().iloc[-1] or ema50.isna().iloc[-1]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    w = wr.iloc[-1]
    w_prev = wr.iloc[-2]
    p = df['close'].iloc[-1]
    above_ema = p > ema50.iloc[-1]

    if w_prev < -80 and w >= -80 and above_ema:
        return {"signal": "BUY", "confidence": 84,
                "reason_fa": f"%R برگشت از اشباع فروش + بالای EMA50 — تایید صعودی ({w:.1f})"}
    elif w_prev > -20 and w <= -20 and not above_ema:
        return {"signal": "SELL", "confidence": 84,
                "reason_fa": f"%R برگشت از اشباع خرید + زیر EMA50 — تایید نزولی ({w:.1f})"}
    elif w < -80 and above_ema:
        return {"signal": "BUY", "confidence": 65,
                "reason_fa": f"%R اشباع فروش در روند صعودی — فرصت خرید ({w:.1f})"}
    elif w > -20 and not above_ema:
        return {"signal": "SELL", "confidence": 65,
                "reason_fa": f"%R اشباع خرید در روند نزولی — فرصت فروش ({w:.1f})"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"%R+EMA بدون سیگنال ({w:.1f})"}


# ═══════════════════════════════════════════════════════
# REGISTRY
# ═══════════════════════════════════════════════════════

WILLR_STRATEGIES = [
    {"id": "WR_01", "name": "Williams %R Classic", "name_fa": "ویلیامز %R کلاسیک", "func": wr_01_classic},
    {"id": "WR_02", "name": "Williams %R Failure Swing", "name_fa": "نوسان شکست %R", "func": wr_02_failure_swing},
    {"id": "WR_03", "name": "Williams %R + Trend", "name_fa": "ویلیامز %R + فیلتر روند", "func": wr_03_trend_filter},
]
