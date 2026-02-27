"""
Whilber-AI — OBV Strategy Pack (5)
OBV_01: OBV Trend
OBV_02: OBV Divergence
OBV_03: OBV + EMA Cross
OBV_04: OBV Breakout
OBV_05: OBV Rate of Change
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


CATEGORY_ID = "OBV"
CATEGORY_NAME = "On-Balance Volume"
CATEGORY_FA = "حجم تعادلی"

def _obv(close, volume):
    obv = np.zeros(len(close))
    for i in range(1, len(close)):
        if close[i] > close[i-1]: obv[i] = obv[i-1] + volume[i]
        elif close[i] < close[i-1]: obv[i] = obv[i-1] - volume[i]
        else: obv[i] = obv[i-1]
    return obv

def obv_01(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    v = _get_volume(df)
    if len(c) < 25: return _neutral("داده کافی نیست")
    obv = _obv(c, v); obv_ema = _ema(obv, 20)
    atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if obv_ema is None: return _neutral("محاسبه ناموفق")
    if obv[-1] > obv_ema[-1] and obv[-2] <= obv_ema[-2]:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 68, "reason_fa": "OBV بالای میانگین — ورود پول", "setup": s}
    if obv[-1] < obv_ema[-1] and obv[-2] >= obv_ema[-2]:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 68, "reason_fa": "OBV زیر میانگین — خروج پول", "setup": s}
    return _neutral("روند OBV شناسایی نشد")

def obv_02(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    v = _get_volume(df)
    if len(c) < 30: return _neutral("داده کافی نیست")
    obv = _obv(c, v); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if c[-1] > c[-10] and obv[-1] < obv[-10]:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 70, "reason_fa": "واگرایی نزولی OBV — قیمت بالا ولی حجم پایین", "setup": s}
    if c[-1] < c[-10] and obv[-1] > obv[-10]:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 70, "reason_fa": "واگرایی صعودی OBV — قیمت پایین ولی حجم بالا", "setup": s}
    return _neutral("واگرایی OBV شناسایی نشد")

def obv_03(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    v = _get_volume(df)
    if len(c) < 25: return _neutral("داده کافی نیست")
    obv = _obv(c, v); ema_fast = _ema(obv, 10); ema_slow = _ema(obv, 30)
    atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if ema_fast is None or ema_slow is None: return _neutral("محاسبه ناموفق")
    if ema_fast[-1] > ema_slow[-1] and ema_fast[-2] <= ema_slow[-2]:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 72, "reason_fa": "تقاطع صعودی EMA حجم — فشار خرید", "setup": s}
    if ema_fast[-1] < ema_slow[-1] and ema_fast[-2] >= ema_slow[-2]:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 72, "reason_fa": "تقاطع نزولی EMA حجم — فشار فروش", "setup": s}
    return _neutral("تقاطع EMA حجم شناسایی نشد")

def obv_04(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    v = _get_volume(df)
    if len(c) < 30: return _neutral("داده کافی نیست")
    obv = _obv(c, v); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    obv_high = np.max(obv[-20:-1]); obv_low = np.min(obv[-20:-1])
    if obv[-1] > obv_high:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 73, "reason_fa": "شکست سقف OBV — حجم قوی صعودی", "setup": s}
    if obv[-1] < obv_low:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 73, "reason_fa": "شکست کف OBV — حجم قوی نزولی", "setup": s}
    return _neutral("شکست OBV شناسایی نشد")

def obv_05(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    v = _get_volume(df)
    if len(c) < 20: return _neutral("داده کافی نیست")
    obv = _obv(c, v); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if obv[-10] != 0:
        roc = (obv[-1] - obv[-10]) / abs(obv[-10]) * 100
    else: roc = 0
    if roc > 20:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 67, "reason_fa": f"نرخ تغییر OBV={roc:.0f}% — شتاب حجم خرید", "setup": s}
    if roc < -20:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 67, "reason_fa": f"نرخ تغییر OBV={roc:.0f}% — شتاب حجم فروش", "setup": s}
    return _neutral("شتاب OBV کافی نیست")

OBV_STRATEGIES = [
    {"id": "OBV_01", "name": "OBV Trend", "name_fa": "روند OBV", "func": obv_01},
    {"id": "OBV_02", "name": "OBV Divergence", "name_fa": "واگرایی OBV", "func": obv_02},
    {"id": "OBV_03", "name": "OBV EMA Cross", "name_fa": "تقاطع EMA حجم", "func": obv_03},
    {"id": "OBV_04", "name": "OBV Breakout", "name_fa": "شکست OBV", "func": obv_04},
    {"id": "OBV_05", "name": "OBV ROC", "name_fa": "نرخ تغییر OBV", "func": obv_05},
]
