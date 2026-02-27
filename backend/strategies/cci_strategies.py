"""
Whilber-AI — CCI Strategy Pack (4 Sub-Strategies)
===================================================
CCI_01: Classic CCI Overbought/Oversold (+100/-100)
CCI_02: CCI Zero-Line Cross
CCI_03: CCI Trend (CCI > +100 sustained = strong trend)
CCI_04: CCI + EMA Filter
"""

import numpy as np
import pandas as pd


def _cci(df, period=20):
    tp = (df['high'] + df['low'] + df['close']) / 3
    sma = tp.rolling(period).mean()
    mad = tp.rolling(period).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    return (tp - sma) / (0.015 * mad).replace(0, 1e-10)


def _ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


# ─────────────────────────────────────────────────────
# CCI_01: Classic CCI Overbought/Oversold
# BUY:  CCI crosses above -100 from below (leaving oversold)
# SELL: CCI crosses below +100 from above (leaving overbought)
# ─────────────────────────────────────────────────────
def cci_01_classic(df, context=None):
    cci = _cci(df, 20)
    if cci.isna().iloc[-1]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    c = cci.iloc[-1]
    c_prev = cci.iloc[-2]

    if c_prev < -100 and c >= -100:
        conf = min(82, 60 + int(abs(cci.iloc[-3] + 100) * 0.2)) if len(cci) > 3 else 72
        return {"signal": "BUY", "confidence": conf,
                "reason_fa": f"CCI از اشباع فروش برگشت ({c:.0f}) — عبور از -100"}
    elif c_prev > 100 and c <= 100:
        conf = min(82, 60 + int(abs(cci.iloc[-3] - 100) * 0.2)) if len(cci) > 3 else 72
        return {"signal": "SELL", "confidence": conf,
                "reason_fa": f"CCI از اشباع خرید برگشت ({c:.0f}) — عبور از +100"}
    elif c < -100:
        return {"signal": "BUY", "confidence": 55,
                "reason_fa": f"CCI در اشباع فروش ({c:.0f}) — منتظر برگشت"}
    elif c > 100:
        return {"signal": "SELL", "confidence": 55,
                "reason_fa": f"CCI در اشباع خرید ({c:.0f}) — منتظر برگشت"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"CCI خنثی ({c:.0f})"}


# ─────────────────────────────────────────────────────
# CCI_02: CCI Zero-Line Cross
# BUY:  CCI crosses above 0 (momentum shifts bullish)
# SELL: CCI crosses below 0 (momentum shifts bearish)
# ─────────────────────────────────────────────────────
def cci_02_zero_cross(df, context=None):
    cci = _cci(df, 20)
    if cci.isna().iloc[-1]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    c = cci.iloc[-1]
    c_prev = cci.iloc[-2]

    if c_prev <= 0 and c > 0:
        return {"signal": "BUY", "confidence": 70,
                "reason_fa": f"CCI از خط صفر عبور کرد (بالا) — مومنتوم صعودی ({c:.0f})"}
    elif c_prev >= 0 and c < 0:
        return {"signal": "SELL", "confidence": 70,
                "reason_fa": f"CCI از خط صفر عبور کرد (پایین) — مومنتوم نزولی ({c:.0f})"}
    elif c > 50:
        return {"signal": "BUY", "confidence": 45,
                "reason_fa": f"CCI مثبت و قوی ({c:.0f})"}
    elif c < -50:
        return {"signal": "SELL", "confidence": 45,
                "reason_fa": f"CCI منفی و قوی ({c:.0f})"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"CCI نزدیک صفر ({c:.0f}) — بلاتکلیف"}


# ─────────────────────────────────────────────────────
# CCI_03: CCI Trend (Sustained above/below 100)
# BUY:  CCI stays above +100 for 3+ bars = strong uptrend
# SELL: CCI stays below -100 for 3+ bars = strong downtrend
# ─────────────────────────────────────────────────────
def cci_03_trend(df, context=None):
    cci = _cci(df, 20)
    if cci.isna().iloc[-1] or len(cci.dropna()) < 5:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    c = cci.iloc[-1]
    recent = cci.dropna().tail(5)
    above_100 = sum(1 for v in recent if v > 100)
    below_100 = sum(1 for v in recent if v < -100)

    if above_100 >= 4 and c > 100:
        return {"signal": "BUY", "confidence": 80,
                "reason_fa": f"CCI در روند صعودی قوی — {above_100}/5 بار بالای +100 ({c:.0f})"}
    elif below_100 >= 4 and c < -100:
        return {"signal": "SELL", "confidence": 80,
                "reason_fa": f"CCI در روند نزولی قوی — {below_100}/5 بار زیر -100 ({c:.0f})"}
    elif above_100 >= 3:
        return {"signal": "BUY", "confidence": 62,
                "reason_fa": f"CCI عمدتا بالای +100 — روند صعودی ({above_100}/5, CCI={c:.0f})"}
    elif below_100 >= 3:
        return {"signal": "SELL", "confidence": 62,
                "reason_fa": f"CCI عمدتا زیر -100 — روند نزولی ({below_100}/5, CCI={c:.0f})"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"CCI بدون روند پایدار ({c:.0f})"}


# ─────────────────────────────────────────────────────
# CCI_04: CCI + EMA Filter
# BUY:  CCI oversold + price above EMA50
# SELL: CCI overbought + price below EMA50
# ─────────────────────────────────────────────────────
def cci_04_ema_filter(df, context=None):
    cci = _cci(df, 20)
    ema50 = _ema(df['close'], 50)
    if cci.isna().iloc[-1] or ema50.isna().iloc[-1]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    c = cci.iloc[-1]
    c_prev = cci.iloc[-2]
    p = df['close'].iloc[-1]
    above_ema = p > ema50.iloc[-1]
    ema_dist = (p - ema50.iloc[-1]) / p * 100

    if c_prev < -100 and c >= -100 and above_ema:
        return {"signal": "BUY", "confidence": 84,
                "reason_fa": f"CCI برگشت اشباع فروش + بالای EMA50 — سیگنال تایید شده ({c:.0f}, {ema_dist:+.2f}%)"}
    elif c_prev > 100 and c <= 100 and not above_ema:
        return {"signal": "SELL", "confidence": 84,
                "reason_fa": f"CCI برگشت اشباع خرید + زیر EMA50 — سیگنال تایید شده ({c:.0f}, {ema_dist:+.2f}%)"}
    elif c < -100 and above_ema:
        return {"signal": "BUY", "confidence": 62,
                "reason_fa": f"CCI اشباع فروش + بالای EMA50 — آماده برگشت ({c:.0f})"}
    elif c > 100 and not above_ema:
        return {"signal": "SELL", "confidence": 62,
                "reason_fa": f"CCI اشباع خرید + زیر EMA50 — آماده برگشت ({c:.0f})"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"CCI+EMA بدون سیگنال ({c:.0f}, EMA {ema_dist:+.2f}%)"}


# ═══════════════════════════════════════════════════════
# REGISTRY
# ═══════════════════════════════════════════════════════

CCI_STRATEGIES = [
    {"id": "CCI_01", "name": "CCI Classic OB/OS", "name_fa": "CCI کلاسیک اشباع خرید/فروش", "func": cci_01_classic},
    {"id": "CCI_02", "name": "CCI Zero Cross", "name_fa": "CCI تقاطع خط صفر", "func": cci_02_zero_cross},
    {"id": "CCI_03", "name": "CCI Trend Sustained", "name_fa": "CCI روند پایدار", "func": cci_03_trend},
    {"id": "CCI_04", "name": "CCI + EMA50 Filter", "name_fa": "CCI + فیلتر EMA50", "func": cci_04_ema_filter},
]
