"""
ADX Advanced Pack (5)
ADX_ADV_01: DI Cross
ADX_ADV_02: ADX Rising
ADX_ADV_03: ADX Threshold
ADX_ADV_04: ADX+EMA
ADX_ADV_05: ADX Divergence
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


def adx_adv_01(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<35: return _neutral("داده کافی نیست")
    adx,pdi,mdi = _adx(h,l,c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if adx is None: return _neutral("محاسبه ناموفق")
    if pdi[-1]>mdi[-1] and pdi[-2]<=mdi[-2] and adx[-1]>20:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":75,"reason_fa":f"تقاطع +DI بالای -DI + ADX={adx[-1]:.0f}","setup":s}
    if mdi[-1]>pdi[-1] and mdi[-2]<=pdi[-2] and adx[-1]>20:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":75,"reason_fa":f"تقاطع -DI بالای +DI + ADX={adx[-1]:.0f}","setup":s}
    return _neutral("تقاطع DI شناسایی نشد")

def adx_adv_02(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<35: return _neutral("داده کافی نیست")
    adx,pdi,mdi = _adx(h,l,c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if adx is None: return _neutral("محاسبه ناموفق")
    rising = adx[-1]>adx[-2]>adx[-3] and adx[-1]>25
    if rising and pdi[-1]>mdi[-1]:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":78,"reason_fa":f"ADX صعودی ({adx[-1]:.0f}) + DI مثبت — روند قوی","setup":s}
    if rising and mdi[-1]>pdi[-1]:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":78,"reason_fa":f"ADX صعودی ({adx[-1]:.0f}) + DI منفی — روند نزولی قوی","setup":s}
    return _neutral("ADX صعودی شناسایی نشد")

def adx_adv_03(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<35: return _neutral("داده کافی نیست")
    adx,pdi,mdi = _adx(h,l,c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if adx is None: return _neutral("محاسبه ناموفق")
    if adx[-2]<25 and adx[-1]>=25:
        if pdi[-1]>mdi[-1]:
            s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"BUY","confidence":72,"reason_fa":"ADX عبور ۲۵ + DI مثبت — شروع روند","setup":s}
        else:
            s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"SELL","confidence":72,"reason_fa":"ADX عبور ۲۵ + DI منفی — شروع روند نزولی","setup":s}
    return _neutral("عبور آستانه ADX شناسایی نشد")

def adx_adv_04(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<55: return _neutral("داده کافی نیست")
    adx,pdi,mdi = _adx(h,l,c); ema50=_ema(c,50); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if adx is None or ema50 is None: return _neutral("محاسبه ناموفق")
    if adx[-1]>25 and pdi[-1]>mdi[-1] and c[-1]>ema50[-1]:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":80,"reason_fa":"ADX قوی + DI مثبت + بالای EMA50","setup":s}
    if adx[-1]>25 and mdi[-1]>pdi[-1] and c[-1]<ema50[-1]:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":80,"reason_fa":"ADX قوی + DI منفی + زیر EMA50","setup":s}
    return _neutral("ADX+EMA شناسایی نشد")

def adx_adv_05(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<40: return _neutral("داده کافی نیست")
    adx,pdi,mdi = _adx(h,l,c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if adx is None: return _neutral("محاسبه ناموفق")
    if c[-1]>c[-10] and adx[-1]<adx[-10]:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":66,"reason_fa":"واگرایی ADX نزولی — روند ضعیف","setup":s}
    if c[-1]<c[-10] and adx[-1]<adx[-10] and pdi[-1]>mdi[-1]:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":66,"reason_fa":"واگرایی ADX + DI مثبت — بازگشت","setup":s}
    return _neutral("واگرایی ADX شناسایی نشد")

ADX_ADV_STRATEGIES = [
    {"id":"ADX_ADV_01","name":"DI Cross","name_fa":"تقاطع DI","func":adx_adv_01},
    {"id":"ADX_ADV_02","name":"ADX Rising","name_fa":"ADX صعودی","func":adx_adv_02},
    {"id":"ADX_ADV_03","name":"ADX Threshold","name_fa":"آستانه ADX","func":adx_adv_03},
    {"id":"ADX_ADV_04","name":"ADX+EMA","name_fa":"ADX+EMA","func":adx_adv_04},
    {"id":"ADX_ADV_05","name":"ADX Divergence","name_fa":"واگرایی ADX","func":adx_adv_05},
]
