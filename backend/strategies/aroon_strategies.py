"""
Aroon Pack (5)
AROON_01: Cross
AROON_02: Extreme
AROON_03: Oscillator
AROON_04: Trend
AROON_05: +ADX
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

def _adx(high, low, close, period=14):
    if len(high) < period*2+1: return None, None, None
    n = len(high); pdm=np.zeros(n); mdm=np.zeros(n); tr=np.zeros(n)
    for i in range(1,n):
        up=high[i]-high[i-1]; down=low[i-1]-low[i]
        pdm[i]=up if up>down and up>0 else 0
        mdm[i]=down if down>up and down>0 else 0
        tr[i]=max(high[i]-low[i],abs(high[i]-close[i-1]),abs(low[i]-close[i-1]))
    atr=np.zeros(n); sp=np.zeros(n); sm=np.zeros(n)
    atr[period]=np.mean(tr[1:period+1]); sp[period]=np.mean(pdm[1:period+1]); sm[period]=np.mean(mdm[1:period+1])
    for i in range(period+1,n):
        atr[i]=(atr[i-1]*(period-1)+tr[i])/period
        sp[i]=(sp[i-1]*(period-1)+pdm[i])/period
        sm[i]=(sm[i-1]*(period-1)+mdm[i])/period
    pdi=np.where(atr>0,sp/atr*100,0); mdi=np.where(atr>0,sm/atr*100,0)
    dx=np.where((pdi+mdi)>0,abs(pdi-mdi)/(pdi+mdi)*100,0)
    adx=np.zeros(n); s=period*2
    if s<n:
        adx[s]=np.mean(dx[period+1:s+1])
        for i in range(s+1,n): adx[i]=(adx[i-1]*(period-1)+dx[i])/period
    return adx, pdi, mdi


def _aroon(high, low, period=25):
    if len(high)<period+1: return None, None, None
    n=len(high); up=np.zeros(n); dn=np.zeros(n)
    for i in range(period,n):
        hh=np.argmax(high[i-period:i+1])
        ll=np.argmin(low[i-period:i+1])
        up[i]=hh/period*100; dn[i]=ll/period*100
    osc=up-dn
    return up, dn, osc

def aroon_01(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<30: return _neutral("داده کافی نیست")
    up,dn,_=_aroon(h,l); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if up is None: return _neutral("محاسبه ناموفق")
    if up[-1]>dn[-1] and up[-2]<=dn[-2]:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":70,"reason_fa":"تقاطع صعودی Aroon","setup":s}
    if dn[-1]>up[-1] and dn[-2]<=up[-2]:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":70,"reason_fa":"تقاطع نزولی Aroon","setup":s}
    return _neutral("تقاطع Aroon شناسایی نشد")

def aroon_02(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<30: return _neutral("داده کافی نیست")
    up,dn,_=_aroon(h,l); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if up is None: return _neutral("محاسبه ناموفق")
    if up[-1]>90 and dn[-1]<10:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":78,"reason_fa":"Aroon Up>90 + Down<10 — روند صعودی قوی","setup":s}
    if dn[-1]>90 and up[-1]<10:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":78,"reason_fa":"Aroon Down>90 + Up<10 — روند نزولی قوی","setup":s}
    return _neutral("اکستریم Aroon شناسایی نشد")

def aroon_03(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<30: return _neutral("داده کافی نیست")
    _,_,osc=_aroon(h,l); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if osc is None: return _neutral("محاسبه ناموفق")
    if osc[-1]>0 and osc[-2]<=0:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":68,"reason_fa":"اسیلاتور Aroon مثبت شد","setup":s}
    if osc[-1]<0 and osc[-2]>=0:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":68,"reason_fa":"اسیلاتور Aroon منفی شد","setup":s}
    return _neutral("تغییر اسیلاتور Aroon شناسایی نشد")

def aroon_04(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<35: return _neutral("داده کافی نیست")
    up,dn,_=_aroon(h,l); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if up is None: return _neutral("محاسبه ناموفق")
    above=sum(1 for i in range(-5,0) if up[i]>dn[i])
    below=sum(1 for i in range(-5,0) if dn[i]>up[i])
    if above>=4:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":67,"reason_fa":f"روند Aroon صعودی — {above}/5","setup":s}
    if below>=4:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":67,"reason_fa":f"روند Aroon نزولی — {below}/5","setup":s}
    return _neutral("روند Aroon شناسایی نشد")

def aroon_05(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<40: return _neutral("داده کافی نیست")
    up,dn,_=_aroon(h,l); adx,pdi,mdi=_adx(h,l,c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if up is None or adx is None: return _neutral("محاسبه ناموفق")
    if up[-1]>70 and adx[-1]>25 and pdi[-1]>mdi[-1]:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":80,"reason_fa":"Aroon+ADX صعودی — تایید دوگانه","setup":s}
    if dn[-1]>70 and adx[-1]>25 and mdi[-1]>pdi[-1]:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":80,"reason_fa":"Aroon+ADX نزولی — تایید دوگانه","setup":s}
    return _neutral("Aroon+ADX شناسایی نشد")

AROON_STRATEGIES = [
    {"id":"AROON_01","name":"Aroon Cross","name_fa":"تقاطع Aroon","func":aroon_01},
    {"id":"AROON_02","name":"Aroon Extreme","name_fa":"اکستریم Aroon","func":aroon_02},
    {"id":"AROON_03","name":"Aroon Oscillator","name_fa":"اسیلاتور Aroon","func":aroon_03},
    {"id":"AROON_04","name":"Aroon Trend","name_fa":"روند Aroon","func":aroon_04},
    {"id":"AROON_05","name":"Aroon+ADX","name_fa":"Aroon+ADX","func":aroon_05},
]
