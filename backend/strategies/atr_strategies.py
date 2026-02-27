"""
Whilber-AI — ATR Strategy Pack (4 Sub-Strategies)
===================================================
ATR_01: ATR Breakout (Volatility Expansion)
ATR_02: ATR Squeeze (Low Volatility = Pending Move)
ATR_03: ATR Trailing Stop Signal
ATR_04: ATR Channel (Keltner-like)
"""

import numpy as np
import pandas as pd


def _atr(df, period=14):
    high = df['high']; low = df['low']; close = df['close']
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period, min_periods=period).mean()


def _ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def _sma(series, period):
    return series.rolling(window=period, min_periods=period).mean()


# ─────────────────────────────────────────────────────
# ATR_01: ATR Breakout (Volatility Expansion)
# When current candle range > 1.5x ATR = breakout move
# BUY:  Big bullish candle exceeding ATR
# SELL: Big bearish candle exceeding ATR
# ─────────────────────────────────────────────────────
def atr_01_breakout(df, context=None):
    atr = _atr(df, 14)
    if atr.isna().iloc[-1]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    high = df['high'].iloc[-1]; low = df['low'].iloc[-1]
    close = df['close'].iloc[-1]; op = df['open'].iloc[-1]
    candle_range = high - low
    a = atr.iloc[-1]
    ratio = candle_range / a if a > 0 else 0
    is_bull = close > op
    body_pct = (close - op) / close * 100

    if ratio >= 2 and is_bull:
        return {"signal": "BUY", "confidence": min(85, 65 + int(ratio * 8)),
                "reason_fa": f"شکست نوسانی صعودی — رنج {ratio:.1f}x ATR + کندل صعودی ({body_pct:+.2f}%)"}
    elif ratio >= 2 and not is_bull:
        return {"signal": "SELL", "confidence": min(85, 65 + int(ratio * 8)),
                "reason_fa": f"شکست نوسانی نزولی — رنج {ratio:.1f}x ATR + کندل نزولی ({body_pct:+.2f}%)"}
    elif ratio >= 1.5 and is_bull:
        return {"signal": "BUY", "confidence": 62,
                "reason_fa": f"حرکت بالای ATR صعودی ({ratio:.1f}x)"}
    elif ratio >= 1.5 and not is_bull:
        return {"signal": "SELL", "confidence": 62,
                "reason_fa": f"حرکت بالای ATR نزولی ({ratio:.1f}x)"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"رنج عادی ({ratio:.1f}x ATR)"}


# ─────────────────────────────────────────────────────
# ATR_02: ATR Squeeze (Low Volatility = Pending Move)
# ATR at multi-bar low = volatility squeeze, breakout imminent
# ─────────────────────────────────────────────────────
def atr_02_squeeze(df, context=None):
    atr = _atr(df, 14)
    if atr.isna().iloc[-1] or len(atr.dropna()) < 50:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    a = atr.iloc[-1]
    atr_hist = atr.dropna().tail(50)
    percentile = (atr_hist < a).sum() / len(atr_hist) * 100
    atr_sma = _sma(atr, 20).iloc[-1]
    ratio = a / atr_sma if atr_sma > 0 else 1

    close = df['close']
    ema20 = _ema(close, 20)
    above_ema = close.iloc[-1] > ema20.iloc[-1] if not ema20.isna().iloc[-1] else None

    if percentile < 10:
        if above_ema:
            return {"signal": "BUY", "confidence": 72,
                    "reason_fa": f"فشردگی ATR شدید (پرسنتایل {percentile:.0f}%) + بالای EMA — شکست صعودی محتمل"}
        elif above_ema is False:
            return {"signal": "SELL", "confidence": 72,
                    "reason_fa": f"فشردگی ATR شدید (پرسنتایل {percentile:.0f}%) + زیر EMA — شکست نزولی محتمل"}
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"فشردگی ATR شدید (پرسنتایل {percentile:.0f}%) — شکست نزدیک، جهت نامشخص"}
    elif percentile < 20:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"ATR نسبتا پایین (پرسنتایل {percentile:.0f}%) — نوسان کم"}
    elif percentile > 90:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"ATR بسیار بالا (پرسنتایل {percentile:.0f}%) — نوسان شدید، احتیاط"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"ATR عادی (پرسنتایل {percentile:.0f}%, نسبت {ratio:.2f}x)"}


# ─────────────────────────────────────────────────────
# ATR_03: ATR Trailing Stop Signal
# Uses ATR-based trailing stop to detect trend changes
# BUY:  Price moves above ATR trailing stop (bullish flip)
# SELL: Price moves below ATR trailing stop (bearish flip)
# ─────────────────────────────────────────────────────
def atr_03_trailing(df, context=None):
    atr = _atr(df, 14)
    close = df['close']
    if atr.isna().iloc[-1] or len(close) < 20:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    multiplier = 2.5
    # Calculate trailing stop
    trail_up = pd.Series(np.nan, index=close.index)
    trail_down = pd.Series(np.nan, index=close.index)
    direction = pd.Series(1, index=close.index)

    start = atr.first_valid_index()
    if start is None:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    start_loc = close.index.get_loc(start)

    for i in range(start_loc + 1, len(close)):
        if pd.isna(atr.iloc[i]):
            continue
        up = close.iloc[i] - multiplier * atr.iloc[i]
        down = close.iloc[i] + multiplier * atr.iloc[i]

        if i > start_loc + 1:
            prev_up = trail_up.iloc[i-1]
            prev_down = trail_down.iloc[i-1]
            if not pd.isna(prev_up):
                up = max(up, prev_up) if close.iloc[i-1] > prev_up else up
            if not pd.isna(prev_down):
                down = min(down, prev_down) if close.iloc[i-1] < prev_down else down

        trail_up.iloc[i] = up
        trail_down.iloc[i] = down

        prev_dir = direction.iloc[i-1] if i > start_loc else 1
        if close.iloc[i] > trail_down.iloc[i] if not pd.isna(trail_down.iloc[i]) else False:
            direction.iloc[i] = 1
        elif close.iloc[i] < trail_up.iloc[i] if not pd.isna(trail_up.iloc[i]) else False:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = prev_dir

    d = direction.iloc[-1]
    d_prev = direction.iloc[-2]
    p = close.iloc[-1]
    stop_val = trail_up.iloc[-1] if d == 1 else trail_down.iloc[-1]
    dist_pct = (p - stop_val) / p * 100 if not pd.isna(stop_val) else 0

    if d_prev == -1 and d == 1:
        return {"signal": "BUY", "confidence": 80,
                "reason_fa": f"ATR Trailing Stop تغییر به صعودی — استاپ {stop_val:.4f} ({dist_pct:+.2f}%)"}
    elif d_prev == 1 and d == -1:
        return {"signal": "SELL", "confidence": 80,
                "reason_fa": f"ATR Trailing Stop تغییر به نزولی — استاپ {stop_val:.4f} ({dist_pct:+.2f}%)"}
    elif d == 1:
        return {"signal": "BUY", "confidence": 48,
                "reason_fa": f"ATR Trailing صعودی — استاپ {stop_val:.4f} ({dist_pct:+.2f}%)"}
    else:
        return {"signal": "SELL", "confidence": 48,
                "reason_fa": f"ATR Trailing نزولی — استاپ {stop_val:.4f} ({dist_pct:+.2f}%)"}


# ─────────────────────────────────────────────────────
# ATR_04: ATR Channel (Keltner-like)
# Upper = EMA(20) + 2*ATR, Lower = EMA(20) - 2*ATR
# BUY:  Price touches lower channel
# SELL: Price touches upper channel
# ─────────────────────────────────────────────────────
def atr_04_channel(df, context=None):
    atr = _atr(df, 14)
    ema20 = _ema(df['close'], 20)
    if atr.isna().iloc[-1] or ema20.isna().iloc[-1]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    mult = 2.0
    upper = ema20 + mult * atr
    lower = ema20 - mult * atr
    p = df['close'].iloc[-1]
    p_prev = df['close'].iloc[-2]
    u = upper.iloc[-1]; l = lower.iloc[-1]; m = ema20.iloc[-1]

    channel_width = (u - l) / p * 100
    pos = (p - l) / (u - l) * 100 if u != l else 50

    if p <= l and p_prev > lower.iloc[-2]:
        return {"signal": "BUY", "confidence": 78,
                "reason_fa": f"قیمت به کف کانال ATR رسید — اشباع فروش (موقعیت {pos:.0f}%, عرض {channel_width:.2f}%)"}
    elif p >= u and p_prev < upper.iloc[-2]:
        return {"signal": "SELL", "confidence": 78,
                "reason_fa": f"قیمت به سقف کانال ATR رسید — اشباع خرید (موقعیت {pos:.0f}%, عرض {channel_width:.2f}%)"}
    elif p < l:
        return {"signal": "BUY", "confidence": 65,
                "reason_fa": f"قیمت زیر کانال ATR ({pos:.0f}%)"}
    elif p > u:
        return {"signal": "SELL", "confidence": 65,
                "reason_fa": f"قیمت بالای کانال ATR ({pos:.0f}%)"}
    elif p < m:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"قیمت زیر EMA20 در کانال ({pos:.0f}%)"}
    else:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"قیمت بالای EMA20 در کانال ({pos:.0f}%)"}


# ═══════════════════════════════════════════════════════
# REGISTRY
# ═══════════════════════════════════════════════════════

ATR_STRATEGIES = [
    {"id": "ATR_01", "name": "ATR Breakout", "name_fa": "شکست نوسانی ATR", "func": atr_01_breakout},
    {"id": "ATR_02", "name": "ATR Squeeze", "name_fa": "فشردگی ATR", "func": atr_02_squeeze},
    {"id": "ATR_03", "name": "ATR Trailing Stop", "name_fa": "استاپ دنباله‌دار ATR", "func": atr_03_trailing},
    {"id": "ATR_04", "name": "ATR Channel", "name_fa": "کانال ATR (کلتنر)", "func": atr_04_channel},
]
