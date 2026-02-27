"""
Whilber-AI — Squeeze Momentum Strategy Pack (5 Sub-Strategies)
================================================================
SQZ_01: Squeeze Fire (BB exits KC → momentum direction)
SQZ_02: Squeeze + Volume Confirm
SQZ_03: Squeeze Duration Filter (long squeeze → stronger breakout)
SQZ_04: Squeeze + ADX Trend Filter
SQZ_05: Squeeze Momentum Shift (histogram color change)
"""

import numpy as np

CATEGORY_ID = "SQZ"
CATEGORY_NAME = "Squeeze Momentum"
CATEGORY_FA = "فشردگی مومنتوم"
ICON = "🔥"
COLOR = "#ff5722"


def _ema(data, period):
    if len(data) < period: return None
    e = np.zeros(len(data))
    e[period - 1] = np.mean(data[:period])
    m = 2 / (period + 1)
    for i in range(period, len(data)):
        e[i] = data[i] * m + e[i - 1] * (1 - m)
    return e


def _sma(data, period):
    if len(data) < period: return None
    r = np.zeros(len(data))
    for i in range(period - 1, len(data)):
        r[i] = np.mean(data[i - period + 1:i + 1])
    return r


def _atr(high, low, close, period=14):
    if len(high) < period + 1: return None
    tr = np.maximum(high[1:] - low[1:], np.maximum(abs(high[1:] - close[:-1]), abs(low[1:] - close[:-1])))
    atr = np.zeros(len(tr))
    atr[period - 1] = np.mean(tr[:period])
    for i in range(period, len(tr)):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return np.concatenate([[0], atr])


def _adx(high, low, close, period=14):
    if len(high) < period * 2: return None
    n = len(high)
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)
    tr = np.zeros(n)
    for i in range(1, n):
        up = high[i] - high[i - 1]
        down = low[i - 1] - low[i]
        plus_dm[i] = up if up > down and up > 0 else 0
        minus_dm[i] = down if down > up and down > 0 else 0
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
    atr = np.zeros(n)
    s_pdm = np.zeros(n)
    s_mdm = np.zeros(n)
    atr[period] = np.mean(tr[1:period + 1])
    s_pdm[period] = np.mean(plus_dm[1:period + 1])
    s_mdm[period] = np.mean(minus_dm[1:period + 1])
    for i in range(period + 1, n):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
        s_pdm[i] = (s_pdm[i - 1] * (period - 1) + plus_dm[i]) / period
        s_mdm[i] = (s_mdm[i - 1] * (period - 1) + minus_dm[i]) / period
    plus_di = np.where(atr > 0, s_pdm / atr * 100, 0)
    minus_di = np.where(atr > 0, s_mdm / atr * 100, 0)
    dx = np.where((plus_di + minus_di) > 0, abs(plus_di - minus_di) / (plus_di + minus_di) * 100, 0)
    adx = np.zeros(n)
    start = period * 2
    if start < n:
        adx[start] = np.mean(dx[period + 1:start + 1])
        for i in range(start + 1, n):
            adx[i] = (adx[i - 1] * (period - 1) + dx[i]) / period
    return adx


def _squeeze(high, low, close, bb_period=20, bb_mult=2.0, kc_period=20, kc_mult=1.5):
    """Returns squeeze_on (bool array), momentum array."""
    n = len(close)
    if n < bb_period + 5: return None, None

    # Bollinger Bands
    bb_mid = _sma(close, bb_period)
    if bb_mid is None: return None, None
    bb_std = np.zeros(n)
    for i in range(bb_period - 1, n):
        bb_std[i] = np.std(close[i - bb_period + 1:i + 1])
    bb_upper = bb_mid + bb_mult * bb_std
    bb_lower = bb_mid - bb_mult * bb_std

    # Keltner Channel
    kc_mid = _ema(close, kc_period)
    atr_v = _atr(high, low, close, kc_period)
    if kc_mid is None or atr_v is None: return None, None
    kc_upper = kc_mid + kc_mult * atr_v
    kc_lower = kc_mid - kc_mult * atr_v

    # Squeeze: BB inside KC
    squeeze_on = (bb_lower > kc_lower) & (bb_upper < kc_upper)

    # Momentum: close - midline
    dc_high = np.zeros(n)
    dc_low = np.zeros(n)
    for i in range(bb_period - 1, n):
        dc_high[i] = np.max(high[i - bb_period + 1:i + 1])
        dc_low[i] = np.min(low[i - bb_period + 1:i + 1])
    dc_mid = (dc_high + dc_low) / 2.0
    mid_line = (kc_mid + dc_mid) / 2.0
    mom = close - mid_line

    return squeeze_on, mom


def _pip_size(symbol):
    s = symbol.upper()
    if "JPY" in s: return 0.01
    if "XAU" in s: return 0.1
    if "XAG" in s: return 0.01
    if "BTC" in s: return 1.0
    if s in ("NAS100", "US30", "SPX500", "GER40", "UK100"): return 1.0
    return 0.0001


def _make_setup(direction, entry, atr_val, pip, rr_min=1.5):
    if atr_val is None or atr_val <= 0: return None
    sl_dist = atr_val * 1.5
    tp1_dist = sl_dist * rr_min
    tp2_dist = sl_dist * 3.0
    if direction == "BUY":
        sl, tp1, tp2 = entry - sl_dist, entry + tp1_dist, entry + tp2_dist
    else:
        sl, tp1, tp2 = entry + sl_dist, entry - tp1_dist, entry - tp2_dist
    return {"has_setup": True, "direction": direction,
            "direction_fa": "خرید" if direction == "BUY" else "فروش",
            "entry": round(entry, 6), "stop_loss": round(sl, 6),
            "tp1": round(tp1, 6), "tp2": round(tp2, 6),
            "rr1": round(tp1_dist / sl_dist, 2), "rr2": round(tp2_dist / sl_dist, 2),
            "sl_pips": round(sl_dist / pip, 1) if pip > 0 else 0,
            "tp1_pips": round(tp1_dist / pip, 1) if pip > 0 else 0}


def _neutral(r):
    return {"signal": "NEUTRAL", "confidence": 0, "reason_fa": r, "setup": {"has_setup": False}}


def sqz_01(df, indicators, symbol, timeframe):
    """Squeeze Fire: BB exits KC, momentum direction."""
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(c) < 30: return _neutral("داده کافی نیست")
    sq, mom = _squeeze(h, l, c)
    if sq is None: return _neutral("محاسبه Squeeze ناموفق")
    atr_v = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]

    # Squeeze just released (was on, now off)
    if sq[-2] and not sq[-1]:
        if mom[-1] > 0:
            setup = _make_setup("BUY", price, atr_v[-1] if atr_v is not None else None, pip)
            if setup:
                return {"signal": "BUY", "confidence": 78, "reason_fa": "Squeeze آزاد شد — مومنتوم صعودی", "setup": setup}
        elif mom[-1] < 0:
            setup = _make_setup("SELL", price, atr_v[-1] if atr_v is not None else None, pip)
            if setup:
                return {"signal": "SELL", "confidence": 78, "reason_fa": "Squeeze آزاد شد — مومنتوم نزولی", "setup": setup}

    return _neutral("Squeeze فعال نشد")


def sqz_02(df, indicators, symbol, timeframe):
    """Squeeze + Volume Confirm."""
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    v = df["tick_volume"].values if "tick_volume" in df.columns else df.get("volume", np.ones(len(c))).values
    if len(c) < 30: return _neutral("داده کافی نیست")
    sq, mom = _squeeze(h, l, c)
    if sq is None: return _neutral("محاسبه Squeeze ناموفق")
    atr_v = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]
    vol_avg = np.mean(v[-20:]) if len(v) >= 20 else np.mean(v)

    if sq[-2] and not sq[-1] and v[-1] > vol_avg * 1.5:
        if mom[-1] > 0:
            setup = _make_setup("BUY", price, atr_v[-1] if atr_v is not None else None, pip)
            if setup:
                return {"signal": "BUY", "confidence": 82, "reason_fa": "Squeeze + حجم بالا — شکست صعودی", "setup": setup}
        elif mom[-1] < 0:
            setup = _make_setup("SELL", price, atr_v[-1] if atr_v is not None else None, pip)
            if setup:
                return {"signal": "SELL", "confidence": 82, "reason_fa": "Squeeze + حجم بالا — شکست نزولی", "setup": setup}

    return _neutral("Squeeze + حجم شناسایی نشد")


def sqz_03(df, indicators, symbol, timeframe):
    """Squeeze Duration Filter: long squeeze → stronger breakout."""
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(c) < 40: return _neutral("داده کافی نیست")
    sq, mom = _squeeze(h, l, c)
    if sq is None: return _neutral("محاسبه Squeeze ناموفق")
    atr_v = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]

    # Count how long squeeze was on before release
    if sq[-2] and not sq[-1]:
        duration = 0
        for i in range(len(sq) - 2, -1, -1):
            if sq[i]:
                duration += 1
            else:
                break

        if duration >= 6:
            conf = min(85, 72 + duration)
            if mom[-1] > 0:
                setup = _make_setup("BUY", price, atr_v[-1] if atr_v is not None else None, pip)
                if setup:
                    return {"signal": "BUY", "confidence": conf, "reason_fa": f"Squeeze طولانی ({duration} کندل) — شکست صعودی قوی", "setup": setup}
            elif mom[-1] < 0:
                setup = _make_setup("SELL", price, atr_v[-1] if atr_v is not None else None, pip)
                if setup:
                    return {"signal": "SELL", "confidence": conf, "reason_fa": f"Squeeze طولانی ({duration} کندل) — شکست نزولی قوی", "setup": setup}

    return _neutral("Squeeze طولانی شناسایی نشد")


def sqz_04(df, indicators, symbol, timeframe):
    """Squeeze + ADX Trend Filter."""
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(c) < 40: return _neutral("داده کافی نیست")
    sq, mom = _squeeze(h, l, c)
    adx_v = _adx(h, l, c)
    if sq is None or adx_v is None: return _neutral("محاسبه ناموفق")
    atr_v = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]

    if sq[-2] and not sq[-1] and adx_v[-1] > 20:
        if mom[-1] > 0:
            setup = _make_setup("BUY", price, atr_v[-1] if atr_v is not None else None, pip)
            if setup:
                return {"signal": "BUY", "confidence": 80, "reason_fa": f"Squeeze + ADX={adx_v[-1]:.0f} — شکست روندی صعودی", "setup": setup}
        elif mom[-1] < 0:
            setup = _make_setup("SELL", price, atr_v[-1] if atr_v is not None else None, pip)
            if setup:
                return {"signal": "SELL", "confidence": 80, "reason_fa": f"Squeeze + ADX={adx_v[-1]:.0f} — شکست روندی نزولی", "setup": setup}

    return _neutral("Squeeze + ADX شناسایی نشد")


def sqz_05(df, indicators, symbol, timeframe):
    """Squeeze Momentum Shift: histogram changes direction."""
    h, l, c = df["high"].values, df["low"].values, df["close"].values
    if len(c) < 30: return _neutral("داده کافی نیست")
    sq, mom = _squeeze(h, l, c)
    if sq is None: return _neutral("محاسبه Squeeze ناموفق")
    atr_v = _atr(h, l, c, 14)
    pip = _pip_size(symbol)
    price = c[-1]

    # Momentum shifts from negative to positive (or increasing from decreasing)
    if not sq[-1]:  # Only when squeeze is off
        if mom[-1] > 0 and mom[-2] < 0:
            setup = _make_setup("BUY", price, atr_v[-1] if atr_v is not None else None, pip)
            if setup:
                return {"signal": "BUY", "confidence": 73, "reason_fa": "مومنتوم Squeeze صعودی شد", "setup": setup}

        if mom[-1] < 0 and mom[-2] > 0:
            setup = _make_setup("SELL", price, atr_v[-1] if atr_v is not None else None, pip)
            if setup:
                return {"signal": "SELL", "confidence": 73, "reason_fa": "مومنتوم Squeeze نزولی شد", "setup": setup}

    return _neutral("تغییر مومنتوم Squeeze شناسایی نشد")


SQZ_STRATEGIES = [
    {"id": "SQZ_01", "name": "Squeeze Fire", "name_fa": "آتش Squeeze", "func": sqz_01},
    {"id": "SQZ_02", "name": "Squeeze + Volume", "name_fa": "Squeeze + حجم", "func": sqz_02},
    {"id": "SQZ_03", "name": "Squeeze Duration", "name_fa": "مدت Squeeze", "func": sqz_03},
    {"id": "SQZ_04", "name": "Squeeze + ADX", "name_fa": "Squeeze + ADX", "func": sqz_04},
    {"id": "SQZ_05", "name": "Squeeze Momentum Shift", "name_fa": "تغییر مومنتوم Squeeze", "func": sqz_05},
]
