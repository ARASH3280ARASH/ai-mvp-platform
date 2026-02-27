"""
Whilber-AI — MFI Strategy Pack (5)
MFI_01: OB/OS
MFI_02: Divergence
MFI_03: MFI + RSI
MFI_04: MFI Trend
MFI_05: MFI Reversal
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

def _sma(data, period):
    if len(data) < period: return None
    return np.array([np.mean(data[max(0,i-period+1):i+1]) for i in range(len(data))])

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
    tp1_d = sl_d * rr_min; tp2_d = sl_d * 3.0
    if direction == "BUY": sl, tp1, tp2 = entry-sl_d, entry+tp1_d, entry+tp2_d
    else: sl, tp1, tp2 = entry+sl_d, entry-tp1_d, entry-tp2_d
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

def _get_volume(df):
    """Get volume, use tick_volume as fallback for forex."""
    if "volume" in df.columns and df["volume"].sum() > 0:
        return df["volume"].values.astype(float)
    if "tick_volume" in df.columns and df["tick_volume"].sum() > 0:
        return df["tick_volume"].values.astype(float)
    if "real_volume" in df.columns and df["real_volume"].sum() > 0:
        return df["real_volume"].values.astype(float)
    return np.ones(len(df))  # fallback: equal volume


CATEGORY_ID = "MFI"
CATEGORY_NAME = "Money Flow Index"
CATEGORY_FA = "شاخص جریان پول"

def _mfi(high, low, close, volume, period=14):
    if len(close) < period + 1: return None
    tp = (high + low + close) / 3
    mf = tp * volume
    mfi = np.zeros(len(close))
    for i in range(period, len(close)):
        pos = sum(mf[j] for j in range(i-period+1, i+1) if tp[j] > tp[j-1])
        neg = sum(mf[j] for j in range(i-period+1, i+1) if tp[j] < tp[j-1])
        if neg == 0: mfi[i] = 100
        else: mfi[i] = 100 - 100/(1 + pos/neg)
    return mfi

def mfi_01(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    v = _get_volume(df)
    if len(c) < 20: return _neutral("داده کافی نیست")
    mfi = _mfi(h, l, c, v); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if mfi is None: return _neutral("محاسبه ناموفق")
    if mfi[-1] < 20 and mfi[-1] > mfi[-2]:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 70, "reason_fa": f"MFI اشباع فروش ({mfi[-1]:.0f}) + بازگشت", "setup": s}
    if mfi[-1] > 80 and mfi[-1] < mfi[-2]:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 70, "reason_fa": f"MFI اشباع خرید ({mfi[-1]:.0f}) + بازگشت", "setup": s}
    return _neutral("اشباع MFI شناسایی نشد")

def mfi_02(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    v = _get_volume(df)
    if len(c) < 30: return _neutral("داده کافی نیست")
    mfi = _mfi(h, l, c, v); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if mfi is None: return _neutral("محاسبه ناموفق")
    if c[-1] > c[-10] and mfi[-1] < mfi[-10]:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 68, "reason_fa": "واگرایی نزولی MFI", "setup": s}
    if c[-1] < c[-10] and mfi[-1] > mfi[-10]:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 68, "reason_fa": "واگرایی صعودی MFI", "setup": s}
    return _neutral("واگرایی MFI شناسایی نشد")

def mfi_03(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    v = _get_volume(df)
    if len(c) < 20: return _neutral("داده کافی نیست")
    mfi = _mfi(h, l, c, v); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if mfi is None: return _neutral("محاسبه ناموفق")
    # RSI calc
    gains = np.zeros(len(c)); losses = np.zeros(len(c))
    for i in range(1, len(c)):
        d = c[i]-c[i-1]
        if d > 0: gains[i] = d
        else: losses[i] = -d
    avg_g = _ema(gains, 14); avg_l = _ema(losses, 14)
    if avg_g is None or avg_l is None: return _neutral("محاسبه ناموفق")
    rs = np.where(avg_l > 0, avg_g/avg_l, 100)
    rsi = 100 - 100/(1+rs)
    if mfi[-1] < 30 and rsi[-1] < 30:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 78, "reason_fa": f"MFI({mfi[-1]:.0f})+RSI({rsi[-1]:.0f}) هر دو اشباع فروش", "setup": s}
    if mfi[-1] > 70 and rsi[-1] > 70:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 78, "reason_fa": f"MFI({mfi[-1]:.0f})+RSI({rsi[-1]:.0f}) هر دو اشباع خرید", "setup": s}
    return _neutral("MFI + RSI همزمان شناسایی نشد")

def mfi_04(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    v = _get_volume(df)
    if len(c) < 25: return _neutral("داده کافی نیست")
    mfi = _mfi(h, l, c, v); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if mfi is None: return _neutral("محاسبه ناموفق")
    above = sum(1 for i in range(-5, 0) if mfi[i] > 50)
    below = sum(1 for i in range(-5, 0) if mfi[i] < 50)
    if above >= 4 and mfi[-1] > mfi[-2]:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 66, "reason_fa": f"روند MFI صعودی — {above}/5 بالای ۵۰", "setup": s}
    if below >= 4 and mfi[-1] < mfi[-2]:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 66, "reason_fa": f"روند MFI نزولی — {below}/5 زیر ۵۰", "setup": s}
    return _neutral("روند MFI شناسایی نشد")

def mfi_05(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    v = _get_volume(df)
    if len(c) < 20: return _neutral("داده کافی نیست")
    mfi = _mfi(h, l, c, v); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if mfi is None: return _neutral("محاسبه ناموفق")
    if mfi[-2] < 20 and mfi[-1] > 20:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 72, "reason_fa": "MFI خروج از اشباع فروش — بازگشت تایید شده", "setup": s}
    if mfi[-2] > 80 and mfi[-1] < 80:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 72, "reason_fa": "MFI خروج از اشباع خرید — بازگشت تایید شده", "setup": s}
    return _neutral("بازگشت MFI شناسایی نشد")

MFI_STRATEGIES = [
    {"id": "MFI_01", "name": "MFI OB/OS", "name_fa": "اشباع MFI", "func": mfi_01},
    {"id": "MFI_02", "name": "MFI Divergence", "name_fa": "واگرایی MFI", "func": mfi_02},
    {"id": "MFI_03", "name": "MFI + RSI", "name_fa": "MFI + RSI", "func": mfi_03},
    {"id": "MFI_04", "name": "MFI Trend", "name_fa": "روند MFI", "func": mfi_04},
    {"id": "MFI_05", "name": "MFI Reversal", "name_fa": "بازگشت MFI", "func": mfi_05},
]
