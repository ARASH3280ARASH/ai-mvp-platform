"""
Whilber-AI — VWAP Strategy Pack (5)
VWAP_01: Price Cross
VWAP_02: Band Touch
VWAP_03: VWAP Trend
VWAP_04: VWAP + Volume
VWAP_05: Multi-VWAP
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


CATEGORY_ID = "VWAP"
CATEGORY_NAME = "VWAP"
CATEGORY_FA = "میانگین وزنی حجم"

def _vwap(high, low, close, volume):
    tp = (high + low + close) / 3
    cum_vol = np.cumsum(volume)
    cum_tp_vol = np.cumsum(tp * volume)
    vwap = np.where(cum_vol > 0, cum_tp_vol / cum_vol, close)
    # Bands (1 std)
    cum_tp2_vol = np.cumsum(tp**2 * volume)
    variance = np.where(cum_vol > 0, cum_tp2_vol/cum_vol - vwap**2, 0)
    std = np.sqrt(np.maximum(variance, 0))
    return vwap, vwap + std, vwap - std

def vwap_01(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    v = _get_volume(df)
    if len(c) < 15: return _neutral("داده کافی نیست")
    vwap, _, _ = _vwap(h, l, c, v); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if c[-1] > vwap[-1] and c[-2] <= vwap[-2]:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 68, "reason_fa": "عبور صعودی از VWAP", "setup": s}
    if c[-1] < vwap[-1] and c[-2] >= vwap[-2]:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 68, "reason_fa": "عبور نزولی از VWAP", "setup": s}
    return _neutral("عبور VWAP شناسایی نشد")

def vwap_02(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    v = _get_volume(df)
    if len(c) < 15: return _neutral("داده کافی نیست")
    vwap, upper, lower = _vwap(h, l, c, v); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if c[-1] <= lower[-1] and c[-2] < c[-1]:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 70, "reason_fa": "بانس از باند پایین VWAP", "setup": s}
    if c[-1] >= upper[-1] and c[-2] > c[-1]:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 70, "reason_fa": "بانس از باند بالای VWAP", "setup": s}
    return _neutral("بانس باند VWAP شناسایی نشد")

def vwap_03(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    v = _get_volume(df)
    if len(c) < 20: return _neutral("داده کافی نیست")
    vwap, _, _ = _vwap(h, l, c, v); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    above = sum(1 for i in range(-5, 0) if c[i] > vwap[i])
    below = sum(1 for i in range(-5, 0) if c[i] < vwap[i])
    if above >= 4:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 66, "reason_fa": f"روند VWAP صعودی — {above}/5 بالا", "setup": s}
    if below >= 4:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 66, "reason_fa": f"روند VWAP نزولی — {below}/5 پایین", "setup": s}
    return _neutral("روند VWAP شناسایی نشد")

def vwap_04(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    v = _get_volume(df)
    if len(c) < 20: return _neutral("داده کافی نیست")
    vwap, _, _ = _vwap(h, l, c, v); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    vol_avg = np.mean(v[-20:])
    if c[-1] > vwap[-1] and v[-1] > vol_avg * 1.5:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 75, "reason_fa": "بالای VWAP + حجم بالا — تایید خریداران", "setup": s}
    if c[-1] < vwap[-1] and v[-1] > vol_avg * 1.5:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 75, "reason_fa": "زیر VWAP + حجم بالا — تایید فروشندگان", "setup": s}
    return _neutral("VWAP + حجم شناسایی نشد")

def vwap_05(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    v = _get_volume(df)
    if len(c) < 30: return _neutral("داده کافی نیست")
    vwap_full, _, _ = _vwap(h, l, c, v)
    mid = len(c) // 2
    vwap_half, _, _ = _vwap(h[mid:], l[mid:], c[mid:], v[mid:])
    atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    vf = vwap_full[-1]; vh = vwap_half[-1]
    if c[-1] > vf and c[-1] > vh and vh > vf:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 72, "reason_fa": "بالای هر دو VWAP — روند صعودی قوی", "setup": s}
    if c[-1] < vf and c[-1] < vh and vh < vf:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 72, "reason_fa": "زیر هر دو VWAP — روند نزولی قوی", "setup": s}
    return _neutral("Multi-VWAP شناسایی نشد")

VWAP_STRATEGIES = [
    {"id": "VWAP_01", "name": "VWAP Cross", "name_fa": "عبور VWAP", "func": vwap_01},
    {"id": "VWAP_02", "name": "VWAP Band", "name_fa": "باند VWAP", "func": vwap_02},
    {"id": "VWAP_03", "name": "VWAP Trend", "name_fa": "روند VWAP", "func": vwap_03},
    {"id": "VWAP_04", "name": "VWAP + Volume", "name_fa": "VWAP + حجم", "func": vwap_04},
    {"id": "VWAP_05", "name": "Multi-VWAP", "name_fa": "چند VWAP", "func": vwap_05},
]
