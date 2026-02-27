"""
Whilber-AI — Force Index Strategy Pack (5)
FI_01: FI Zero Cross
FI_02: FI EMA Cross
FI_03: FI Divergence
FI_04: FI Extreme
FI_05: FI Dual Period
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


CATEGORY_ID = "FI"
CATEGORY_NAME = "Force Index"
CATEGORY_FA = "شاخص قدرت"

def _fi(close, volume):
    fi = np.zeros(len(close))
    for i in range(1, len(close)):
        fi[i] = (close[i] - close[i-1]) * volume[i]
    return fi

def fi_01(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    v = _get_volume(df)
    if len(c) < 15: return _neutral("داده کافی نیست")
    fi = _fi(c, v); fi_ema = _ema(fi, 13)
    atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if fi_ema is None: return _neutral("محاسبه ناموفق")
    if fi_ema[-1] > 0 and fi_ema[-2] <= 0:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 68, "reason_fa": "شاخص قدرت مثبت شد — فشار خرید", "setup": s}
    if fi_ema[-1] < 0 and fi_ema[-2] >= 0:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 68, "reason_fa": "شاخص قدرت منفی شد — فشار فروش", "setup": s}
    return _neutral("تغییر FI شناسایی نشد")

def fi_02(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    v = _get_volume(df)
    if len(c) < 20: return _neutral("داده کافی نیست")
    fi = _fi(c, v); fast = _ema(fi, 2); slow = _ema(fi, 13)
    atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if fast is None or slow is None: return _neutral("محاسبه ناموفق")
    if fast[-1] > slow[-1] and fast[-2] <= slow[-2]:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 70, "reason_fa": "تقاطع صعودی FI سریع/آهسته", "setup": s}
    if fast[-1] < slow[-1] and fast[-2] >= slow[-2]:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 70, "reason_fa": "تقاطع نزولی FI سریع/آهسته", "setup": s}
    return _neutral("تقاطع FI شناسایی نشد")

def fi_03(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    v = _get_volume(df)
    if len(c) < 30: return _neutral("داده کافی نیست")
    fi = _fi(c, v); fi_ema = _ema(fi, 13)
    atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if fi_ema is None: return _neutral("محاسبه ناموفق")
    if c[-1] > c[-10] and fi_ema[-1] < fi_ema[-10]:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 68, "reason_fa": "واگرایی نزولی FI", "setup": s}
    if c[-1] < c[-10] and fi_ema[-1] > fi_ema[-10]:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 68, "reason_fa": "واگرایی صعودی FI", "setup": s}
    return _neutral("واگرایی FI شناسایی نشد")

def fi_04(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    v = _get_volume(df)
    if len(c) < 25: return _neutral("داده کافی نیست")
    fi = _fi(c, v); fi_ema = _ema(fi, 13)
    atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if fi_ema is None: return _neutral("محاسبه ناموفق")
    avg = np.mean(np.abs(fi_ema[-20:])); std = np.std(fi_ema[-20:])
    if std > 0:
        z = fi_ema[-1] / std
        if z < -2 and fi_ema[-1] > fi_ema[-2]:
            s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
            if s: return {"signal": "BUY", "confidence": 70, "reason_fa": f"FI در کف اکستریم + بازگشت", "setup": s}
        if z > 2 and fi_ema[-1] < fi_ema[-2]:
            s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
            if s: return {"signal": "SELL", "confidence": 70, "reason_fa": f"FI در سقف اکستریم + بازگشت", "setup": s}
    return _neutral("اکستریم FI شناسایی نشد")

def fi_05(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    v = _get_volume(df)
    if len(c) < 20: return _neutral("داده کافی نیست")
    fi = _fi(c, v)
    fi2 = _ema(fi, 2); fi13 = _ema(fi, 13)
    atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if fi2 is None or fi13 is None: return _neutral("محاسبه ناموفق")
    if fi2[-1] > 0 and fi13[-1] > 0:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 74, "reason_fa": "FI کوتاه + بلند هر دو مثبت — قدرت خرید", "setup": s}
    if fi2[-1] < 0 and fi13[-1] < 0:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 74, "reason_fa": "FI کوتاه + بلند هر دو منفی — قدرت فروش", "setup": s}
    return _neutral("FI دوگانه شناسایی نشد")

FI_STRATEGIES = [
    {"id": "FI_01", "name": "FI Zero Cross", "name_fa": "عبور صفر FI", "func": fi_01},
    {"id": "FI_02", "name": "FI EMA Cross", "name_fa": "تقاطع FI", "func": fi_02},
    {"id": "FI_03", "name": "FI Divergence", "name_fa": "واگرایی FI", "func": fi_03},
    {"id": "FI_04", "name": "FI Extreme", "name_fa": "اکستریم FI", "func": fi_04},
    {"id": "FI_05", "name": "FI Dual", "name_fa": "FI دوگانه", "func": fi_05},
]
