"""
Whilber-AI — Kaufman Adaptive MA Strategy Pack (5 Sub-Strategies)
===================================================================
KAMA_01: KAMA Direction Change (slope flip)
KAMA_02: Price-KAMA Cross
KAMA_03: KAMA + RSI Filter
KAMA_04: Dual KAMA Cross (fast vs slow)
KAMA_05: KAMA Efficiency Ratio Breakout
"""

import numpy as np

CATEGORY_ID = "KAMA"
CATEGORY_NAME = "Kaufman Adaptive MA"
CATEGORY_FA = "میانگین تطبیقی کافمن"
ICON = "🎯"
COLOR = "#9c27b0"


def _kama(close, period=10, fast=2, slow=30):
    """Kaufman Adaptive Moving Average."""
    n = len(close)
    if n <= period: return None, None
    fast_sc = 2.0 / (fast + 1.0)
    slow_sc = 2.0 / (slow + 1.0)
    result = np.zeros(n)
    er = np.zeros(n)
    result[period - 1] = close[period - 1]

    for i in range(period, n):
        direction = abs(close[i] - close[i - period])
        volatility = np.sum(np.abs(np.diff(close[i - period:i + 1])))
        if volatility == 0:
            er[i] = 0
        else:
            er[i] = direction / volatility
        sc = (er[i] * (fast_sc - slow_sc) + slow_sc) ** 2
        result[i] = result[i - 1] + sc * (close[i] - result[i - 1])

    return result, er


def _rsi(close, period=14):
    if len(close) < period + 1: return None
    n = len(close)
    rsi = np.zeros(n)
    delta = np.diff(close)
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = np.mean(gain[:period])
    avg_loss = np.mean(loss[:period])
    if avg_loss == 0:
        rsi[period] = 100
    else:
        rsi[period] = 100 - 100 / (1 + avg_gain / avg_loss)
    for i in range(period + 1, n):
        avg_gain = (avg_gain * (period - 1) + gain[i - 1]) / period
        avg_loss = (avg_loss * (period - 1) + loss[i - 1]) / period
        if avg_loss == 0:
            rsi[i] = 100
        else:
            rsi[i] = 100 - 100 / (1 + avg_gain / avg_loss)
    return rsi


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


def kama_01(df, indicators, symbol, timeframe):
    """KAMA Direction Change (slope flip)."""
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(c) < 20: return _neutral("داده کافی نیست")
    k, er = _kama(c, 10)
    if k is None: return _neutral("محاسبه KAMA ناموفق")
    atr_v = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]

    slope_now = k[-1] - k[-2]
    slope_prev = k[-2] - k[-3]

    if slope_now > 0 and slope_prev <= 0:
        setup = _make_setup("BUY", price, atr_v[-1] if atr_v is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 72, "reason_fa": "KAMA شیب صعودی شد", "setup": setup}

    if slope_now < 0 and slope_prev >= 0:
        setup = _make_setup("SELL", price, atr_v[-1] if atr_v is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 72, "reason_fa": "KAMA شیب نزولی شد", "setup": setup}

    return _neutral("تغییر جهت KAMA شناسایی نشد")


def kama_02(df, indicators, symbol, timeframe):
    """Price-KAMA Cross."""
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(c) < 20: return _neutral("داده کافی نیست")
    k, er = _kama(c, 10)
    if k is None: return _neutral("محاسبه KAMA ناموفق")
    atr_v = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]

    if c[-1] > k[-1] and c[-2] <= k[-2]:
        setup = _make_setup("BUY", price, atr_v[-1] if atr_v is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 73, "reason_fa": "قیمت از KAMA عبور کرد به بالا", "setup": setup}

    if c[-1] < k[-1] and c[-2] >= k[-2]:
        setup = _make_setup("SELL", price, atr_v[-1] if atr_v is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 73, "reason_fa": "قیمت از KAMA عبور کرد به پایین", "setup": setup}

    return _neutral("عبور قیمت از KAMA شناسایی نشد")


def kama_03(df, indicators, symbol, timeframe):
    """KAMA + RSI Filter."""
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(c) < 25: return _neutral("داده کافی نیست")
    k, er = _kama(c, 10)
    rsi_v = _rsi(c, 14)
    if k is None or rsi_v is None: return _neutral("محاسبه ناموفق")
    atr_v = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]

    if c[-1] > k[-1] and c[-2] <= k[-2] and rsi_v[-1] > 50 and rsi_v[-1] < 70:
        setup = _make_setup("BUY", price, atr_v[-1] if atr_v is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 78, "reason_fa": f"KAMA صعودی + RSI={rsi_v[-1]:.0f} تایید", "setup": setup}

    if c[-1] < k[-1] and c[-2] >= k[-2] and rsi_v[-1] < 50 and rsi_v[-1] > 30:
        setup = _make_setup("SELL", price, atr_v[-1] if atr_v is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 78, "reason_fa": f"KAMA نزولی + RSI={rsi_v[-1]:.0f} تایید", "setup": setup}

    return _neutral("KAMA + RSI شناسایی نشد")


def kama_04(df, indicators, symbol, timeframe):
    """Dual KAMA Cross (fast 10 vs slow 30)."""
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(c) < 40: return _neutral("داده کافی نیست")
    k_fast, _ = _kama(c, 10)
    k_slow, _ = _kama(c, 30)
    if k_fast is None or k_slow is None: return _neutral("محاسبه KAMA ناموفق")
    atr_v = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]

    if k_fast[-1] > k_slow[-1] and k_fast[-2] <= k_slow[-2]:
        setup = _make_setup("BUY", price, atr_v[-1] if atr_v is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 76, "reason_fa": "KAMA سریع از KAMA کند عبور کرد — صعودی", "setup": setup}

    if k_fast[-1] < k_slow[-1] and k_fast[-2] >= k_slow[-2]:
        setup = _make_setup("SELL", price, atr_v[-1] if atr_v is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 76, "reason_fa": "KAMA سریع از KAMA کند عبور کرد — نزولی", "setup": setup}

    return _neutral("عبور دوگانه KAMA شناسایی نشد")


def kama_05(df, indicators, symbol, timeframe):
    """KAMA Efficiency Ratio Breakout."""
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(c) < 20: return _neutral("داده کافی نیست")
    k, er = _kama(c, 10)
    if k is None or er is None: return _neutral("محاسبه KAMA ناموفق")
    atr_v = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]

    # High efficiency ratio = trending market
    if er[-1] > 0.6 and c[-1] > k[-1]:
        slope = k[-1] - k[-3]
        if slope > 0:
            setup = _make_setup("BUY", price, atr_v[-1] if atr_v is not None else None, pip)
            if setup:
                return {"signal": "BUY", "confidence": 77, "reason_fa": f"KAMA ER={er[-1]:.2f} — بازار روندی صعودی", "setup": setup}

    if er[-1] > 0.6 and c[-1] < k[-1]:
        slope = k[-1] - k[-3]
        if slope < 0:
            setup = _make_setup("SELL", price, atr_v[-1] if atr_v is not None else None, pip)
            if setup:
                return {"signal": "SELL", "confidence": 77, "reason_fa": f"KAMA ER={er[-1]:.2f} — بازار روندی نزولی", "setup": setup}

    return _neutral("ER کافمن پایین است — بازار رنج")


KAMA_STRATEGIES = [
    {"id": "KAMA_01", "name": "KAMA Direction", "name_fa": "جهت KAMA", "func": kama_01},
    {"id": "KAMA_02", "name": "Price-KAMA Cross", "name_fa": "عبور قیمت-KAMA", "func": kama_02},
    {"id": "KAMA_03", "name": "KAMA + RSI", "name_fa": "KAMA + RSI", "func": kama_03},
    {"id": "KAMA_04", "name": "Dual KAMA Cross", "name_fa": "عبور دوگانه KAMA", "func": kama_04},
    {"id": "KAMA_05", "name": "KAMA ER Breakout", "name_fa": "شکست ER کافمن", "func": kama_05},
]
