"""
Whilber-AI — ROC Strategy Pack (5)
ROC_01: Zero Cross
ROC_02: Momentum Thrust
ROC_03: Divergence
ROC_04: Multi-Period
ROC_05: ROC Extreme
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


CATEGORY_ID = "ROC"
CATEGORY_NAME = "Rate of Change"
CATEGORY_FA = "نرخ تغییر"

def _roc(close, period=14):
    if len(close) < period + 1: return None
    roc = np.zeros(len(close))
    for i in range(period, len(close)):
        if close[i-period] != 0:
            roc[i] = (close[i] - close[i-period]) / close[i-period] * 100
    return roc

def roc_01(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    if len(c) < 20: return _neutral("داده کافی نیست")
    roc = _roc(c, 14); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if roc is None: return _neutral("محاسبه ناموفق")
    if roc[-1] > 0 and roc[-2] <= 0:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 68, "reason_fa": "ROC عبور صفر به بالا — مومنتوم مثبت", "setup": s}
    if roc[-1] < 0 and roc[-2] >= 0:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 68, "reason_fa": "ROC عبور صفر به پایین — مومنتوم منفی", "setup": s}
    return _neutral("عبور صفر ROC شناسایی نشد")

def roc_02(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    if len(c) < 20: return _neutral("داده کافی نیست")
    roc = _roc(c, 14); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if roc is None: return _neutral("محاسبه ناموفق")
    if roc[-1] > 3:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 75, "reason_fa": f"جهش مومنتوم ROC={roc[-1]:.1f}% — فشار خرید قوی", "setup": s}
    if roc[-1] < -3:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 75, "reason_fa": f"جهش مومنتوم ROC={roc[-1]:.1f}% — فشار فروش قوی", "setup": s}
    return _neutral("جهش مومنتوم ROC شناسایی نشد")

def roc_03(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    if len(c) < 30: return _neutral("داده کافی نیست")
    roc = _roc(c, 14); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if roc is None: return _neutral("محاسبه ناموفق")
    if c[-1] > c[-10] and roc[-1] < roc[-10]:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 66, "reason_fa": "واگرایی نزولی ROC", "setup": s}
    if c[-1] < c[-10] and roc[-1] > roc[-10]:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 66, "reason_fa": "واگرایی صعودی ROC", "setup": s}
    return _neutral("واگرایی ROC شناسایی نشد")

def roc_04(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    if len(c) < 30: return _neutral("داده کافی نیست")
    roc_fast = _roc(c, 7); roc_slow = _roc(c, 21)
    atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if roc_fast is None or roc_slow is None: return _neutral("محاسبه ناموفق")
    if roc_fast[-1] > roc_slow[-1] and roc_fast[-2] <= roc_slow[-2]:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 70, "reason_fa": "ROC سریع بالای آهسته — شتاب صعودی", "setup": s}
    if roc_fast[-1] < roc_slow[-1] and roc_fast[-2] >= roc_slow[-2]:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 70, "reason_fa": "ROC سریع زیر آهسته — شتاب نزولی", "setup": s}
    return _neutral("تقاطع ROC چندگانه شناسایی نشد")

def roc_05(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    if len(c) < 30: return _neutral("داده کافی نیست")
    roc = _roc(c, 14); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if roc is None: return _neutral("محاسبه ناموفق")
    avg = np.mean(np.abs(roc[-20:])) if len(roc) >= 20 else 1
    if avg > 0 and roc[-1] < -avg * 2 and roc[-1] > roc[-2]:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 65, "reason_fa": "ROC در کف اکستریم + بازگشت", "setup": s}
    if avg > 0 and roc[-1] > avg * 2 and roc[-1] < roc[-2]:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 65, "reason_fa": "ROC در سقف اکستریم + بازگشت", "setup": s}
    return _neutral("اکستریم ROC شناسایی نشد")

ROC_STRATEGIES = [
    {"id": "ROC_01", "name": "ROC Zero Cross", "name_fa": "عبور صفر ROC", "func": roc_01},
    {"id": "ROC_02", "name": "ROC Thrust", "name_fa": "جهش ROC", "func": roc_02},
    {"id": "ROC_03", "name": "ROC Divergence", "name_fa": "واگرایی ROC", "func": roc_03},
    {"id": "ROC_04", "name": "ROC Multi-Period", "name_fa": "ROC چندگانه", "func": roc_04},
    {"id": "ROC_05", "name": "ROC Extreme", "name_fa": "اکستریم ROC", "func": roc_05},
]
