"""
Whilber-AI — Combo Strategy Pack (18)
Multi-indicator confirmation strategies for highest-quality signals.
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

def _rsi(close, period=14):
    if len(close) < period+1: return None
    gains = np.zeros(len(close)); losses = np.zeros(len(close))
    for i in range(1, len(close)):
        d = close[i]-close[i-1]
        if d > 0: gains[i] = d
        else: losses[i] = -d
    ag = _ema(gains, period); al = _ema(losses, period)
    if ag is None or al is None: return None
    rs = np.where(al > 0, ag/al, 100)
    return 100 - 100/(1+rs)

def _bb(close, period=20, std=2):
    if len(close) < period: return None, None, None
    sma = np.array([np.mean(close[max(0,i-period+1):i+1]) for i in range(len(close))])
    s = np.array([np.std(close[max(0,i-period+1):i+1]) for i in range(len(close))])
    return sma, sma+std*s, sma-std*s

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

def _supertrend(high, low, close, period=10, multiplier=3.0):
    atr = _atr(high, low, close, period)
    if atr is None: return None, None
    n=len(close); st=np.zeros(n); d=np.ones(n)
    upper=(high+low)/2+multiplier*atr; lower=(high+low)/2-multiplier*atr
    for i in range(1,n):
        if close[i-1]>upper[i-1]: d[i]=1
        elif close[i-1]<lower[i-1]: d[i]=-1
        else: d[i]=d[i-1]
        st[i]=lower[i] if d[i]==1 else upper[i]
    return st, d

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
    sl_d=atr_val*1.5; tp1_d=sl_d*rr_min; tp2_d=sl_d*3.0
    if direction=="BUY": sl,tp1,tp2=entry-sl_d,entry+tp1_d,entry+tp2_d
    else: sl,tp1,tp2=entry+sl_d,entry-tp1_d,entry-tp2_d
    return {"has_setup":True,"direction":direction,"direction_fa":"خرید" if direction=="BUY" else "فروش",
            "entry":round(entry,6),"stop_loss":round(sl,6),"tp1":round(tp1,6),"tp2":round(tp2,6),
            "rr1":round(tp1_d/sl_d,2),"rr2":round(tp2_d/sl_d,2),
            "sl_pips":round(sl_d/pip,1) if pip>0 else 0,"tp1_pips":round(tp1_d/pip,1) if pip>0 else 0}

def _n(r):
    return {"signal":"NEUTRAL","confidence":0,"reason_fa":r,"setup":{"has_setup":False}}


# ── 1. RSI + BB ──
def combo_01(df, ind, symbol, tf):
    c=df["close"].values; h,l=df["high"].values,df["low"].values
    if len(c)<25: return _n("داده کافی نیست")
    rsi=_rsi(c); _,ub,lb=_bb(c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if rsi is None or lb is None: return _n("محاسبه ناموفق")
    if rsi[-1]<30 and c[-1]<=lb[-1]:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":82,"reason_fa":"RSI اشباع فروش + برخورد باند پایین BB","setup":s}
    if rsi[-1]>70 and c[-1]>=ub[-1]:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":82,"reason_fa":"RSI اشباع خرید + برخورد باند بالای BB","setup":s}
    return _n("RSI+BB شناسایی نشد")

# ── 2. EMA Cross + ADX ──
def combo_02(df, ind, symbol, tf):
    c=df["close"].values; h,l=df["high"].values,df["low"].values
    if len(c)<35: return _n("داده کافی نیست")
    ema9=_ema(c,9); ema21=_ema(c,21); adx,pdi,mdi=_adx(h,l,c)
    atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if ema9 is None or ema21 is None or adx is None: return _n("محاسبه ناموفق")
    if ema9[-1]>ema21[-1] and ema9[-2]<=ema21[-2] and adx[-1]>25:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":85,"reason_fa":f"تقاطع EMA صعودی + ADX={adx[-1]:.0f} — روند قوی","setup":s}
    if ema9[-1]<ema21[-1] and ema9[-2]>=ema21[-2] and adx[-1]>25:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":85,"reason_fa":f"تقاطع EMA نزولی + ADX={adx[-1]:.0f} — روند قوی","setup":s}
    return _n("EMA+ADX شناسایی نشد")

# ── 3. RSI + EMA + Volume ──
def combo_03(df, ind, symbol, tf):
    c=df["close"].values; h,l=df["high"].values,df["low"].values
    if len(c)<25: return _n("داده کافی نیست")
    rsi=_rsi(c); ema20=_ema(c,20); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if "tick_volume" in df.columns: v=df["tick_volume"].values.astype(float)
    elif "volume" in df.columns: v=df["volume"].values.astype(float)
    else: v=np.ones(len(c))
    if rsi is None or ema20 is None: return _n("محاسبه ناموفق")
    va=np.mean(v[-20:])
    if rsi[-1]<35 and c[-1]>ema20[-1] and v[-1]>va*1.2:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":80,"reason_fa":"RSI پولبک + بالای EMA + حجم بالا","setup":s}
    if rsi[-1]>65 and c[-1]<ema20[-1] and v[-1]>va*1.2:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":80,"reason_fa":"RSI اشباع + زیر EMA + حجم بالا","setup":s}
    return _n("RSI+EMA+Vol شناسایی نشد")

# ── 4. Supertrend + RSI ──
def combo_04(df, ind, symbol, tf):
    c=df["close"].values; h,l=df["high"].values,df["low"].values
    if len(c)<20: return _n("داده کافی نیست")
    st,d=_supertrend(h,l,c); rsi=_rsi(c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if d is None or rsi is None: return _n("محاسبه ناموفق")
    if d[-1]==1 and d[-2]==-1 and rsi[-1]<60:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":80,"reason_fa":"سوپرترند صعودی + RSI غیراشباع — ورود بهینه","setup":s}
    if d[-1]==-1 and d[-2]==1 and rsi[-1]>40:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":80,"reason_fa":"سوپرترند نزولی + RSI غیراشباع — ورود بهینه","setup":s}
    return _n("ST+RSI شناسایی نشد")

# ── 5. BB Squeeze + ADX Rising ──
def combo_05(df, ind, symbol, tf):
    c=df["close"].values; h,l=df["high"].values,df["low"].values
    if len(c)<35: return _n("داده کافی نیست")
    mid,ub,lb=_bb(c); adx,pdi,mdi=_adx(h,l,c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if ub is None or adx is None: return _n("محاسبه ناموفق")
    bw=(ub[-1]-lb[-1])/mid[-1]*100 if mid[-1]>0 else 0
    bw_prev=(ub[-5]-lb[-5])/mid[-5]*100 if mid[-5]>0 else 0
    if bw<bw_prev*0.7 and adx[-1]>adx[-2]>adx[-3]:
        if pdi[-1]>mdi[-1]:
            s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"BUY","confidence":82,"reason_fa":"BB فشرده + ADX صعودی — انفجار صعودی","setup":s}
        else:
            s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"SELL","confidence":82,"reason_fa":"BB فشرده + ADX صعودی — انفجار نزولی","setup":s}
    return _n("BB Squeeze+ADX شناسایی نشد")

# ── 6. Triple EMA + RSI Filter ──
def combo_06(df, ind, symbol, tf):
    c=df["close"].values; h,l=df["high"].values,df["low"].values
    if len(c)<55: return _n("داده کافی نیست")
    e8=_ema(c,8); e21=_ema(c,21); e50=_ema(c,50); rsi=_rsi(c)
    atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if e8 is None or e21 is None or e50 is None or rsi is None: return _n("محاسبه ناموفق")
    if e8[-1]>e21[-1]>e50[-1] and 40<rsi[-1]<70:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":84,"reason_fa":"EMA سه‌گانه صعودی + RSI متعادل","setup":s}
    if e8[-1]<e21[-1]<e50[-1] and 30<rsi[-1]<60:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":84,"reason_fa":"EMA سه‌گانه نزولی + RSI متعادل","setup":s}
    return _n("Triple EMA+RSI شناسایی نشد")

# ── 7. ADX + Supertrend + EMA ──
def combo_07(df, ind, symbol, tf):
    c=df["close"].values; h,l=df["high"].values,df["low"].values
    if len(c)<55: return _n("داده کافی نیست")
    adx,pdi,mdi=_adx(h,l,c); _,d=_supertrend(h,l,c); ema50=_ema(c,50)
    atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if adx is None or d is None or ema50 is None: return _n("محاسبه ناموفق")
    if adx[-1]>25 and d[-1]==1 and c[-1]>ema50[-1]:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":88,"reason_fa":f"ADX({adx[-1]:.0f})+ST صعودی+بالای EMA50 — سیگنال طلایی","setup":s}
    if adx[-1]>25 and d[-1]==-1 and c[-1]<ema50[-1]:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":88,"reason_fa":f"ADX({adx[-1]:.0f})+ST نزولی+زیر EMA50 — سیگنال طلایی","setup":s}
    return _n("سیگنال طلایی شناسایی نشد")

# ── 8. RSI Divergence + BB Touch ──
def combo_08(df, ind, symbol, tf):
    c=df["close"].values; h,l=df["high"].values,df["low"].values
    if len(c)<30: return _n("داده کافی نیست")
    rsi=_rsi(c); _,ub,lb=_bb(c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if rsi is None or lb is None: return _n("محاسبه ناموفق")
    if c[-1]<c[-10] and rsi[-1]>rsi[-10] and c[-1]<=lb[-1]:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":85,"reason_fa":"واگرایی صعودی RSI + باند پایین BB — بازگشت قوی","setup":s}
    if c[-1]>c[-10] and rsi[-1]<rsi[-10] and c[-1]>=ub[-1]:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":85,"reason_fa":"واگرایی نزولی RSI + باند بالای BB — بازگشت قوی","setup":s}
    return _n("RSI Div+BB شناسایی نشد")

# ── 9. EMA200 + RSI + ADX ──
def combo_09(df, ind, symbol, tf):
    c=df["close"].values; h,l=df["high"].values,df["low"].values
    if len(c)<205: return _n("داده کافی نیست")
    ema200=_ema(c,200); rsi=_rsi(c); adx,pdi,mdi=_adx(h,l,c)
    atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if ema200 is None or rsi is None or adx is None: return _n("محاسبه ناموفق")
    if c[-1]>ema200[-1] and rsi[-1]>50 and adx[-1]>20 and pdi[-1]>mdi[-1]:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":86,"reason_fa":"بالای EMA200+RSI>50+ADX مثبت — trend following","setup":s}
    if c[-1]<ema200[-1] and rsi[-1]<50 and adx[-1]>20 and mdi[-1]>pdi[-1]:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":86,"reason_fa":"زیر EMA200+RSI<50+ADX منفی — trend following","setup":s}
    return _n("EMA200 Trend شناسایی نشد")

# ── 10. Stochastic + BB ──
def combo_10(df, ind, symbol, tf):
    c=df["close"].values; h,l=df["high"].values,df["low"].values
    if len(c)<25: return _n("داده کافی نیست")
    _,ub,lb=_bb(c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    # Stoch calc
    k_p=14
    k=np.zeros(len(c))
    for i in range(k_p-1,len(c)):
        hh=np.max(h[i-k_p+1:i+1]); ll=np.min(l[i-k_p+1:i+1])
        k[i]=(c[i]-ll)/(hh-ll)*100 if hh!=ll else 50
    if lb is None: return _n("محاسبه ناموفق")
    if k[-1]<20 and c[-1]<=lb[-1]:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":80,"reason_fa":"Stoch اشباع فروش + باند پایین BB","setup":s}
    if k[-1]>80 and c[-1]>=ub[-1]:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":80,"reason_fa":"Stoch اشباع خرید + باند بالای BB","setup":s}
    return _n("Stoch+BB شناسایی نشد")

# ── 11. MACD + EMA + Volume ──
def combo_11(df, ind, symbol, tf):
    c=df["close"].values; h,l=df["high"].values,df["low"].values
    if len(c)<35: return _n("داده کافی نیست")
    e12=_ema(c,12); e26=_ema(c,26); e50=_ema(c,50)
    atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if "tick_volume" in df.columns: v=df["tick_volume"].values.astype(float)
    else: v=np.ones(len(c))
    if e12 is None or e26 is None or e50 is None: return _n("محاسبه ناموفق")
    macd=e12-e26; va=np.mean(v[-20:])
    if macd[-1]>0 and macd[-2]<=0 and c[-1]>e50[-1] and v[-1]>va:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":82,"reason_fa":"MACD صعودی + بالای EMA50 + حجم تایید","setup":s}
    if macd[-1]<0 and macd[-2]>=0 and c[-1]<e50[-1] and v[-1]>va:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":82,"reason_fa":"MACD نزولی + زیر EMA50 + حجم تایید","setup":s}
    return _n("MACD+EMA+Vol شناسایی نشد")

# ── 12. RSI + Supertrend + ADX ──
def combo_12(df, ind, symbol, tf):
    c=df["close"].values; h,l=df["high"].values,df["low"].values
    if len(c)<35: return _n("داده کافی نیست")
    rsi=_rsi(c); _,d=_supertrend(h,l,c); adx,pdi,mdi=_adx(h,l,c)
    atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if rsi is None or d is None or adx is None: return _n("محاسبه ناموفق")
    if d[-1]==1 and rsi[-1]>50 and rsi[-1]<70 and adx[-1]>25:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":86,"reason_fa":"ST صعودی+RSI متعادل+ADX قوی — تریپل تایید","setup":s}
    if d[-1]==-1 and rsi[-1]<50 and rsi[-1]>30 and adx[-1]>25:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":86,"reason_fa":"ST نزولی+RSI متعادل+ADX قوی — تریپل تایید","setup":s}
    return _n("Triple Confirm شناسایی نشد")

# ── 13. BB Width + RSI Extreme ──
def combo_13(df, ind, symbol, tf):
    c=df["close"].values; h,l=df["high"].values,df["low"].values
    if len(c)<25: return _n("داده کافی نیست")
    rsi=_rsi(c); mid,ub,lb=_bb(c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if rsi is None or ub is None: return _n("محاسبه ناموفق")
    bw=(ub[-1]-lb[-1])/mid[-1] if mid[-1]>0 else 0
    bw_avg=np.mean([(ub[i]-lb[i])/mid[i] for i in range(-20,-1) if mid[i]>0])
    if bw>bw_avg*1.5 and rsi[-1]<25:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":78,"reason_fa":"BB پهن + RSI اکستریم پایین — بازگشت","setup":s}
    if bw>bw_avg*1.5 and rsi[-1]>75:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":78,"reason_fa":"BB پهن + RSI اکستریم بالا — بازگشت","setup":s}
    return _n("BB Width+RSI شناسایی نشد")

# ── 14. EMA + MACD + RSI ──
def combo_14(df, ind, symbol, tf):
    c=df["close"].values; h,l=df["high"].values,df["low"].values
    if len(c)<30: return _n("داده کافی نیست")
    ema20=_ema(c,20); rsi=_rsi(c); e12=_ema(c,12); e26=_ema(c,26)
    atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if ema20 is None or rsi is None or e12 is None or e26 is None: return _n("محاسبه ناموفق")
    macd=e12-e26
    if c[-1]>ema20[-1] and macd[-1]>0 and 50<rsi[-1]<70:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":83,"reason_fa":"EMA+MACD+RSI هر سه صعودی — ورود مطمئن","setup":s}
    if c[-1]<ema20[-1] and macd[-1]<0 and 30<rsi[-1]<50:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":83,"reason_fa":"EMA+MACD+RSI هر سه نزولی — ورود مطمئن","setup":s}
    return _n("EMA+MACD+RSI شناسایی نشد")

# ── 15. Multi-Timeframe Proxy ──
def combo_15(df, ind, symbol, tf):
    c=df["close"].values; h,l=df["high"].values,df["low"].values
    if len(c)<105: return _n("داده کافی نیست")
    e20=_ema(c,20); e50=_ema(c,50); e100=_ema(c,100); rsi=_rsi(c)
    atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if e20 is None or e50 is None or e100 is None or rsi is None: return _n("محاسبه ناموفق")
    if c[-1]>e20[-1] and c[-1]>e50[-1] and c[-1]>e100[-1] and rsi[-1]>55:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":84,"reason_fa":"بالای EMA20/50/100 + RSI>55 — روند چندتایم‌فریم","setup":s}
    if c[-1]<e20[-1] and c[-1]<e50[-1] and c[-1]<e100[-1] and rsi[-1]<45:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":84,"reason_fa":"زیر EMA20/50/100 + RSI<45 — روند چندتایم‌فریم","setup":s}
    return _n("MTF Proxy شناسایی نشد")

# ── 16. Momentum Score ──
def combo_16(df, ind, symbol, tf):
    c=df["close"].values; h,l=df["high"].values,df["low"].values
    if len(c)<35: return _n("داده کافی نیست")
    rsi=_rsi(c); e12=_ema(c,12); e26=_ema(c,26); adx,pdi,mdi=_adx(h,l,c)
    atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if rsi is None or e12 is None or adx is None: return _n("محاسبه ناموفق")
    macd=e12-e26; score=0
    if rsi[-1]>50: score+=1
    if macd[-1]>0: score+=1
    if adx[-1]>25 and pdi[-1]>mdi[-1]: score+=1
    if c[-1]>c[-5]: score+=1
    if score>=3:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":70+score*4,"reason_fa":f"امتیاز مومنتوم {score}/4 — خرید","setup":s}
    score_s=0
    if rsi[-1]<50: score_s+=1
    if macd[-1]<0: score_s+=1
    if adx[-1]>25 and mdi[-1]>pdi[-1]: score_s+=1
    if c[-1]<c[-5]: score_s+=1
    if score_s>=3:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":70+score_s*4,"reason_fa":f"امتیاز مومنتوم {score_s}/4 — فروش","setup":s}
    return _n("امتیاز مومنتوم کافی نیست")

# ── 17. Mean Reversion Multi ──
def combo_17(df, ind, symbol, tf):
    c=df["close"].values; h,l=df["high"].values,df["low"].values
    if len(c)<25: return _n("داده کافی نیست")
    rsi=_rsi(c); _,ub,lb=_bb(c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    # Stoch
    k_p=14; k=np.zeros(len(c))
    for i in range(k_p-1,len(c)):
        hh=np.max(h[i-k_p+1:i+1]); ll=np.min(l[i-k_p+1:i+1])
        k[i]=(c[i]-ll)/(hh-ll)*100 if hh!=ll else 50
    if rsi is None or lb is None: return _n("محاسبه ناموفق")
    os_count=0
    if rsi[-1]<30: os_count+=1
    if k[-1]<20: os_count+=1
    if c[-1]<=lb[-1]: os_count+=1
    if os_count>=2 and c[-1]>c[-2]:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":78+os_count*3,"reason_fa":f"Mean Reversion: {os_count}/3 اشباع فروش + بازگشت","setup":s}
    ob_count=0
    if rsi[-1]>70: ob_count+=1
    if k[-1]>80: ob_count+=1
    if c[-1]>=ub[-1]: ob_count+=1
    if ob_count>=2 and c[-1]<c[-2]:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":78+ob_count*3,"reason_fa":f"Mean Reversion: {ob_count}/3 اشباع خرید + بازگشت","setup":s}
    return _n("Mean Reversion شناسایی نشد")

# ── 18. Ultimate Signal (5 indicators) ──
def combo_18(df, ind, symbol, tf):
    c=df["close"].values; h,l=df["high"].values,df["low"].values
    if len(c)<55: return _n("داده کافی نیست")
    rsi=_rsi(c); e12=_ema(c,12); e26=_ema(c,26); e50=_ema(c,50)
    adx,pdi,mdi=_adx(h,l,c); _,d=_supertrend(h,l,c); _,ub,lb=_bb(c)
    atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if rsi is None or e50 is None or adx is None or d is None or ub is None: return _n("محاسبه ناموفق")
    macd=e12-e26; score=0
    if rsi[-1]>50 and rsi[-1]<70: score+=1
    if macd[-1]>0: score+=1
    if c[-1]>e50[-1]: score+=1
    if adx[-1]>20 and pdi[-1]>mdi[-1]: score+=1
    if d[-1]==1: score+=1
    if score>=4:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":min(95,80+score*3),"reason_fa":f"سیگنال نهایی {score}/5 — خرید با اطمینان بالا","setup":s}
    score_s=0
    if rsi[-1]<50 and rsi[-1]>30: score_s+=1
    if macd[-1]<0: score_s+=1
    if c[-1]<e50[-1]: score_s+=1
    if adx[-1]>20 and mdi[-1]>pdi[-1]: score_s+=1
    if d[-1]==-1: score_s+=1
    if score_s>=4:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":min(95,80+score_s*3),"reason_fa":f"سیگنال نهایی {score_s}/5 — فروش با اطمینان بالا","setup":s}
    return _n(f"سیگنال نهایی: خرید={score}/5 فروش={score_s}/5 — ناکافی")


COMBO_STRATEGIES = [
    {"id":"COMBO_01","name":"RSI+BB","name_fa":"RSI+بولینجر","func":combo_01},
    {"id":"COMBO_02","name":"EMA Cross+ADX","name_fa":"تقاطع EMA+ADX","func":combo_02},
    {"id":"COMBO_03","name":"RSI+EMA+Vol","name_fa":"RSI+EMA+حجم","func":combo_03},
    {"id":"COMBO_04","name":"ST+RSI","name_fa":"سوپرترند+RSI","func":combo_04},
    {"id":"COMBO_05","name":"BB Squeeze+ADX","name_fa":"فشردگی BB+ADX","func":combo_05},
    {"id":"COMBO_06","name":"Triple EMA+RSI","name_fa":"EMA سه‌گانه+RSI","func":combo_06},
    {"id":"COMBO_07","name":"ADX+ST+EMA","name_fa":"ADX+ST+EMA طلایی","func":combo_07},
    {"id":"COMBO_08","name":"RSI Div+BB","name_fa":"واگرایی RSI+BB","func":combo_08},
    {"id":"COMBO_09","name":"EMA200 Trend","name_fa":"روند EMA200","func":combo_09},
    {"id":"COMBO_10","name":"Stoch+BB","name_fa":"استوکستیک+BB","func":combo_10},
    {"id":"COMBO_11","name":"MACD+EMA+Vol","name_fa":"MACD+EMA+حجم","func":combo_11},
    {"id":"COMBO_12","name":"RSI+ST+ADX","name_fa":"RSI+ST+ADX تریپل","func":combo_12},
    {"id":"COMBO_13","name":"BB Width+RSI","name_fa":"عرض BB+RSI","func":combo_13},
    {"id":"COMBO_14","name":"EMA+MACD+RSI","name_fa":"EMA+MACD+RSI","func":combo_14},
    {"id":"COMBO_15","name":"MTF Proxy","name_fa":"چندتایم‌فریم","func":combo_15},
    {"id":"COMBO_16","name":"Momentum Score","name_fa":"امتیاز مومنتوم","func":combo_16},
    {"id":"COMBO_17","name":"Mean Reversion","name_fa":"بازگشت به میانگین","func":combo_17},
    {"id":"COMBO_18","name":"Ultimate Signal","name_fa":"سیگنال نهایی","func":combo_18},
]
