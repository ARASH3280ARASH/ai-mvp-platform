"""
Advanced Pivots Pack (5)
PIVOT_ADV_01: Camarilla Bounce
PIVOT_ADV_02: Woodie Pivot
PIVOT_ADV_03: Fibonacci Pivot
PIVOT_ADV_04: DeMark Pivot
PIVOT_ADV_05: Multi-Pivot Confluence
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


def _daily_hlc(df):
    """Get previous day H/L/C from hourly data (last 24 bars approx)."""
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<24: return None,None,None,None
    ph=np.max(h[-48:-24]) if len(h)>48 else np.max(h[:-24])
    pl=np.min(l[-48:-24]) if len(l)>48 else np.min(l[:-24])
    pc=c[-25] if len(c)>25 else c[0]
    po=df["open"].values[-48] if len(c)>48 else df["open"].values[0]
    return ph, pl, pc, po

def pivot_adv_01(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<30: return _neutral("داده کافی نیست")
    ph,pl,pc,_ = _daily_hlc(df)
    if ph is None: return _neutral("داده روزانه ناکافی")
    atr=_atr(h,l,c,14); pip=_pip_size(symbol); price=c[-1]
    rng=ph-pl
    # Camarilla levels
    h3=pc+rng*1.1/4; h4=pc+rng*1.1/2
    l3=pc-rng*1.1/4; l4=pc-rng*1.1/2
    if price<=l3*1.001 and price>l4:
        s=_make_setup("BUY",price,atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":72,"reason_fa":f"بانس از L3 کاماریلا ({l3:.5f})","setup":s}
    if price>=h3*0.999 and price<h4:
        s=_make_setup("SELL",price,atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":72,"reason_fa":f"بانس از H3 کاماریلا ({h3:.5f})","setup":s}
    if price>h4:
        s=_make_setup("BUY",price,atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":75,"reason_fa":f"شکست H4 کاماریلا — breakout صعودی","setup":s}
    if price<l4:
        s=_make_setup("SELL",price,atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":75,"reason_fa":f"شکست L4 کاماریلا — breakout نزولی","setup":s}
    return _neutral("سطح کاماریلا شناسایی نشد")

def pivot_adv_02(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<30: return _neutral("داده کافی نیست")
    ph,pl,pc,_ = _daily_hlc(df)
    if ph is None: return _neutral("داده روزانه ناکافی")
    atr=_atr(h,l,c,14); pip=_pip_size(symbol); price=c[-1]
    # Woodie pivot
    pp=(ph+pl+2*pc)/4
    r1=2*pp-pl; s1=2*pp-ph
    if price>pp and c[-2]<=pp:
        s=_make_setup("BUY",price,atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":68,"reason_fa":f"عبور بالای پیوت Woodie ({pp:.5f})","setup":s}
    if price<pp and c[-2]>=pp:
        s=_make_setup("SELL",price,atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":68,"reason_fa":f"عبور زیر پیوت Woodie ({pp:.5f})","setup":s}
    return _neutral("پیوت Woodie شناسایی نشد")

def pivot_adv_03(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<30: return _neutral("داده کافی نیست")
    ph,pl,pc,_ = _daily_hlc(df)
    if ph is None: return _neutral("داده روزانه ناکافی")
    atr=_atr(h,l,c,14); pip=_pip_size(symbol); price=c[-1]
    pp=(ph+pl+pc)/3; rng=ph-pl
    r1=pp+0.382*rng; r2=pp+0.618*rng; r3=pp+rng
    s1=pp-0.382*rng; s2=pp-0.618*rng; s3=pp-rng
    if abs(price-s1)/price<0.001 and c[-1]>c[-2]:
        s=_make_setup("BUY",price,atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":70,"reason_fa":f"بانس از S1 فیبوناچی ({s1:.5f})","setup":s}
    if abs(price-r1)/price<0.001 and c[-1]<c[-2]:
        s=_make_setup("SELL",price,atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":70,"reason_fa":f"بانس از R1 فیبوناچی ({r1:.5f})","setup":s}
    return _neutral("پیوت فیبوناچی شناسایی نشد")

def pivot_adv_04(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    o = df["open"].values
    if len(c)<30: return _neutral("داده کافی نیست")
    ph,pl,pc,po = _daily_hlc(df)
    if ph is None: return _neutral("داده روزانه ناکافی")
    atr=_atr(h,l,c,14); pip=_pip_size(symbol); price=c[-1]
    # DeMark
    if pc<po: x=ph+2*pl+pc
    elif pc>po: x=2*ph+pl+pc
    else: x=ph+pl+2*pc
    dm_pp=x/4; dm_r=x/2-pl; dm_s=x/2-ph
    if price>dm_pp and c[-2]<=dm_pp:
        s=_make_setup("BUY",price,atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":68,"reason_fa":f"عبور بالای DeMark PP ({dm_pp:.5f})","setup":s}
    if price<dm_pp and c[-2]>=dm_pp:
        s=_make_setup("SELL",price,atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":68,"reason_fa":f"عبور زیر DeMark PP ({dm_pp:.5f})","setup":s}
    return _neutral("پیوت DeMark شناسایی نشد")

def pivot_adv_05(df, indicators, symbol, timeframe):
    h,l,c = df["high"].values, df["low"].values, df["close"].values
    if len(c)<30: return _neutral("داده کافی نیست")
    ph,pl,pc,_ = _daily_hlc(df)
    if ph is None: return _neutral("داده روزانه ناکافی")
    atr=_atr(h,l,c,14); pip=_pip_size(symbol); price=c[-1]
    pp_std=(ph+pl+pc)/3; pp_wood=(ph+pl+2*pc)/4; pp_cam=pc
    rng=ph-pl
    # Confluence: multiple pivots near same level
    pivots=[pp_std, pp_wood, pp_cam]
    near_support=sum(1 for p in pivots if price<p and abs(price-p)/price<0.003)
    near_resist=sum(1 for p in pivots if price>p and abs(price-p)/price<0.003)
    if near_support>=2 and c[-1]>c[-2]:
        s=_make_setup("BUY",price,atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"BUY","confidence":76,"reason_fa":f"تلاقی {near_support} پیوت — حمایت قوی","setup":s}
    if near_resist>=2 and c[-1]<c[-2]:
        s=_make_setup("SELL",price,atr[-1] if atr is not None else None,pip)
        if s: return {"signal":"SELL","confidence":76,"reason_fa":f"تلاقی {near_resist} پیوت — مقاومت قوی","setup":s}
    return _neutral("تلاقی پیوت شناسایی نشد")

PIVOT_ADV_STRATEGIES = [
    {"id":"PIVOT_ADV_01","name":"Camarilla","name_fa":"کاماریلا","func":pivot_adv_01},
    {"id":"PIVOT_ADV_02","name":"Woodie Pivot","name_fa":"پیوت Woodie","func":pivot_adv_02},
    {"id":"PIVOT_ADV_03","name":"Fib Pivot","name_fa":"پیوت فیبوناچی","func":pivot_adv_03},
    {"id":"PIVOT_ADV_04","name":"DeMark Pivot","name_fa":"پیوت DeMark","func":pivot_adv_04},
    {"id":"PIVOT_ADV_05","name":"Multi-Pivot","name_fa":"تلاقی پیوت","func":pivot_adv_05},
]
