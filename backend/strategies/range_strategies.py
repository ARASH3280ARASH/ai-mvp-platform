"""
Range Detection Pack (5)
RANGE_01: Range Breakout
RANGE_02: Range Bounce
RANGE_03: Narrow Range
RANGE_04: Range+Volume
RANGE_05: Inside Bar
"""

import numpy as np

def _ema(data, period):
    if len(data) < period: return None
    e = np.zeros(len(data)); e[period-1] = np.mean(data[:period]); m = 2/(period+1)
    for i in range(period, len(data)): e[i] = data[i]*m + e[i-1]*(1-m)
    return e

def _atr(high, low, close, period=14):
    if len(high) < period+1: return None
    tr = np.maximum(high[1:]-low[1:], np.maximum(abs(high[1:]-close[:-1]), abs(low[1:]-close[:-1])))
    a = np.zeros(len(tr)); a[period-1] = np.mean(tr[:period])
    for i in range(period, len(tr)): a[i] = (a[i-1]*(period-1)+tr[i])/period
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
    sl_d = atr_val*1.5; tp1_d = sl_d*rr_min; tp2_d = sl_d*3.0
    if direction == "BUY": sl,tp1,tp2 = entry-sl_d, entry+tp1_d, entry+tp2_d
    else: sl,tp1,tp2 = entry+sl_d, entry-tp1_d, entry-tp2_d
    if tp1_d/sl_d < rr_min: return None
    return {"has_setup":True,"direction":direction,"direction_fa":"خرید" if direction=="BUY" else "فروش",
            "entry":round(entry,6),"stop_loss":round(sl,6),"tp1":round(tp1,6),"tp2":round(tp2,6),
            "rr1":round(tp1_d/sl_d,2),"rr2":round(tp2_d/sl_d,2),
            "sl_pips":round(sl_d/pip,1) if pip>0 else 0,"tp1_pips":round(tp1_d/pip,1) if pip>0 else 0}

def _neutral(r):
    return {"signal":"NEUTRAL","confidence":0,"reason_fa":r,"setup":{"has_setup":False}}


def _get_volume(df):
    if "tick_volume" in df.columns and df["tick_volume"].sum()>0: return df["tick_volume"].values.astype(float)
    if "volume" in df.columns and df["volume"].sum()>0: return df["volume"].values.astype(float)
    return np.ones(len(df))

def range_01(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<25: return _neutral("داده کافی نیست")
    atr=_atr(h,l,c,14); pip=_pip_size(symbol); price=c[-1]
    hh=np.max(h[-20:-1]); ll=np.min(l[-20:-1])
    if price>hh:
        s=_make_setup("BUY",price,atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":74,"reason_fa":f"شکست سقف رنج ۲۰ ({hh:.5f})","setup":s}
    if price<ll:
        s=_make_setup("SELL",price,atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":74,"reason_fa":f"شکست کف رنج ۲۰ ({ll:.5f})","setup":s}
    return _neutral("شکست رنج شناسایی نشد")

def range_02(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<25: return _neutral("داده کافی نیست")
    atr=_atr(h,l,c,14); pip=_pip_size(symbol); price=c[-1]
    hh=np.max(h[-20:-1]); ll=np.min(l[-20:-1]); rng=hh-ll
    pos=(price-ll)/rng if rng>0 else 0.5
    if pos<0.1 and c[-1]>c[-2]:
        s=_make_setup("BUY",price,atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":68,"reason_fa":"بانس از کف رنج — حمایت","setup":s}
    if pos>0.9 and c[-1]<c[-2]:
        s=_make_setup("SELL",price,atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":68,"reason_fa":"بانس از سقف رنج — مقاومت","setup":s}
    return _neutral("بانس رنج شناسایی نشد")

def range_03(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<25: return _neutral("داده کافی نیست")
    atr=_atr(h,l,c,14); pip=_pip_size(symbol); price=c[-1]
    ranges = h[-7:]-l[-7:]
    avg_rng = np.mean(h[-20:-1]-l[-20:-1])
    if np.mean(ranges)<avg_rng*0.5:
        if price>np.mean(c[-3:]):
            s=_make_setup("BUY",price,atr[-1]*1.5 if atr is not None else None,pip)
            if s: return {"signal":"BUY","confidence":66,"reason_fa":"رنج باریک — آماده انفجار صعودی","setup":s}
        else:
            s=_make_setup("SELL",price,atr[-1]*1.5 if atr is not None else None,pip)
            if s: return {"signal":"SELL","confidence":66,"reason_fa":"رنج باریک — آماده انفجار نزولی","setup":s}
    return _neutral("رنج باریک شناسایی نشد")

def range_04(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    v = _get_volume(df)
    if len(c)<25: return _neutral("داده کافی نیست")
    atr=_atr(h,l,c,14); pip=_pip_size(symbol); price=c[-1]
    hh=np.max(h[-20:-1]); ll=np.min(l[-20:-1]); va=np.mean(v[-20:])
    if price>hh and v[-1]>va*1.3:
        s=_make_setup("BUY",price,atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":78,"reason_fa":"شکست رنج + حجم بالا — تایید صعودی","setup":s}
    if price<ll and v[-1]>va*1.3:
        s=_make_setup("SELL",price,atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":78,"reason_fa":"شکست رنج + حجم بالا — تایید نزولی","setup":s}
    return _neutral("شکست رنج+حجم شناسایی نشد")

def range_05(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<5: return _neutral("داده کافی نیست")
    atr=_atr(h,l,c,14); pip=_pip_size(symbol); price=c[-1]
    # Inside bar: current bar within previous bar
    inside = h[-2]<=h[-3] and l[-2]>=l[-3]
    if inside:
        if price>h[-2]:
            s=_make_setup("BUY",price,atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"BUY","confidence":70,"reason_fa":"شکست صعودی Inside Bar","setup":s}
        if price<l[-2]:
            s=_make_setup("SELL",price,atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"SELL","confidence":70,"reason_fa":"شکست نزولی Inside Bar","setup":s}
    return _neutral("Inside Bar شناسایی نشد")

RANGE_STRATEGIES = [
    {"id":"RANGE_01","name":"Range Breakout","name_fa":"شکست رنج","func":range_01},
    {"id":"RANGE_02","name":"Range Bounce","name_fa":"بانس رنج","func":range_02},
    {"id":"RANGE_03","name":"Narrow Range","name_fa":"رنج باریک","func":range_03},
    {"id":"RANGE_04","name":"Range+Volume","name_fa":"رنج+حجم","func":range_04},
    {"id":"RANGE_05","name":"Inside Bar","name_fa":"Inside Bar","func":range_05},
]
