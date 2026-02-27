"""
DPO Pack (5)
DPO_01: Zero Cross
DPO_02: Extreme
DPO_03: Divergence
DPO_04: Trend
DPO_05: +EMA
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


def _dpo(close, period=20):
    if len(close)<period+period//2+1: return None
    shift=period//2+1; sma=np.zeros(len(close))
    for i in range(period-1,len(close)): sma[i]=np.mean(close[i-period+1:i+1])
    dpo=np.zeros(len(close))
    for i in range(shift,len(close)): dpo[i]=close[i]-sma[i-shift] if sma[i-shift]>0 else 0
    return dpo

def dpo_01(df, indicators, symbol, timeframe):
    c=df["close"].values; h,l=df["high"].values,df["low"].values
    if len(c)<35: return _neutral("داده کافی نیست")
    dpo=_dpo(c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if dpo is None: return _neutral("محاسبه ناموفق")
    if dpo[-1]>0 and dpo[-2]<=0:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":65,"reason_fa":"DPO عبور صفر به بالا — چرخه صعودی","setup":s}
    if dpo[-1]<0 and dpo[-2]>=0:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":65,"reason_fa":"DPO عبور صفر به پایین — چرخه نزولی","setup":s}
    return _neutral("عبور صفر DPO شناسایی نشد")

def dpo_02(df, indicators, symbol, timeframe):
    c=df["close"].values; h,l=df["high"].values,df["low"].values
    if len(c)<35: return _neutral("داده کافی نیست")
    dpo=_dpo(c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if dpo is None: return _neutral("محاسبه ناموفق")
    avg=np.mean(np.abs(dpo[-20:])); std=np.std(dpo[-20:])
    if std>0:
        z=dpo[-1]/std
        if z<-2 and dpo[-1]>dpo[-2]:
            s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"BUY","confidence":70,"reason_fa":f"DPO در کف اکستریم + بازگشت","setup":s}
        if z>2 and dpo[-1]<dpo[-2]:
            s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"SELL","confidence":70,"reason_fa":f"DPO در سقف اکستریم + بازگشت","setup":s}
    return _neutral("اکستریم DPO شناسایی نشد")

def dpo_03(df, indicators, symbol, timeframe):
    c=df["close"].values; h,l=df["high"].values,df["low"].values
    if len(c)<40: return _neutral("داده کافی نیست")
    dpo=_dpo(c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if dpo is None: return _neutral("محاسبه ناموفق")
    if c[-1]>c[-10] and dpo[-1]<dpo[-10]:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":66,"reason_fa":"واگرایی نزولی DPO","setup":s}
    if c[-1]<c[-10] and dpo[-1]>dpo[-10]:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":66,"reason_fa":"واگرایی صعودی DPO","setup":s}
    return _neutral("واگرایی DPO شناسایی نشد")

def dpo_04(df, indicators, symbol, timeframe):
    c=df["close"].values; h,l=df["high"].values,df["low"].values
    if len(c)<35: return _neutral("داده کافی نیست")
    dpo=_dpo(c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if dpo is None: return _neutral("محاسبه ناموفق")
    above=sum(1 for i in range(-5,0) if dpo[i]>0)
    below=sum(1 for i in range(-5,0) if dpo[i]<0)
    if above>=4 and dpo[-1]>dpo[-2]:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":66,"reason_fa":f"چرخه DPO صعودی — {above}/5 مثبت","setup":s}
    if below>=4 and dpo[-1]<dpo[-2]:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":66,"reason_fa":f"چرخه DPO نزولی — {below}/5 منفی","setup":s}
    return _neutral("چرخه DPO شناسایی نشد")

def dpo_05(df, indicators, symbol, timeframe):
    c=df["close"].values; h,l=df["high"].values,df["low"].values
    if len(c)<55: return _neutral("داده کافی نیست")
    dpo=_dpo(c); ema50=_ema(c,50); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if dpo is None or ema50 is None: return _neutral("محاسبه ناموفق")
    if dpo[-1]>0 and dpo[-2]<=0 and c[-1]>ema50[-1]:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":72,"reason_fa":"DPO مثبت + بالای EMA50","setup":s}
    if dpo[-1]<0 and dpo[-2]>=0 and c[-1]<ema50[-1]:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":72,"reason_fa":"DPO منفی + زیر EMA50","setup":s}
    return _neutral("DPO+EMA شناسایی نشد")

DPO_STRATEGIES = [
    {"id":"DPO_01","name":"DPO Zero Cross","name_fa":"عبور صفر DPO","func":dpo_01},
    {"id":"DPO_02","name":"DPO Extreme","name_fa":"اکستریم DPO","func":dpo_02},
    {"id":"DPO_03","name":"DPO Divergence","name_fa":"واگرایی DPO","func":dpo_03},
    {"id":"DPO_04","name":"DPO Trend","name_fa":"چرخه DPO","func":dpo_04},
    {"id":"DPO_05","name":"DPO+EMA","name_fa":"DPO+EMA","func":dpo_05},
]
