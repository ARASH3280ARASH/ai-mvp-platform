"""
Fisher Transform Pack (5)
FISHER_01: Zero Cross
FISHER_02: Signal Cross
FISHER_03: Extreme
FISHER_04: Divergence
FISHER_05: +EMA
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


def _fisher(high, low, period=10):
    if len(high)<period+2: return None, None
    n=len(high); val=np.zeros(n); fish=np.zeros(n); sig=np.zeros(n)
    for i in range(period-1, n):
        hh=np.max(high[i-period+1:i+1]); ll=np.min(low[i-period+1:i+1])
        mid=(high[i]+low[i])/2
        if hh!=ll: raw=(mid-ll)/(hh-ll)-0.5
        else: raw=0
        val[i]=max(-0.999,min(0.999, 0.33*2*raw + 0.67*val[i-1]))
        if abs(val[i])>=0.999: val[i]=0.999*np.sign(val[i])
        fish[i]=0.5*np.log((1+val[i])/(1-val[i])) + 0.5*fish[i-1]
    sig[1:]=fish[:-1]
    return fish, sig

def fisher_01(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<15: return _neutral("داده کافی نیست")
    fish,sig = _fisher(h,l); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if fish is None: return _neutral("محاسبه ناموفق")
    if fish[-1]>0 and fish[-2]<=0:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":70,"reason_fa":"Fisher عبور صفر به بالا","setup":s}
    if fish[-1]<0 and fish[-2]>=0:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":70,"reason_fa":"Fisher عبور صفر به پایین","setup":s}
    return _neutral("عبور صفر Fisher شناسایی نشد")

def fisher_02(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<15: return _neutral("داده کافی نیست")
    fish,sig = _fisher(h,l); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if fish is None: return _neutral("محاسبه ناموفق")
    if fish[-1]>sig[-1] and fish[-2]<=sig[-2]:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":68,"reason_fa":"Fisher بالای سیگنال","setup":s}
    if fish[-1]<sig[-1] and fish[-2]>=sig[-2]:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":68,"reason_fa":"Fisher زیر سیگنال","setup":s}
    return _neutral("تقاطع سیگنال Fisher شناسایی نشد")

def fisher_03(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<20: return _neutral("داده کافی نیست")
    fish,_ = _fisher(h,l); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if fish is None: return _neutral("محاسبه ناموفق")
    if fish[-1]<-1.5 and fish[-1]>fish[-2]:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":72,"reason_fa":f"Fisher اکستریم پایین ({fish[-1]:.2f}) + بازگشت","setup":s}
    if fish[-1]>1.5 and fish[-1]<fish[-2]:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":72,"reason_fa":f"Fisher اکستریم بالا ({fish[-1]:.2f}) + بازگشت","setup":s}
    return _neutral("اکستریم Fisher شناسایی نشد")

def fisher_04(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<25: return _neutral("داده کافی نیست")
    fish,_ = _fisher(h,l); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if fish is None: return _neutral("محاسبه ناموفق")
    if c[-1]>c[-10] and fish[-1]<fish[-10]:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":66,"reason_fa":"واگرایی نزولی Fisher","setup":s}
    if c[-1]<c[-10] and fish[-1]>fish[-10]:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":66,"reason_fa":"واگرایی صعودی Fisher","setup":s}
    return _neutral("واگرایی Fisher شناسایی نشد")

def fisher_05(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<25: return _neutral("داده کافی نیست")
    fish,_ = _fisher(h,l); ema20=_ema(c,20); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if fish is None or ema20 is None: return _neutral("محاسبه ناموفق")
    if fish[-1]>0 and fish[-2]<=0 and c[-1]>ema20[-1]:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":75,"reason_fa":"Fisher مثبت + بالای EMA20","setup":s}
    if fish[-1]<0 and fish[-2]>=0 and c[-1]<ema20[-1]:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":75,"reason_fa":"Fisher منفی + زیر EMA20","setup":s}
    return _neutral("Fisher+EMA شناسایی نشد")

FISHER_STRATEGIES = [
    {"id":"FISHER_01","name":"Fisher Zero","name_fa":"عبور صفر Fisher","func":fisher_01},
    {"id":"FISHER_02","name":"Fisher Signal","name_fa":"تقاطع Fisher","func":fisher_02},
    {"id":"FISHER_03","name":"Fisher Extreme","name_fa":"اکستریم Fisher","func":fisher_03},
    {"id":"FISHER_04","name":"Fisher Divergence","name_fa":"واگرایی Fisher","func":fisher_04},
    {"id":"FISHER_05","name":"Fisher+EMA","name_fa":"Fisher+EMA","func":fisher_05},
]
