"""
Whilber-AI — A/D Strategy Pack (5)
AD_01: AD Trend
AD_02: AD Divergence
AD_03: AD EMA Cross
AD_04: AD Breakout
AD_05: AD + Price
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


CATEGORY_ID = "AD"
CATEGORY_NAME = "Accumulation/Distribution"
CATEGORY_FA = "تجمع/توزیع"

def _ad(high, low, close, volume):
    ad = np.zeros(len(close))
    for i in range(len(close)):
        hl = high[i] - low[i]
        if hl > 0:
            clv = ((close[i]-low[i]) - (high[i]-close[i])) / hl
        else:
            clv = 0
        ad[i] = (ad[i-1] if i > 0 else 0) + clv * volume[i]
    return ad

def ad_01(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    v = _get_volume(df)
    if len(c) < 25: return _neutral("داده کافی نیست")
    ad = _ad(h, l, c, v); ad_ema = _ema(ad, 20)
    atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if ad_ema is None: return _neutral("محاسبه ناموفق")
    if ad[-1] > ad_ema[-1] and ad[-2] <= ad_ema[-2]:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 67, "reason_fa": "A/D بالای میانگین — تجمع", "setup": s}
    if ad[-1] < ad_ema[-1] and ad[-2] >= ad_ema[-2]:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 67, "reason_fa": "A/D زیر میانگین — توزیع", "setup": s}
    return _neutral("روند A/D شناسایی نشد")

def ad_02(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    v = _get_volume(df)
    if len(c) < 30: return _neutral("داده کافی نیست")
    ad = _ad(h, l, c, v); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if c[-1] > c[-10] and ad[-1] < ad[-10]:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 70, "reason_fa": "واگرایی نزولی A/D", "setup": s}
    if c[-1] < c[-10] and ad[-1] > ad[-10]:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 70, "reason_fa": "واگرایی صعودی A/D", "setup": s}
    return _neutral("واگرایی A/D شناسایی نشد")

def ad_03(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    v = _get_volume(df)
    if len(c) < 35: return _neutral("داده کافی نیست")
    ad = _ad(h, l, c, v); fast = _ema(ad, 10); slow = _ema(ad, 30)
    atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    if fast is None or slow is None: return _neutral("محاسبه ناموفق")
    if fast[-1] > slow[-1] and fast[-2] <= slow[-2]:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 72, "reason_fa": "تقاطع صعودی EMA تجمع/توزیع", "setup": s}
    if fast[-1] < slow[-1] and fast[-2] >= slow[-2]:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 72, "reason_fa": "تقاطع نزولی EMA تجمع/توزیع", "setup": s}
    return _neutral("تقاطع A/D شناسایی نشد")

def ad_04(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    v = _get_volume(df)
    if len(c) < 25: return _neutral("داده کافی نیست")
    ad = _ad(h, l, c, v); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    ad_high = np.max(ad[-20:-1]); ad_low = np.min(ad[-20:-1])
    if ad[-1] > ad_high:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 70, "reason_fa": "شکست سقف A/D — تجمع قوی", "setup": s}
    if ad[-1] < ad_low:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 70, "reason_fa": "شکست کف A/D — توزیع قوی", "setup": s}
    return _neutral("شکست A/D شناسایی نشد")

def ad_05(df, indicators, symbol, timeframe):
    c = df["close"].values; h, l = df["high"].values, df["low"].values
    v = _get_volume(df)
    if len(c) < 20: return _neutral("داده کافی نیست")
    ad = _ad(h, l, c, v); atr = _atr(h, l, c, 14); pip = _pip_size(symbol)
    p_up = c[-1] > c[-5]; ad_up = ad[-1] > ad[-5]
    if p_up and ad_up:
        s = _make_setup("BUY", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "BUY", "confidence": 65, "reason_fa": "قیمت + A/D هر دو صعودی — تایید", "setup": s}
    if not p_up and not ad_up:
        s = _make_setup("SELL", c[-1], atr[-1] if atr is not None else None, pip)
        if s: return {"signal": "SELL", "confidence": 65, "reason_fa": "قیمت + A/D هر دو نزولی — تایید", "setup": s}
    return _neutral("همسویی A/D + قیمت شناسایی نشد")

AD_STRATEGIES = [
    {"id": "AD_01", "name": "A/D Trend", "name_fa": "روند A/D", "func": ad_01},
    {"id": "AD_02", "name": "A/D Divergence", "name_fa": "واگرایی A/D", "func": ad_02},
    {"id": "AD_03", "name": "A/D EMA Cross", "name_fa": "تقاطع A/D", "func": ad_03},
    {"id": "AD_04", "name": "A/D Breakout", "name_fa": "شکست A/D", "func": ad_04},
    {"id": "AD_05", "name": "A/D + Price", "name_fa": "A/D + قیمت", "func": ad_05},
]
