"""
Supertrend Pack (5)
STREND_01: Classic Flip
STREND_02: Multi-Period
STREND_03: +ADX
STREND_04: +Volume
STREND_05: Trail
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


def _supertrend(high, low, close, period=10, multiplier=3.0):
    atr = _atr(high, low, close, period)
    if atr is None: return None, None
    n = len(close); st = np.zeros(n); direction = np.ones(n)
    upper = (high+low)/2 + multiplier*atr; lower = (high+low)/2 - multiplier*atr
    for i in range(1, n):
        if close[i-1] > upper[i-1]: direction[i] = 1
        elif close[i-1] < lower[i-1]: direction[i] = -1
        else: direction[i] = direction[i-1]
        st[i] = lower[i] if direction[i] == 1 else upper[i]
    return st, direction

def strend_01(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<15: return _neutral("داده کافی نیست")
    st,d = _supertrend(h,l,c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if st is None: return _neutral("محاسبه ناموفق")
    if d[-1]==1 and d[-2]==-1:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":72,"reason_fa":"سوپرترند صعودی شد — تغییر روند","setup":s}
    if d[-1]==-1 and d[-2]==1:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":72,"reason_fa":"سوپرترند نزولی شد — تغییر روند","setup":s}
    return _neutral("تغییر سوپرترند شناسایی نشد")

def strend_02(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<20: return _neutral("داده کافی نیست")
    _,d1 = _supertrend(h,l,c,10,2); _,d2 = _supertrend(h,l,c,20,3)
    atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if d1 is None or d2 is None: return _neutral("محاسبه ناموفق")
    if d1[-1]==1 and d2[-1]==1:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":78,"reason_fa":"سوپرترند دوگانه صعودی — روند قوی","setup":s}
    if d1[-1]==-1 and d2[-1]==-1:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":78,"reason_fa":"سوپرترند دوگانه نزولی — روند قوی","setup":s}
    return _neutral("هم‌راستایی سوپرترند شناسایی نشد")

def strend_03(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<35: return _neutral("داده کافی نیست")
    _,d = _supertrend(h,l,c); adx,pdi,mdi = _adx(h,l,c)
    atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if d is None or adx is None: return _neutral("محاسبه ناموفق")
    if d[-1]==1 and d[-2]==-1 and adx[-1]>25:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":82,"reason_fa":f"سوپرترند صعودی + ADX={adx[-1]:.0f} — سیگنال قوی","setup":s}
    if d[-1]==-1 and d[-2]==1 and adx[-1]>25:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":82,"reason_fa":f"سوپرترند نزولی + ADX={adx[-1]:.0f} — سیگنال قوی","setup":s}
    return _neutral("سوپرترند+ADX شناسایی نشد")

def strend_04(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<20: return _neutral("داده کافی نیست")
    st,d = _supertrend(h,l,c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if d is None: return _neutral("محاسبه ناموفق")
    if "tick_volume" in df.columns: v = df["tick_volume"].values.astype(float)
    elif "volume" in df.columns: v = df["volume"].values.astype(float)
    else: v = np.ones(len(c))
    va = np.mean(v[-20:])
    if d[-1]==1 and d[-2]==-1 and v[-1]>va*1.3:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":76,"reason_fa":"سوپرترند صعودی + حجم بالا","setup":s}
    if d[-1]==-1 and d[-2]==1 and v[-1]>va*1.3:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":76,"reason_fa":"سوپرترند نزولی + حجم بالا","setup":s}
    return _neutral("سوپرترند+حجم شناسایی نشد")

def strend_05(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<15: return _neutral("داده کافی نیست")
    st,d = _supertrend(h,l,c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if d is None: return _neutral("محاسبه ناموفق")
    cnt=0; dr=d[-1]
    for i in range(-1,-min(15,len(d)),-1):
        if d[i]==dr: cnt+=1
        else: break
    if dr==1 and cnt>=5:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s:
            s["stop_loss"]=round(st[-1],6)
            return {"signal":"BUY","confidence":70,"reason_fa":f"تریل سوپرترند — {cnt} کندل صعودی | SL=ST","setup":s}
    if dr==-1 and cnt>=5:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s:
            s["stop_loss"]=round(st[-1],6)
            return {"signal":"SELL","confidence":70,"reason_fa":f"تریل سوپرترند — {cnt} کندل نزولی | SL=ST","setup":s}
    return _neutral("تریل سوپرترند شناسایی نشد")

STREND_STRATEGIES = [
    {"id":"STREND_01","name":"Supertrend Flip","name_fa":"تغییر سوپرترند","func":strend_01},
    {"id":"STREND_02","name":"Multi Supertrend","name_fa":"سوپرترند دوگانه","func":strend_02},
    {"id":"STREND_03","name":"Supertrend+ADX","name_fa":"سوپرترند+ADX","func":strend_03},
    {"id":"STREND_04","name":"Supertrend+Vol","name_fa":"سوپرترند+حجم","func":strend_04},
    {"id":"STREND_05","name":"Supertrend Trail","name_fa":"تریل سوپرترند","func":strend_05},
]
