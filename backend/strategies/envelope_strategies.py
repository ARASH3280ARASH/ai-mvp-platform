"""
Whilber-AI — Envelope / MA Band Strategy Pack (5 Sub-Strategies)
==================================================================
ENV_01: Classic Envelope (fixed % band around SMA)
ENV_02: Dynamic ATR Envelope (ATR-based bands)
ENV_03: Envelope Cross (price crosses band)
ENV_04: Envelope Squeeze (bands narrow → breakout)
ENV_05: Envelope Trend (price within upper/lower half)
"""

import numpy as np

CATEGORY_ID = "ENV"
CATEGORY_NAME = "Envelope"
CATEGORY_FA = "پوشش میانگین"
ICON = "📦"
COLOR = "#9c27b0"


def _sma(data, period):
    if len(data) < period:
        return None
    return np.array([np.mean(data[max(0,i-period+1):i+1]) for i in range(len(data))])


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
    if tp1_dist / sl_dist < rr_min:
        return None
    return {"has_setup": True, "direction": direction,
            "direction_fa": "خرید" if direction == "BUY" else "فروش",
            "entry": round(entry, 6), "stop_loss": round(sl, 6),
            "tp1": round(tp1, 6), "tp2": round(tp2, 6),
            "rr1": round(tp1_dist/sl_dist, 2), "rr2": round(tp2_dist/sl_dist, 2),
            "sl_pips": round(sl_dist/pip, 1) if pip > 0 else 0,
            "tp1_pips": round(tp1_dist/pip, 1) if pip > 0 else 0}


def _neutral(r):
    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": r, "setup": {"has_setup": False}}


def env_01(df, indicators, symbol, timeframe):
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(c) < 25: return _neutral("داده کافی نیست")
    sma = _sma(c, 20)
    atr = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]
    pct = 0.02
    upper = sma * (1 + pct)
    lower = sma * (1 - pct)

    if price <= lower[-1] and c[-2] > lower[-2]:
        setup = _make_setup("BUY", price, atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 65, "reason_fa": "رسیدن به کف پوشش ۲٪ — سیگنال خرید", "setup": setup}
    if price >= upper[-1] and c[-2] < upper[-2]:
        setup = _make_setup("SELL", price, atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 65, "reason_fa": "رسیدن به سقف پوشش ۲٪ — سیگنال فروش", "setup": setup}
    return _neutral("سیگنال پوشش کلاسیک شناسایی نشد")


def env_02(df, indicators, symbol, timeframe):
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(c) < 25: return _neutral("داده کافی نیست")
    sma = _sma(c, 20)
    atr = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]
    if atr is None: return _neutral("محاسبه ATR ناموفق")
    upper = sma + atr * 2
    lower = sma - atr * 2

    if price <= lower[-1] and c[-2] > lower[-2]:
        setup = _make_setup("BUY", price, atr[-1], pip)
        if setup:
            return {"signal": "BUY", "confidence": 70, "reason_fa": "رسیدن به کف پوشش ATR — بانس صعودی", "setup": setup}
    if price >= upper[-1] and c[-2] < upper[-2]:
        setup = _make_setup("SELL", price, atr[-1], pip)
        if setup:
            return {"signal": "SELL", "confidence": 70, "reason_fa": "رسیدن به سقف پوشش ATR — بانس نزولی", "setup": setup}
    return _neutral("سیگنال پوشش ATR شناسایی نشد")


def env_03(df, indicators, symbol, timeframe):
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(c) < 25: return _neutral("داده کافی نیست")
    sma = _sma(c, 20)
    atr = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price, prev = c[-1], c[-2]
    pct = 0.015
    upper, lower = sma * (1 + pct), sma * (1 - pct)

    if prev < upper[-2] and price > upper[-1]:
        setup = _make_setup("BUY", price, atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 70, "reason_fa": "عبور صعودی از باند بالای پوشش", "setup": setup}
    if prev > lower[-2] and price < lower[-1]:
        setup = _make_setup("SELL", price, atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 70, "reason_fa": "عبور نزولی از باند پایین پوشش", "setup": setup}
    return _neutral("عبور باند پوشش شناسایی نشد")


def env_04(df, indicators, symbol, timeframe):
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(c) < 30: return _neutral("داده کافی نیست")
    atr = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]
    if atr is None: return _neutral("محاسبه ناموفق")
    atr_now = atr[-1]
    atr_avg = np.mean(atr[-20:-1])
    if atr_now < atr_avg * 0.6:
        if price > np.mean(c[-5:]):
            setup = _make_setup("BUY", price, atr_now * 2, pip)
            if setup:
                return {"signal": "BUY", "confidence": 60, "reason_fa": "فشردگی پوشش — آماده انفجار صعودی", "setup": setup}
        else:
            setup = _make_setup("SELL", price, atr_now * 2, pip)
            if setup:
                return {"signal": "SELL", "confidence": 60, "reason_fa": "فشردگی پوشش — آماده انفجار نزولی", "setup": setup}
    return _neutral("فشردگی پوشش شناسایی نشد")


def env_05(df, indicators, symbol, timeframe):
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(c) < 30: return _neutral("داده کافی نیست")
    sma = _sma(c, 20)
    atr = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]
    if sma is None: return _neutral("محاسبه ناموفق")
    above = sum(1 for i in range(-5, 0) if c[i] > sma[i])
    below = sum(1 for i in range(-5, 0) if c[i] < sma[i])
    if above >= 4:
        setup = _make_setup("BUY", price, atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 65, "reason_fa": f"روند صعودی پوشش — {above}/5 بالای SMA", "setup": setup}
    if below >= 4:
        setup = _make_setup("SELL", price, atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 65, "reason_fa": f"روند نزولی پوشش — {below}/5 زیر SMA", "setup": setup}
    return _neutral("روند پوشش شناسایی نشد")


ENV_STRATEGIES = [
    {"id": "ENV_01", "name": "Classic Envelope", "name_fa": "پوشش کلاسیک", "func": env_01},
    {"id": "ENV_02", "name": "ATR Envelope", "name_fa": "پوشش ATR", "func": env_02},
    {"id": "ENV_03", "name": "Envelope Cross", "name_fa": "عبور پوشش", "func": env_03},
    {"id": "ENV_04", "name": "Envelope Squeeze", "name_fa": "فشردگی پوشش", "func": env_04},
    {"id": "ENV_05", "name": "Envelope Trend", "name_fa": "روند پوشش", "func": env_05},
]
