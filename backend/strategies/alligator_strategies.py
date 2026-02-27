"""
Whilber-AI — Williams Alligator Strategy Pack (5 Sub-Strategies)
==================================================================
ALLI_01: Alligator Awake (all 3 lines fan out)
ALLI_02: Alligator + Awesome Oscillator
ALLI_03: Alligator Mouth Open (lines diverge → strong trend)
ALLI_04: Alligator Sleep Detection (convergence → wait for breakout)
ALLI_05: Alligator + Accelerator Oscillator
"""

import numpy as np

CATEGORY_ID = "ALLI"
CATEGORY_NAME = "Williams Alligator"
CATEGORY_FA = "تمساح ویلیامز"
ICON = "🐊"
COLOR = "#4caf50"


def _smma(data, period, offset=0):
    """Smoothed Moving Average (Bill Williams method)."""
    if len(data) < period + offset: return None
    n = len(data)
    result = np.zeros(n)
    result[period - 1] = np.mean(data[:period])
    for i in range(period, n):
        result[i] = (result[i - 1] * (period - 1) + data[i]) / period
    if offset > 0:
        shifted = np.zeros(n)
        shifted[offset:] = result[:-offset] if offset < n else 0
        return shifted
    return result


def _alligator(high, low):
    """Williams Alligator: Jaw(13,8), Teeth(8,5), Lips(5,3)."""
    midpoint = (high + low) / 2.0
    jaw = _smma(midpoint, 13, 8)
    teeth = _smma(midpoint, 8, 5)
    lips = _smma(midpoint, 5, 3)
    return jaw, teeth, lips


def _ao(high, low):
    """Awesome Oscillator = SMA(midpoint, 5) - SMA(midpoint, 34)."""
    midpoint = (high + low) / 2.0
    n = len(midpoint)
    if n < 34: return None
    sma5 = np.zeros(n)
    sma34 = np.zeros(n)
    for i in range(4, n):
        sma5[i] = np.mean(midpoint[i - 4:i + 1])
    for i in range(33, n):
        sma34[i] = np.mean(midpoint[i - 33:i + 1])
    ao = sma5 - sma34
    return ao


def _ac(high, low):
    """Accelerator Oscillator = AO - SMA(AO, 5)."""
    ao = _ao(high, low)
    if ao is None: return None
    n = len(ao)
    sma5_ao = np.zeros(n)
    for i in range(4, n):
        sma5_ao[i] = np.mean(ao[i - 4:i + 1])
    return ao - sma5_ao


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


def alli_01(df, indicators, symbol, timeframe):
    """Alligator Awake: all 3 lines fan out in order."""
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(c) < 40: return _neutral("داده کافی نیست")
    jaw, teeth, lips = _alligator(h, l)
    if jaw is None or teeth is None or lips is None: return _neutral("محاسبه Alligator ناموفق")
    atr_v = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]

    # Bullish: Lips > Teeth > Jaw (and just formed)
    if lips[-1] > teeth[-1] > jaw[-1]:
        was_sleeping = abs(lips[-5] - teeth[-5]) < abs(lips[-1] - teeth[-1]) * 0.3 if len(c) > 5 else False
        if was_sleeping or (lips[-2] <= teeth[-2]):
            setup = _make_setup("BUY", price, atr_v[-1] if atr_v is not None else None, pip)
            if setup:
                return {"signal": "BUY", "confidence": 76, "reason_fa": "تمساح بیدار شد — Lips > Teeth > Jaw صعودی", "setup": setup}

    # Bearish: Jaw > Teeth > Lips
    if jaw[-1] > teeth[-1] > lips[-1]:
        was_sleeping = abs(lips[-5] - teeth[-5]) < abs(lips[-1] - teeth[-1]) * 0.3 if len(c) > 5 else False
        if was_sleeping or (lips[-2] >= teeth[-2]):
            setup = _make_setup("SELL", price, atr_v[-1] if atr_v is not None else None, pip)
            if setup:
                return {"signal": "SELL", "confidence": 76, "reason_fa": "تمساح بیدار شد — Jaw > Teeth > Lips نزولی", "setup": setup}

    return _neutral("تمساح در حال خواب")


def alli_02(df, indicators, symbol, timeframe):
    """Alligator + Awesome Oscillator."""
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(c) < 40: return _neutral("داده کافی نیست")
    jaw, teeth, lips = _alligator(h, l)
    ao = _ao(h, l)
    if jaw is None or ao is None: return _neutral("محاسبه ناموفق")
    atr_v = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]

    if lips[-1] > teeth[-1] > jaw[-1] and ao[-1] > 0 and ao[-1] > ao[-2]:
        setup = _make_setup("BUY", price, atr_v[-1] if atr_v is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 80, "reason_fa": "تمساح صعودی + AO مثبت و افزایشی", "setup": setup}

    if jaw[-1] > teeth[-1] > lips[-1] and ao[-1] < 0 and ao[-1] < ao[-2]:
        setup = _make_setup("SELL", price, atr_v[-1] if atr_v is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 80, "reason_fa": "تمساح نزولی + AO منفی و کاهشی", "setup": setup}

    return _neutral("تمساح + AO شناسایی نشد")


def alli_03(df, indicators, symbol, timeframe):
    """Alligator Mouth Open: lines diverge strongly."""
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(c) < 40: return _neutral("داده کافی نیست")
    jaw, teeth, lips = _alligator(h, l)
    if jaw is None: return _neutral("محاسبه ناموفق")
    atr_v = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]

    spread_now = abs(lips[-1] - jaw[-1])
    spread_prev = abs(lips[-5] - jaw[-5]) if len(c) > 5 else 0

    if spread_now > spread_prev * 2 and spread_now > 0:
        if lips[-1] > jaw[-1]:
            setup = _make_setup("BUY", price, atr_v[-1] if atr_v is not None else None, pip)
            if setup:
                return {"signal": "BUY", "confidence": 77, "reason_fa": "دهان تمساح باز — واگرایی خطوط صعودی", "setup": setup}
        else:
            setup = _make_setup("SELL", price, atr_v[-1] if atr_v is not None else None, pip)
            if setup:
                return {"signal": "SELL", "confidence": 77, "reason_fa": "دهان تمساح باز — واگرایی خطوط نزولی", "setup": setup}

    return _neutral("دهان تمساح باز نیست")


def alli_04(df, indicators, symbol, timeframe):
    """Alligator Sleep Detection: convergence → breakout entry."""
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(c) < 40: return _neutral("داده کافی نیست")
    jaw, teeth, lips = _alligator(h, l)
    if jaw is None: return _neutral("محاسبه ناموفق")
    atr_v = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]

    # Was sleeping (lines close together), now waking up
    avg_price = (h[-1] + l[-1]) / 2.0
    threshold = avg_price * 0.002

    was_sleeping = abs(lips[-3] - jaw[-3]) < threshold and abs(teeth[-3] - jaw[-3]) < threshold
    now_awake = abs(lips[-1] - jaw[-1]) > threshold * 2

    if was_sleeping and now_awake:
        if price > lips[-1] and price > teeth[-1] and price > jaw[-1]:
            setup = _make_setup("BUY", price, atr_v[-1] if atr_v is not None else None, pip)
            if setup:
                return {"signal": "BUY", "confidence": 75, "reason_fa": "تمساح از خواب بیدار شد — شکست صعودی", "setup": setup}
        elif price < lips[-1] and price < teeth[-1] and price < jaw[-1]:
            setup = _make_setup("SELL", price, atr_v[-1] if atr_v is not None else None, pip)
            if setup:
                return {"signal": "SELL", "confidence": 75, "reason_fa": "تمساح از خواب بیدار شد — شکست نزولی", "setup": setup}

    return _neutral("تمساح هنوز خواب است")


def alli_05(df, indicators, symbol, timeframe):
    """Alligator + Accelerator Oscillator."""
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(c) < 40: return _neutral("داده کافی نیست")
    jaw, teeth, lips = _alligator(h, l)
    ac = _ac(h, l)
    if jaw is None or ac is None: return _neutral("محاسبه ناموفق")
    atr_v = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]

    if lips[-1] > teeth[-1] > jaw[-1] and ac[-1] > 0 and ac[-1] > ac[-2]:
        setup = _make_setup("BUY", price, atr_v[-1] if atr_v is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 79, "reason_fa": "تمساح صعودی + AC شتاب مثبت", "setup": setup}

    if jaw[-1] > teeth[-1] > lips[-1] and ac[-1] < 0 and ac[-1] < ac[-2]:
        setup = _make_setup("SELL", price, atr_v[-1] if atr_v is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 79, "reason_fa": "تمساح نزولی + AC شتاب منفی", "setup": setup}

    return _neutral("تمساح + AC شناسایی نشد")


ALLI_STRATEGIES = [
    {"id": "ALLI_01", "name": "Alligator Awake", "name_fa": "بیداری تمساح", "func": alli_01},
    {"id": "ALLI_02", "name": "Alligator + AO", "name_fa": "تمساح + AO", "func": alli_02},
    {"id": "ALLI_03", "name": "Alligator Mouth", "name_fa": "دهان تمساح", "func": alli_03},
    {"id": "ALLI_04", "name": "Alligator Sleep", "name_fa": "خواب تمساح", "func": alli_04},
    {"id": "ALLI_05", "name": "Alligator + AC", "name_fa": "تمساح + AC", "func": alli_05},
]
