"""
Whilber-AI — True Strength Index Strategy Pack (5 Sub-Strategies)
==================================================================
TSI_01: TSI Zero-Line Cross
TSI_02: TSI Signal-Line Cross
TSI_03: TSI Overbought/Oversold Reversal
TSI_04: TSI + ADX Trend Filter
TSI_05: TSI Divergence
"""

import numpy as np

CATEGORY_ID = "TSI"
CATEGORY_NAME = "True Strength Index"
CATEGORY_FA = "شاخص قدرت واقعی"
ICON = "💪"
COLOR = "#00bcd4"


def _ema(data, period):
    if len(data) < period:
        return None
    e = np.zeros(len(data))
    e[period - 1] = np.mean(data[:period])
    m = 2 / (period + 1)
    for i in range(period, len(data)):
        e[i] = data[i] * m + e[i - 1] * (1 - m)
    return e


def _tsi(close, long_p=25, short_p=13, signal_p=7):
    if len(close) < long_p + short_p + signal_p:
        return None, None
    diff = np.diff(close)
    diff = np.concatenate([[0], diff])
    ds1 = _ema(diff, long_p)
    if ds1 is None:
        return None, None
    ds2 = _ema(ds1, short_p)
    abs_diff = np.abs(diff)
    ads1 = _ema(abs_diff, long_p)
    if ads1 is None:
        return None, None
    ads2 = _ema(ads1, short_p)
    tsi_line = np.where(ads2 != 0, ds2 / ads2 * 100, 0)
    sig = _ema(tsi_line, signal_p)
    return tsi_line, sig


def _adx(high, low, close, period=14):
    if len(high) < period * 2:
        return None
    n = len(high)
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)
    tr = np.zeros(n)
    for i in range(1, n):
        up = high[i] - high[i - 1]
        down = low[i - 1] - low[i]
        plus_dm[i] = up if up > down and up > 0 else 0
        minus_dm[i] = down if down > up and down > 0 else 0
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
    atr = np.zeros(n)
    s_pdm = np.zeros(n)
    s_mdm = np.zeros(n)
    atr[period] = np.mean(tr[1:period + 1])
    s_pdm[period] = np.mean(plus_dm[1:period + 1])
    s_mdm[period] = np.mean(minus_dm[1:period + 1])
    for i in range(period + 1, n):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
        s_pdm[i] = (s_pdm[i - 1] * (period - 1) + plus_dm[i]) / period
        s_mdm[i] = (s_mdm[i - 1] * (period - 1) + minus_dm[i]) / period
    plus_di = np.where(atr > 0, s_pdm / atr * 100, 0)
    minus_di = np.where(atr > 0, s_mdm / atr * 100, 0)
    dx = np.where((plus_di + minus_di) > 0, abs(plus_di - minus_di) / (plus_di + minus_di) * 100, 0)
    adx = np.zeros(n)
    start = period * 2
    if start < n:
        adx[start] = np.mean(dx[period + 1:start + 1])
        for i in range(start + 1, n):
            adx[i] = (adx[i - 1] * (period - 1) + dx[i]) / period
    return adx


def _atr(high, low, close, period=14):
    if len(high) < period + 1:
        return None
    tr = np.maximum(high[1:] - low[1:], np.maximum(abs(high[1:] - close[:-1]), abs(low[1:] - close[:-1])))
    atr = np.zeros(len(tr))
    atr[period - 1] = np.mean(tr[:period])
    for i in range(period, len(tr)):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return np.concatenate([[0], atr])


def _pip_size(symbol):
    s = symbol.upper()
    if "JPY" in s: return 0.01
    if "XAU" in s: return 0.1
    if "XAG" in s: return 0.01
    if "BTC" in s: return 1.0
    if s in ("NAS100", "US30", "SPX500", "GER40", "UK100"): return 1.0
    return 0.0001


def _make_setup(direction, entry, atr_val, pip, rr_min=1.5):
    if atr_val is None or atr_val <= 0: return None
    sl_dist = atr_val * 1.5
    tp1_dist = sl_dist * rr_min
    tp2_dist = sl_dist * 3.0
    if direction == "BUY":
        sl, tp1, tp2 = entry - sl_dist, entry + tp1_dist, entry + tp2_dist
    else:
        sl, tp1, tp2 = entry + sl_dist, entry - tp1_dist, entry - tp2_dist
    return {"has_setup": True, "direction": direction,
            "direction_fa": "خرید" if direction == "BUY" else "فروش",
            "entry": round(entry, 6), "stop_loss": round(sl, 6),
            "tp1": round(tp1, 6), "tp2": round(tp2, 6),
            "rr1": round(tp1_dist / sl_dist, 2), "rr2": round(tp2_dist / sl_dist, 2),
            "sl_pips": round(sl_dist / pip, 1) if pip > 0 else 0,
            "tp1_pips": round(tp1_dist / pip, 1) if pip > 0 else 0}


def _neutral(r):
    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": r, "setup": {"has_setup": False}}


def tsi_01(df, indicators, symbol, timeframe):
    """TSI Zero-Line Cross."""
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(c) < 50: return _neutral("داده کافی نیست")
    tsi_line, sig = _tsi(c)
    if tsi_line is None: return _neutral("محاسبه TSI ناموفق")
    atr_v = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]

    if tsi_line[-1] > 0 and tsi_line[-2] <= 0:
        setup = _make_setup("BUY", price, atr_v[-1] if atr_v is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 72, "reason_fa": f"TSI عبور از خط صفر به بالا ({tsi_line[-1]:.1f})", "setup": setup}

    if tsi_line[-1] < 0 and tsi_line[-2] >= 0:
        setup = _make_setup("SELL", price, atr_v[-1] if atr_v is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 72, "reason_fa": f"TSI عبور از خط صفر به پایین ({tsi_line[-1]:.1f})", "setup": setup}

    return _neutral("عبور TSI از خط صفر شناسایی نشد")


def tsi_02(df, indicators, symbol, timeframe):
    """TSI Signal-Line Cross."""
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(c) < 50: return _neutral("داده کافی نیست")
    tsi_line, sig = _tsi(c)
    if tsi_line is None or sig is None: return _neutral("محاسبه TSI ناموفق")
    atr_v = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]

    if tsi_line[-1] > sig[-1] and tsi_line[-2] <= sig[-2]:
        setup = _make_setup("BUY", price, atr_v[-1] if atr_v is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 74, "reason_fa": "TSI عبور سیگنال صعودی", "setup": setup}

    if tsi_line[-1] < sig[-1] and tsi_line[-2] >= sig[-2]:
        setup = _make_setup("SELL", price, atr_v[-1] if atr_v is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 74, "reason_fa": "TSI عبور سیگنال نزولی", "setup": setup}

    return _neutral("عبور سیگنال TSI شناسایی نشد")


def tsi_03(df, indicators, symbol, timeframe):
    """TSI Overbought/Oversold Reversal."""
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(c) < 50: return _neutral("داده کافی نیست")
    tsi_line, sig = _tsi(c)
    if tsi_line is None: return _neutral("محاسبه TSI ناموفق")
    atr_v = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]

    if tsi_line[-2] < -25 and tsi_line[-1] > tsi_line[-2]:
        setup = _make_setup("BUY", price, atr_v[-1] if atr_v is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 70, "reason_fa": f"TSI برگشت از اشباع فروش ({tsi_line[-1]:.1f})", "setup": setup}

    if tsi_line[-2] > 25 and tsi_line[-1] < tsi_line[-2]:
        setup = _make_setup("SELL", price, atr_v[-1] if atr_v is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 70, "reason_fa": f"TSI برگشت از اشباع خرید ({tsi_line[-1]:.1f})", "setup": setup}

    return _neutral("TSI در ناحیه اشباع نیست")


def tsi_04(df, indicators, symbol, timeframe):
    """TSI + ADX Trend Filter."""
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(c) < 50: return _neutral("داده کافی نیست")
    tsi_line, sig = _tsi(c)
    adx_v = _adx(h, l, c)
    if tsi_line is None or adx_v is None: return _neutral("محاسبه ناموفق")
    atr_v = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]

    if tsi_line[-1] > sig[-1] and tsi_line[-2] <= sig[-2] and adx_v[-1] > 25:
        setup = _make_setup("BUY", price, atr_v[-1] if atr_v is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 80, "reason_fa": f"TSI صعودی + ADX={adx_v[-1]:.0f} — روند قوی", "setup": setup}

    if tsi_line[-1] < sig[-1] and tsi_line[-2] >= sig[-2] and adx_v[-1] > 25:
        setup = _make_setup("SELL", price, atr_v[-1] if atr_v is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 80, "reason_fa": f"TSI نزولی + ADX={adx_v[-1]:.0f} — روند قوی", "setup": setup}

    return _neutral("TSI + ADX شناسایی نشد")


def tsi_05(df, indicators, symbol, timeframe):
    """TSI Divergence."""
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(c) < 60: return _neutral("داده کافی نیست")
    tsi_line, sig = _tsi(c)
    if tsi_line is None: return _neutral("محاسبه TSI ناموفق")
    atr_v = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]
    lookback = 20

    # Bullish divergence: price lower low, TSI higher low
    price_min1 = np.min(c[-lookback * 2:-lookback])
    price_min2 = np.min(c[-lookback:])
    tsi_min1 = np.min(tsi_line[-lookback * 2:-lookback])
    tsi_min2 = np.min(tsi_line[-lookback:])

    if price_min2 < price_min1 and tsi_min2 > tsi_min1:
        setup = _make_setup("BUY", price, atr_v[-1] if atr_v is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 76, "reason_fa": "واگرایی صعودی TSI — قیمت کف پایین‌تر، TSI کف بالاتر", "setup": setup}

    # Bearish divergence
    price_max1 = np.max(c[-lookback * 2:-lookback])
    price_max2 = np.max(c[-lookback:])
    tsi_max1 = np.max(tsi_line[-lookback * 2:-lookback])
    tsi_max2 = np.max(tsi_line[-lookback:])

    if price_max2 > price_max1 and tsi_max2 < tsi_max1:
        setup = _make_setup("SELL", price, atr_v[-1] if atr_v is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 76, "reason_fa": "واگرایی نزولی TSI — قیمت سقف بالاتر، TSI سقف پایین‌تر", "setup": setup}

    return _neutral("واگرایی TSI شناسایی نشد")


TSI_STRATEGIES = [
    {"id": "TSI_01", "name": "TSI Zero Cross", "name_fa": "عبور صفر TSI", "func": tsi_01},
    {"id": "TSI_02", "name": "TSI Signal Cross", "name_fa": "عبور سیگنال TSI", "func": tsi_02},
    {"id": "TSI_03", "name": "TSI OB/OS Reversal", "name_fa": "برگشت اشباع TSI", "func": tsi_03},
    {"id": "TSI_04", "name": "TSI + ADX Filter", "name_fa": "TSI + فیلتر ADX", "func": tsi_04},
    {"id": "TSI_05", "name": "TSI Divergence", "name_fa": "واگرایی TSI", "func": tsi_05},
]
