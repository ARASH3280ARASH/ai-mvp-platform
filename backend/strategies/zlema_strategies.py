"""
Whilber-AI — Zero-Lag EMA Strategy Pack (5 Sub-Strategies)
=============================================================
ZLEMA_01: ZLEMA Cross (price crosses ZLEMA)
ZLEMA_02: ZLEMA Dual Cross (fast vs slow ZLEMA)
ZLEMA_03: Zero-Lag MACD
ZLEMA_04: ZLEMA + BB Squeeze
ZLEMA_05: ZLEMA Momentum (slope acceleration)
"""

import numpy as np

CATEGORY_ID = "ZLEMA"
CATEGORY_NAME = "Zero-Lag EMA"
CATEGORY_FA = "میانگین بدون تاخیر"
ICON = "⚡"
COLOR = "#ff9800"


def _zlema(data, period):
    """Zero-Lag EMA: uses error correction to reduce lag."""
    n = len(data)
    if n < period: return None
    lag = (period - 1) // 2
    corrected = np.zeros(n)
    for i in range(lag, n):
        corrected[i] = 2 * data[i] - data[i - lag]
    # Apply EMA to corrected data
    e = np.zeros(n)
    e[period - 1] = np.mean(corrected[:period])
    m = 2 / (period + 1)
    for i in range(period, n):
        e[i] = corrected[i] * m + e[i - 1] * (1 - m)
    return e


def _ema(data, period):
    if len(data) < period: return None
    e = np.zeros(len(data))
    e[period - 1] = np.mean(data[:period])
    m = 2 / (period + 1)
    for i in range(period, len(data)):
        e[i] = data[i] * m + e[i - 1] * (1 - m)
    return e


def _sma(data, period):
    if len(data) < period: return None
    r = np.zeros(len(data))
    for i in range(period - 1, len(data)):
        r[i] = np.mean(data[i - period + 1:i + 1])
    return r


def _atr(high, low, close, period=14):
    if len(high) < period + 1: return None
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


def zlema_01(df, indicators, symbol, timeframe):
    """ZLEMA Cross: price crosses zero-lag EMA."""
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(c) < 25: return _neutral("داده کافی نیست")
    zl = _zlema(c, 21)
    if zl is None: return _neutral("محاسبه ZLEMA ناموفق")
    atr_v = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]

    if c[-1] > zl[-1] and c[-2] <= zl[-2]:
        setup = _make_setup("BUY", price, atr_v[-1] if atr_v is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 73, "reason_fa": "قیمت از ZLEMA-21 عبور کرد — صعودی", "setup": setup}

    if c[-1] < zl[-1] and c[-2] >= zl[-2]:
        setup = _make_setup("SELL", price, atr_v[-1] if atr_v is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 73, "reason_fa": "قیمت از ZLEMA-21 عبور کرد — نزولی", "setup": setup}

    return _neutral("عبور ZLEMA شناسایی نشد")


def zlema_02(df, indicators, symbol, timeframe):
    """ZLEMA Dual Cross: fast ZLEMA(10) vs slow ZLEMA(30)."""
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(c) < 35: return _neutral("داده کافی نیست")
    zl_fast = _zlema(c, 10)
    zl_slow = _zlema(c, 30)
    if zl_fast is None or zl_slow is None: return _neutral("محاسبه ZLEMA ناموفق")
    atr_v = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]

    if zl_fast[-1] > zl_slow[-1] and zl_fast[-2] <= zl_slow[-2]:
        setup = _make_setup("BUY", price, atr_v[-1] if atr_v is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 76, "reason_fa": "ZLEMA سریع از ZLEMA کند عبور کرد — صعودی", "setup": setup}

    if zl_fast[-1] < zl_slow[-1] and zl_fast[-2] >= zl_slow[-2]:
        setup = _make_setup("SELL", price, atr_v[-1] if atr_v is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 76, "reason_fa": "ZLEMA سریع از ZLEMA کند عبور کرد — نزولی", "setup": setup}

    return _neutral("عبور دوگانه ZLEMA شناسایی نشد")


def zlema_03(df, indicators, symbol, timeframe):
    """Zero-Lag MACD."""
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(c) < 35: return _neutral("داده کافی نیست")
    zl_fast = _zlema(c, 12)
    zl_slow = _zlema(c, 26)
    if zl_fast is None or zl_slow is None: return _neutral("محاسبه ناموفق")
    macd_line = zl_fast - zl_slow
    signal = _ema(macd_line, 9)
    if signal is None: return _neutral("محاسبه سیگنال ناموفق")
    atr_v = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]
    hist = macd_line - signal

    if macd_line[-1] > signal[-1] and macd_line[-2] <= signal[-2]:
        setup = _make_setup("BUY", price, atr_v[-1] if atr_v is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 77, "reason_fa": "Zero-Lag MACD عبور سیگنال صعودی", "setup": setup}

    if macd_line[-1] < signal[-1] and macd_line[-2] >= signal[-2]:
        setup = _make_setup("SELL", price, atr_v[-1] if atr_v is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 77, "reason_fa": "Zero-Lag MACD عبور سیگنال نزولی", "setup": setup}

    return _neutral("Zero-Lag MACD سیگنال ندارد")


def zlema_04(df, indicators, symbol, timeframe):
    """ZLEMA + BB Squeeze: ZLEMA direction after BB squeeze."""
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(c) < 30: return _neutral("داده کافی نیست")
    zl = _zlema(c, 21)
    if zl is None: return _neutral("محاسبه ZLEMA ناموفق")

    # Bollinger Band width
    sma20 = _sma(c, 20)
    if sma20 is None: return _neutral("محاسبه BB ناموفق")
    n = len(c)
    bb_std = np.zeros(n)
    for i in range(19, n):
        bb_std[i] = np.std(c[i - 19:i + 1])
    bb_width = np.where(sma20 > 0, (4 * bb_std) / sma20, 0)

    atr_v = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]

    # Narrow BB (squeeze) + ZLEMA direction
    avg_width = np.mean(bb_width[-50:-1]) if len(bb_width) > 50 else np.mean(bb_width[20:])
    if bb_width[-1] < avg_width * 0.7 or (bb_width[-2] < avg_width * 0.7 and bb_width[-1] > bb_width[-2]):
        if c[-1] > zl[-1] and zl[-1] > zl[-2]:
            setup = _make_setup("BUY", price, atr_v[-1] if atr_v is not None else None, pip)
            if setup:
                return {"signal": "BUY", "confidence": 79, "reason_fa": "BB فشرده + ZLEMA صعودی — شکست احتمالی", "setup": setup}

        if c[-1] < zl[-1] and zl[-1] < zl[-2]:
            setup = _make_setup("SELL", price, atr_v[-1] if atr_v is not None else None, pip)
            if setup:
                return {"signal": "SELL", "confidence": 79, "reason_fa": "BB فشرده + ZLEMA نزولی — شکست احتمالی", "setup": setup}

    return _neutral("ZLEMA + BB Squeeze شناسایی نشد")


def zlema_05(df, indicators, symbol, timeframe):
    """ZLEMA Momentum: slope acceleration (2nd derivative)."""
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(c) < 25: return _neutral("داده کافی نیست")
    zl = _zlema(c, 21)
    if zl is None: return _neutral("محاسبه ZLEMA ناموفق")
    atr_v = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]

    # First derivative (slope)
    slope1 = zl[-1] - zl[-2]
    slope2 = zl[-2] - zl[-3]
    slope3 = zl[-3] - zl[-4]

    # Acceleration: slope increasing
    if slope1 > slope2 > slope3 and slope1 > 0:
        setup = _make_setup("BUY", price, atr_v[-1] if atr_v is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 74, "reason_fa": "ZLEMA شتاب صعودی — شیب افزایشی", "setup": setup}

    if slope1 < slope2 < slope3 and slope1 < 0:
        setup = _make_setup("SELL", price, atr_v[-1] if atr_v is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 74, "reason_fa": "ZLEMA شتاب نزولی — شیب کاهشی", "setup": setup}

    return _neutral("شتاب ZLEMA شناسایی نشد")


ZLEMA_STRATEGIES = [
    {"id": "ZLEMA_01", "name": "ZLEMA Cross", "name_fa": "عبور ZLEMA", "func": zlema_01},
    {"id": "ZLEMA_02", "name": "ZLEMA Dual Cross", "name_fa": "عبور دوگانه ZLEMA", "func": zlema_02},
    {"id": "ZLEMA_03", "name": "Zero-Lag MACD", "name_fa": "MACD بدون تاخیر", "func": zlema_03},
    {"id": "ZLEMA_04", "name": "ZLEMA + BB Squeeze", "name_fa": "ZLEMA + فشردگی BB", "func": zlema_04},
    {"id": "ZLEMA_05", "name": "ZLEMA Momentum", "name_fa": "مومنتوم ZLEMA", "func": zlema_05},
]
