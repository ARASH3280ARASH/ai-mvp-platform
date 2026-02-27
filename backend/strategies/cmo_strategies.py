"""
Whilber-AI — CMO Strategy Pack (5)
CMO_01: OB/OS
CMO_02: Zero Cross
CMO_03: Divergence
CMO_04: CMO + ADX
CMO_05: Trend
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


CATEGORY_ID = "CMO"
CATEGORY_NAME = "Chande Momentum"
CATEGORY_FA = "مومنتوم چاند"

def _cmo(close, period=14):
    if len(close) < period + 1: return None
    cmo = np.zeros(len(close))
    for i in range(period, len(close)):
        gains = sum(max(0, close[j]-close[j-1]) for j in range(i-period+1, i+1))
        losses = sum(max(0, close[j-1]-close[j]) for j in range(i-period+1, i+1))
        total = gains + losses
        cmo[i] = (gains - losses) / total * 100 if total > 0 else 0
    return cmo

def cmo_01(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    if len(c) < 20: return _neutral("داده کافی نیست")
    cmo = _cmo(c); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if cmo is None: return _neutral("محاسبه ناموفق")
    if cmo[-1] < -50 and cmo[-1] > cmo[-2]:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 68, "reason_fa": f"CMO اشباع فروش ({cmo[-1]:.0f}) + بازگشت", "setup": s}
    if cmo[-1] > 50 and cmo[-1] < cmo[-2]:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 68, "reason_fa": f"CMO اشباع خرید ({cmo[-1]:.0f}) + بازگشت", "setup": s}
    return _neutral("اشباع CMO شناسایی نشد")

def cmo_02(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    if len(c) < 20: return _neutral("داده کافی نیست")
    cmo = _cmo(c); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if cmo is None: return _neutral("محاسبه ناموفق")
    if cmo[-1] > 0 and cmo[-2] <= 0:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 65, "reason_fa": "CMO عبور صفر به بالا", "setup": s}
    if cmo[-1] < 0 and cmo[-2] >= 0:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 65, "reason_fa": "CMO عبور صفر به پایین", "setup": s}
    return _neutral("عبور صفر CMO شناسایی نشد")

def cmo_03(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    if len(c) < 30: return _neutral("داده کافی نیست")
    cmo = _cmo(c); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if cmo is None: return _neutral("محاسبه ناموفق")
    if c[-1] > c[-10] and cmo[-1] < cmo[-10]:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 66, "reason_fa": "واگرایی نزولی CMO", "setup": s}
    if c[-1] < c[-10] and cmo[-1] > cmo[-10]:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 66, "reason_fa": "واگرایی صعودی CMO", "setup": s}
    return _neutral("واگرایی CMO شناسایی نشد")

def cmo_04(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    if len(c) < 30: return _neutral("داده کافی نیست")
    cmo = _cmo(c); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if cmo is None: return _neutral("محاسبه ناموفق")
    # Simple ADX proxy: use absolute CMO as trend strength
    abs_cmo = abs(cmo[-1])
    if cmo[-1] > 25 and abs_cmo > 40:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 72, "reason_fa": f"CMO مثبت قوی ({cmo[-1]:.0f}) — روند صعودی", "setup": s}
    if cmo[-1] < -25 and abs_cmo > 40:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 72, "reason_fa": f"CMO منفی قوی ({cmo[-1]:.0f}) — روند نزولی", "setup": s}
    return _neutral("CMO + قدرت روند کافی نیست")

def cmo_05(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    if len(c) < 25: return _neutral("داده کافی نیست")
    cmo = _cmo(c); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if cmo is None: return _neutral("محاسبه ناموفق")
    above = sum(1 for i in range(-5, 0) if cmo[i] > 0)
    below = sum(1 for i in range(-5, 0) if cmo[i] < 0)
    if above >= 4 and cmo[-1] > cmo[-2]:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 67, "reason_fa": f"روند CMO صعودی — {above}/5 مثبت", "setup": s}
    if below >= 4 and cmo[-1] < cmo[-2]:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 67, "reason_fa": f"روند CMO نزولی — {below}/5 منفی", "setup": s}
    return _neutral("روند CMO شناسایی نشد")

CMO_STRATEGIES = [
    {"id": "CMO_01", "name": "CMO OB/OS", "name_fa": "اشباع CMO", "func": cmo_01},
    {"id": "CMO_02", "name": "CMO Zero Cross", "name_fa": "عبور صفر CMO", "func": cmo_02},
    {"id": "CMO_03", "name": "CMO Divergence", "name_fa": "واگرایی CMO", "func": cmo_03},
    {"id": "CMO_04", "name": "CMO + Trend", "name_fa": "CMO + روند", "func": cmo_04},
    {"id": "CMO_05", "name": "CMO Trend", "name_fa": "روند CMO", "func": cmo_05},
]
