"""
Whilber-AI — TRIX Strategy Pack (5)
TRIX_01: Zero-Line Cross
TRIX_02: Signal Line Cross
TRIX_03: Divergence
TRIX_04: Histogram
TRIX_05: TRIX + EMA Confirm
"""

import numpy as np

def _ema(data, period):
    if len(data) < period: return None
    e = np.zeros(len(data))
    e[period-1] = np.mean(data[:period])
    m = 2 / (period + 1)
    for i in range(period, len(data)):
        e[i] = data[i] * m + e[i-1] * (1 - m)
    return e

def _atr(high, low, close, period=14):
    if len(high) < period + 1: return None
    tr = np.maximum(high[1:]-low[1:], np.maximum(abs(high[1:]-close[:-1]), abs(low[1:]-close[:-1])))
    a = np.zeros(len(tr))
    a[period-1] = np.mean(tr[:period])
    for i in range(period, len(tr)):
        a[i] = (a[i-1]*(period-1)+tr[i])/period
    return np.concatenate([[0], a])

def _pip_size(symbol):
    s = symbol.upper()
    if "JPY" in s: return 0.01
    if "XAU" in s: return 0.1
    if "XAG" in s: return 0.01
    if "BTC" in s: return 1.0
    if s in ("NAS100","US30","SPX500","GER40","UK100"): return 1.0
    return 0.0001

def _make_setup(direction, entry, atr_val, pip, rr_min=1.5):
    if atr_val is None or atr_val <= 0: return None
    sl_d = atr_val * 1.5
    tp1_d = sl_d * rr_min
    tp2_d = sl_d * 3.0
    if direction == "BUY":
        sl, tp1, tp2 = entry-sl_d, entry+tp1_d, entry+tp2_d
    else:
        sl, tp1, tp2 = entry+sl_d, entry-tp1_d, entry-tp2_d
    if tp1_d/sl_d < rr_min: return None
    return {"has_setup": True, "direction": direction,
            "direction_fa": "خرید" if direction=="BUY" else "فروش",
            "entry": round(entry,6), "stop_loss": round(sl,6),
            "tp1": round(tp1,6), "tp2": round(tp2,6),
            "rr1": round(tp1_d/sl_d,2), "rr2": round(tp2_d/sl_d,2),
            "sl_pips": round(sl_d/pip,1) if pip>0 else 0,
            "tp1_pips": round(tp1_d/pip,1) if pip>0 else 0}

def _neutral(r):
    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": r, "setup": {"has_setup": False}}


CATEGORY_ID = "TRIX"
CATEGORY_NAME = "TRIX"
CATEGORY_FA = "تریکس"

def _trix(close, period=15):
    e1 = _ema(close, period)
    if e1 is None: return None, None
    e2 = _ema(e1, period)
    if e2 is None: return None, None
    e3 = _ema(e2, period)
    if e3 is None: return None, None
    trix = np.zeros(len(e3))
    for i in range(1, len(e3)):
        trix[i] = (e3[i] - e3[i-1]) / e3[i-1] * 100 if e3[i-1] != 0 else 0
    signal = _ema(trix, 9)
    return trix, signal

def trix_01(df, indicators, symbol, timeframe):
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(c) < 50: return _neutral("داده کافی نیست")
    trix, sig = _trix(c)
    atr = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    if trix is None: return _neutral("محاسبه TRIX ناموفق")
    if trix[-1] > 0 and trix[-2] <= 0:
        setup = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 72, "reason_fa": "TRIX عبور از صفر به بالا — شروع روند صعودی", "setup": setup}
    if trix[-1] < 0 and trix[-2] >= 0:
        setup = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 72, "reason_fa": "TRIX عبور از صفر به پایین — شروع روند نزولی", "setup": setup}
    return _neutral("عبور صفر TRIX شناسایی نشد")

def trix_02(df, indicators, symbol, timeframe):
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(c) < 50: return _neutral("داده کافی نیست")
    trix, sig = _trix(c)
    atr = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    if trix is None or sig is None: return _neutral("محاسبه ناموفق")
    if trix[-1] > sig[-1] and trix[-2] <= sig[-2]:
        setup = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 70, "reason_fa": "TRIX بالای خط سیگنال — مومنتوم صعودی", "setup": setup}
    if trix[-1] < sig[-1] and trix[-2] >= sig[-2]:
        setup = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 70, "reason_fa": "TRIX زیر خط سیگنال — مومنتوم نزولی", "setup": setup}
    return _neutral("تقاطع سیگنال TRIX شناسایی نشد")

def trix_03(df, indicators, symbol, timeframe):
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(c) < 60: return _neutral("داده کافی نیست")
    trix, _ = _trix(c)
    atr = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    if trix is None: return _neutral("محاسبه ناموفق")
    # Bearish div: price HH but TRIX LH
    if c[-1] > c[-10] and trix[-1] < trix[-10]:
        setup = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 68, "reason_fa": "واگرایی نزولی TRIX — قیمت بالا ولی TRIX پایین", "setup": setup}
    # Bullish div: price LL but TRIX HL
    if c[-1] < c[-10] and trix[-1] > trix[-10]:
        setup = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 68, "reason_fa": "واگرایی صعودی TRIX — قیمت پایین ولی TRIX بالا", "setup": setup}
    return _neutral("واگرایی TRIX شناسایی نشد")

def trix_04(df, indicators, symbol, timeframe):
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(c) < 50: return _neutral("داده کافی نیست")
    trix, sig = _trix(c)
    atr = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    if trix is None or sig is None: return _neutral("محاسبه ناموفق")
    hist = trix - sig
    if hist[-1] > 0 and hist[-2] <= 0:
        setup = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 65, "reason_fa": "هیستوگرام TRIX مثبت شد", "setup": setup}
    if hist[-1] < 0 and hist[-2] >= 0:
        setup = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 65, "reason_fa": "هیستوگرام TRIX منفی شد", "setup": setup}
    return _neutral("تغییر هیستوگرام TRIX شناسایی نشد")

def trix_05(df, indicators, symbol, timeframe):
    c = df["close"].values
    h, l = df["high"].values, df["low"].values
    if len(c) < 55: return _neutral("داده کافی نیست")
    trix, _ = _trix(c)
    ema50 = _ema(c, 50)
    atr = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    if trix is None or ema50 is None: return _neutral("محاسبه ناموفق")
    if trix[-1] > 0 and trix[-2] <= 0 and c[-1] > ema50[-1]:
        setup = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 78, "reason_fa": "TRIX صعودی + بالای EMA50 — تایید دوگانه", "setup": setup}
    if trix[-1] < 0 and trix[-2] >= 0 and c[-1] < ema50[-1]:
        setup = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 78, "reason_fa": "TRIX نزولی + زیر EMA50 — تایید دوگانه", "setup": setup}
    return _neutral("TRIX + EMA شناسایی نشد")

TRIX_STRATEGIES = [
    {"id": "TRIX_01", "name": "TRIX Zero Cross", "name_fa": "عبور صفر TRIX", "func": trix_01},
    {"id": "TRIX_02", "name": "TRIX Signal Cross", "name_fa": "تقاطع سیگنال TRIX", "func": trix_02},
    {"id": "TRIX_03", "name": "TRIX Divergence", "name_fa": "واگرایی TRIX", "func": trix_03},
    {"id": "TRIX_04", "name": "TRIX Histogram", "name_fa": "هیستوگرام TRIX", "func": trix_04},
    {"id": "TRIX_05", "name": "TRIX + EMA", "name_fa": "TRIX + EMA", "func": trix_05},
]
