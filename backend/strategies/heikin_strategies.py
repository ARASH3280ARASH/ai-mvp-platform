"""
Heikin Ashi Pack (5)
HEIKIN_01: Color Change
HEIKIN_02: No Wick
HEIKIN_03: Trend Count
HEIKIN_04: HA+EMA
HEIKIN_05: HA Reversal
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


def _heikin_ashi(o, h, l, c):
    n=len(c); ha_c=(o+h+l+c)/4; ha_o=np.zeros(n); ha_h=np.zeros(n); ha_l=np.zeros(n)
    ha_o[0]=o[0]
    for i in range(1,n): ha_o[i]=(ha_o[i-1]+ha_c[i-1])/2
    ha_h=np.maximum(h,np.maximum(ha_o,ha_c))
    ha_l=np.minimum(l,np.minimum(ha_o,ha_c))
    return ha_o, ha_h, ha_l, ha_c

def heikin_01(df, indicators, symbol, timeframe):
    o,h,l,c = df["open"].values, df["high"].values, df["low"].values, df["close"].values
    if len(c)<10: return _neutral("داده کافی نیست")
    ha_o,ha_h,ha_l,ha_c = _heikin_ashi(o,h,l,c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    bull_now=ha_c[-1]>ha_o[-1]; bull_prev=ha_c[-2]>ha_o[-2]
    if bull_now and not bull_prev:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":68,"reason_fa":"هیکن آشی سبز شد — تغییر روند صعودی","setup":s}
    if not bull_now and bull_prev:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":68,"reason_fa":"هیکن آشی قرمز شد — تغییر روند نزولی","setup":s}
    return _neutral("تغییر رنگ HA شناسایی نشد")

def heikin_02(df, indicators, symbol, timeframe):
    o,h,l,c = df["open"].values, df["high"].values, df["low"].values, df["close"].values
    if len(c)<10: return _neutral("داده کافی نیست")
    ha_o,ha_h,ha_l,ha_c = _heikin_ashi(o,h,l,c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    # No lower wick on bull = strong
    bull=ha_c[-1]>ha_o[-1]; no_lower=abs(ha_l[-1]-min(ha_o[-1],ha_c[-1]))<atr[-1]*0.05 if atr is not None else False
    bear=ha_c[-1]<ha_o[-1]; no_upper=abs(ha_h[-1]-max(ha_o[-1],ha_c[-1]))<atr[-1]*0.05 if atr is not None else False
    if bull and no_lower:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":75,"reason_fa":"HA سبز بدون سایه پایین — صعود قوی","setup":s}
    if bear and no_upper:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":75,"reason_fa":"HA قرمز بدون سایه بالا — نزول قوی","setup":s}
    return _neutral("HA بدون سایه شناسایی نشد")

def heikin_03(df, indicators, symbol, timeframe):
    o,h,l,c = df["open"].values, df["high"].values, df["low"].values, df["close"].values
    if len(c)<15: return _neutral("داده کافی نیست")
    ha_o,_,_,ha_c = _heikin_ashi(o,h,l,c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    green=0; red=0
    for i in range(-1,-min(10,len(c)),-1):
        if ha_c[i]>ha_o[i]: green+=1
        else: break
    for i in range(-1,-min(10,len(c)),-1):
        if ha_c[i]<ha_o[i]: red+=1
        else: break
    if green>=5:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":min(78,60+green*2),"reason_fa":f"HA {green} کندل سبز متوالی","setup":s}
    if red>=5:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":min(78,60+red*2),"reason_fa":f"HA {red} کندل قرمز متوالی","setup":s}
    return _neutral("روند HA شناسایی نشد")

def heikin_04(df, indicators, symbol, timeframe):
    o,h,l,c = df["open"].values, df["high"].values, df["low"].values, df["close"].values
    if len(c)<25: return _neutral("داده کافی نیست")
    ha_o,_,_,ha_c = _heikin_ashi(o,h,l,c); ema20=_ema(c,20); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    if ema20 is None: return _neutral("محاسبه ناموفق")
    bull=ha_c[-1]>ha_o[-1]
    if bull and not (ha_c[-2]>ha_o[-2]) and c[-1]>ema20[-1]:
        s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":74,"reason_fa":"HA سبز شد + بالای EMA20","setup":s}
    if not bull and (ha_c[-2]>ha_o[-2]) and c[-1]<ema20[-1]:
        s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":74,"reason_fa":"HA قرمز شد + زیر EMA20","setup":s}
    return _neutral("HA+EMA شناسایی نشد")

def heikin_05(df, indicators, symbol, timeframe):
    o,h,l,c = df["open"].values, df["high"].values, df["low"].values, df["close"].values
    if len(c)<10: return _neutral("داده کافی نیست")
    ha_o,ha_h,ha_l,ha_c = _heikin_ashi(o,h,l,c); atr=_atr(h,l,c,14); pip=_pip_size(symbol)
    # Doji = small body
    body=abs(ha_c[-1]-ha_o[-1]); rng=ha_h[-1]-ha_l[-1]
    if rng>0 and body/rng<0.1:
        prev_bull=ha_c[-2]>ha_o[-2]
        if prev_bull:
            s=_make_setup("SELL",c[-1],atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"SELL","confidence":65,"reason_fa":"HA دوجی بعد از صعود — سیگنال بازگشت","setup":s}
        else:
            s=_make_setup("BUY",c[-1],atr[-1] if atr is not None else None,pip)
            if s: return {"signal":"BUY","confidence":65,"reason_fa":"HA دوجی بعد از نزول — سیگنال بازگشت","setup":s}
    return _neutral("بازگشت HA شناسایی نشد")

HEIKIN_STRATEGIES = [
    {"id":"HEIKIN_01","name":"HA Color Change","name_fa":"تغییر رنگ HA","func":heikin_01},
    {"id":"HEIKIN_02","name":"HA No Wick","name_fa":"HA بدون سایه","func":heikin_02},
    {"id":"HEIKIN_03","name":"HA Trend Count","name_fa":"شمارش روند HA","func":heikin_03},
    {"id":"HEIKIN_04","name":"HA+EMA","name_fa":"HA+EMA","func":heikin_04},
    {"id":"HEIKIN_05","name":"HA Reversal","name_fa":"بازگشت HA","func":heikin_05},
]
