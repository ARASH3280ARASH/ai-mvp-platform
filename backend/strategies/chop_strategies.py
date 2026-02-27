"""
Choppiness Index Pack (5)
CHOP_01: Trending
CHOP_02: Range Exit
CHOP_03: CHOP+ADX
CHOP_04: Trend Confirm
CHOP_05: CHOP Zones
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
    if len(high)<period*2+1: return None, None, None
    n=len(high); pdm=np.zeros(n); mdm=np.zeros(n); tr=np.zeros(n)
    for i in range(1,n):
        up=high[i]-high[i-1]; down=low[i-1]-low[i]
        pdm[i]=up if up>down and up>0 else 0
        mdm[i]=down if down>up and down>0 else 0
        tr[i]=max(high[i]-low[i],abs(high[i]-close[i-1]),abs(low[i]-close[i-1]))
    at=np.zeros(n); sp=np.zeros(n); sm=np.zeros(n)
    at[period]=np.mean(tr[1:period+1]); sp[period]=np.mean(pdm[1:period+1]); sm[period]=np.mean(mdm[1:period+1])
    for i in range(period+1,n):
        at[i]=(at[i-1]*(period-1)+tr[i])/period
        sp[i]=(sp[i-1]*(period-1)+pdm[i])/period
        sm[i]=(sm[i-1]*(period-1)+mdm[i])/period
    pdi=np.where(at>0,sp/at*100,0); mdi=np.where(at>0,sm/at*100,0)
    dx=np.where((pdi+mdi)>0,abs(pdi-mdi)/(pdi+mdi)*100,0)
    adx=np.zeros(n); s=period*2
    if s<n:
        adx[s]=np.mean(dx[period+1:s+1])
        for i in range(s+1,n): adx[i]=(adx[i-1]*(period-1)+dx[i])/period
    return adx, pdi, mdi

def _chop(high, low, close, period=14):
    atr = _atr(high, low, close, 1)
    if atr is None or len(high)<period+1: return None
    n=len(high); chop=np.zeros(n)
    for i in range(period, n):
        atr_sum=np.sum(atr[i-period+1:i+1])
        hh=np.max(high[i-period+1:i+1]); ll=np.min(low[i-period+1:i+1])
        rng=hh-ll
        if rng>0 and atr_sum>0:
            chop[i]=100*np.log10(atr_sum/rng)/np.log10(period)
    return chop

def chop_01(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<20: return _neutral("داده کافی نیست")
    chop=_chop(h,l,c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if chop is None: return _neutral("محاسبه ناموفق")
    if chop[-1]<38.2:
        if c[-1]>c[-3]:
            s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"BUY","confidence":72,"reason_fa":f"CHOP={chop[-1]:.0f} ترندینگ + صعودی","setup":s}
        else:
            s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"SELL","confidence":72,"reason_fa":f"CHOP={chop[-1]:.0f} ترندینگ + نزولی","setup":s}
    return _neutral("بازار ترندینگ نیست")

def chop_02(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<20: return _neutral("داده کافی نیست")
    chop=_chop(h,l,c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if chop is None: return _neutral("محاسبه ناموفق")
    if chop[-2]>61.8 and chop[-1]<61.8:
        if c[-1]>c[-3]:
            s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"BUY","confidence":70,"reason_fa":"خروج از رنج (CHOP<61.8) — شروع روند صعودی","setup":s}
        else:
            s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"SELL","confidence":70,"reason_fa":"خروج از رنج (CHOP<61.8) — شروع روند نزولی","setup":s}
    return _neutral("خروج از رنج شناسایی نشد")

def chop_03(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<35: return _neutral("داده کافی نیست")
    chop=_chop(h,l,c); adx,pdi,mdi=_adx(h,l,c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if chop is None or adx is None: return _neutral("محاسبه ناموفق")
    if chop[-1]<50 and adx[-1]>25:
        if pdi[-1]>mdi[-1]:
            s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"BUY","confidence":80,"reason_fa":f"CHOP ترندینگ + ADX={adx[-1]:.0f} صعودی","setup":s}
        else:
            s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"SELL","confidence":80,"reason_fa":f"CHOP ترندینگ + ADX={adx[-1]:.0f} نزولی","setup":s}
    return _neutral("CHOP+ADX شناسایی نشد")

def chop_04(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<25: return _neutral("داده کافی نیست")
    chop=_chop(h,l,c); ema20=_ema(c,20); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if chop is None or ema20 is None: return _neutral("محاسبه ناموفق")
    if chop[-1]<45 and c[-1]>ema20[-1] and c[-2]<=ema20[-2]:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":73,"reason_fa":"CHOP ترندینگ + عبور EMA20 صعودی","setup":s}
    if chop[-1]<45 and c[-1]<ema20[-1] and c[-2]>=ema20[-2]:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":73,"reason_fa":"CHOP ترندینگ + عبور EMA20 نزولی","setup":s}
    return _neutral("CHOP+EMA شناسایی نشد")

def chop_05(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<20: return _neutral("داده کافی نیست")
    chop=_chop(h,l,c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if chop is None: return _neutral("محاسبه ناموفق")
    if chop[-1]>61.8:
        return _neutral(f"CHOP={chop[-1]:.0f} — بازار رنج، صبر کنید")
    if chop[-1]<38.2:
        trend_up=c[-1]>c[-5]
        conf=76
        if trend_up:
            s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"BUY","confidence":conf,"reason_fa":f"CHOP={chop[-1]:.0f} زون ترند قوی صعودی","setup":s}
        else:
            s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"SELL","confidence":conf,"reason_fa":f"CHOP={chop[-1]:.0f} زون ترند قوی نزولی","setup":s}
    return _neutral(f"CHOP={chop[-1]:.0f} — زون خنثی")

CHOP_STRATEGIES = [
    {"id":"CHOP_01","name":"CHOP Trending","name_fa":"CHOP ترندینگ","func":chop_01},
    {"id":"CHOP_02","name":"CHOP Range Exit","name_fa":"خروج از رنج","func":chop_02},
    {"id":"CHOP_03","name":"CHOP+ADX","name_fa":"CHOP+ADX","func":chop_03},
    {"id":"CHOP_04","name":"CHOP+EMA","name_fa":"CHOP+EMA","func":chop_04},
    {"id":"CHOP_05","name":"CHOP Zones","name_fa":"زون‌های CHOP","func":chop_05},
]
