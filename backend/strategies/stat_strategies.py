"""
Whilber-AI — Statistical Strategy Pack (3 Sub-Strategies)
==========================================================
STAT_01: Z-Score (Standard Deviation from Mean)
STAT_02: Linear Regression Channel
STAT_03: Hurst Exponent (Trend vs Mean-Revert Detection)
"""

import numpy as np
import pandas as pd


def _sma(series, period):
    return series.rolling(window=period, min_periods=period).mean()


def _ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


# ─────────────────────────────────────────────────────
# STAT_01: Z-Score (Distance from Mean in Std Devs)
# BUY:  Z-Score < -2 (price far below mean = oversold)
# SELL: Z-Score > +2 (price far above mean = overbought)
# ─────────────────────────────────────────────────────
def stat_01_zscore(df, context=None):
    close = df['close']
    period = 50
    if len(close) < period + 2:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    mean = _sma(close, period)
    std = close.rolling(period).std()

    if mean.isna().iloc[-1] or std.isna().iloc[-1] or std.iloc[-1] == 0:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    z = (close.iloc[-1] - mean.iloc[-1]) / std.iloc[-1]
    z_prev = (close.iloc[-2] - mean.iloc[-2]) / std.iloc[-2] if std.iloc[-2] != 0 else 0

    if z_prev < -2 and z >= -2:
        return {"signal": "BUY", "confidence": 82,
                "reason_fa": f"Z-Score از اشباع فروش برگشت ({z:+.2f}) — بازگشت به میانگین"}
    elif z_prev > 2 and z <= 2:
        return {"signal": "SELL", "confidence": 82,
                "reason_fa": f"Z-Score از اشباع خرید برگشت ({z:+.2f}) — بازگشت به میانگین"}
    elif z < -2.5:
        return {"signal": "BUY", "confidence": 75,
                "reason_fa": f"Z-Score بسیار پایین ({z:+.2f}) — ۲.۵ انحراف زیر میانگین"}
    elif z > 2.5:
        return {"signal": "SELL", "confidence": 75,
                "reason_fa": f"Z-Score بسیار بالا ({z:+.2f}) — ۲.۵ انحراف بالای میانگین"}
    elif z < -2:
        return {"signal": "BUY", "confidence": 65,
                "reason_fa": f"Z-Score پایین ({z:+.2f}) — اشباع فروش آماری"}
    elif z > 2:
        return {"signal": "SELL", "confidence": 65,
                "reason_fa": f"Z-Score بالا ({z:+.2f}) — اشباع خرید آماری"}
    elif z < -1:
        return {"signal": "BUY", "confidence": 42,
                "reason_fa": f"Z-Score نسبتا پایین ({z:+.2f})"}
    elif z > 1:
        return {"signal": "SELL", "confidence": 42,
                "reason_fa": f"Z-Score نسبتا بالا ({z:+.2f})"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"Z-Score خنثی ({z:+.2f}) — نزدیک میانگین"}


# ─────────────────────────────────────────────────────
# STAT_02: Linear Regression Channel
# Fits linear regression + 2 std dev channel
# BUY:  Price at lower channel boundary
# SELL: Price at upper channel boundary
# ─────────────────────────────────────────────────────
def stat_02_linreg_channel(df, context=None):
    close = df['close']
    period = 50
    if len(close) < period + 2:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    y = close.tail(period).values.astype(float)
    x = np.arange(period)

    slope, intercept = np.polyfit(x, y, 1)
    y_pred = intercept + slope * x
    residuals = y - y_pred
    std_dev = np.std(residuals)

    # Current position
    reg_value = intercept + slope * (period - 1)
    upper = reg_value + 2 * std_dev
    lower = reg_value - 2 * std_dev
    p = close.iloc[-1]
    p_prev = close.iloc[-2]

    # R-squared
    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    slope_pct = slope / p * 100
    pos = (p - lower) / (upper - lower) * 100 if upper != lower else 50

    if p <= lower and p > p_prev:
        return {"signal": "BUY", "confidence": min(82, 60 + int(r2 * 25)),
                "reason_fa": f"برگشت از کف کانال رگرسیون (موقعیت {pos:.0f}%, R²={r2:.2f})"}
    elif p >= upper and p < p_prev:
        return {"signal": "SELL", "confidence": min(82, 60 + int(r2 * 25)),
                "reason_fa": f"ریجکت از سقف کانال رگرسیون (موقعیت {pos:.0f}%, R²={r2:.2f})"}
    elif p < lower:
        return {"signal": "BUY", "confidence": 65,
                "reason_fa": f"زیر کانال رگرسیون ({pos:.0f}%, شیب {slope_pct:+.3f}%)"}
    elif p > upper:
        return {"signal": "SELL", "confidence": 65,
                "reason_fa": f"بالای کانال رگرسیون ({pos:.0f}%, شیب {slope_pct:+.3f}%)"}
    elif pos < 20:
        return {"signal": "BUY", "confidence": 48,
                "reason_fa": f"نیمه پایینی کانال ({pos:.0f}%, شیب {slope_pct:+.3f}%)"}
    elif pos > 80:
        return {"signal": "SELL", "confidence": 48,
                "reason_fa": f"نیمه بالایی کانال ({pos:.0f}%, شیب {slope_pct:+.3f}%)"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"وسط کانال رگرسیون ({pos:.0f}%, R²={r2:.2f})"}


# ─────────────────────────────────────────────────────
# STAT_03: Hurst Exponent (Trend vs Mean-Reversion)
# H > 0.5 = trending, H < 0.5 = mean-reverting, H ≈ 0.5 = random
# BUY:  H > 0.6 + price rising (trending up)
# SELL: H > 0.6 + price falling (trending down)
# ─────────────────────────────────────────────────────
def stat_03_hurst(df, context=None):
    close = df['close']
    if len(close) < 100:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست (حداقل ۱۰۰ کندل)"}

    # Simplified Hurst exponent using R/S analysis
    series = close.tail(100).values.astype(float)
    n = len(series)

    # Calculate Hurst using different sub-period sizes
    sizes = [10, 20, 25, 50]
    rs_list = []

    for size in sizes:
        if size > n:
            continue
        num_chunks = n // size
        rs_values = []
        for i in range(num_chunks):
            chunk = series[i * size:(i + 1) * size]
            returns = np.diff(chunk) / chunk[:-1]
            if len(returns) == 0:
                continue
            mean_r = np.mean(returns)
            dev = np.cumsum(returns - mean_r)
            r = np.max(dev) - np.min(dev)
            s = np.std(returns)
            if s > 0:
                rs_values.append(r / s)
        if rs_values:
            rs_list.append((np.log(size), np.log(np.mean(rs_values))))

    if len(rs_list) < 2:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "محاسبه هرست ممکن نشد"}

    # Fit line to get Hurst exponent
    x_h = np.array([r[0] for r in rs_list])
    y_h = np.array([r[1] for r in rs_list])
    if len(x_h) >= 2:
        hurst, _ = np.polyfit(x_h, y_h, 1)
    else:
        hurst = 0.5

    # Clamp to valid range
    hurst = max(0, min(1, hurst))

    # Recent price direction
    recent_change = (close.iloc[-1] - close.iloc[-10]) / close.iloc[-10] * 100

    if hurst > 0.65:
        if recent_change > 0.5:
            return {"signal": "BUY", "confidence": min(80, 58 + int(hurst * 30)),
                    "reason_fa": f"هرست={hurst:.2f} (روندی) + صعودی ({recent_change:+.2f}%) — ادامه صعود محتمل"}
        elif recent_change < -0.5:
            return {"signal": "SELL", "confidence": min(80, 58 + int(hurst * 30)),
                    "reason_fa": f"هرست={hurst:.2f} (روندی) + نزولی ({recent_change:+.2f}%) — ادامه نزول محتمل"}
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"هرست={hurst:.2f} (روندی) ولی جهت نامشخص"}

    elif hurst < 0.4:
        # Mean-reverting: counter-trend signals
        if recent_change > 2:
            return {"signal": "SELL", "confidence": min(75, 55 + int((0.5 - hurst) * 60)),
                    "reason_fa": f"هرست={hurst:.2f} (بازگشتی) + رشد اخیر ({recent_change:+.2f}%) — بازگشت به میانگین"}
        elif recent_change < -2:
            return {"signal": "BUY", "confidence": min(75, 55 + int((0.5 - hurst) * 60)),
                    "reason_fa": f"هرست={hurst:.2f} (بازگشتی) + افت اخیر ({recent_change:+.2f}%) — بازگشت به میانگین"}
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"هرست={hurst:.2f} (بازگشتی) — حرکت بعدی میانگین‌گرا"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"هرست={hurst:.2f} (تصادفی) — بازار بدون الگوی مشخص"}


# ═══════════════════════════════════════════════════════
# REGISTRY
# ═══════════════════════════════════════════════════════

STAT_STRATEGIES = [
    {"id": "STAT_01", "name": "Z-Score Mean Reversion", "name_fa": "Z-Score بازگشت به میانگین", "func": stat_01_zscore},
    {"id": "STAT_02", "name": "LinReg Channel", "name_fa": "کانال رگرسیون خطی", "func": stat_02_linreg_channel},
    {"id": "STAT_03", "name": "Hurst Exponent", "name_fa": "نمای هرست (روندی/بازگشتی)", "func": stat_03_hurst},
]
