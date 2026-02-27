"""
Whilber-AI — Parabolic SAR Strategy Pack (5 Sub-Strategies)
==============================================================
PSAR_01: SAR Flip (dot switches sides)
PSAR_02: SAR + ADX Filter (trend strength confirm)
PSAR_03: SAR Acceleration (AF increases → strong trend)
PSAR_04: SAR + EMA Filter (SAR flip only with EMA trend)
PSAR_05: SAR Trailing System (entry + trail management)
"""

import numpy as np

CATEGORY_ID = "PSAR"
CATEGORY_NAME = "Parabolic SAR"
CATEGORY_FA = "پارابولیک SAR"
ICON = "⚡"
COLOR = "#e91e63"


def _psar(high, low, close, af_start=0.02, af_step=0.02, af_max=0.2):
    """Calculate Parabolic SAR."""
    n = len(high)
    if n < 5:
        return None, None
    sar = np.zeros(n)
    af_arr = np.zeros(n)
    direction = np.ones(n)  # 1=bull, -1=bear

    sar[0] = low[0]
    af = af_start
    ep = high[0]
    is_bull = True

    for i in range(1, n):
        sar[i] = sar[i-1] + af * (ep - sar[i-1])

        if is_bull:
            sar[i] = min(sar[i], low[i-1], low[max(0,i-2)])
            if high[i] > ep:
                ep = high[i]
                af = min(af + af_step, af_max)
            if low[i] < sar[i]:
                is_bull = False
                sar[i] = ep
                ep = low[i]
                af = af_start
        else:
            sar[i] = max(sar[i], high[i-1], high[max(0,i-2)])
            if low[i] < ep:
                ep = low[i]
                af = min(af + af_step, af_max)
            if high[i] > sar[i]:
                is_bull = True
                sar[i] = ep
                ep = high[i]
                af = af_start

        direction[i] = 1 if is_bull else -1
        af_arr[i] = af

    return sar, direction, af_arr


def _ema(data, period):
    if len(data) < period: return None
    e = np.zeros(len(data))
    e[period-1] = np.mean(data[:period])
    m = 2 / (period + 1)
    for i in range(period, len(data)):
        e[i] = data[i] * m + e[i-1] * (1 - m)
    return e


def _adx(high, low, close, period=14):
    if len(high) < period * 2: return None, None, None
    n = len(high)
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)
    tr = np.zeros(n)
    for i in range(1, n):
        up = high[i] - high[i-1]
        down = low[i-1] - low[i]
        plus_dm[i] = up if up > down and up > 0 else 0
        minus_dm[i] = down if down > up and down > 0 else 0
        tr[i] = max(high[i]-low[i], abs(high[i]-close[i-1]), abs(low[i]-close[i-1]))
    atr = np.zeros(n)
    s_pdm = np.zeros(n)
    s_mdm = np.zeros(n)
    atr[period] = np.mean(tr[1:period+1])
    s_pdm[period] = np.mean(plus_dm[1:period+1])
    s_mdm[period] = np.mean(minus_dm[1:period+1])
    for i in range(period+1, n):
        atr[i] = (atr[i-1]*(period-1)+tr[i])/period
        s_pdm[i] = (s_pdm[i-1]*(period-1)+plus_dm[i])/period
        s_mdm[i] = (s_mdm[i-1]*(period-1)+minus_dm[i])/period
    plus_di = np.where(atr>0, s_pdm/atr*100, 0)
    minus_di = np.where(atr>0, s_mdm/atr*100, 0)
    dx = np.where((plus_di+minus_di)>0, abs(plus_di-minus_di)/(plus_di+minus_di)*100, 0)
    adx = np.zeros(n)
    start = period*2
    if start < n:
        adx[start] = np.mean(dx[period+1:start+1])
        for i in range(start+1, n):
            adx[i] = (adx[i-1]*(period-1)+dx[i])/period
    return adx, plus_di, minus_di


def _atr(high, low, close, period=14):
    if len(high) < period + 1: return None
    tr = np.maximum(high[1:]-low[1:], np.maximum(abs(high[1:]-close[:-1]), abs(low[1:]-close[:-1])))
    atr = np.zeros(len(tr))
    atr[period-1] = np.mean(tr[:period])
    for i in range(period, len(tr)):
        atr[i] = (atr[i-1]*(period-1)+tr[i])/period
    return np.concatenate([[0], atr])


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
    sl_dist = atr_val * 1.5
    tp1_dist = sl_dist * rr_min
    tp2_dist = sl_dist * 3.0
    if direction == "BUY":
        sl, tp1, tp2 = entry-sl_dist, entry+tp1_dist, entry+tp2_dist
    else:
        sl, tp1, tp2 = entry+sl_dist, entry-tp1_dist, entry-tp2_dist
    if tp1_dist/sl_dist < rr_min: return None
    return {"has_setup": True, "direction": direction,
            "direction_fa": "خرید" if direction=="BUY" else "فروش",
            "entry": round(entry,6), "stop_loss": round(sl,6),
            "tp1": round(tp1,6), "tp2": round(tp2,6),
            "rr1": round(tp1_dist/sl_dist,2), "rr2": round(tp2_dist/sl_dist,2),
            "sl_pips": round(sl_dist/pip,1) if pip>0 else 0,
            "tp1_pips": round(tp1_dist/pip,1) if pip>0 else 0}


def _neutral(r):
    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": r, "setup": {"has_setup": False}}


def psar_01(df, indicators, symbol, timeframe):
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(c) < 10: return _neutral("داده کافی نیست")
    sar, dirs, _ = _psar(h, l, c)
    atr = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]
    if sar is None: return _neutral("محاسبه SAR ناموفق")

    # Flip from bear to bull
    if dirs[-1] == 1 and dirs[-2] == -1:
        setup = _make_setup("BUY", price, atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 70, "reason_fa": "تغییر SAR به صعودی — نقطه زیر قیمت", "setup": setup}

    if dirs[-1] == -1 and dirs[-2] == 1:
        setup = _make_setup("SELL", price, atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 70, "reason_fa": "تغییر SAR به نزولی — نقطه بالای قیمت", "setup": setup}

    return _neutral("تغییر SAR شناسایی نشد")


def psar_02(df, indicators, symbol, timeframe):
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(c) < 30: return _neutral("داده کافی نیست")
    sar, dirs, _ = _psar(h, l, c)
    adx, pdi, mdi = _adx(h, l, c)
    atr = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]
    if sar is None or adx is None: return _neutral("محاسبه ناموفق")

    if dirs[-1] == 1 and dirs[-2] == -1 and adx[-1] > 25:
        setup = _make_setup("BUY", price, atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 80, "reason_fa": f"SAR صعودی + ADX={adx[-1]:.0f} — روند قوی", "setup": setup}

    if dirs[-1] == -1 and dirs[-2] == 1 and adx[-1] > 25:
        setup = _make_setup("SELL", price, atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 80, "reason_fa": f"SAR نزولی + ADX={adx[-1]:.0f} — روند قوی", "setup": setup}

    return _neutral("SAR + ADX شناسایی نشد")


def psar_03(df, indicators, symbol, timeframe):
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(c) < 15: return _neutral("داده کافی نیست")
    sar, dirs, af = _psar(h, l, c)
    atr = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]
    if sar is None: return _neutral("محاسبه ناموفق")

    if dirs[-1] == 1 and af[-1] >= 0.1:
        setup = _make_setup("BUY", price, atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 75, "reason_fa": f"SAR شتاب‌دار صعودی — AF={af[-1]:.2f}", "setup": setup}

    if dirs[-1] == -1 and af[-1] >= 0.1:
        setup = _make_setup("SELL", price, atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 75, "reason_fa": f"SAR شتاب‌دار نزولی — AF={af[-1]:.2f}", "setup": setup}

    return _neutral("شتاب SAR کافی نیست")


def psar_04(df, indicators, symbol, timeframe):
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(c) < 55: return _neutral("داده کافی نیست")
    sar, dirs, _ = _psar(h, l, c)
    ema50 = _ema(c, 50)
    atr = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]
    if sar is None or ema50 is None: return _neutral("محاسبه ناموفق")

    if dirs[-1] == 1 and dirs[-2] == -1 and price > ema50[-1]:
        setup = _make_setup("BUY", price, atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "BUY", "confidence": 78, "reason_fa": "SAR صعودی + قیمت بالای EMA50 — تایید روند", "setup": setup}

    if dirs[-1] == -1 and dirs[-2] == 1 and price < ema50[-1]:
        setup = _make_setup("SELL", price, atr[-1] if atr is not None else None, pip)
        if setup:
            return {"signal": "SELL", "confidence": 78, "reason_fa": "SAR نزولی + قیمت زیر EMA50 — تایید روند", "setup": setup}

    return _neutral("SAR + EMA شناسایی نشد")


def psar_05(df, indicators, symbol, timeframe):
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(c) < 15: return _neutral("داده کافی نیست")
    sar, dirs, af = _psar(h, l, c)
    atr = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]
    if sar is None: return _neutral("محاسبه ناموفق")

    # Count consecutive direction
    count = 0
    d = dirs[-1]
    for i in range(-1, -min(15, len(dirs)), -1):
        if dirs[i] == d:
            count += 1
        else:
            break

    if d == 1 and count >= 5 and af[-1] >= 0.06:
        setup = _make_setup("BUY", price, atr[-1] if atr is not None else None, pip)
        if setup:
            setup["stop_loss"] = round(sar[-1], 6)  # Use SAR as SL
            return {"signal": "BUY", "confidence": 72, "reason_fa": f"سیستم تریل SAR — {count} کندل صعودی | SL=SAR", "setup": setup}

    if d == -1 and count >= 5 and af[-1] >= 0.06:
        setup = _make_setup("SELL", price, atr[-1] if atr is not None else None, pip)
        if setup:
            setup["stop_loss"] = round(sar[-1], 6)
            return {"signal": "SELL", "confidence": 72, "reason_fa": f"سیستم تریل SAR — {count} کندل نزولی | SL=SAR", "setup": setup}

    return _neutral("سیستم تریل SAR شناسایی نشد")


PSAR_STRATEGIES = [
    {"id": "PSAR_01", "name": "SAR Flip", "name_fa": "تغییر SAR", "func": psar_01},
    {"id": "PSAR_02", "name": "SAR + ADX", "name_fa": "SAR + ADX", "func": psar_02},
    {"id": "PSAR_03", "name": "SAR Acceleration", "name_fa": "شتاب SAR", "func": psar_03},
    {"id": "PSAR_04", "name": "SAR + EMA", "name_fa": "SAR + EMA", "func": psar_04},
    {"id": "PSAR_05", "name": "SAR Trail", "name_fa": "تریل SAR", "func": psar_05},
]
