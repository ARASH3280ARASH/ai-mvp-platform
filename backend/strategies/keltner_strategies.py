"""
Whilber-AI — Keltner Channel Strategy Pack (5 Sub-Strategies)
===============================================================
KC_01: Keltner Bounce (price touches band → reversal)
KC_02: Keltner Breakout (price closes outside band)
KC_03: Keltner + BB Squeeze (Keltner inside BB → explosion)
KC_04: Keltner Trend Walk (price stays above/below middle)
KC_05: Keltner Width Expansion (channel widening → trend)
"""

import numpy as np

CATEGORY_ID = "KC"
CATEGORY_NAME = "Keltner Channel"
CATEGORY_FA = "کانال کلتنر"
ICON = "📈"
COLOR = "#ff9800"


def _ema(data, period):
    if len(data) < period:
        return None
    e = np.zeros(len(data))
    e[period-1] = np.mean(data[:period])
    m = 2 / (period + 1)
    for i in range(period, len(data)):
        e[i] = data[i] * m + e[i-1] * (1 - m)
    return e


def _atr(high, low, close, period=14):
    if len(high) < period + 1:
        return None
    tr = np.maximum(high[1:] - low[1:],
         np.maximum(abs(high[1:] - close[:-1]), abs(low[1:] - close[:-1])))
    atr = np.zeros(len(tr))
    atr[period-1] = np.mean(tr[:period])
    for i in range(period, len(tr)):
        atr[i] = (atr[i-1] * (period-1) + tr[i]) / period
    return np.concatenate([[0], atr])


def _keltner(high, low, close, ema_period=20, atr_period=10, multiplier=2.0):
    ema = _ema(close, ema_period)
    atr = _atr(high, low, close, atr_period)
    if ema is None or atr is None:
        return None, None, None
    upper = ema + multiplier * atr
    lower = ema - multiplier * atr
    return upper, lower, ema


def _bb(close, period=20, std_mult=2.0):
    if len(close) < period:
        return None, None, None
    sma = np.array([np.mean(close[max(0,i-period+1):i+1]) for i in range(len(close))])
    std = np.array([np.std(close[max(0,i-period+1):i+1]) for i in range(len(close))])
    upper = sma + std_mult * std
    lower = sma - std_mult * std
    return upper, lower, sma


def _pip_size(symbol):
    s = symbol.upper()
    if "JPY" in s: return 0.01
    if "XAU" in s: return 0.1
    if "XAG" in s: return 0.01
    if "BTC" in s: return 1.0
    if s in ("NAS100","US30","SPX500","GER40","UK100"): return 1.0
    return 0.0001


def _make_setup(direction, entry, atr_val, pip, rr_min=1.5):
    if atr_val is None or atr_val <= 0:
        return None
    sl_dist = atr_val * 1.5
    tp1_dist = sl_dist * rr_min
    tp2_dist = sl_dist * 3.0
    if direction == "BUY":
        sl, tp1, tp2 = entry - sl_dist, entry + tp1_dist, entry + tp2_dist
    else:
        sl, tp1, tp2 = entry + sl_dist, entry - tp1_dist, entry - tp2_dist
    rr1 = tp1_dist / sl_dist if sl_dist > 0 else 0
    if rr1 < rr_min:
        return None
    return {"has_setup": True, "direction": direction,
            "direction_fa": "خرید" if direction == "BUY" else "فروش",
            "entry": round(entry, 6), "stop_loss": round(sl, 6),
            "tp1": round(tp1, 6), "tp2": round(tp2, 6),
            "rr1": round(rr1, 2), "rr2": round(tp2_dist/sl_dist, 2),
            "sl_pips": round(sl_dist/pip, 1) if pip > 0 else 0,
            "tp1_pips": round(tp1_dist/pip, 1) if pip > 0 else 0}


def _neutral(reason_fa):
    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": reason_fa,
            "setup": {"has_setup": False}}


def kc_01(df, indicators, symbol, timeframe):
    """Keltner Bounce — reversal at bands."""
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(c) < 25:
        return _neutral("داده کافی نیست")
    upper, lower, mid = _keltner(h, l, c)
    atr = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]

    if upper is None:
        return _neutral("محاسبه کلتنر ناموفق")

    # Touch lower band + bounce
    if price <= lower[-1] * 1.002 and c[-2] < c[-1]:
        setup = _make_setup("BUY", price, atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 65,
                    "reason_fa": f"برگشت از کف کانال کلتنر — بانس صعودی",
                    "setup": setup}

    if price >= upper[-1] * 0.998 and c[-2] > c[-1]:
        setup = _make_setup("SELL", price, atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 65,
                    "reason_fa": f"برگشت از سقف کانال کلتنر — بانس نزولی",
                    "setup": setup}

    return _neutral("بانس کلتنر شناسایی نشد")


def kc_02(df, indicators, symbol, timeframe):
    """Keltner Breakout — close outside band."""
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(c) < 25:
        return _neutral("داده کافی نیست")
    upper, lower, mid = _keltner(h, l, c)
    atr = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]
    prev = c[-2]

    if upper is None:
        return _neutral("محاسبه کلتنر ناموفق")

    if price > upper[-1] and prev <= upper[-2]:
        setup = _make_setup("BUY", price, atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 75,
                    "reason_fa": f"شکست صعودی کانال کلتنر — بسته شدن بالای باند",
                    "setup": setup}

    if price < lower[-1] and prev >= lower[-2]:
        setup = _make_setup("SELL", price, atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 75,
                    "reason_fa": f"شکست نزولی کانال کلتنر — بسته شدن زیر باند",
                    "setup": setup}

    return _neutral("شکست کلتنر شناسایی نشد")


def kc_03(df, indicators, symbol, timeframe):
    """Keltner + BB Squeeze — BB inside Keltner → explosion."""
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(c) < 25:
        return _neutral("داده کافی نیست")
    kc_upper, kc_lower, kc_mid = _keltner(h, l, c)
    bb_upper, bb_lower, bb_mid = _bb(c)
    atr = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]

    if kc_upper is None or bb_upper is None:
        return _neutral("محاسبه ناموفق")

    # Squeeze: BB inside Keltner
    squeeze = bb_upper[-1] < kc_upper[-1] and bb_lower[-1] > kc_lower[-1]
    was_squeeze = bb_upper[-2] < kc_upper[-2] and bb_lower[-2] > kc_lower[-2]

    # Squeeze release
    if was_squeeze and not squeeze:
        if price > kc_mid[-1]:
            setup = _make_setup("BUY", price, atr[-1] if atr is not None else None, pip)
            if setup:
                return {"signal": "BUY", "confidence": 80,
                        "reason_fa": f"اسکوئیز کلتنر+بولینجر آزاد شد — انفجار صعودی",
                        "setup": setup}
        else:
            setup = _make_setup("SELL", price, atr[-1] if atr is not None else None, pip)
            if setup:
                return {"signal": "SELL", "confidence": 80,
                        "reason_fa": f"اسکوئیز کلتنر+بولینجر آزاد شد — انفجار نزولی",
                        "setup": setup}

    if squeeze:
        return _neutral("اسکوئیز کلتنر+بولینجر فعال — منتظر رهایی")

    return _neutral("اسکوئیز کلتنر+بولینجر شناسایی نشد")


def kc_04(df, indicators, symbol, timeframe):
    """Keltner Trend Walk — price stays above/below middle."""
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(c) < 30:
        return _neutral("داده کافی نیست")
    upper, lower, mid = _keltner(h, l, c)
    atr = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]

    if mid is None:
        return _neutral("محاسبه کلتنر ناموفق")

    # Count consecutive bars above/below middle
    above_count = 0
    below_count = 0
    for i in range(-1, -min(10, len(c)), -1):
        if c[i] > mid[i]:
            above_count += 1
        else:
            break
    for i in range(-1, -min(10, len(c)), -1):
        if c[i] < mid[i]:
            below_count += 1
        else:
            break

    if above_count >= 5:
        conf = min(75, 50 + above_count * 3)
        setup = _make_setup("BUY", price, atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": conf,
                    "reason_fa": f"روند صعودی کلتنر — {above_count} کندل بالای خط میانی",
                    "setup": setup}

    if below_count >= 5:
        conf = min(75, 50 + below_count * 3)
        setup = _make_setup("SELL", price, atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": conf,
                    "reason_fa": f"روند نزولی کلتنر — {below_count} کندل زیر خط میانی",
                    "setup": setup}

    return _neutral("روند کلتنر شناسایی نشد")


def kc_05(df, indicators, symbol, timeframe):
    """Keltner Width Expansion — channel widening."""
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(c) < 30:
        return _neutral("داده کافی نیست")
    upper, lower, mid = _keltner(h, l, c)
    atr = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]

    if upper is None:
        return _neutral("محاسبه کلتنر ناموفق")

    width_now = upper[-1] - lower[-1]
    width_prev = np.mean(upper[-20:-1] - lower[-20:-1])

    if width_now > width_prev * 1.5:
        if price > mid[-1]:
            setup = _make_setup("BUY", price, atr[-1] if atr is not None else None, pip)
            if setup:
                return {"signal": "BUY", "confidence": 70,
                        "reason_fa": f"گسترش کانال کلتنر — نوسان بالا + قیمت صعودی",
                        "setup": setup}
        else:
            setup = _make_setup("SELL", price, atr[-1] if atr is not None else None, pip)
            if setup:
                return {"signal": "SELL", "confidence": 70,
                        "reason_fa": f"گسترش کانال کلتنر — نوسان بالا + قیمت نزولی",
                        "setup": setup}

    return _neutral("گسترش کانال کلتنر شناسایی نشد")


KC_STRATEGIES = [
    {"id": "KC_01", "name": "Keltner Bounce", "name_fa": "بانس کلتنر", "func": kc_01},
    {"id": "KC_02", "name": "Keltner Breakout", "name_fa": "شکست کلتنر", "func": kc_02},
    {"id": "KC_03", "name": "KC+BB Squeeze", "name_fa": "اسکوئیز کلتنر+بولینجر", "func": kc_03},
    {"id": "KC_04", "name": "Keltner Trend Walk", "name_fa": "روند کلتنر", "func": kc_04},
    {"id": "KC_05", "name": "Keltner Width", "name_fa": "گسترش کلتنر", "func": kc_05},
]
