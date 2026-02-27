"""
Whilber-AI — Moving Average Strategy Pack (12 Sub-Strategies)
==============================================================
MA_01: SMA 20/50 Golden Cross
MA_02: SMA 50/200 Golden Cross
MA_03: EMA 9/21 Fast Cross
MA_04: EMA 12/26 Classic Cross
MA_05: Triple EMA (5/13/34)
MA_06: Price vs SMA 200 Trend
MA_07: EMA Ribbon (8/13/21/34/55)
MA_08: MA Envelope (SMA20 +/- 2%)
MA_09: DEMA(21) Crossover
MA_10: Hull MA(20) Direction
MA_11: VWMA vs SMA Divergence
MA_12: Adaptive MA (KAMA)
"""

import numpy as np
import pandas as pd


def _sma(series, period):
    return series.rolling(window=period, min_periods=period).mean()


def _ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def _dema(series, period):
    e1 = _ema(series, period)
    e2 = _ema(e1, period)
    return 2 * e1 - e2


def _hull_ma(series, period):
    half = int(period / 2)
    sqrt_p = int(np.sqrt(period))
    wma_half = series.rolling(window=half, min_periods=half).mean()
    wma_full = series.rolling(window=period, min_periods=period).mean()
    diff = 2 * wma_half - wma_full
    return diff.rolling(window=sqrt_p, min_periods=sqrt_p).mean()


def _kama(series, er_period=10, fast_sc=2, slow_sc=30):
    """Kaufman Adaptive Moving Average."""
    fast_alpha = 2 / (fast_sc + 1)
    slow_alpha = 2 / (slow_sc + 1)
    arr = series.values.astype(float)
    kama = np.full(len(arr), np.nan)
    if len(arr) < er_period + 1:
        return pd.Series(kama, index=series.index)
    kama[er_period] = arr[er_period]
    for i in range(er_period + 1, len(arr)):
        direction = abs(arr[i] - arr[i - er_period])
        volatility = sum(abs(arr[j] - arr[j-1]) for j in range(i - er_period + 1, i + 1))
        if volatility == 0:
            er = 0
        else:
            er = direction / volatility
        sc = (er * (fast_alpha - slow_alpha) + slow_alpha) ** 2
        kama[i] = kama[i-1] + sc * (arr[i] - kama[i-1])
    return pd.Series(kama, index=series.index)


# ─────────────────────────────────────────────────────
# MA_01: SMA 20/50 Golden Cross
# BUY:  SMA20 crosses above SMA50
# SELL: SMA20 crosses below SMA50
# ─────────────────────────────────────────────────────
def ma_01_sma_20_50(df, context=None):
    close = df['close']
    sma20 = _sma(close, 20)
    sma50 = _sma(close, 50)
    if sma20.isna().iloc[-1] or sma50.isna().iloc[-1]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی برای SMA 20/50 نیست"}

    diff_now = sma20.iloc[-1] - sma50.iloc[-1]
    diff_prev = sma20.iloc[-2] - sma50.iloc[-2]
    gap_pct = abs(diff_now) / close.iloc[-1] * 100

    if diff_prev <= 0 and diff_now > 0:
        conf = min(88, 65 + int(gap_pct * 10))
        return {"signal": "BUY", "confidence": conf,
                "reason_fa": f"تقاطع طلایی SMA20/50 — SMA20 بالای SMA50 (فاصله {gap_pct:.2f}%)"}
    elif diff_prev >= 0 and diff_now < 0:
        conf = min(88, 65 + int(gap_pct * 10))
        return {"signal": "SELL", "confidence": conf,
                "reason_fa": f"تقاطع مرگ SMA20/50 — SMA20 زیر SMA50 (فاصله {gap_pct:.2f}%)"}
    elif diff_now > 0:
        return {"signal": "BUY", "confidence": 45,
                "reason_fa": f"SMA20 بالای SMA50 — روند صعودی ادامه‌دار ({gap_pct:.2f}%)"}
    elif diff_now < 0:
        return {"signal": "SELL", "confidence": 45,
                "reason_fa": f"SMA20 زیر SMA50 — روند نزولی ادامه‌دار ({gap_pct:.2f}%)"}
    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "SMA20 و SMA50 همپوشانی دارند"}


# ─────────────────────────────────────────────────────
# MA_02: SMA 50/200 Golden Cross (Long-term)
# BUY:  SMA50 crosses above SMA200
# SELL: SMA50 crosses below SMA200
# ─────────────────────────────────────────────────────
def ma_02_sma_50_200(df, context=None):
    close = df['close']
    sma50 = _sma(close, 50)
    sma200 = _sma(close, 200)
    if sma200.isna().iloc[-1]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی برای SMA 50/200 نیست (200 کندل لازم)"}

    diff_now = sma50.iloc[-1] - sma200.iloc[-1]
    diff_prev = sma50.iloc[-2] - sma200.iloc[-2]
    gap_pct = abs(diff_now) / close.iloc[-1] * 100

    if diff_prev <= 0 and diff_now > 0:
        return {"signal": "BUY", "confidence": 85,
                "reason_fa": f"تقاطع طلایی بزرگ SMA50/200 — سیگنال صعودی بلندمدت ({gap_pct:.2f}%)"}
    elif diff_prev >= 0 and diff_now < 0:
        return {"signal": "SELL", "confidence": 85,
                "reason_fa": f"تقاطع مرگ بزرگ SMA50/200 — سیگنال نزولی بلندمدت ({gap_pct:.2f}%)"}
    elif diff_now > 0:
        return {"signal": "BUY", "confidence": 50,
                "reason_fa": f"SMA50 بالای SMA200 — روند بلندمدت صعودی ({gap_pct:.2f}%)"}
    else:
        return {"signal": "SELL", "confidence": 50,
                "reason_fa": f"SMA50 زیر SMA200 — روند بلندمدت نزولی ({gap_pct:.2f}%)"}


# ─────────────────────────────────────────────────────
# MA_03: EMA 9/21 Fast Cross
# BUY:  EMA9 crosses above EMA21
# SELL: EMA9 crosses below EMA21
# ─────────────────────────────────────────────────────
def ma_03_ema_9_21(df, context=None):
    close = df['close']
    ema9 = _ema(close, 9)
    ema21 = _ema(close, 21)

    diff_now = ema9.iloc[-1] - ema21.iloc[-1]
    diff_prev = ema9.iloc[-2] - ema21.iloc[-2]
    gap_pct = abs(diff_now) / close.iloc[-1] * 100

    if diff_prev <= 0 and diff_now > 0:
        conf = min(82, 60 + int(gap_pct * 15))
        return {"signal": "BUY", "confidence": conf,
                "reason_fa": f"تقاطع صعودی EMA9/21 — ورود سریع ({gap_pct:.2f}%)"}
    elif diff_prev >= 0 and diff_now < 0:
        conf = min(82, 60 + int(gap_pct * 15))
        return {"signal": "SELL", "confidence": conf,
                "reason_fa": f"تقاطع نزولی EMA9/21 — خروج سریع ({gap_pct:.2f}%)"}
    elif diff_now > 0 and gap_pct > 0.3:
        return {"signal": "BUY", "confidence": 50,
                "reason_fa": f"EMA9 بالای EMA21 — مومنتوم صعودی ({gap_pct:.2f}%)"}
    elif diff_now < 0 and gap_pct > 0.3:
        return {"signal": "SELL", "confidence": 50,
                "reason_fa": f"EMA9 زیر EMA21 — مومنتوم نزولی ({gap_pct:.2f}%)"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"EMA9/21 بدون سیگنال مشخص ({gap_pct:.2f}%)"}


# ─────────────────────────────────────────────────────
# MA_04: EMA 12/26 Classic Cross
# BUY:  EMA12 crosses above EMA26
# SELL: EMA12 crosses below EMA26
# ─────────────────────────────────────────────────────
def ma_04_ema_12_26(df, context=None):
    close = df['close']
    ema12 = _ema(close, 12)
    ema26 = _ema(close, 26)

    diff_now = ema12.iloc[-1] - ema26.iloc[-1]
    diff_prev = ema12.iloc[-2] - ema26.iloc[-2]
    gap_pct = abs(diff_now) / close.iloc[-1] * 100

    if diff_prev <= 0 and diff_now > 0:
        conf = min(85, 62 + int(gap_pct * 12))
        return {"signal": "BUY", "confidence": conf,
                "reason_fa": f"تقاطع صعودی EMA12/26 — کلاسیک MACD بدون هیستوگرام ({gap_pct:.2f}%)"}
    elif diff_prev >= 0 and diff_now < 0:
        conf = min(85, 62 + int(gap_pct * 12))
        return {"signal": "SELL", "confidence": conf,
                "reason_fa": f"تقاطع نزولی EMA12/26 — برگشت روند ({gap_pct:.2f}%)"}
    elif diff_now > 0:
        return {"signal": "BUY", "confidence": 45,
                "reason_fa": f"EMA12 بالای EMA26 — روند صعودی ({gap_pct:.2f}%)"}
    else:
        return {"signal": "SELL", "confidence": 45,
                "reason_fa": f"EMA12 زیر EMA26 — روند نزولی ({gap_pct:.2f}%)"}


# ─────────────────────────────────────────────────────
# MA_05: Triple EMA (5/13/34) Alignment
# BUY:  EMA5 > EMA13 > EMA34 (all aligned bullish)
# SELL: EMA5 < EMA13 < EMA34 (all aligned bearish)
# ─────────────────────────────────────────────────────
def ma_05_triple_ema(df, context=None):
    close = df['close']
    e5 = _ema(close, 5).iloc[-1]
    e13 = _ema(close, 13).iloc[-1]
    e34 = _ema(close, 34).iloc[-1]

    e5_p = _ema(close, 5).iloc[-2]
    e13_p = _ema(close, 13).iloc[-2]
    e34_p = _ema(close, 34).iloc[-2]

    bullish_now = e5 > e13 > e34
    bearish_now = e5 < e13 < e34
    bullish_prev = e5_p > e13_p > e34_p
    bearish_prev = e5_p < e13_p < e34_p

    if bullish_now and not bullish_prev:
        return {"signal": "BUY", "confidence": 82,
                "reason_fa": "سه‌گانه EMA صف شد: EMA5 > EMA13 > EMA34 — شروع روند صعودی"}
    elif bearish_now and not bearish_prev:
        return {"signal": "SELL", "confidence": 82,
                "reason_fa": "سه‌گانه EMA معکوس شد: EMA5 < EMA13 < EMA34 — شروع روند نزولی"}
    elif bullish_now:
        return {"signal": "BUY", "confidence": 55,
                "reason_fa": "سه‌گانه EMA صعودی ادامه‌دار: EMA5 > EMA13 > EMA34"}
    elif bearish_now:
        return {"signal": "SELL", "confidence": 55,
                "reason_fa": "سه‌گانه EMA نزولی ادامه‌دار: EMA5 < EMA13 < EMA34"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "سه‌گانه EMA بدون ترتیب مشخص — بازار بلاتکلیف"}


# ─────────────────────────────────────────────────────
# MA_06: Price vs SMA 200 Trend
# BUY:  Price crosses above SMA200
# SELL: Price crosses below SMA200
# ─────────────────────────────────────────────────────
def ma_06_price_sma200(df, context=None):
    close = df['close']
    sma200 = _sma(close, 200)
    if sma200.isna().iloc[-1]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی برای SMA200 نیست"}

    p = close.iloc[-1]
    p_prev = close.iloc[-2]
    s = sma200.iloc[-1]
    s_prev = sma200.iloc[-2]
    dist_pct = (p - s) / s * 100

    if p_prev <= s_prev and p > s:
        return {"signal": "BUY", "confidence": 78,
                "reason_fa": f"قیمت از SMA200 عبور کرد (بالا) — تغییر روند بلندمدت ({dist_pct:+.2f}%)"}
    elif p_prev >= s_prev and p < s:
        return {"signal": "SELL", "confidence": 78,
                "reason_fa": f"قیمت از SMA200 عبور کرد (پایین) — تغییر روند بلندمدت ({dist_pct:+.2f}%)"}
    elif p > s and dist_pct > 5:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"قیمت خیلی بالای SMA200 ({dist_pct:+.2f}%) — احتمال اصلاح"}
    elif p < s and dist_pct < -5:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"قیمت خیلی زیر SMA200 ({dist_pct:+.2f}%) — احتمال بازگشت"}
    elif p > s:
        return {"signal": "BUY", "confidence": 45,
                "reason_fa": f"قیمت بالای SMA200 — روند بلندمدت صعودی ({dist_pct:+.2f}%)"}
    else:
        return {"signal": "SELL", "confidence": 45,
                "reason_fa": f"قیمت زیر SMA200 — روند بلندمدت نزولی ({dist_pct:+.2f}%)"}


# ─────────────────────────────────────────────────────
# MA_07: EMA Ribbon (8/13/21/34/55)
# BUY:  All EMAs aligned bullish + expanding
# SELL: All EMAs aligned bearish + expanding
# ─────────────────────────────────────────────────────
def ma_07_ema_ribbon(df, context=None):
    close = df['close']
    periods = [8, 13, 21, 34, 55]
    emas = [_ema(close, p) for p in periods]
    vals = [e.iloc[-1] for e in emas]
    vals_prev = [e.iloc[-2] for e in emas]

    # Check if all aligned (descending = bullish, ascending = bearish)
    bullish = all(vals[i] > vals[i+1] for i in range(len(vals)-1))
    bearish = all(vals[i] < vals[i+1] for i in range(len(vals)-1))
    bullish_prev = all(vals_prev[i] > vals_prev[i+1] for i in range(len(vals_prev)-1))
    bearish_prev = all(vals_prev[i] < vals_prev[i+1] for i in range(len(vals_prev)-1))

    # Spread (ribbon width)
    spread = (vals[0] - vals[-1]) / close.iloc[-1] * 100

    if bullish and not bullish_prev:
        return {"signal": "BUY", "confidence": 85,
                "reason_fa": f"ریبون EMA کاملا صعودی شد — ۵ خط هم‌جهت (عرض {spread:.2f}%)"}
    elif bearish and not bearish_prev:
        return {"signal": "SELL", "confidence": 85,
                "reason_fa": f"ریبون EMA کاملا نزولی شد — ۵ خط هم‌جهت (عرض {spread:.2f}%)"}
    elif bullish and abs(spread) > 1:
        return {"signal": "BUY", "confidence": 60,
                "reason_fa": f"ریبون EMA صعودی و در حال باز شدن ({spread:.2f}%)"}
    elif bearish and abs(spread) > 1:
        return {"signal": "SELL", "confidence": 60,
                "reason_fa": f"ریبون EMA نزولی و در حال باز شدن ({spread:.2f}%)"}
    elif bullish:
        return {"signal": "BUY", "confidence": 48,
                "reason_fa": f"ریبون EMA صعودی ولی فشرده ({spread:.2f}%)"}
    elif bearish:
        return {"signal": "SELL", "confidence": 48,
                "reason_fa": f"ریبون EMA نزولی ولی فشرده ({spread:.2f}%)"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "ریبون EMA بی‌نظم — بازار رنج"}


# ─────────────────────────────────────────────────────
# MA_08: MA Envelope (SMA20 +/- 2%)
# BUY:  Price touches lower envelope
# SELL: Price touches upper envelope
# ─────────────────────────────────────────────────────
def ma_08_envelope(df, context=None):
    close = df['close']
    sma20 = _sma(close, 20)
    if sma20.isna().iloc[-1]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    pct = 2.0
    upper = sma20 * (1 + pct/100)
    lower = sma20 * (1 - pct/100)
    p = close.iloc[-1]
    p_prev = close.iloc[-2]
    u = upper.iloc[-1]
    l = lower.iloc[-1]
    mid = sma20.iloc[-1]

    pos = (p - l) / (u - l) * 100 if u != l else 50

    if p <= l and p_prev > lower.iloc[-2]:
        return {"signal": "BUY", "confidence": 78,
                "reason_fa": f"قیمت به پاکت پایین SMA20-2% رسید — اشباع فروش (موقعیت {pos:.0f}%)"}
    elif p >= u and p_prev < upper.iloc[-2]:
        return {"signal": "SELL", "confidence": 78,
                "reason_fa": f"قیمت به پاکت بالای SMA20+2% رسید — اشباع خرید (موقعیت {pos:.0f}%)"}
    elif p < l:
        return {"signal": "BUY", "confidence": 65,
                "reason_fa": f"قیمت زیر پاکت پایین — بازگشت محتمل (موقعیت {pos:.0f}%)"}
    elif p > u:
        return {"signal": "SELL", "confidence": 65,
                "reason_fa": f"قیمت بالای پاکت بالا — اصلاح محتمل (موقعیت {pos:.0f}%)"}
    elif p > mid:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"قیمت بین میانگین و پاکت بالا (موقعیت {pos:.0f}%)"}
    else:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": f"قیمت بین میانگین و پاکت پایین (موقعیت {pos:.0f}%)"}


# ─────────────────────────────────────────────────────
# MA_09: DEMA(21) Direction Change
# BUY:  DEMA starts rising after falling
# SELL: DEMA starts falling after rising
# ─────────────────────────────────────────────────────
def ma_09_dema(df, context=None):
    close = df['close']
    dema = _dema(close, 21)
    if dema.isna().iloc[-1] or dema.isna().iloc[-3]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی برای DEMA نیست"}

    d0 = dema.iloc[-1]
    d1 = dema.iloc[-2]
    d2 = dema.iloc[-3]
    slope_now = d0 - d1
    slope_prev = d1 - d2
    dist_pct = (close.iloc[-1] - d0) / d0 * 100

    if slope_prev <= 0 and slope_now > 0:
        return {"signal": "BUY", "confidence": 75,
                "reason_fa": f"DEMA(21) شروع به صعود کرد — تغییر جهت ({dist_pct:+.2f}% از قیمت)"}
    elif slope_prev >= 0 and slope_now < 0:
        return {"signal": "SELL", "confidence": 75,
                "reason_fa": f"DEMA(21) شروع به نزول کرد — تغییر جهت ({dist_pct:+.2f}% از قیمت)"}
    elif slope_now > 0 and close.iloc[-1] > d0:
        return {"signal": "BUY", "confidence": 50,
                "reason_fa": f"DEMA(21) صعودی و قیمت بالای آن ({dist_pct:+.2f}%)"}
    elif slope_now < 0 and close.iloc[-1] < d0:
        return {"signal": "SELL", "confidence": 50,
                "reason_fa": f"DEMA(21) نزولی و قیمت زیر آن ({dist_pct:+.2f}%)"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"DEMA(21) بدون سیگنال واضح ({dist_pct:+.2f}%)"}


# ─────────────────────────────────────────────────────
# MA_10: Hull MA(20) Direction
# BUY:  HMA turns up (slope change)
# SELL: HMA turns down (slope change)
# ─────────────────────────────────────────────────────
def ma_10_hull(df, context=None):
    close = df['close']
    hma = _hull_ma(close, 20)
    if hma.isna().iloc[-1] or hma.isna().iloc[-3]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی برای Hull MA نیست"}

    h0 = hma.iloc[-1]
    h1 = hma.iloc[-2]
    h2 = hma.iloc[-3]
    slope_now = h0 - h1
    slope_prev = h1 - h2
    dist_pct = (close.iloc[-1] - h0) / h0 * 100

    if slope_prev <= 0 and slope_now > 0:
        return {"signal": "BUY", "confidence": 78,
                "reason_fa": f"Hull MA(20) تغییر جهت به بالا — سیگنال سریع ({dist_pct:+.2f}%)"}
    elif slope_prev >= 0 and slope_now < 0:
        return {"signal": "SELL", "confidence": 78,
                "reason_fa": f"Hull MA(20) تغییر جهت به پایین — سیگنال سریع ({dist_pct:+.2f}%)"}
    elif slope_now > 0:
        return {"signal": "BUY", "confidence": 48,
                "reason_fa": f"Hull MA(20) صعودی ({dist_pct:+.2f}%)"}
    elif slope_now < 0:
        return {"signal": "SELL", "confidence": 48,
                "reason_fa": f"Hull MA(20) نزولی ({dist_pct:+.2f}%)"}
    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "Hull MA خنثی"}


# ─────────────────────────────────────────────────────
# MA_11: VWMA vs SMA Divergence
# BUY:  VWMA > SMA (volume supports price rise)
# SELL: VWMA < SMA (volume supports price drop)
# ─────────────────────────────────────────────────────
def ma_11_vwma(df, context=None):
    close = df['close']
    vol = df.get('tick_volume', df.get('volume', None))
    if vol is None or vol.sum() == 0:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده حجم موجود نیست"}

    period = 20
    vwma = (close * vol).rolling(period).sum() / vol.rolling(period).sum()
    sma = _sma(close, period)
    if vwma.isna().iloc[-1]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    diff = vwma.iloc[-1] - sma.iloc[-1]
    diff_prev = vwma.iloc[-2] - sma.iloc[-2]
    diff_pct = diff / close.iloc[-1] * 100

    if diff_prev <= 0 and diff > 0:
        return {"signal": "BUY", "confidence": 72,
                "reason_fa": f"VWMA بالای SMA رفت — حجم از قیمت حمایت می‌کند ({diff_pct:+.3f}%)"}
    elif diff_prev >= 0 and diff < 0:
        return {"signal": "SELL", "confidence": 72,
                "reason_fa": f"VWMA زیر SMA رفت — حجم ضعیف ({diff_pct:+.3f}%)"}
    elif diff > 0:
        return {"signal": "BUY", "confidence": 45,
                "reason_fa": f"VWMA بالای SMA — حمایت حجمی ادامه‌دار ({diff_pct:+.3f}%)"}
    elif diff < 0:
        return {"signal": "SELL", "confidence": 45,
                "reason_fa": f"VWMA زیر SMA — ضعف حجمی ادامه‌دار ({diff_pct:+.3f}%)"}
    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "VWMA و SMA یکسان"}


# ─────────────────────────────────────────────────────
# MA_12: Kaufman Adaptive MA (KAMA)
# BUY:  Price crosses above KAMA + KAMA rising
# SELL: Price crosses below KAMA + KAMA falling
# ─────────────────────────────────────────────────────
def ma_12_kama(df, context=None):
    close = df['close']
    kama = _kama(close, 10, 2, 30)
    if kama.isna().iloc[-1] or kama.isna().iloc[-3]:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی برای KAMA نیست"}

    p = close.iloc[-1]
    p_prev = close.iloc[-2]
    k = kama.iloc[-1]
    k_prev = kama.iloc[-2]
    slope = k - k_prev
    dist_pct = (p - k) / k * 100

    if p_prev <= k_prev and p > k and slope > 0:
        return {"signal": "BUY", "confidence": 80,
                "reason_fa": f"قیمت بالای KAMA رفت + KAMA صعودی — سیگنال تطبیقی ({dist_pct:+.2f}%)"}
    elif p_prev >= k_prev and p < k and slope < 0:
        return {"signal": "SELL", "confidence": 80,
                "reason_fa": f"قیمت زیر KAMA رفت + KAMA نزولی — سیگنال تطبیقی ({dist_pct:+.2f}%)"}
    elif p > k and slope > 0:
        return {"signal": "BUY", "confidence": 52,
                "reason_fa": f"قیمت بالای KAMA صعودی ({dist_pct:+.2f}%)"}
    elif p < k and slope < 0:
        return {"signal": "SELL", "confidence": 52,
                "reason_fa": f"قیمت زیر KAMA نزولی ({dist_pct:+.2f}%)"}
    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"KAMA بدون سیگنال واضح ({dist_pct:+.2f}%)"}


# ═══════════════════════════════════════════════════════
# REGISTRY
# ═══════════════════════════════════════════════════════

MA_STRATEGIES = [
    {"id": "MA_01", "name": "SMA 20/50 Golden Cross", "name_fa": "تقاطع طلایی SMA 20/50", "func": ma_01_sma_20_50},
    {"id": "MA_02", "name": "SMA 50/200 Golden Cross", "name_fa": "تقاطع طلایی SMA 50/200", "func": ma_02_sma_50_200},
    {"id": "MA_03", "name": "EMA 9/21 Fast Cross", "name_fa": "تقاطع سریع EMA 9/21", "func": ma_03_ema_9_21},
    {"id": "MA_04", "name": "EMA 12/26 Classic Cross", "name_fa": "تقاطع کلاسیک EMA 12/26", "func": ma_04_ema_12_26},
    {"id": "MA_05", "name": "Triple EMA Alignment", "name_fa": "هم‌ترازی سه‌گانه EMA", "func": ma_05_triple_ema},
    {"id": "MA_06", "name": "Price vs SMA 200", "name_fa": "قیمت در برابر SMA 200", "func": ma_06_price_sma200},
    {"id": "MA_07", "name": "EMA Ribbon (5-line)", "name_fa": "ریبون EMA (۵ خط)", "func": ma_07_ema_ribbon},
    {"id": "MA_08", "name": "MA Envelope 2%", "name_fa": "پاکت میانگین متحرک ۲٪", "func": ma_08_envelope},
    {"id": "MA_09", "name": "DEMA(21) Direction", "name_fa": "جهت DEMA(21)", "func": ma_09_dema},
    {"id": "MA_10", "name": "Hull MA(20) Signal", "name_fa": "سیگنال Hull MA(20)", "func": ma_10_hull},
    {"id": "MA_11", "name": "VWMA vs SMA", "name_fa": "واگرایی VWMA/SMA", "func": ma_11_vwma},
    {"id": "MA_12", "name": "KAMA Adaptive", "name_fa": "میانگین تطبیقی KAMA", "func": ma_12_kama},
]
