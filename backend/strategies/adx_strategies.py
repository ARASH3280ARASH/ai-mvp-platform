"""
Whilber-AI — ADX Strategy Pack (8 Sub-Strategies)
===================================================
ADX_01: Classic DI Cross (DI+ crosses DI-)
ADX_02: ADX Trend Strength (ADX > 25)
ADX_03: ADX + DI Combined (ADX strong + DI cross)
ADX_04: ADX Rising (Trend Starting)
ADX_05: ADX Falling (Trend Weakening)
ADX_06: DI Spread (Distance between DI+ and DI-)
ADX_07: ADX Extreme (ADX > 50 Overextended)
ADX_08: ADX + SuperTrend Confirmation
"""

import numpy as np
import pandas as pd


def _adx_calc(df, period=14):
    """Calculate ADX, +DI, -DI."""
    high = df['high']
    low = df['low']
    close = df['close']

    # True Range
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Directional Movement
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low

    plus_dm = pd.Series(0.0, index=close.index)
    minus_dm = pd.Series(0.0, index=close.index)

    plus_dm[(up_move > down_move) & (up_move > 0)] = up_move
    minus_dm[(down_move > up_move) & (down_move > 0)] = down_move

    # Smoothed with Wilder's method
    atr = tr.ewm(alpha=1/period, min_periods=period).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1/period, min_periods=period).mean() / atr.replace(0, 1e-10)
    minus_di = 100 * minus_dm.ewm(alpha=1/period, min_periods=period).mean() / atr.replace(0, 1e-10)

    # ADX
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, 1e-10)
    adx = dx.ewm(alpha=1/period, min_periods=period).mean()

    return adx, plus_di, minus_di


def _supertrend_simple(df, period=10, multiplier=3.0):
    """Simplified SuperTrend for ADX combo strategy."""
    high = df['high']
    low = df['low']
    close = df['close']
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period, min_periods=period).mean()
    hl2 = (high + low) / 2
    upper = hl2 + multiplier * atr
    lower = hl2 - multiplier * atr
    direction = pd.Series(1, index=close.index)
    for i in range(period + 1, len(close)):
        if pd.isna(atr.iloc[i]):
            continue
        if direction.iloc[i-1] == 1:
            direction.iloc[i] = -1 if close.iloc[i] < lower.iloc[i] else 1
        else:
            direction.iloc[i] = 1 if close.iloc[i] > upper.iloc[i] else -1
    return direction


# ─────────────────────────────────────────────────────
# ADX_01: Classic DI Cross
# BUY:  DI+ crosses above DI-
# SELL: DI+ crosses below DI-
# ─────────────────────────────────────────────────────
def adx_01_di_cross(df, context=None):
    adx, plus_di, minus_di = _adx_calc(df)
    if adx.isna().iloc[-1]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    p_di = plus_di.iloc[-1]
    m_di = minus_di.iloc[-1]
    p_di_prev = plus_di.iloc[-2]
    m_di_prev = minus_di.iloc[-2]
    a = adx.iloc[-1]

    if p_di_prev <= m_di_prev and p_di > m_di:
        conf = min(85, 60 + int(a))
        return {"signal": "BUY", "confidence": conf,
                "reason_fa": f"تقاطع صعودی DI+ بالای DI- (ADX={a:.1f}, +DI={p_di:.1f}, -DI={m_di:.1f})"}
    elif p_di_prev >= m_di_prev and p_di < m_di:
        conf = min(85, 60 + int(a))
        return {"signal": "SELL", "confidence": conf,
                "reason_fa": f"تقاطع نزولی DI- بالای DI+ (ADX={a:.1f}, +DI={p_di:.1f}, -DI={m_di:.1f})"}
    elif p_di > m_di:
        return {"signal": "BUY", "confidence": 42,
                "reason_fa": f"DI+ بالای DI- — فشار خریدار (+DI={p_di:.1f}, -DI={m_di:.1f})"}
    else:
        return {"signal": "SELL", "confidence": 42,
                "reason_fa": f"DI- بالای DI+ — فشار فروشنده (+DI={p_di:.1f}, -DI={m_di:.1f})"}


# ─────────────────────────────────────────────────────
# ADX_02: ADX Trend Strength
# ADX > 25 = trending, ADX < 20 = ranging
# Direction from DI
# ─────────────────────────────────────────────────────
def adx_02_trend_strength(df, context=None):
    adx, plus_di, minus_di = _adx_calc(df)
    if adx.isna().iloc[-1]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    a = adx.iloc[-1]
    p_di = plus_di.iloc[-1]
    m_di = minus_di.iloc[-1]

    if a > 40:
        strength = "بسیار قوی"
        conf = 75
    elif a > 25:
        strength = "قوی"
        conf = 62
    elif a > 20:
        strength = "ضعیف"
        conf = 45
    else:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"ADX={a:.1f} — بازار بدون روند (رنج)"}

    if p_di > m_di:
        return {"signal": "BUY", "confidence": conf,
                "reason_fa": f"روند صعودی {strength} — ADX={a:.1f} (+DI={p_di:.1f} > -DI={m_di:.1f})"}
    else:
        return {"signal": "SELL", "confidence": conf,
                "reason_fa": f"روند نزولی {strength} — ADX={a:.1f} (-DI={m_di:.1f} > +DI={p_di:.1f})"}


# ─────────────────────────────────────────────────────
# ADX_03: ADX + DI Combined (Strong trend + DI cross)
# BUY:  ADX > 25 + DI+ cross above DI-
# SELL: ADX > 25 + DI- cross above DI+
# ─────────────────────────────────────────────────────
def adx_03_adx_di_combo(df, context=None):
    adx, plus_di, minus_di = _adx_calc(df)
    if adx.isna().iloc[-1]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    a = adx.iloc[-1]
    p_di = plus_di.iloc[-1]
    m_di = minus_di.iloc[-1]
    p_di_prev = plus_di.iloc[-2]
    m_di_prev = minus_di.iloc[-2]
    trending = a > 25

    cross_up = p_di_prev <= m_di_prev and p_di > m_di
    cross_down = p_di_prev >= m_di_prev and p_di < m_di

    if cross_up and trending:
        return {"signal": "BUY", "confidence": 85,
                "reason_fa": f"DI+ بالای DI- + ADX قوی = سیگنال خرید تایید شده (ADX={a:.1f})"}
    elif cross_down and trending:
        return {"signal": "SELL", "confidence": 85,
                "reason_fa": f"DI- بالای DI+ + ADX قوی = سیگنال فروش تایید شده (ADX={a:.1f})"}
    elif cross_up and not trending:
        return {"signal": "BUY", "confidence": 55,
                "reason_fa": f"DI+ بالای DI- ولی ADX ضعیف ({a:.1f}) — سیگنال بدون تایید"}
    elif cross_down and not trending:
        return {"signal": "SELL", "confidence": 55,
                "reason_fa": f"DI- بالای DI+ ولی ADX ضعیف ({a:.1f}) — سیگنال بدون تایید"}
    elif trending and p_di > m_di:
        return {"signal": "BUY", "confidence": 50,
                "reason_fa": f"روند صعودی فعال ADX={a:.1f} — +DI برتر"}
    elif trending and m_di > p_di:
        return {"signal": "SELL", "confidence": 50,
                "reason_fa": f"روند نزولی فعال ADX={a:.1f} — -DI برتر"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"ADX={a:.1f} — بدون سیگنال ترکیبی"}


# ─────────────────────────────────────────────────────
# ADX_04: ADX Rising (New Trend Starting)
# BUY:  ADX crosses above 20 from below + DI+ > DI-
# SELL: ADX crosses above 20 from below + DI- > DI+
# ─────────────────────────────────────────────────────
def adx_04_rising(df, context=None):
    adx, plus_di, minus_di = _adx_calc(df)
    if adx.isna().iloc[-1]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    a = adx.iloc[-1]
    a_prev = adx.iloc[-2]
    a_prev2 = adx.iloc[-3] if len(adx) > 3 else a_prev
    p_di = plus_di.iloc[-1]
    m_di = minus_di.iloc[-1]

    rising = a > a_prev > a_prev2
    crossing_20 = a_prev < 20 and a >= 20
    crossing_25 = a_prev < 25 and a >= 25

    if crossing_20 and p_di > m_di:
        return {"signal": "BUY", "confidence": 76,
                "reason_fa": f"ADX از ۲۰ عبور کرد — شروع روند صعودی (ADX={a:.1f})"}
    elif crossing_20 and m_di > p_di:
        return {"signal": "SELL", "confidence": 76,
                "reason_fa": f"ADX از ۲۰ عبور کرد — شروع روند نزولی (ADX={a:.1f})"}
    elif crossing_25 and p_di > m_di:
        return {"signal": "BUY", "confidence": 80,
                "reason_fa": f"ADX از ۲۵ عبور کرد — روند صعودی قوی شد (ADX={a:.1f})"}
    elif crossing_25 and m_di > p_di:
        return {"signal": "SELL", "confidence": 80,
                "reason_fa": f"ADX از ۲۵ عبور کرد — روند نزولی قوی شد (ADX={a:.1f})"}
    elif rising and a > 20:
        dir_str = "صعودی" if p_di > m_di else "نزولی"
        return {"signal": "BUY" if p_di > m_di else "SELL", "confidence": 55,
                "reason_fa": f"ADX در حال افزایش — روند {dir_str} تقویت (ADX={a:.1f})"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"ADX={a:.1f} — بدون تغییر قابل توجه"}


# ─────────────────────────────────────────────────────
# ADX_05: ADX Falling (Trend Weakening)
# When ADX starts falling from high = trend exhaustion
# ─────────────────────────────────────────────────────
def adx_05_falling(df, context=None):
    adx, plus_di, minus_di = _adx_calc(df)
    if adx.isna().iloc[-1]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    a = adx.iloc[-1]
    a_prev = adx.iloc[-2]
    a_prev2 = adx.iloc[-3] if len(adx) > 3 else a_prev
    p_di = plus_di.iloc[-1]
    m_di = minus_di.iloc[-1]

    falling = a < a_prev < a_prev2
    was_strong = a_prev > 30

    if falling and was_strong and p_di > m_di:
        return {"signal": "SELL", "confidence": 68,
                "reason_fa": f"ADX افت از بالا — روند صعودی ضعیف شده (ADX: {a_prev2:.0f}->{a_prev:.0f}->{a:.0f})"}
    elif falling and was_strong and m_di > p_di:
        return {"signal": "BUY", "confidence": 68,
                "reason_fa": f"ADX افت از بالا — روند نزولی ضعیف شده (ADX: {a_prev2:.0f}->{a_prev:.0f}->{a:.0f})"}
    elif falling and a < 20:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"ADX در حال افت و زیر ۲۰ — ورود به رنج (ADX={a:.1f})"}
    elif falling:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"ADX در حال کاهش ({a:.1f}) — روند ضعیف می‌شود"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"ADX={a:.1f} — بدون افت مشخص"}


# ─────────────────────────────────────────────────────
# ADX_06: DI Spread (Distance between DI+ and DI-)
# Large spread = strong trend, narrow = weak/reversing
# ─────────────────────────────────────────────────────
def adx_06_di_spread(df, context=None):
    adx, plus_di, minus_di = _adx_calc(df)
    if adx.isna().iloc[-1]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    p_di = plus_di.iloc[-1]
    m_di = minus_di.iloc[-1]
    spread = p_di - m_di
    spread_prev = plus_di.iloc[-2] - minus_di.iloc[-2]
    a = adx.iloc[-1]

    # Calculate historical spread for percentile
    spread_series = plus_di - minus_di
    spread_abs = spread_series.abs().dropna().tail(50)
    current_abs = abs(spread)
    if len(spread_abs) > 10:
        pct = (spread_abs < current_abs).sum() / len(spread_abs) * 100
    else:
        pct = 50

    if spread > 15 and spread > spread_prev:
        return {"signal": "BUY", "confidence": min(82, 55 + int(spread)),
                "reason_fa": f"فاصله DI بالا و در حال افزایش — روند صعودی قوی (+DI-(-DI)={spread:.1f}, پرسنتایل {pct:.0f}%)"}
    elif spread < -15 and spread < spread_prev:
        return {"signal": "SELL", "confidence": min(82, 55 + int(abs(spread))),
                "reason_fa": f"فاصله DI بالا و در حال افزایش — روند نزولی قوی (+DI-(-DI)={spread:.1f}, پرسنتایل {pct:.0f}%)"}
    elif abs(spread) > 15 and abs(spread) < abs(spread_prev):
        dir_str = "صعودی" if spread > 0 else "نزولی"
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"فاصله DI در حال کاهش — روند {dir_str} ضعیف شده (فاصله={spread:.1f})"}
    elif abs(spread) < 5:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"DI+ و DI- نزدیک هم — بدون روند (فاصله={spread:.1f})"}
    elif spread > 0:
        return {"signal": "BUY", "confidence": 45,
                "reason_fa": f"DI+ اندکی برتر (فاصله={spread:.1f})"}
    else:
        return {"signal": "SELL", "confidence": 45,
                "reason_fa": f"DI- اندکی برتر (فاصله={spread:.1f})"}


# ─────────────────────────────────────────────────────
# ADX_07: ADX Extreme (ADX > 50 = Overextended)
# Very high ADX often precedes reversals
# ─────────────────────────────────────────────────────
def adx_07_extreme(df, context=None):
    adx, plus_di, minus_di = _adx_calc(df)
    if adx.isna().iloc[-1]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    a = adx.iloc[-1]
    a_prev = adx.iloc[-2]
    p_di = plus_di.iloc[-1]
    m_di = minus_di.iloc[-1]

    if a > 50 and a < a_prev:
        # Extreme ADX falling = potential reversal
        if p_di > m_di:
            return {"signal": "SELL", "confidence": 72,
                    "reason_fa": f"ADX فوق‌العاده ({a:.1f}) در حال افت — احتمال برگشت از صعود"}
        else:
            return {"signal": "BUY", "confidence": 72,
                    "reason_fa": f"ADX فوق‌العاده ({a:.1f}) در حال افت — احتمال برگشت از نزول"}
    elif a > 50:
        if p_di > m_di:
            return {"signal": "BUY", "confidence": 55,
                    "reason_fa": f"ADX فوق‌العاده ({a:.1f}) ولی هنوز بالا — روند صعودی بسیار قوی"}
        else:
            return {"signal": "SELL", "confidence": 55,
                    "reason_fa": f"ADX فوق‌العاده ({a:.1f}) ولی هنوز بالا — روند نزولی بسیار قوی"}
    elif a > 40 and a < a_prev:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"ADX بالا ({a:.1f}) و در حال کاهش — احتیاط"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"ADX={a:.1f} — بدون شرایط اکستریم"}


# ─────────────────────────────────────────────────────
# ADX_08: ADX + SuperTrend Confirmation
# BUY:  ADX trending + ST bullish + DI+ > DI-
# SELL: ADX trending + ST bearish + DI- > DI+
# ─────────────────────────────────────────────────────
def adx_08_supertrend(df, context=None):
    adx, plus_di, minus_di = _adx_calc(df)
    st_dir = _supertrend_simple(df, 10, 3.0)
    if adx.isna().iloc[-1]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    a = adx.iloc[-1]
    p_di = plus_di.iloc[-1]
    m_di = minus_di.iloc[-1]
    st = st_dir.iloc[-1]
    st_prev = st_dir.iloc[-2]

    trending = a > 25
    di_bull = p_di > m_di
    di_bear = m_di > p_di
    st_bull = st == 1
    st_bear = st == -1

    # Triple confirmation
    if trending and di_bull and st_bull:
        conf = min(92, 70 + int(a - 25))
        if st_prev == -1:
            return {"signal": "BUY", "confidence": conf,
                    "reason_fa": f"سه‌گانه تایید: ADX({a:.0f})>25 + DI+ برتر + سوپرترند صعودی شد"}
        return {"signal": "BUY", "confidence": min(conf, 65),
                "reason_fa": f"سه‌گانه تایید صعودی: ADX={a:.0f}, +DI={p_di:.0f}, ST صعودی"}

    elif trending and di_bear and st_bear:
        conf = min(92, 70 + int(a - 25))
        if st_prev == 1:
            return {"signal": "SELL", "confidence": conf,
                    "reason_fa": f"سه‌گانه تایید: ADX({a:.0f})>25 + DI- برتر + سوپرترند نزولی شد"}
        return {"signal": "SELL", "confidence": min(conf, 65),
                "reason_fa": f"سه‌گانه تایید نزولی: ADX={a:.0f}, -DI={m_di:.0f}, ST نزولی"}

    # Partial agreement
    elif di_bull and st_bull:
        return {"signal": "BUY", "confidence": 50,
                "reason_fa": f"DI+ و ST صعودی ولی ADX ضعیف ({a:.1f})"}
    elif di_bear and st_bear:
        return {"signal": "SELL", "confidence": 50,
                "reason_fa": f"DI- و ST نزولی ولی ADX ضعیف ({a:.1f})"}
    # Conflicting
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"سیگنال متناقض — ADX={a:.1f}, DI: {'+' if di_bull else '-'}, ST: {'صعودی' if st_bull else 'نزولی'}"}


# ═══════════════════════════════════════════════════════
# REGISTRY
# ═══════════════════════════════════════════════════════

ADX_STRATEGIES = [
    {"id": "ADX_01", "name": "DI Cross Classic", "name_fa": "تقاطع DI کلاسیک", "func": adx_01_di_cross},
    {"id": "ADX_02", "name": "ADX Trend Strength", "name_fa": "قدرت روند ADX", "func": adx_02_trend_strength},
    {"id": "ADX_03", "name": "ADX + DI Combined", "name_fa": "ترکیب ADX و DI", "func": adx_03_adx_di_combo},
    {"id": "ADX_04", "name": "ADX Rising (New Trend)", "name_fa": "ADX صعودی (روند جدید)", "func": adx_04_rising},
    {"id": "ADX_05", "name": "ADX Falling (Weakening)", "name_fa": "ADX نزولی (ضعف روند)", "func": adx_05_falling},
    {"id": "ADX_06", "name": "DI Spread Analysis", "name_fa": "تحلیل فاصله DI", "func": adx_06_di_spread},
    {"id": "ADX_07", "name": "ADX Extreme (>50)", "name_fa": "ADX اکستریم (بالای ۵۰)", "func": adx_07_extreme},
    {"id": "ADX_08", "name": "ADX + SuperTrend", "name_fa": "ADX + سوپرترند", "func": adx_08_supertrend},
]
