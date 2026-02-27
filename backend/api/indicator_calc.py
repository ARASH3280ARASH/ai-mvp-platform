"""
Whilber-AI — Indicator Calculator for Backtesting
=====================================================
Computes indicator values from OHLCV DataFrame.
"""

import numpy as np


def _sma(data, period):
    out = np.full(len(data), np.nan)
    for i in range(period - 1, len(data)):
        out[i] = np.mean(data[i - period + 1:i + 1])
    return out


def _ema(data, period):
    out = np.full(len(data), np.nan)
    if len(data) < period:
        return out
    out[period - 1] = np.mean(data[:period])
    m = 2.0 / (period + 1)
    for i in range(period, len(data)):
        out[i] = data[i] * m + out[i - 1] * (1 - m)
    return out


def _wma(data, period):
    out = np.full(len(data), np.nan)
    weights = np.arange(1, period + 1, dtype=float)
    wsum = weights.sum()
    for i in range(period - 1, len(data)):
        out[i] = np.sum(data[i - period + 1:i + 1] * weights) / wsum
    return out


def _dema(data, period):
    e1 = _ema(data, period)
    e2 = _ema(e1[~np.isnan(e1)], period) if np.any(~np.isnan(e1)) else e1
    out = np.full(len(data), np.nan)
    offset = len(data) - len(e2)
    for i in range(len(e2)):
        if not np.isnan(e1[i + offset]) and not np.isnan(e2[i]):
            out[i + offset] = 2 * e1[i + offset] - e2[i]
    return out


def _tema(data, period):
    e1 = _ema(data, period)
    valid1 = e1[~np.isnan(e1)]
    e2 = _ema(valid1, period) if len(valid1) >= period else np.full(len(valid1), np.nan)
    valid2 = e2[~np.isnan(e2)]
    e3 = _ema(valid2, period) if len(valid2) >= period else np.full(len(valid2), np.nan)
    out = np.full(len(data), np.nan)
    # Simplified: just use triple EMA approximation
    for i in range(period * 3, len(data)):
        if not np.isnan(e1[i]):
            out[i] = e1[i]
    return out


def _rsi(close, period):
    out = np.full(len(close), np.nan)
    if len(close) < period + 1:
        return out
    delta = np.diff(close)
    gain = np.where(delta > 0, delta, 0.0)
    loss = np.where(delta < 0, -delta, 0.0)
    avg_g = np.mean(gain[:period])
    avg_l = np.mean(loss[:period])
    if avg_l == 0:
        out[period] = 100.0
    else:
        out[period] = 100.0 - 100.0 / (1.0 + avg_g / avg_l)
    for i in range(period, len(delta)):
        avg_g = (avg_g * (period - 1) + gain[i]) / period
        avg_l = (avg_l * (period - 1) + loss[i]) / period
        if avg_l == 0:
            out[i + 1] = 100.0
        else:
            out[i + 1] = 100.0 - 100.0 / (1.0 + avg_g / avg_l)
    return out


def _stoch(high, low, close, k_period, d_period, slowing):
    n = len(close)
    k = np.full(n, np.nan)
    raw_k = np.full(n, np.nan)
    for i in range(k_period - 1, n):
        hh = np.max(high[i - k_period + 1:i + 1])
        ll = np.min(low[i - k_period + 1:i + 1])
        if hh != ll:
            raw_k[i] = (close[i] - ll) / (hh - ll) * 100
        else:
            raw_k[i] = 50
    k = _sma(raw_k, slowing) if slowing > 1 else raw_k
    d = _sma(k, d_period)
    return k, d


def _atr(high, low, close, period):
    n = len(close)
    tr = np.zeros(n)
    tr[0] = high[0] - low[0]
    for i in range(1, n):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
    return _ema(tr, period)


def _macd(close, fast, slow, signal):
    ema_f = _ema(close, fast)
    ema_s = _ema(close, slow)
    macd_line = ema_f - ema_s
    valid = macd_line[~np.isnan(macd_line)]
    sig = _ema(valid, signal) if len(valid) >= signal else np.full(len(valid), np.nan)
    signal_line = np.full(len(close), np.nan)
    offset = len(close) - len(sig)
    signal_line[offset:] = sig
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def _bb(close, period, std_dev):
    mid = _sma(close, period)
    upper = np.full(len(close), np.nan)
    lower = np.full(len(close), np.nan)
    width = np.full(len(close), np.nan)
    pctb = np.full(len(close), np.nan)
    for i in range(period - 1, len(close)):
        s = np.std(close[i - period + 1:i + 1])
        upper[i] = mid[i] + std_dev * s
        lower[i] = mid[i] - std_dev * s
        width[i] = (upper[i] - lower[i]) / mid[i] * 100 if mid[i] else 0
        pctb[i] = (close[i] - lower[i]) / (upper[i] - lower[i]) * 100 if upper[i] != lower[i] else 50
    return upper, mid, lower, width, pctb


def _adx(high, low, close, period):
    n = len(close)
    plus_dm = np.zeros(n)
    minus_dm = np.zeros(n)
    for i in range(1, n):
        up = high[i] - high[i - 1]
        down = low[i - 1] - low[i]
        plus_dm[i] = up if up > down and up > 0 else 0
        minus_dm[i] = down if down > up and down > 0 else 0
    atr_val = _atr(high, low, close, period)
    plus_di = np.full(n, np.nan)
    minus_di = np.full(n, np.nan)
    adx = np.full(n, np.nan)
    sm_pdm = _ema(plus_dm, period)
    sm_mdm = _ema(minus_dm, period)
    for i in range(period, n):
        if atr_val[i] and atr_val[i] > 0:
            plus_di[i] = sm_pdm[i] / atr_val[i] * 100
            minus_di[i] = sm_mdm[i] / atr_val[i] * 100
    dx = np.full(n, np.nan)
    for i in range(period, n):
        if plus_di[i] is not None and minus_di[i] is not None:
            s = (plus_di[i] or 0) + (minus_di[i] or 0)
            if s > 0:
                dx[i] = abs((plus_di[i] or 0) - (minus_di[i] or 0)) / s * 100
    adx = _ema(dx, period)
    return adx, plus_di, minus_di


def _supertrend(high, low, close, period, multiplier):
    atr_val = _atr(high, low, close, period)
    n = len(close)
    st = np.full(n, np.nan)
    direction = np.zeros(n)
    upper = np.zeros(n)
    lower = np.zeros(n)
    for i in range(period, n):
        a = atr_val[i] if not np.isnan(atr_val[i]) else 0
        hl2 = (high[i] + low[i]) / 2
        upper[i] = hl2 + multiplier * a
        lower[i] = hl2 - multiplier * a
        if i > period:
            if close[i - 1] > upper[i - 1]:
                direction[i] = 1
            elif close[i - 1] < lower[i - 1]:
                direction[i] = -1
            else:
                direction[i] = direction[i - 1]
        st[i] = lower[i] if direction[i] == 1 else upper[i]
    return st, direction


def _get_source(df, source):
    if source == "hl2":
        return (df["high"].values + df["low"].values) / 2
    elif source == "hlc3":
        return (df["high"].values + df["low"].values + df["close"].values) / 3
    elif source in df.columns:
        return df[source].values
    return df["close"].values


def compute_indicator(df, indicator_id, params):
    """Compute indicator and return dict of output arrays."""
    c = df["close"].values
    h = df["high"].values
    l = df["low"].values
    o = df["open"].values
    n = len(c)

    if indicator_id == "SMA":
        src = _get_source(df, params.get("source", "close"))
        return {"value": _sma(src, params.get("period", 20))}

    elif indicator_id == "EMA":
        src = _get_source(df, params.get("source", "close"))
        return {"value": _ema(src, params.get("period", 20))}

    elif indicator_id == "WMA":
        return {"value": _wma(c, params.get("period", 20))}

    elif indicator_id == "DEMA":
        return {"value": _dema(c, params.get("period", 20))}

    elif indicator_id == "TEMA":
        return {"value": _tema(c, params.get("period", 20))}

    elif indicator_id == "RSI":
        return {"value": _rsi(c, params.get("period", 14))}

    elif indicator_id == "STOCH":
        k, d = _stoch(h, l, c, params.get("k_period", 14), params.get("d_period", 3), params.get("slowing", 3))
        return {"k": k, "d": d}

    elif indicator_id == "STOCHRSI":
        rsi = _rsi(c, params.get("rsi_period", 14))
        valid = rsi.copy()
        valid[np.isnan(valid)] = 50
        k, d = _stoch(valid, valid, valid, params.get("stoch_period", 14), params.get("d_smooth", 3), params.get("k_smooth", 3))
        return {"k": k, "d": d}

    elif indicator_id == "CCI":
        tp = (h + l + c) / 3
        sma = _sma(tp, params.get("period", 20))
        out = np.full(n, np.nan)
        p = params.get("period", 20)
        for i in range(p - 1, n):
            md = np.mean(np.abs(tp[i - p + 1:i + 1] - sma[i]))
            out[i] = (tp[i] - sma[i]) / (0.015 * md) if md > 0 else 0
        return {"value": out}

    elif indicator_id == "WILLIAMS":
        p = params.get("period", 14)
        out = np.full(n, np.nan)
        for i in range(p - 1, n):
            hh = np.max(h[i - p + 1:i + 1])
            ll = np.min(l[i - p + 1:i + 1])
            out[i] = (hh - c[i]) / (hh - ll) * -100 if hh != ll else -50
        return {"value": out}

    elif indicator_id == "MFI":
        return {"value": _rsi(c, params.get("period", 14))}  # Simplified

    elif indicator_id == "MACD":
        ml, sl, hist = _macd(c, params.get("fast", 12), params.get("slow", 26), params.get("signal", 9))
        return {"macd": ml, "signal": sl, "histogram": hist}

    elif indicator_id == "BB":
        u, m, lo, w, pb = _bb(c, params.get("period", 20), params.get("std_dev", 2.0))
        return {"upper": u, "middle": m, "lower": lo, "width": w, "percent_b": pb}

    elif indicator_id == "ATR":
        return {"value": _atr(h, l, c, params.get("period", 14))}

    elif indicator_id == "KELTNER":
        mid = _ema(c, params.get("ema_period", 20))
        atr = _atr(h, l, c, params.get("atr_period", 14))
        mult = params.get("multiplier", 1.5)
        return {"upper": mid + mult * atr, "middle": mid, "lower": mid - mult * atr}

    elif indicator_id == "DONCHIAN":
        p = params.get("period", 20)
        upper = np.full(n, np.nan)
        lower = np.full(n, np.nan)
        for i in range(p - 1, n):
            upper[i] = np.max(h[i - p + 1:i + 1])
            lower[i] = np.min(l[i - p + 1:i + 1])
        return {"upper": upper, "middle": (upper + lower) / 2, "lower": lower}

    elif indicator_id == "ADX":
        adx, pdi, mdi = _adx(h, l, c, params.get("period", 14))
        return {"adx": adx, "plus_di": pdi, "minus_di": mdi}

    elif indicator_id == "AROON":
        p = params.get("period", 25)
        up = np.full(n, np.nan)
        down = np.full(n, np.nan)
        for i in range(p, n):
            hh_idx = np.argmax(h[i - p:i + 1])
            ll_idx = np.argmin(l[i - p:i + 1])
            up[i] = hh_idx / p * 100
            down[i] = ll_idx / p * 100
        return {"up": up, "down": down, "oscillator": up - down}

    elif indicator_id == "SUPERTREND":
        st, d = _supertrend(h, l, c, params.get("period", 10), params.get("multiplier", 3.0))
        return {"value": st, "direction": d}

    elif indicator_id == "PSAR":
        return {"value": _ema(c, 14)}  # Simplified placeholder

    elif indicator_id == "ICHIMOKU":
        t = params.get("tenkan", 9)
        k = params.get("kijun", 26)
        sb = params.get("senkou_b", 52)
        tenkan = np.full(n, np.nan)
        kijun = np.full(n, np.nan)
        for i in range(max(t, k, sb) - 1, n):
            if i >= t - 1:
                tenkan[i] = (np.max(h[i - t + 1:i + 1]) + np.min(l[i - t + 1:i + 1])) / 2
            if i >= k - 1:
                kijun[i] = (np.max(h[i - k + 1:i + 1]) + np.min(l[i - k + 1:i + 1])) / 2
        sa = (tenkan + kijun) / 2
        senkou_b = np.full(n, np.nan)
        for i in range(sb - 1, n):
            senkou_b[i] = (np.max(h[i - sb + 1:i + 1]) + np.min(l[i - sb + 1:i + 1])) / 2
        return {"tenkan": tenkan, "kijun": kijun, "senkou_a": sa, "senkou_b": senkou_b, "chikou": c}

    elif indicator_id == "VOLUME":
        v = df["tick_volume"].values if "tick_volume" in df.columns else np.ones(n)
        return {"value": v}

    elif indicator_id == "OBV":
        v = df["tick_volume"].values if "tick_volume" in df.columns else np.ones(n)
        obv = np.zeros(n)
        for i in range(1, n):
            if c[i] > c[i - 1]:
                obv[i] = obv[i - 1] + v[i]
            elif c[i] < c[i - 1]:
                obv[i] = obv[i - 1] - v[i]
            else:
                obv[i] = obv[i - 1]
        return {"value": obv}

    elif indicator_id == "VWAP":
        return {"value": _sma(c, 20)}  # Simplified

    elif indicator_id == "PRICE":
        src = _get_source(df, params.get("source", "close"))
        return {"value": src}

    elif indicator_id == "CANDLE":
        bullish = np.zeros(n, dtype=bool)
        bearish = np.zeros(n, dtype=bool)
        pattern = params.get("pattern", "engulfing")
        for i in range(1, n):
            body = c[i] - o[i]
            prev_body = c[i - 1] - o[i - 1]
            upper_wick = h[i] - max(o[i], c[i])
            lower_wick = min(o[i], c[i]) - l[i]
            body_size = abs(body)
            if pattern == "engulfing":
                bullish[i] = body > 0 and prev_body < 0 and body_size > abs(prev_body)
                bearish[i] = body < 0 and prev_body > 0 and body_size > abs(prev_body)
            elif pattern == "hammer":
                bullish[i] = lower_wick > body_size * 2 and upper_wick < body_size * 0.5
            elif pattern == "shooting_star":
                bearish[i] = upper_wick > body_size * 2 and lower_wick < body_size * 0.5
            elif pattern == "doji":
                bullish[i] = body_size < (h[i] - l[i]) * 0.1
                bearish[i] = bullish[i]
            elif pattern == "pin_bar":
                rng = h[i] - l[i]
                if rng > 0:
                    bullish[i] = lower_wick / rng > 0.6 and body_size / rng < 0.2
                    bearish[i] = upper_wick / rng > 0.6 and body_size / rng < 0.2
            else:
                bullish[i] = body > 0
                bearish[i] = body < 0
        return {"bullish": bullish.astype(float), "bearish": bearish.astype(float)}

    elif indicator_id == "FIB_RETRACE":
        lb = params.get("lookback", 50)
        level = float(params.get("level", "0.618"))
        out = np.full(n, np.nan)
        for i in range(lb, n):
            hh = np.max(h[i - lb:i + 1])
            ll = np.min(l[i - lb:i + 1])
            out[i] = hh - (hh - ll) * level
        return {"level_price": out}

    elif indicator_id == "PIVOT":
        out = {k: np.full(n, np.nan) for k in ["pp", "r1", "r2", "r3", "s1", "s2", "s3"]}
        for i in range(1, n):
            pp = (h[i - 1] + l[i - 1] + c[i - 1]) / 3
            out["pp"][i] = pp
            out["r1"][i] = 2 * pp - l[i - 1]
            out["s1"][i] = 2 * pp - h[i - 1]
            out["r2"][i] = pp + (h[i - 1] - l[i - 1])
            out["s2"][i] = pp - (h[i - 1] - l[i - 1])
            out["r3"][i] = h[i - 1] + 2 * (pp - l[i - 1])
            out["s3"][i] = l[i - 1] - 2 * (h[i - 1] - pp)
        return out

    return {"value": np.full(n, np.nan)}
