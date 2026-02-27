"""
Whilber-AI — Divergence Strategy Pack (8 Sub-Strategies)
=========================================================
DIV_01: RSI Regular Divergence
DIV_02: RSI Hidden Divergence
DIV_03: MACD Regular Divergence
DIV_04: MACD Hidden Divergence
DIV_05: Stochastic Divergence
DIV_06: OBV Divergence (Price vs On-Balance Volume)
DIV_07: CCI Divergence
DIV_08: Multi-Indicator Divergence (2+ agree)
"""

import numpy as np
import pandas as pd


def _rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    return 100 - (100 / (1 + rs))


def _ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def _macd_hist(close):
    ema12 = _ema(close, 12)
    ema26 = _ema(close, 26)
    macd_line = ema12 - ema26
    signal = _ema(macd_line, 9)
    return macd_line - signal


def _stoch_k(df, period=14, smooth=3):
    high_roll = df['high'].rolling(period).max()
    low_roll = df['low'].rolling(period).min()
    k = 100 * (df['close'] - low_roll) / (high_roll - low_roll).replace(0, 1e-10)
    return k.rolling(smooth).mean()


def _cci(df, period=20):
    tp = (df['high'] + df['low'] + df['close']) / 3
    sma = tp.rolling(period).mean()
    mad = tp.rolling(period).apply(lambda x: np.mean(np.abs(x - x.mean())), raw=True)
    return (tp - sma) / (0.015 * mad).replace(0, 1e-10)


def _obv(df):
    obv = pd.Series(0.0, index=df.index)
    vol = df.get('tick_volume', df.get('volume', pd.Series(0, index=df.index)))
    for i in range(1, len(df)):
        if df['close'].iloc[i] > df['close'].iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] + vol.iloc[i]
        elif df['close'].iloc[i] < df['close'].iloc[i-1]:
            obv.iloc[i] = obv.iloc[i-1] - vol.iloc[i]
        else:
            obv.iloc[i] = obv.iloc[i-1]
    return obv


def _find_swing_points(series, lookback=20, n_points=2):
    """Find the last n swing highs and lows in the series."""
    arr = series.values
    length = len(arr)
    if length < lookback + 5:
        return [], []

    highs = []  # (index, value)
    lows = []

    order = 5
    for i in range(length - lookback, length - order):
        if i < order:
            continue
        is_high = all(arr[i] >= arr[i-j] for j in range(1, order+1)) and all(arr[i] >= arr[i+j] for j in range(1, order+1))
        is_low = all(arr[i] <= arr[i-j] for j in range(1, order+1)) and all(arr[i] <= arr[i+j] for j in range(1, order+1))
        if is_high:
            highs.append((i, arr[i]))
        if is_low:
            lows.append((i, arr[i]))

    return highs[-n_points:], lows[-n_points:]


def _check_divergence(price_series, indicator_series, lookback=40):
    """
    Check for regular and hidden divergences.
    Returns: (div_type, direction) or (None, None)
    div_type: 'regular' or 'hidden'
    direction: 'bullish' or 'bearish'
    """
    price_highs, price_lows = _find_swing_points(price_series, lookback)
    ind_highs, ind_lows = _find_swing_points(indicator_series, lookback)

    # Need at least 2 swing points
    if len(price_highs) < 2 or len(ind_highs) < 2:
        # Try with lows
        if len(price_lows) < 2 or len(ind_lows) < 2:
            return None, None

    # Regular Bullish: Price makes lower low, indicator makes higher low
    if len(price_lows) >= 2 and len(ind_lows) >= 2:
        pl1, pl2 = price_lows[-2][1], price_lows[-1][1]
        il1, il2 = ind_lows[-2][1], ind_lows[-1][1]
        if pl2 < pl1 and il2 > il1:
            return "regular", "bullish"

    # Regular Bearish: Price makes higher high, indicator makes lower high
    if len(price_highs) >= 2 and len(ind_highs) >= 2:
        ph1, ph2 = price_highs[-2][1], price_highs[-1][1]
        ih1, ih2 = ind_highs[-2][1], ind_highs[-1][1]
        if ph2 > ph1 and ih2 < ih1:
            return "regular", "bearish"

    # Hidden Bullish: Price makes higher low, indicator makes lower low
    if len(price_lows) >= 2 and len(ind_lows) >= 2:
        pl1, pl2 = price_lows[-2][1], price_lows[-1][1]
        il1, il2 = ind_lows[-2][1], ind_lows[-1][1]
        if pl2 > pl1 and il2 < il1:
            return "hidden", "bullish"

    # Hidden Bearish: Price makes lower high, indicator makes higher high
    if len(price_highs) >= 2 and len(ind_highs) >= 2:
        ph1, ph2 = price_highs[-2][1], price_highs[-1][1]
        ih1, ih2 = ind_highs[-2][1], ind_highs[-1][1]
        if ph2 < ph1 and ih2 > ih1:
            return "hidden", "bearish"

    return None, None


# ─────────────────────────────────────────────────────
# DIV_01: RSI Regular Divergence
# BUY:  Price lower low + RSI higher low (regular bullish)
# SELL: Price higher high + RSI lower high (regular bearish)
# ─────────────────────────────────────────────────────
def div_01_rsi_regular(df, context=None):
    close = df['close']
    rsi = _rsi(close, 14)
    if rsi.isna().sum() > len(rsi) * 0.5:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    div_type, direction = _check_divergence(close, rsi, 40)
    r = rsi.iloc[-1]

    if div_type == "regular" and direction == "bullish":
        conf = min(85, 65 + int((40 - r) * 0.5)) if r < 40 else 68
        return {"signal": "BUY", "confidence": conf,
                "reason_fa": f"واگرایی مثبت RSI — قیمت کف پایین‌تر ولی RSI({r:.1f}) کف بالاتر"}
    elif div_type == "regular" and direction == "bearish":
        conf = min(85, 65 + int((r - 60) * 0.5)) if r > 60 else 68
        return {"signal": "SELL", "confidence": conf,
                "reason_fa": f"واگرایی منفی RSI — قیمت سقف بالاتر ولی RSI({r:.1f}) سقف پایین‌تر"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"واگرایی معمولی RSI شناسایی نشد (RSI={r:.1f})"}


# ─────────────────────────────────────────────────────
# DIV_02: RSI Hidden Divergence
# BUY:  Price higher low + RSI lower low (hidden bullish = trend continuation)
# SELL: Price lower high + RSI higher high (hidden bearish)
# ─────────────────────────────────────────────────────
def div_02_rsi_hidden(df, context=None):
    close = df['close']
    rsi = _rsi(close, 14)
    if rsi.isna().sum() > len(rsi) * 0.5:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    div_type, direction = _check_divergence(close, rsi, 40)
    r = rsi.iloc[-1]

    if div_type == "hidden" and direction == "bullish":
        return {"signal": "BUY", "confidence": 72,
                "reason_fa": f"واگرایی مخفی مثبت RSI — ادامه روند صعودی (RSI={r:.1f})"}
    elif div_type == "hidden" and direction == "bearish":
        return {"signal": "SELL", "confidence": 72,
                "reason_fa": f"واگرایی مخفی منفی RSI — ادامه روند نزولی (RSI={r:.1f})"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"واگرایی مخفی RSI شناسایی نشد (RSI={r:.1f})"}


# ─────────────────────────────────────────────────────
# DIV_03: MACD Regular Divergence
# BUY:  Price lower low + MACD histogram higher low
# SELL: Price higher high + MACD histogram lower high
# ─────────────────────────────────────────────────────
def div_03_macd_regular(df, context=None):
    close = df['close']
    hist = _macd_hist(close)
    if hist.isna().sum() > len(hist) * 0.5:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    div_type, direction = _check_divergence(close, hist, 40)
    h = hist.iloc[-1]

    if div_type == "regular" and direction == "bullish":
        return {"signal": "BUY", "confidence": 78,
                "reason_fa": f"واگرایی مثبت MACD — قیمت کف پایین‌تر ولی هیستوگرام کف بالاتر ({h:.4f})"}
    elif div_type == "regular" and direction == "bearish":
        return {"signal": "SELL", "confidence": 78,
                "reason_fa": f"واگرایی منفی MACD — قیمت سقف بالاتر ولی هیستوگرام سقف پایین‌تر ({h:.4f})"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"واگرایی معمولی MACD شناسایی نشد (hist={h:.4f})"}


# ─────────────────────────────────────────────────────
# DIV_04: MACD Hidden Divergence
# BUY:  Price higher low + MACD hist lower low (hidden bullish)
# SELL: Price lower high + MACD hist higher high (hidden bearish)
# ─────────────────────────────────────────────────────
def div_04_macd_hidden(df, context=None):
    close = df['close']
    hist = _macd_hist(close)
    if hist.isna().sum() > len(hist) * 0.5:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    div_type, direction = _check_divergence(close, hist, 40)
    h = hist.iloc[-1]

    if div_type == "hidden" and direction == "bullish":
        return {"signal": "BUY", "confidence": 70,
                "reason_fa": f"واگرایی مخفی مثبت MACD — ادامه صعود ({h:.4f})"}
    elif div_type == "hidden" and direction == "bearish":
        return {"signal": "SELL", "confidence": 70,
                "reason_fa": f"واگرایی مخفی منفی MACD — ادامه نزول ({h:.4f})"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"واگرایی مخفی MACD شناسایی نشد (hist={h:.4f})"}


# ─────────────────────────────────────────────────────
# DIV_05: Stochastic Divergence
# BUY:  Price lower low + Stoch %K higher low
# SELL: Price higher high + Stoch %K lower high
# ─────────────────────────────────────────────────────
def div_05_stoch(df, context=None):
    close = df['close']
    stoch = _stoch_k(df, 14, 3)
    if stoch.isna().sum() > len(stoch) * 0.5:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    div_type, direction = _check_divergence(close, stoch, 40)
    k = stoch.iloc[-1]

    if div_type == "regular" and direction == "bullish":
        conf = min(82, 60 + int((30 - k) * 0.8)) if k < 30 else 68
        return {"signal": "BUY", "confidence": conf,
                "reason_fa": f"واگرایی مثبت استوکاستیک — قیمت کف پایین‌تر ولی %K({k:.1f}) کف بالاتر"}
    elif div_type == "regular" and direction == "bearish":
        conf = min(82, 60 + int((k - 70) * 0.8)) if k > 70 else 68
        return {"signal": "SELL", "confidence": conf,
                "reason_fa": f"واگرایی منفی استوکاستیک — قیمت سقف بالاتر ولی %K({k:.1f}) سقف پایین‌تر"}
    elif div_type == "hidden" and direction == "bullish":
        return {"signal": "BUY", "confidence": 65,
                "reason_fa": f"واگرایی مخفی مثبت استوکاستیک (%K={k:.1f})"}
    elif div_type == "hidden" and direction == "bearish":
        return {"signal": "SELL", "confidence": 65,
                "reason_fa": f"واگرایی مخفی منفی استوکاستیک (%K={k:.1f})"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"واگرایی استوکاستیک شناسایی نشد (%K={k:.1f})"}


# ─────────────────────────────────────────────────────
# DIV_06: OBV Divergence (On-Balance Volume)
# BUY:  Price lower low + OBV higher low (buying pressure)
# SELL: Price higher high + OBV lower high (selling pressure)
# ─────────────────────────────────────────────────────
def div_06_obv(df, context=None):
    close = df['close']
    vol = df.get('tick_volume', df.get('volume', None))
    if vol is None or vol.sum() == 0:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده حجم موجود نیست"}

    obv = _obv(df)
    div_type, direction = _check_divergence(close, obv, 40)

    if div_type == "regular" and direction == "bullish":
        return {"signal": "BUY", "confidence": 75,
                "reason_fa": "واگرایی مثبت OBV — قیمت کف پایین‌تر ولی حجم تجمعی بالاتر (فشار خرید پنهان)"}
    elif div_type == "regular" and direction == "bearish":
        return {"signal": "SELL", "confidence": 75,
                "reason_fa": "واگرایی منفی OBV — قیمت سقف بالاتر ولی حجم تجمعی پایین‌تر (فشار فروش پنهان)"}
    elif div_type == "hidden" and direction == "bullish":
        return {"signal": "BUY", "confidence": 62,
                "reason_fa": "واگرایی مخفی مثبت OBV — ادامه صعود با حمایت حجم"}
    elif div_type == "hidden" and direction == "bearish":
        return {"signal": "SELL", "confidence": 62,
                "reason_fa": "واگرایی مخفی منفی OBV — ادامه نزول با فشار حجم"}

    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "واگرایی OBV شناسایی نشد"}


# ─────────────────────────────────────────────────────
# DIV_07: CCI Divergence
# BUY:  Price lower low + CCI higher low
# SELL: Price higher high + CCI lower high
# ─────────────────────────────────────────────────────
def div_07_cci(df, context=None):
    close = df['close']
    cci = _cci(df, 20)
    if cci.isna().sum() > len(cci) * 0.5:
        return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": "داده کافی نیست"}

    div_type, direction = _check_divergence(close, cci, 40)
    c_val = cci.iloc[-1]

    if div_type == "regular" and direction == "bullish":
        conf = min(80, 60 + int(abs(c_val) * 0.1)) if c_val < -100 else 68
        return {"signal": "BUY", "confidence": conf,
                "reason_fa": f"واگرایی مثبت CCI — قیمت کف پایین‌تر ولی CCI({c_val:.0f}) کف بالاتر"}
    elif div_type == "regular" and direction == "bearish":
        conf = min(80, 60 + int(abs(c_val) * 0.1)) if c_val > 100 else 68
        return {"signal": "SELL", "confidence": conf,
                "reason_fa": f"واگرایی منفی CCI — قیمت سقف بالاتر ولی CCI({c_val:.0f}) سقف پایین‌تر"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"واگرایی CCI شناسایی نشد (CCI={c_val:.0f})"}


# ─────────────────────────────────────────────────────
# DIV_08: Multi-Indicator Divergence (2+ indicators agree)
# Checks RSI, MACD, Stoch — strong signal when 2+ agree
# ─────────────────────────────────────────────────────
def div_08_multi(df, context=None):
    close = df['close']

    # Check each indicator
    signals = {"bullish": 0, "bearish": 0}
    details = []

    # RSI
    rsi = _rsi(close, 14)
    if rsi.isna().sum() < len(rsi) * 0.5:
        dt, dd = _check_divergence(close, rsi, 40)
        if dt == "regular" and dd == "bullish":
            signals["bullish"] += 1; details.append("RSI+")
        elif dt == "regular" and dd == "bearish":
            signals["bearish"] += 1; details.append("RSI-")

    # MACD
    hist = _macd_hist(close)
    if hist.isna().sum() < len(hist) * 0.5:
        dt, dd = _check_divergence(close, hist, 40)
        if dt == "regular" and dd == "bullish":
            signals["bullish"] += 1; details.append("MACD+")
        elif dt == "regular" and dd == "bearish":
            signals["bearish"] += 1; details.append("MACD-")

    # Stochastic
    stoch = _stoch_k(df, 14, 3)
    if stoch.isna().sum() < len(stoch) * 0.5:
        dt, dd = _check_divergence(close, stoch, 40)
        if dt == "regular" and dd == "bullish":
            signals["bullish"] += 1; details.append("Stoch+")
        elif dt == "regular" and dd == "bearish":
            signals["bearish"] += 1; details.append("Stoch-")

    detail_str = " + ".join(details) if details else "هیچ"

    if signals["bullish"] >= 3:
        return {"signal": "BUY", "confidence": 90,
                "reason_fa": f"واگرایی مثبت سه‌گانه — {detail_str} — سیگنال بسیار قوی"}
    elif signals["bearish"] >= 3:
        return {"signal": "SELL", "confidence": 90,
                "reason_fa": f"واگرایی منفی سه‌گانه — {detail_str} — سیگنال بسیار قوی"}
    elif signals["bullish"] >= 2:
        return {"signal": "BUY", "confidence": 80,
                "reason_fa": f"واگرایی مثبت دوگانه — {detail_str}"}
    elif signals["bearish"] >= 2:
        return {"signal": "SELL", "confidence": 80,
                "reason_fa": f"واگرایی منفی دوگانه — {detail_str}"}
    elif signals["bullish"] == 1:
        return {"signal": "BUY", "confidence": 55,
                "reason_fa": f"واگرایی مثبت تکی — {detail_str}"}
    elif signals["bearish"] == 1:
        return {"signal": "SELL", "confidence": 55,
                "reason_fa": f"واگرایی منفی تکی — {detail_str}"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "واگرایی چندگانه شناسایی نشد"}


# ═══════════════════════════════════════════════════════
# REGISTRY
# ═══════════════════════════════════════════════════════

DIV_STRATEGIES = [
    {"id": "DIV_01", "name": "RSI Regular Divergence", "name_fa": "واگرایی معمولی RSI", "func": div_01_rsi_regular},
    {"id": "DIV_02", "name": "RSI Hidden Divergence", "name_fa": "واگرایی مخفی RSI", "func": div_02_rsi_hidden},
    {"id": "DIV_03", "name": "MACD Regular Divergence", "name_fa": "واگرایی معمولی MACD", "func": div_03_macd_regular},
    {"id": "DIV_04", "name": "MACD Hidden Divergence", "name_fa": "واگرایی مخفی MACD", "func": div_04_macd_hidden},
    {"id": "DIV_05", "name": "Stochastic Divergence", "name_fa": "واگرایی استوکاستیک", "func": div_05_stoch},
    {"id": "DIV_06", "name": "OBV Divergence", "name_fa": "واگرایی حجم تجمعی", "func": div_06_obv},
    {"id": "DIV_07", "name": "CCI Divergence", "name_fa": "واگرایی CCI", "func": div_07_cci},
    {"id": "DIV_08", "name": "Multi-Indicator Divergence", "name_fa": "واگرایی چندگانه", "func": div_08_multi},
]
