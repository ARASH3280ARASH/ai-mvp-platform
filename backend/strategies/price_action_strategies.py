"""
Whilber-AI — Price Action Strategy Pack (6 Sub-Strategies)
============================================================
PA_01: Support/Resistance Bounce
PA_02: Trend Line Break (Dynamic S/R)
PA_03: Inside Bar Breakout
PA_04: Pin Bar Reversal
PA_05: Double Top / Double Bottom
PA_06: Higher Highs & Lows Structure
"""

import numpy as np
import pandas as pd


def _swing_points(series, order=5):
    """Find swing highs and lows."""
    arr = series.values
    highs = []
    lows = []
    for i in range(order, len(arr) - order):
        if all(arr[i] >= arr[i-j] for j in range(1, order+1)) and all(arr[i] >= arr[i+j] for j in range(1, order+1)):
            highs.append((i, arr[i]))
        if all(arr[i] <= arr[i-j] for j in range(1, order+1)) and all(arr[i] <= arr[i+j] for j in range(1, order+1)):
            lows.append((i, arr[i]))
    return highs, lows


def _avg_body(df, n=14):
    return (df['close'] - df['open']).abs().tail(n).mean()


def _near(price, level, tol_pct=0.3):
    return abs(price - level) / price * 100 < tol_pct


# ─────────────────────────────────────────────────────
# PA_01: Support / Resistance Bounce
# Finds horizontal S/R from repeated swing levels
# BUY:  Price bouncing off support
# SELL: Price rejecting resistance
# ─────────────────────────────────────────────────────
def pa_01_sr_bounce(df, context=None):
    if len(df) < 50:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    high = df['high']; low = df['low']; close = df['close']
    p = close.iloc[-1]; p_prev = close.iloc[-2]

    highs, lows = _swing_points(high, order=5)
    _, low_swings = _swing_points(low, order=5)

    # Cluster swing highs for resistance
    resistance_levels = []
    high_vals = [h[1] for h in highs[-10:]]
    for i in range(len(high_vals)):
        for j in range(i+1, len(high_vals)):
            if abs(high_vals[i] - high_vals[j]) / p < 0.005:
                resistance_levels.append((high_vals[i] + high_vals[j]) / 2)

    # Cluster swing lows for support
    support_levels = []
    low_vals = [l[1] for l in low_swings[-10:]]
    for i in range(len(low_vals)):
        for j in range(i+1, len(low_vals)):
            if abs(low_vals[i] - low_vals[j]) / p < 0.005:
                support_levels.append((low_vals[i] + low_vals[j]) / 2)

    # Check support bounce
    for sup in support_levels[-3:]:
        if _near(p, sup, 0.4) and p > p_prev:
            touches = sum(1 for lv in low_vals if abs(lv - sup) / p < 0.005)
            conf = min(85, 60 + touches * 8)
            return {"signal": "BUY", "confidence": conf,
                    "reason_fa": f"برگشت از حمایت ({sup:.4f}) — {touches} بار لمس شده"}

    # Check resistance rejection
    for res in resistance_levels[-3:]:
        if _near(p, res, 0.4) and p < p_prev:
            touches = sum(1 for hv in high_vals if abs(hv - res) / p < 0.005)
            conf = min(85, 60 + touches * 8)
            return {"signal": "SELL", "confidence": conf,
                    "reason_fa": f"ریجکت از مقاومت ({res:.4f}) — {touches} بار لمس شده"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "حمایت/مقاومت فعال در نزدیکی قیمت یافت نشد"}


# ─────────────────────────────────────────────────────
# PA_02: Trend Line Break (Linear Regression Slope)
# Uses slope of recent lows (uptrend) or highs (downtrend)
# BUY:  Uptrend trendline holding + bouncing
# SELL: Downtrend trendline holding + rejecting
# ─────────────────────────────────────────────────────
def pa_02_trendline(df, context=None):
    if len(df) < 30:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    close = df['close']
    p = close.iloc[-1]
    n = 20

    # Linear regression on last n closes
    x = np.arange(n)
    y = close.tail(n).values.astype(float)
    if len(y) < n:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    slope, intercept = np.polyfit(x, y, 1)
    slope_pct = slope / p * 100
    trendline_val = intercept + slope * (n - 1)
    dist_pct = (p - trendline_val) / p * 100

    # R-squared for trend strength
    y_pred = intercept + slope * x
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    if slope_pct > 0.1 and r2 > 0.7:
        if abs(dist_pct) < 0.5 and p > close.iloc[-2]:
            return {"signal": "BUY", "confidence": min(82, 60 + int(r2 * 25)),
                    "reason_fa": f"برگشت از خط روند صعودی (شیب {slope_pct:+.3f}%, R²={r2:.2f})"}
        return {"signal": "BUY", "confidence": 52,
                "reason_fa": f"روند صعودی فعال (شیب {slope_pct:+.3f}%, R²={r2:.2f})"}
    elif slope_pct < -0.1 and r2 > 0.7:
        if abs(dist_pct) < 0.5 and p < close.iloc[-2]:
            return {"signal": "SELL", "confidence": min(82, 60 + int(r2 * 25)),
                    "reason_fa": f"ریجکت از خط روند نزولی (شیب {slope_pct:+.3f}%, R²={r2:.2f})"}
        return {"signal": "SELL", "confidence": 52,
                "reason_fa": f"روند نزولی فعال (شیب {slope_pct:+.3f}%, R²={r2:.2f})"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"خط روند ضعیف (شیب {slope_pct:+.3f}%, R²={r2:.2f})"}


# ─────────────────────────────────────────────────────
# PA_03: Inside Bar Breakout
# Inside bar: current bar H/L completely inside previous bar
# BUY:  Break above inside bar high
# SELL: Break below inside bar low
# ─────────────────────────────────────────────────────
def pa_03_inside_bar(df, context=None):
    if len(df) < 4:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    # Check if bar[-2] was inside bar[-3] (mother bar)
    h_mother = df['high'].iloc[-3]; l_mother = df['low'].iloc[-3]
    h_inside = df['high'].iloc[-2]; l_inside = df['low'].iloc[-2]

    is_inside = h_inside <= h_mother and l_inside >= l_mother
    if not is_inside:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "الگوی اینساید بار شناسایی نشد"}

    # Current bar breaks the inside bar
    p = df['close'].iloc[-1]
    h_curr = df['high'].iloc[-1]; l_curr = df['low'].iloc[-1]
    range_pct = (h_mother - l_mother) / p * 100

    if p > h_inside and h_curr > h_inside:
        conf = min(82, 62 + int(range_pct * 8))
        return {"signal": "BUY", "confidence": conf,
                "reason_fa": f"شکست اینساید بار به بالا — بریک‌اوت صعودی (رنج مادر {range_pct:.2f}%)"}
    elif p < l_inside and l_curr < l_inside:
        conf = min(82, 62 + int(range_pct * 8))
        return {"signal": "SELL", "confidence": conf,
                "reason_fa": f"شکست اینساید بار به پایین — بریک‌اوت نزولی (رنج مادر {range_pct:.2f}%)"}
    elif h_curr <= h_inside and l_curr >= l_inside:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"اینساید بار دوم — فشردگی ادامه‌دار (رنج {range_pct:.2f}%)"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "اینساید بار بدون شکست مشخص"}


# ─────────────────────────────────────────────────────
# PA_04: Pin Bar Reversal
# Long shadow + small body at extreme of range
# BUY:  Pin bar with long lower wick at support
# SELL: Pin bar with long upper wick at resistance
# ─────────────────────────────────────────────────────
def pa_04_pin_bar(df, context=None):
    if len(df) < 10:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    o = df['open'].iloc[-1]; h = df['high'].iloc[-1]
    l = df['low'].iloc[-1]; c = df['close'].iloc[-1]
    body = abs(c - o)
    candle_range = h - l
    if candle_range == 0:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "کندل بدون حرکت"}

    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l
    body_pct = body / candle_range
    avg = _avg_body(df, 14)

    # Check recent trend for context
    close = df['close']
    trend_change = (close.iloc[-1] - close.iloc[-10]) / close.iloc[-10] * 100 if len(close) >= 10 else 0

    # Bullish pin bar: long lower wick, small body at top, after decline
    if lower_wick > 2 * body and lower_wick > 0.6 * candle_range and upper_wick < 0.2 * candle_range:
        ratio = lower_wick / max(body, 0.0001)
        if trend_change < -1:
            return {"signal": "BUY", "confidence": min(84, 65 + int(ratio * 4)),
                    "reason_fa": f"پین بار صعودی بعد از نزول — سایه پایین {ratio:.1f}x بدنه"}
        return {"signal": "BUY", "confidence": min(70, 55 + int(ratio * 4)),
                "reason_fa": f"پین بار صعودی — سایه پایین {ratio:.1f}x بدنه"}

    # Bearish pin bar: long upper wick, small body at bottom, after rally
    if upper_wick > 2 * body and upper_wick > 0.6 * candle_range and lower_wick < 0.2 * candle_range:
        ratio = upper_wick / max(body, 0.0001)
        if trend_change > 1:
            return {"signal": "SELL", "confidence": min(84, 65 + int(ratio * 4)),
                    "reason_fa": f"پین بار نزولی بعد از صعود — سایه بالا {ratio:.1f}x بدنه"}
        return {"signal": "SELL", "confidence": min(70, 55 + int(ratio * 4)),
                "reason_fa": f"پین بار نزولی — سایه بالا {ratio:.1f}x بدنه"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "پین بار شناسایی نشد"}


# ─────────────────────────────────────────────────────
# PA_05: Double Top / Double Bottom
# Two peaks/troughs at similar levels = reversal pattern
# BUY:  Double bottom detected
# SELL: Double top detected
# ─────────────────────────────────────────────────────
def pa_05_double_pattern(df, context=None):
    if len(df) < 40:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    high = df['high']; low = df['low']; close = df['close']
    p = close.iloc[-1]

    highs, lows = _swing_points(high, order=5)
    _, low_swings = _swing_points(low, order=5)

    # Double Top: two swing highs at similar level, price now falling
    if len(highs) >= 2:
        h1_idx, h1_val = highs[-2]
        h2_idx, h2_val = highs[-1]
        if abs(h1_val - h2_val) / p < 0.005 and h2_idx - h1_idx > 5:
            neckline = min(low.iloc[h1_idx:h2_idx+1])
            if p < neckline:
                return {"signal": "SELL", "confidence": 82,
                        "reason_fa": f"دابل تاپ — دو سقف مشابه ({h1_val:.4f}/{h2_val:.4f}) + شکست خط گردن"}
            elif _near(p, (h1_val + h2_val)/2, 0.5):
                return {"signal": "SELL", "confidence": 68,
                        "reason_fa": f"نزدیک سقف دابل تاپ ({(h1_val+h2_val)/2:.4f})"}

    # Double Bottom: two swing lows at similar level, price now rising
    if len(low_swings) >= 2:
        l1_idx, l1_val = low_swings[-2]
        l2_idx, l2_val = low_swings[-1]
        if abs(l1_val - l2_val) / p < 0.005 and l2_idx - l1_idx > 5:
            neckline = max(high.iloc[l1_idx:l2_idx+1])
            if p > neckline:
                return {"signal": "BUY", "confidence": 82,
                        "reason_fa": f"دابل باتم — دو کف مشابه ({l1_val:.4f}/{l2_val:.4f}) + شکست خط گردن"}
            elif _near(p, (l1_val + l2_val)/2, 0.5):
                return {"signal": "BUY", "confidence": 68,
                        "reason_fa": f"نزدیک کف دابل باتم ({(l1_val+l2_val)/2:.4f})"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "الگوی دابل تاپ/باتم شناسایی نشد"}


# ─────────────────────────────────────────────────────
# PA_06: Higher Highs & Higher Lows Structure
# Analyzes swing structure for trend identification
# BUY:  HH + HL pattern (uptrend structure intact)
# SELL: LH + LL pattern (downtrend structure intact)
# ─────────────────────────────────────────────────────
def pa_06_hh_hl(df, context=None):
    if len(df) < 40:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    highs, lows = _swing_points(df['high'], order=4)
    _, low_swings = _swing_points(df['low'], order=4)

    if len(highs) < 3 or len(low_swings) < 3:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "سوئینگ کافی نیست"}

    h_vals = [h[1] for h in highs[-4:]]
    l_vals = [l[1] for l in low_swings[-4:]]

    # Count HH/HL and LH/LL
    hh_count = sum(1 for i in range(1, len(h_vals)) if h_vals[i] > h_vals[i-1])
    hl_count = sum(1 for i in range(1, len(l_vals)) if l_vals[i] > l_vals[i-1])
    lh_count = sum(1 for i in range(1, len(h_vals)) if h_vals[i] < h_vals[i-1])
    ll_count = sum(1 for i in range(1, len(l_vals)) if l_vals[i] < l_vals[i-1])

    total_checks = max(len(h_vals) - 1, 1)

    if hh_count >= 2 and hl_count >= 2:
        return {"signal": "BUY", "confidence": 80,
                "reason_fa": f"ساختار صعودی قوی — HH: {hh_count}/{total_checks}, HL: {hl_count}/{total_checks}"}
    elif lh_count >= 2 and ll_count >= 2:
        return {"signal": "SELL", "confidence": 80,
                "reason_fa": f"ساختار نزولی قوی — LH: {lh_count}/{total_checks}, LL: {ll_count}/{total_checks}"}
    elif hh_count >= 1 and hl_count >= 1 and lh_count == 0:
        return {"signal": "BUY", "confidence": 60,
                "reason_fa": f"ساختار صعودی — HH: {hh_count}, HL: {hl_count}"}
    elif lh_count >= 1 and ll_count >= 1 and hh_count == 0:
        return {"signal": "SELL", "confidence": 60,
                "reason_fa": f"ساختار نزولی — LH: {lh_count}, LL: {ll_count}"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"ساختار مختلط — HH:{hh_count} HL:{hl_count} LH:{lh_count} LL:{ll_count}"}


# ═══════════════════════════════════════════════════════
# REGISTRY
# ═══════════════════════════════════════════════════════

PA_STRATEGIES = [
    {"id": "PA_01", "name": "S/R Bounce", "name_fa": "برگشت از حمایت/مقاومت", "func": pa_01_sr_bounce},
    {"id": "PA_02", "name": "Trend Line", "name_fa": "خط روند (رگرسیون)", "func": pa_02_trendline},
    {"id": "PA_03", "name": "Inside Bar Breakout", "name_fa": "شکست اینساید بار", "func": pa_03_inside_bar},
    {"id": "PA_04", "name": "Pin Bar Reversal", "name_fa": "پین بار برگشتی", "func": pa_04_pin_bar},
    {"id": "PA_05", "name": "Double Top/Bottom", "name_fa": "دابل تاپ/باتم", "func": pa_05_double_pattern},
    {"id": "PA_06", "name": "HH/HL Structure", "name_fa": "ساختار سقف/کف بالاتر", "func": pa_06_hh_hl},
]
