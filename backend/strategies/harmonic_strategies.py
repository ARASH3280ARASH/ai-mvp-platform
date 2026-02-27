"""
Harmonic Patterns Pack (5)
HARMONIC_01: AB=CD
HARMONIC_02: Gartley Zone
HARMONIC_03: Bat Zone
HARMONIC_04: Butterfly Zone
HARMONIC_05: Shark Zone
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


def _swing_points(high, low, lookback=5):
    n=len(high); sh=[]; sl=[]
    for i in range(lookback, n-lookback):
        if high[i]==max(high[i-lookback:i+lookback+1]): sh.append((i,high[i]))
        if low[i]==min(low[i-lookback:i+lookback+1]): sl.append((i,low[i]))
    return sh, sl

def _fib_ratio(a, b, c):
    """Check retracement ratio of C between A and B."""
    ab = abs(b-a)
    if ab == 0: return 0
    return abs(c-b)/ab

def harmonic_01(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<40: return _neutral("داده کافی نیست")
    sh,sl = _swing_points(h,l,5); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    # AB=CD: find 4 swings
    swings = sorted([(i,v,'H') for i,v in sh]+[(i,v,'L') for i,v in sl], key=lambda x:x[0])
    if len(swings)<4: return _neutral("نقاط swing کافی نیست")
    a,b,cc,d = swings[-4], swings[-3], swings[-2], swings[-1]
    ab=abs(b[1]-a[1]); cd=abs(d[1]-cc[1])
    if ab>0 and 0.8<cd/ab<1.2:
        if d[2]=='L' and c[-1]>d[1]:
            s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"BUY","confidence":72,"reason_fa":f"الگوی AB=CD صعودی — CD/AB={cd/ab:.2f}","setup":s}
        if d[2]=='H' and c[-1]<d[1]:
            s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"SELL","confidence":72,"reason_fa":f"الگوی AB=CD نزولی — CD/AB={cd/ab:.2f}","setup":s}
    return _neutral("الگوی AB=CD شناسایی نشد")

def harmonic_02(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<40: return _neutral("داده کافی نیست")
    sh,sl = _swing_points(h,l,5); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    # Gartley: B at 0.618 retrace of XA, D at 0.786 of XA
    if len(sl)>=2 and len(sh)>=2:
        xa_low=sl[-2][1]; xa_high=sh[-1][1]; xa=xa_high-xa_low
        if xa>0:
            b_ret=(xa_high-sl[-1][1])/xa if sl[-1][0]>sh[-1][0] else 0
            d_level=xa_high-0.786*xa
            if 0.55<b_ret<0.72 and abs(c[-1]-d_level)/c[-1]<0.003:
                s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
                if s: return {"signal":"BUY","confidence":70,"reason_fa":f"زون Gartley صعودی — D نزدیک 0.786","setup":s}
    return _neutral("الگوی Gartley شناسایی نشد")

def harmonic_03(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<40: return _neutral("داده کافی نیست")
    sh,sl = _swing_points(h,l,5); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    # Bat: B at 0.382-0.5, D at 0.886
    if len(sl)>=2 and len(sh)>=2:
        xa_low=sl[-2][1]; xa_high=sh[-1][1]; xa=xa_high-xa_low
        if xa>0:
            b_ret=(xa_high-sl[-1][1])/xa if sl[-1][0]>sh[-1][0] else 0
            d_level=xa_high-0.886*xa
            if 0.35<b_ret<0.55 and abs(c[-1]-d_level)/c[-1]<0.003:
                s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
                if s: return {"signal":"BUY","confidence":70,"reason_fa":f"زون Bat صعودی — D نزدیک 0.886","setup":s}
    return _neutral("الگوی Bat شناسایی نشد")

def harmonic_04(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<40: return _neutral("داده کافی نیست")
    sh,sl = _swing_points(h,l,5); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    # Butterfly: B at 0.786, D extends beyond X (1.27)
    if len(sl)>=2 and len(sh)>=2:
        xa_low=sl[-2][1]; xa_high=sh[-1][1]; xa=xa_high-xa_low
        if xa>0:
            b_ret=(xa_high-sl[-1][1])/xa if sl[-1][0]>sh[-1][0] else 0
            d_level=xa_high-1.27*xa
            if 0.72<b_ret<0.85 and c[-1]<xa_low and abs(c[-1]-d_level)/c[-1]<0.005:
                s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
                if s: return {"signal":"BUY","confidence":72,"reason_fa":"زون Butterfly صعودی — D نزدیک 1.27","setup":s}
    return _neutral("الگوی Butterfly شناسایی نشد")

def harmonic_05(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<40: return _neutral("داده کافی نیست")
    sh,sl = _swing_points(h,l,5); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    # Shark: uses 0.886 and 1.13
    if len(sl)>=2 and len(sh)>=2:
        xa_low=sl[-2][1]; xa_high=sh[-1][1]; xa=xa_high-xa_low
        if xa>0:
            d_level=xa_high-1.13*xa
            if c[-1]<xa_low and abs(c[-1]-d_level)/c[-1]<0.005 and c[-1]>c[-2]:
                s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
                if s: return {"signal":"BUY","confidence":68,"reason_fa":"زون Shark صعودی — بازگشت از 1.13","setup":s}
            d_sell=xa_low+1.13*xa
            if c[-1]>xa_high and abs(c[-1]-d_sell)/c[-1]<0.005 and c[-1]<c[-2]:
                s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
                if s: return {"signal":"SELL","confidence":68,"reason_fa":"زون Shark نزولی — بازگشت از 1.13","setup":s}
    return _neutral("الگوی Shark شناسایی نشد")

HARMONIC_STRATEGIES = [
    {"id":"HARMONIC_01","name":"AB=CD","name_fa":"AB=CD","func":harmonic_01},
    {"id":"HARMONIC_02","name":"Gartley","name_fa":"گارتلی","func":harmonic_02},
    {"id":"HARMONIC_03","name":"Bat","name_fa":"خفاش","func":harmonic_03},
    {"id":"HARMONIC_04","name":"Butterfly","name_fa":"پروانه","func":harmonic_04},
    {"id":"HARMONIC_05","name":"Shark","name_fa":"شارک","func":harmonic_05},
]
