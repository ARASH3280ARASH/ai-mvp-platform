"""
Gap Analysis Pack (5)
GAPS_01: Gap Fill
GAPS_02: Gap Continuation
GAPS_03: Gap + Volume
GAPS_04: Opening Gap
GAPS_05: Exhaustion Gap
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

def gaps_01(df, indicators, symbol, timeframe):
    h,l,c,o = df["high"].values,df["low"].values,df["close"].values,df["open"].values
    if len(c)<10: return _neutral("داده کافی نیست")
    atr=_atr(h,l,c,14); pip=_pip_size(symbol); price=c[-1]
    gap_up = o[-1]>h[-2]; gap_dn = o[-1]<l[-2]
    if gap_up and price<o[-1]:
        s=_make_setup("SELL",price,atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":68,"reason_fa":"گپ صعودی در حال پر شدن — فروش","setup":s}
    if gap_dn and price>o[-1]:
        s=_make_setup("BUY",price,atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":68,"reason_fa":"گپ نزولی در حال پر شدن — خرید","setup":s}
    return _neutral("گپ فیل شناسایی نشد")

def gaps_02(df, indicators, symbol, timeframe):
    h,l,c,o = df["high"].values,df["low"].values,df["close"].values,df["open"].values
    if len(c)<10: return _neutral("داده کافی نیست")
    atr=_atr(h,l,c,14); pip=_pip_size(symbol); price=c[-1]
    gap_up = o[-1]>h[-2]; gap_dn = o[-1]<l[-2]
    if gap_up and price>o[-1]:
        s=_make_setup("BUY",price,atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":72,"reason_fa":"گپ صعودی ادامه‌دار — فشار خرید","setup":s}
    if gap_dn and price<o[-1]:
        s=_make_setup("SELL",price,atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":72,"reason_fa":"گپ نزولی ادامه‌دار — فشار فروش","setup":s}
    return _neutral("گپ ادامه‌دار شناسایی نشد")

def gaps_03(df, indicators, symbol, timeframe):
    h,l,c,o = df["high"].values,df["low"].values,df["close"].values,df["open"].values
    v = _get_volume(df)
    if len(c)<15: return _neutral("داده کافی نیست")
    atr=_atr(h,l,c,14); pip=_pip_size(symbol); price=c[-1]
    va=np.mean(v[-20:])
    gap_up = o[-1]>h[-2]; gap_dn = o[-1]<l[-2]
    if gap_up and v[-1]>va*1.5 and price>o[-1]:
        s=_make_setup("BUY",price,atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":78,"reason_fa":"گپ صعودی + حجم بالا — سیگنال قوی","setup":s}
    if gap_dn and v[-1]>va*1.5 and price<o[-1]:
        s=_make_setup("SELL",price,atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":78,"reason_fa":"گپ نزولی + حجم بالا — سیگنال قوی","setup":s}
    return _neutral("گپ+حجم شناسایی نشد")

def gaps_04(df, indicators, symbol, timeframe):
    h,l,c,o = df["high"].values,df["low"].values,df["close"].values,df["open"].values
    if len(c)<10: return _neutral("داده کافی نیست")
    atr=_atr(h,l,c,14); pip=_pip_size(symbol); price=c[-1]
    gap_size=abs(o[-1]-c[-2])
    atr_val=atr[-1] if atr is not None else 0
    if atr_val>0 and gap_size>atr_val*0.5:
        if o[-1]>c[-2] and price>o[-1]:
            s=_make_setup("BUY",price,atr_val,pip)
            if s: return {"signal":"BUY","confidence":70,"reason_fa":f"گپ بزرگ صعودی ({gap_size/pip:.0f} پیپ) + ادامه","setup":s}
        if o[-1]<c[-2] and price<o[-1]:
            s=_make_setup("SELL",price,atr_val,pip)
            if s: return {"signal":"SELL","confidence":70,"reason_fa":f"گپ بزرگ نزولی ({gap_size/pip:.0f} پیپ) + ادامه","setup":s}
    return _neutral("گپ بزرگ شناسایی نشد")

def gaps_05(df, indicators, symbol, timeframe):
    h,l,c,o = df["high"].values,df["low"].values,df["close"].values,df["open"].values
    if len(c)<15: return _neutral("داده کافی نیست")
    atr=_atr(h,l,c,14); pip=_pip_size(symbol); price=c[-1]
    # After a trend, gap that gets filled = exhaustion
    trend_up = all(c[-i]>c[-i-1] for i in range(2,6)) if len(c)>6 else False
    trend_dn = all(c[-i]<c[-i-1] for i in range(2,6)) if len(c)>6 else False
    gap_up = o[-1]>h[-2]
    gap_dn = o[-1]<l[-2]
    if trend_up and gap_up and price<o[-1]:
        s=_make_setup("SELL",price,atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":74,"reason_fa":"گپ خستگی صعودی — بازگشت محتمل","setup":s}
    if trend_dn and gap_dn and price>o[-1]:
        s=_make_setup("BUY",price,atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":74,"reason_fa":"گپ خستگی نزولی — بازگشت محتمل","setup":s}
    return _neutral("گپ خستگی شناسایی نشد")

GAPS_STRATEGIES = [
    {"id":"GAPS_01","name":"Gap Fill","name_fa":"گپ فیل","func":gaps_01},
    {"id":"GAPS_02","name":"Gap Continue","name_fa":"گپ ادامه","func":gaps_02},
    {"id":"GAPS_03","name":"Gap+Volume","name_fa":"گپ+حجم","func":gaps_03},
    {"id":"GAPS_04","name":"Big Gap","name_fa":"گپ بزرگ","func":gaps_04},
    {"id":"GAPS_05","name":"Exhaustion Gap","name_fa":"گپ خستگی","func":gaps_05},
]
