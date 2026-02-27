"""
Elder Ray Pack (5)
ELDER_01: Bull Power Cross
ELDER_02: Bear Power Cross
ELDER_03: Bull+Bear Combined
ELDER_04: Elder+EMA
ELDER_05: Force Index Combo
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


def _elder(high, low, close, period=13):
    ema = _ema(close, period)
    if ema is None: return None, None, None
    bull = high - ema
    bear = low - ema
    return bull, bear, ema

def elder_01(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<20: return _neutral("داده کافی نیست")
    bull,bear,ema = _elder(h,l,c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if bull is None: return _neutral("محاسبه ناموفق")
    if bull[-1]>0 and bull[-2]<=0:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":70,"reason_fa":"قدرت گاوی مثبت شد — خریداران غالب","setup":s}
    if bull[-1]<0 and bull[-2]>=0:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":65,"reason_fa":"قدرت گاوی منفی شد — ضعف خریداران","setup":s}
    return _neutral("تغییر Bull Power شناسایی نشد")

def elder_02(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<20: return _neutral("داده کافی نیست")
    bull,bear,ema = _elder(h,l,c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if bear is None: return _neutral("محاسبه ناموفق")
    if bear[-1]>0 and bear[-2]<=0:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":72,"reason_fa":"Bear Power مثبت — فروشندگان شکست خوردند","setup":s}
    if bear[-1]<bear[-2] and bear[-1]<0 and bear[-2]<bear[-3]:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":68,"reason_fa":"Bear Power در حال کاهش — فشار فروش","setup":s}
    return _neutral("تغییر Bear Power شناسایی نشد")

def elder_03(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<20: return _neutral("داده کافی نیست")
    bull,bear,ema = _elder(h,l,c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if bull is None: return _neutral("محاسبه ناموفق")
    if bull[-1]>0 and bear[-1]>0:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":80,"reason_fa":"Bull+Bear هر دو مثبت — صعود قوی","setup":s}
    if bull[-1]<0 and bear[-1]<0:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":80,"reason_fa":"Bull+Bear هر دو منفی — نزول قوی","setup":s}
    return _neutral("ترکیب Elder شناسایی نشد")

def elder_04(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<30: return _neutral("داده کافی نیست")
    bull,bear,ema = _elder(h,l,c); ema26=_ema(c,26); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if bull is None or ema26 is None: return _neutral("محاسبه ناموفق")
    if c[-1]>ema26[-1] and bear[-1]<0 and bear[-1]>bear[-2]:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":75,"reason_fa":"Elder: بالای EMA26 + Bear Power در حال بهبود","setup":s}
    if c[-1]<ema26[-1] and bull[-1]>0 and bull[-1]<bull[-2]:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":75,"reason_fa":"Elder: زیر EMA26 + Bull Power در حال کاهش","setup":s}
    return _neutral("Elder+EMA شناسایی نشد")

def elder_05(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<25: return _neutral("داده کافی نیست")
    bull,bear,_ = _elder(h,l,c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if bull is None: return _neutral("محاسبه ناموفق")
    bp_rising = bull[-1]>bull[-2]>bull[-3]
    brp_rising = bear[-1]>bear[-2]>bear[-3]
    if bp_rising and brp_rising:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":74,"reason_fa":"Elder: هر دو قدرت صعودی — مومنتوم قوی","setup":s}
    bp_fall = bull[-1]<bull[-2]<bull[-3]
    brp_fall = bear[-1]<bear[-2]<bear[-3]
    if bp_fall and brp_fall:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":74,"reason_fa":"Elder: هر دو قدرت نزولی — مومنتوم منفی","setup":s}
    return _neutral("مومنتوم Elder شناسایی نشد")

ELDER_STRATEGIES = [
    {"id":"ELDER_01","name":"Bull Power","name_fa":"قدرت گاوی","func":elder_01},
    {"id":"ELDER_02","name":"Bear Power","name_fa":"قدرت خرسی","func":elder_02},
    {"id":"ELDER_03","name":"Elder Combined","name_fa":"ترکیب Elder","func":elder_03},
    {"id":"ELDER_04","name":"Elder+EMA","name_fa":"Elder+EMA","func":elder_04},
    {"id":"ELDER_05","name":"Elder Momentum","name_fa":"مومنتوم Elder","func":elder_05},
]
