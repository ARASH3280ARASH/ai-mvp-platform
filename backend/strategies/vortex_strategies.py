"""
Vortex Pack (5)
VORTEX_01: Cross
VORTEX_02: Extreme
VORTEX_03: Trend
VORTEX_04: +ADX
VORTEX_05: Divergence
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


def _vortex(high, low, close, period=14):
    if len(high)<period+1: return None, None
    n=len(high); vmp=np.zeros(n); vmm=np.zeros(n); tr=np.zeros(n)
    for i in range(1,n):
        vmp[i]=abs(high[i]-low[i-1]); vmm[i]=abs(low[i]-high[i-1])
        tr[i]=max(high[i]-low[i],abs(high[i]-close[i-1]),abs(low[i]-close[i-1]))
    vip=np.zeros(n); vim=np.zeros(n)
    for i in range(period,n):
        s_tr=np.sum(tr[i-period+1:i+1])
        if s_tr>0:
            vip[i]=np.sum(vmp[i-period+1:i+1])/s_tr
            vim[i]=np.sum(vmm[i-period+1:i+1])/s_tr
    return vip, vim

def vortex_01(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<20: return _neutral("داده کافی نیست")
    vip,vim=_vortex(h,l,c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if vip is None: return _neutral("محاسبه ناموفق")
    if vip[-1]>vim[-1] and vip[-2]<=vim[-2]:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":70,"reason_fa":"تقاطع صعودی Vortex — VI+ بالای VI-","setup":s}
    if vim[-1]>vip[-1] and vim[-2]<=vip[-2]:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":70,"reason_fa":"تقاطع نزولی Vortex — VI- بالای VI+","setup":s}
    return _neutral("تقاطع Vortex شناسایی نشد")

def vortex_02(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<20: return _neutral("داده کافی نیست")
    vip,vim=_vortex(h,l,c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if vip is None: return _neutral("محاسبه ناموفق")
    diff=vip[-1]-vim[-1]
    if diff>0.3:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":75,"reason_fa":f"Vortex اکستریم صعودی — فاصله={diff:.2f}","setup":s}
    if diff<-0.3:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":75,"reason_fa":f"Vortex اکستریم نزولی — فاصله={diff:.2f}","setup":s}
    return _neutral("اکستریم Vortex شناسایی نشد")

def vortex_03(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<25: return _neutral("داده کافی نیست")
    vip,vim=_vortex(h,l,c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if vip is None: return _neutral("محاسبه ناموفق")
    above=sum(1 for i in range(-5,0) if vip[i]>vim[i])
    below=sum(1 for i in range(-5,0) if vim[i]>vip[i])
    if above>=4:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":68,"reason_fa":f"روند Vortex صعودی — {above}/5","setup":s}
    if below>=4:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":68,"reason_fa":f"روند Vortex نزولی — {below}/5","setup":s}
    return _neutral("روند Vortex شناسایی نشد")

def vortex_04(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<35: return _neutral("داده کافی نیست")
    vip,vim=_vortex(h,l,c); adx,pdi,mdi=_adx(h,l,c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if vip is None or adx is None: return _neutral("محاسبه ناموفق")
    if vip[-1]>vim[-1] and adx[-1]>25:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":78,"reason_fa":f"Vortex صعودی + ADX={adx[-1]:.0f}","setup":s}
    if vim[-1]>vip[-1] and adx[-1]>25:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":78,"reason_fa":f"Vortex نزولی + ADX={adx[-1]:.0f}","setup":s}
    return _neutral("Vortex+ADX شناسایی نشد")

def vortex_05(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<30: return _neutral("داده کافی نیست")
    vip,vim=_vortex(h,l,c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if vip is None: return _neutral("محاسبه ناموفق")
    vdiff=vip-vim
    if c[-1]>c[-10] and vdiff[-1]<vdiff[-10]:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":66,"reason_fa":"واگرایی نزولی Vortex","setup":s}
    if c[-1]<c[-10] and vdiff[-1]>vdiff[-10]:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":66,"reason_fa":"واگرایی صعودی Vortex","setup":s}
    return _neutral("واگرایی Vortex شناسایی نشد")

VORTEX_STRATEGIES = [
    {"id":"VORTEX_01","name":"Vortex Cross","name_fa":"تقاطع Vortex","func":vortex_01},
    {"id":"VORTEX_02","name":"Vortex Extreme","name_fa":"اکستریم Vortex","func":vortex_02},
    {"id":"VORTEX_03","name":"Vortex Trend","name_fa":"روند Vortex","func":vortex_03},
    {"id":"VORTEX_04","name":"Vortex+ADX","name_fa":"Vortex+ADX","func":vortex_04},
    {"id":"VORTEX_05","name":"Vortex Divergence","name_fa":"واگرایی Vortex","func":vortex_05},
]
