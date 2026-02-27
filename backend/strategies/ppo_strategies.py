"""
Whilber-AI — PPO Strategy Pack (5)
PPO_01: Signal Cross
PPO_02: Zero Cross
PPO_03: Histogram
PPO_04: Divergence
PPO_05: PPO + BB
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


CATEGORY_ID = "PPO"
CATEGORY_NAME = "Percentage Price Osc"
CATEGORY_FA = "اسیلاتور درصدی قیمت"

def _ppo(close, fast=12, slow=26, signal=9):
    ema_f = _ema(close, fast)
    ema_s = _ema(close, slow)
    if ema_f is None or ema_s is None: return None, None, None
    ppo = np.where(ema_s != 0, (ema_f - ema_s) / ema_s * 100, 0)
    sig = _ema(ppo, signal)
    if sig is None: return ppo, None, None
    hist = ppo - sig
    return ppo, sig, hist

def ppo_01(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    if len(c) < 35: return _neutral("داده کافی نیست")
    ppo, sig, _ = _ppo(c); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if ppo is None or sig is None: return _neutral("محاسبه ناموفق")
    if ppo[-1] > sig[-1] and ppo[-2] <= sig[-2]:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 70, "reason_fa": "PPO بالای سیگنال — مومنتوم صعودی", "setup": s}
    if ppo[-1] < sig[-1] and ppo[-2] >= sig[-2]:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 70, "reason_fa": "PPO زیر سیگنال — مومنتوم نزولی", "setup": s}
    return _neutral("تقاطع سیگنال PPO شناسایی نشد")

def ppo_02(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    if len(c) < 35: return _neutral("داده کافی نیست")
    ppo, _, _ = _ppo(c); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if ppo is None: return _neutral("محاسبه ناموفق")
    if ppo[-1] > 0 and ppo[-2] <= 0:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 68, "reason_fa": "PPO عبور صفر به بالا", "setup": s}
    if ppo[-1] < 0 and ppo[-2] >= 0:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 68, "reason_fa": "PPO عبور صفر به پایین", "setup": s}
    return _neutral("عبور صفر PPO شناسایی نشد")

def ppo_03(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    if len(c) < 35: return _neutral("داده کافی نیست")
    _, _, hist = _ppo(c); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if hist is None: return _neutral("محاسبه ناموفق")
    if hist[-1] > 0 and hist[-2] <= 0:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 65, "reason_fa": "هیستوگرام PPO مثبت شد", "setup": s}
    if hist[-1] < 0 and hist[-2] >= 0:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 65, "reason_fa": "هیستوگرام PPO منفی شد", "setup": s}
    return _neutral("تغییر هیستوگرام PPO شناسایی نشد")

def ppo_04(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    if len(c) < 40: return _neutral("داده کافی نیست")
    ppo, _, _ = _ppo(c); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if ppo is None: return _neutral("محاسبه ناموفق")
    if c[-1] > c[-10] and ppo[-1] < ppo[-10]:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 66, "reason_fa": "واگرایی نزولی PPO", "setup": s}
    if c[-1] < c[-10] and ppo[-1] > ppo[-10]:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 66, "reason_fa": "واگرایی صعودی PPO", "setup": s}
    return _neutral("واگرایی PPO شناسایی نشد")

def ppo_05(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    if len(c) < 40: return _neutral("داده کافی نیست")
    ppo, _, _ = _ppo(c); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if ppo is None: return _neutral("محاسبه ناموفق")
    avg = np.mean(ppo[-20:]); std = np.std(ppo[-20:])
    if std > 0:
        z = (ppo[-1] - avg) / std
        if z < -2 and ppo[-1] > ppo[-2]:
            s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
            if s: return {"signal": "BUY", "confidence": 70, "reason_fa": f"PPO در باند پایین بولینجر — Z={z:.1f}", "setup": s}
        if z > 2 and ppo[-1] < ppo[-2]:
            s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
            if s: return {"signal": "SELL", "confidence": 70, "reason_fa": f"PPO در باند بالای بولینجر — Z={z:.1f}", "setup": s}
    return _neutral("PPO + بولینجر شناسایی نشد")

PPO_STRATEGIES = [
    {"id": "PPO_01", "name": "PPO Signal Cross", "name_fa": "تقاطع سیگنال PPO", "func": ppo_01},
    {"id": "PPO_02", "name": "PPO Zero Cross", "name_fa": "عبور صفر PPO", "func": ppo_02},
    {"id": "PPO_03", "name": "PPO Histogram", "name_fa": "هیستوگرام PPO", "func": ppo_03},
    {"id": "PPO_04", "name": "PPO Divergence", "name_fa": "واگرایی PPO", "func": ppo_04},
    {"id": "PPO_05", "name": "PPO + BB", "name_fa": "PPO + بولینجر", "func": ppo_05},
]
