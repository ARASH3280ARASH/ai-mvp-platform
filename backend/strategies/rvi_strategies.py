"""
Whilber-AI — RVI Strategy Pack (5)
RVI_01: Signal Cross
RVI_02: Zero Cross
RVI_03: Divergence
RVI_04: RVI + MA
RVI_05: Trend
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


CATEGORY_ID = "RVI"
CATEGORY_NAME = "Relative Vigor"
CATEGORY_FA = "شاخص نیروی نسبی"

def _rvi(o, h, l, c, period=10):
    if len(c) < period + 4: return None, None
    n = len(c)
    num = np.zeros(n)
    den = np.zeros(n)
    for i in range(3, n):
        num[i] = ((c[i]-o[i]) + 2*(c[i-1]-o[i-1]) + 2*(c[i-2]-o[i-2]) + (c[i-3]-o[i-3])) / 6
        den[i] = ((h[i]-l[i]) + 2*(h[i-1]-l[i-1]) + 2*(h[i-2]-l[i-2]) + (h[i-3]-l[i-3])) / 6
    rvi = np.zeros(n)
    for i in range(period+3, n):
        s_num = np.sum(num[i-period+1:i+1])
        s_den = np.sum(den[i-period+1:i+1])
        rvi[i] = s_num / s_den if s_den != 0 else 0
    sig = np.zeros(n)
    for i in range(3, n):
        sig[i] = (rvi[i] + 2*rvi[i-1] + 2*rvi[max(0,i-2)] + rvi[max(0,i-3)]) / 6
    return rvi, sig

def rvi_01(df, indicators, symbol, timeframe):
    o, h, l, c = df["open"].values, df["high"].values, df["low"].values, df["close"].values
    if len(c) < 20: return _neutral("داده کافی نیست")
    rvi, sig = _rvi(o, h, l, c); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if rvi is None: return _neutral("محاسبه ناموفق")
    if rvi[-1] > sig[-1] and rvi[-2] <= sig[-2]:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 68, "reason_fa": "RVI بالای خط سیگنال — نیروی صعودی", "setup": s}
    if rvi[-1] < sig[-1] and rvi[-2] >= sig[-2]:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 68, "reason_fa": "RVI زیر خط سیگنال — نیروی نزولی", "setup": s}
    return _neutral("تقاطع سیگنال RVI شناسایی نشد")

def rvi_02(df, indicators, symbol, timeframe):
    o, h, l, c = df["open"].values, df["high"].values, df["low"].values, df["close"].values
    if len(c) < 20: return _neutral("داده کافی نیست")
    rvi, _ = _rvi(o, h, l, c); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if rvi is None: return _neutral("محاسبه ناموفق")
    if rvi[-1] > 0 and rvi[-2] <= 0:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 65, "reason_fa": "RVI عبور صفر به بالا", "setup": s}
    if rvi[-1] < 0 and rvi[-2] >= 0:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 65, "reason_fa": "RVI عبور صفر به پایین", "setup": s}
    return _neutral("عبور صفر RVI شناسایی نشد")

def rvi_03(df, indicators, symbol, timeframe):
    o, h, l, c = df["open"].values, df["high"].values, df["low"].values, df["close"].values
    if len(c) < 30: return _neutral("داده کافی نیست")
    rvi, _ = _rvi(o, h, l, c); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if rvi is None: return _neutral("محاسبه ناموفق")
    if c[-1] > c[-10] and rvi[-1] < rvi[-10]:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 66, "reason_fa": "واگرایی نزولی RVI", "setup": s}
    if c[-1] < c[-10] and rvi[-1] > rvi[-10]:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 66, "reason_fa": "واگرایی صعودی RVI", "setup": s}
    return _neutral("واگرایی RVI شناسایی نشد")

def rvi_04(df, indicators, symbol, timeframe):
    o, h, l, c = df["open"].values, df["high"].values, df["low"].values, df["close"].values
    if len(c) < 25: return _neutral("داده کافی نیست")
    rvi, _ = _rvi(o, h, l, c); ema20 = _ema(c, 20); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if rvi is None or ema20 is None: return _neutral("محاسبه ناموفق")
    if rvi[-1] > 0 and c[-1] > ema20[-1]:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 72, "reason_fa": "RVI مثبت + بالای EMA20 — تایید", "setup": s}
    if rvi[-1] < 0 and c[-1] < ema20[-1]:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 72, "reason_fa": "RVI منفی + زیر EMA20 — تایید", "setup": s}
    return _neutral("RVI + MA شناسایی نشد")

def rvi_05(df, indicators, symbol, timeframe):
    o, h, l, c = df["open"].values, df["high"].values, df["low"].values, df["close"].values
    if len(c) < 25: return _neutral("داده کافی نیست")
    rvi, _ = _rvi(o, h, l, c); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if rvi is None: return _neutral("محاسبه ناموفق")
    above = sum(1 for i in range(-5, 0) if rvi[i] > 0)
    below = sum(1 for i in range(-5, 0) if rvi[i] < 0)
    if above >= 4:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 66, "reason_fa": f"روند RVI صعودی — {above}/5 مثبت", "setup": s}
    if below >= 4:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 66, "reason_fa": f"روند RVI نزولی — {below}/5 منفی", "setup": s}
    return _neutral("روند RVI شناسایی نشد")

RVI_STRATEGIES = [
    {"id": "RVI_01", "name": "RVI Signal Cross", "name_fa": "تقاطع سیگنال RVI", "func": rvi_01},
    {"id": "RVI_02", "name": "RVI Zero Cross", "name_fa": "عبور صفر RVI", "func": rvi_02},
    {"id": "RVI_03", "name": "RVI Divergence", "name_fa": "واگرایی RVI", "func": rvi_03},
    {"id": "RVI_04", "name": "RVI + MA", "name_fa": "RVI + میانگین", "func": rvi_04},
    {"id": "RVI_05", "name": "RVI Trend", "name_fa": "روند RVI", "func": rvi_05},
]
