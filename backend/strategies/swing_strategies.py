"""
Swing Trading Pack (5)
SWING_01: Higher Highs
SWING_02: Lower Lows
SWING_03: Swing Failure
SWING_04: Swing+EMA
SWING_05: ABC Pattern
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

def swing_01(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<30: return _neutral("داده کافی نیست")
    sh,sl = _swing_points(h,l,5); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if len(sh)>=2 and len(sl)>=2:
        hh = sh[-1][1]>sh[-2][1] and sl[-1][1]>sl[-2][1]  # HH+HL
        if hh:
            s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"BUY","confidence":74,"reason_fa":"سقف بالاتر + کف بالاتر — روند صعودی","setup":s}
    return _neutral("HH/HL شناسایی نشد")

def swing_02(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<30: return _neutral("داده کافی نیست")
    sh,sl = _swing_points(h,l,5); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if len(sh)>=2 and len(sl)>=2:
        ll = sh[-1][1]<sh[-2][1] and sl[-1][1]<sl[-2][1]  # LH+LL
        if ll:
            s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"SELL","confidence":74,"reason_fa":"سقف پایین‌تر + کف پایین‌تر — روند نزولی","setup":s}
    return _neutral("LH/LL شناسایی نشد")

def swing_03(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<30: return _neutral("داده کافی نیست")
    sh,sl = _swing_points(h,l,5); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if len(sh)>=2:
        # Swing failure: breaks above prev high then reverses
        if h[-1]>sh[-1][1] and c[-1]<sh[-1][1]:
            s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"SELL","confidence":72,"reason_fa":"SFP نزولی — شکست کاذب سقف","setup":s}
    if len(sl)>=2:
        if l[-1]<sl[-1][1] and c[-1]>sl[-1][1]:
            s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"BUY","confidence":72,"reason_fa":"SFP صعودی — شکست کاذب کف","setup":s}
    return _neutral("SFP شناسایی نشد")

def swing_04(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<55: return _neutral("داده کافی نیست")
    sh,sl = _swing_points(h,l,5); ema50=_ema(c,50); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if ema50 is None: return _neutral("محاسبه ناموفق")
    if len(sh)>=2 and len(sl)>=2:
        hh = sh[-1][1]>sh[-2][1] and sl[-1][1]>sl[-2][1]
        if hh and c[-1]>ema50[-1]:
            s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"BUY","confidence":78,"reason_fa":"Swing صعودی + بالای EMA50","setup":s}
        ll = sh[-1][1]<sh[-2][1] and sl[-1][1]<sl[-2][1]
        if ll and c[-1]<ema50[-1]:
            s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"SELL","confidence":78,"reason_fa":"Swing نزولی + زیر EMA50","setup":s}
    return _neutral("Swing+EMA شناسایی نشد")

def swing_05(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<30: return _neutral("داده کافی نیست")
    sh,sl = _swing_points(h,l,5); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    # ABC: A=swing, B=retrace, C=continuation
    if len(sl)>=3:
        a,b,cc = sl[-3][1], sl[-2][1], sl[-1][1]
        if a<b and cc>a and cc<b and c[-1]>sl[-1][1]:
            s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"BUY","confidence":70,"reason_fa":"الگوی ABC صعودی — ادامه روند","setup":s}
    if len(sh)>=3:
        a,b,cc = sh[-3][1], sh[-2][1], sh[-1][1]
        if a>b and cc<a and cc>b and c[-1]<sh[-1][1]:
            s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"SELL","confidence":70,"reason_fa":"الگوی ABC نزولی — ادامه روند","setup":s}
    return _neutral("الگوی ABC شناسایی نشد")

SWING_STRATEGIES = [
    {"id":"SWING_01","name":"Higher Highs","name_fa":"سقف بالاتر","func":swing_01},
    {"id":"SWING_02","name":"Lower Lows","name_fa":"کف پایین‌تر","func":swing_02},
    {"id":"SWING_03","name":"Swing Failure","name_fa":"SFP","func":swing_03},
    {"id":"SWING_04","name":"Swing+EMA","name_fa":"Swing+EMA","func":swing_04},
    {"id":"SWING_05","name":"ABC Pattern","name_fa":"الگوی ABC","func":swing_05},
]
