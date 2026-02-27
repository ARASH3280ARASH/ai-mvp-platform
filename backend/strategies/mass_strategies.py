"""
Mass Index Pack (5)
MASS_01: Reversal Bulge
MASS_02: Threshold Cross
MASS_03: MASS+Trend
MASS_04: MASS+EMA
MASS_05: MASS Divergence
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


def _mass_index(high, low, period=25, ema_period=9):
    if len(high)<period+ema_period*2: return None
    rng=high-low
    ema1=_ema(rng, ema_period)
    if ema1 is None: return None
    ema2=_ema(ema1, ema_period)
    if ema2 is None: return None
    ratio=np.where(ema2>0, ema1/ema2, 1)
    mass=np.zeros(len(high))
    for i in range(period-1, len(high)):
        mass[i]=np.sum(ratio[i-period+1:i+1])
    return mass

def mass_01(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<45: return _neutral("داده کافی نیست")
    mass=_mass_index(h,l); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if mass is None: return _neutral("محاسبه ناموفق")
    # Reversal bulge: mass crosses 27 then drops below 26.5
    if mass[-2]>27 and mass[-1]<26.5:
        if c[-1]>c[-3]:
            s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"BUY","confidence":72,"reason_fa":"Mass Index bulge — سیگنال بازگشت صعودی","setup":s}
        else:
            s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"SELL","confidence":72,"reason_fa":"Mass Index bulge — سیگنال بازگشت نزولی","setup":s}
    return _neutral("Bulge Mass Index شناسایی نشد")

def mass_02(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<45: return _neutral("داده کافی نیست")
    mass=_mass_index(h,l); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if mass is None: return _neutral("محاسبه ناموفق")
    if mass[-1]>27 and mass[-2]<=27:
        return _neutral(f"Mass Index={mass[-1]:.1f} — هشدار بازگشت | منتظر تایید")
    if mass[-1]<26 and mass[-2]>=26:
        if c[-1]>c[-5]:
            s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"BUY","confidence":68,"reason_fa":"Mass Index زیر ۲۶ + قیمت صعودی","setup":s}
        else:
            s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"SELL","confidence":68,"reason_fa":"Mass Index زیر ۲۶ + قیمت نزولی","setup":s}
    return _neutral("عبور آستانه Mass شناسایی نشد")

def mass_03(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<45: return _neutral("داده کافی نیست")
    mass=_mass_index(h,l); ema20=_ema(c,20); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if mass is None or ema20 is None: return _neutral("محاسبه ناموفق")
    if mass[-1]<25 and c[-1]>ema20[-1]:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":70,"reason_fa":"Mass Index پایین + روند صعودی — ادامه","setup":s}
    if mass[-1]<25 and c[-1]<ema20[-1]:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":70,"reason_fa":"Mass Index پایین + روند نزولی — ادامه","setup":s}
    return _neutral("Mass+Trend شناسایی نشد")

def mass_04(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<50: return _neutral("داده کافی نیست")
    mass=_mass_index(h,l); ema9=_ema(c,9); ema21=_ema(c,21); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if mass is None or ema9 is None or ema21 is None: return _neutral("محاسبه ناموفق")
    if mass[-2]>27 and mass[-1]<26.5 and ema9[-1]>ema21[-1]:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":76,"reason_fa":"Mass bulge + EMA صعودی — بازگشت تایید","setup":s}
    if mass[-2]>27 and mass[-1]<26.5 and ema9[-1]<ema21[-1]:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":76,"reason_fa":"Mass bulge + EMA نزولی — بازگشت تایید","setup":s}
    return _neutral("Mass+EMA شناسایی نشد")

def mass_05(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<50: return _neutral("داده کافی نیست")
    mass=_mass_index(h,l); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if mass is None: return _neutral("محاسبه ناموفق")
    if c[-1]>c[-10] and mass[-1]>mass[-10]:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":65,"reason_fa":"Mass Index صعودی + قیمت صعودی — تایید","setup":s}
    if c[-1]<c[-10] and mass[-1]>mass[-10]:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":65,"reason_fa":"Mass Index صعودی + قیمت نزولی — نوسان بالا","setup":s}
    return _neutral("Mass Divergence شناسایی نشد")

MASS_STRATEGIES = [
    {"id":"MASS_01","name":"Mass Bulge","name_fa":"بالج Mass","func":mass_01},
    {"id":"MASS_02","name":"Mass Threshold","name_fa":"آستانه Mass","func":mass_02},
    {"id":"MASS_03","name":"Mass+Trend","name_fa":"Mass+روند","func":mass_03},
    {"id":"MASS_04","name":"Mass+EMA","name_fa":"Mass+EMA","func":mass_04},
    {"id":"MASS_05","name":"Mass Divergence","name_fa":"واگرایی Mass","func":mass_05},
]
