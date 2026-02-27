"""
Whilber-AI — StochRSI Strategies
==================================
SRSI_01: StochRSI Overbought/Oversold
SRSI_02: StochRSI K/D Crossover
SRSI_03: StochRSI Divergence
SRSI_04: StochRSI + Trend Filter
SRSI_05: StochRSI Multi-Period
"""

import numpy as np


def _calc_rsi(close, period=14):
    delta = np.diff(close)
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = np.convolve(gain, np.ones(period)/period, mode='valid')
    avg_loss = np.convolve(loss, np.ones(period)/period, mode='valid')
    rs = np.divide(avg_gain, avg_loss, out=np.ones_like(avg_gain), where=avg_loss > 0)
    return 100 - (100 / (1 + rs))


def _calc_stoch_rsi(close, rsi_period=14, stoch_period=14, k_smooth=3, d_smooth=3):
    rsi = _calc_rsi(close, rsi_period)
    if len(rsi) < stoch_period:
        return None, None
    stoch_rsi = np.zeros(len(rsi))
    for i in range(stoch_period - 1, len(rsi)):
        window = rsi[i - stoch_period + 1:i + 1]
        low = np.min(window)
        high = np.max(window)
        if high - low > 0:
            stoch_rsi[i] = (rsi[i] - low) / (high - low)
        else:
            stoch_rsi[i] = 0.5
    valid = stoch_rsi[stoch_period - 1:]
    if len(valid) < k_smooth:
        return None, None
    k = np.convolve(valid, np.ones(k_smooth)/k_smooth, mode='valid')
    if len(k) < d_smooth:
        return None, None
    d = np.convolve(k, np.ones(d_smooth)/d_smooth, mode='valid')
    return k, d


def _ema(data, period):
    if len(data) < period:
        return None
    ema = np.zeros(len(data))
    ema[0] = np.mean(data[:period])
    mult = 2 / (period + 1)
    for i in range(1, len(data)):
        ema[i] = data[i] * mult + ema[i-1] * (1 - mult)
    return ema


# ── SRSI_01: Overbought/Oversold ───────────────────

def stochrsi_obos(df, context=None):
    """StochRSI اشباع خرید/فروش — K<0.2 خرید، K>0.8 فروش"""
    c = df["close"].values
    k, d = _calc_stoch_rsi(c)
    if k is None or len(k) < 2:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "StochRSI — داده کافی نیست"}

    k_now = k[-1]
    k_prev = k[-2]

    if k_now < 0.20 and k_now > k_prev:
        conf = 65 if k_now < 0.10 else 55
        return {"signal": "BUY", "confidence": conf,
                "reason_fa": f"StochRSI اشباع فروش — K={k_now:.3f} و برگشت بالا | ورود خرید"}
    elif k_now > 0.80 and k_now < k_prev:
        conf = 65 if k_now > 0.90 else 55
        return {"signal": "SELL", "confidence": conf,
                "reason_fa": f"StochRSI اشباع خرید — K={k_now:.3f} و برگشت پایین | ورود فروش"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"StochRSI خنثی — K={k_now:.3f}"}


# ── SRSI_02: K/D Crossover ─────────────────────────

def stochrsi_cross(df, context=None):
    """StochRSI تقاطع K و D"""
    c = df["close"].values
    k, d = _calc_stoch_rsi(c)
    if k is None or d is None or len(k) < 2 or len(d) < 2:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "StochRSI Cross — داده کافی نیست"}

    min_len = min(len(k), len(d))
    k = k[-min_len:]
    d = d[-min_len:]

    cross_up = k[-2] <= d[-2] and k[-1] > d[-1]
    cross_dn = k[-2] >= d[-2] and k[-1] < d[-1]

    if cross_up:
        conf = 65 if k[-1] < 0.30 else 50
        return {"signal": "BUY", "confidence": conf,
                "reason_fa": f"StochRSI تقاطع صعودی — K={k[-1]:.3f} از D={d[-1]:.3f} عبور بالا"}
    elif cross_dn:
        conf = 65 if k[-1] > 0.70 else 50
        return {"signal": "SELL", "confidence": conf,
                "reason_fa": f"StochRSI تقاطع نزولی — K={k[-1]:.3f} از D={d[-1]:.3f} عبور پایین"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"StochRSI — بدون تقاطع | K={k[-1]:.3f} D={d[-1]:.3f}"}


# ── SRSI_03: Divergence ────────────────────────────

def stochrsi_divergence(df, context=None):
    """StochRSI واگرایی با قیمت"""
    c = df["close"].values
    k, _ = _calc_stoch_rsi(c)
    if k is None or len(k) < 20:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "StochRSI Div — داده کافی نیست"}

    price_recent = c[-10:]
    price_prev = c[-20:-10]
    k_recent = k[-10:]
    k_prev = k[-20:-10] if len(k) >= 20 else k[:10]

    p_low_r = np.min(price_recent)
    p_low_p = np.min(price_prev)
    k_low_r = np.min(k_recent)
    k_low_p = np.min(k_prev)

    # Bullish divergence: price lower low, StochRSI higher low
    if p_low_r < p_low_p and k_low_r > k_low_p:
        return {"signal": "BUY", "confidence": 62,
                "reason_fa": f"StochRSI واگرایی صعودی — قیمت کف جدید ولی StochRSI کف بالاتر"}

    p_hi_r = np.max(price_recent)
    p_hi_p = np.max(price_prev)
    k_hi_r = np.max(k_recent)
    k_hi_p = np.max(k_prev)

    # Bearish divergence
    if p_hi_r > p_hi_p and k_hi_r < k_hi_p:
        return {"signal": "SELL", "confidence": 62,
                "reason_fa": f"StochRSI واگرایی نزولی — قیمت سقف جدید ولی StochRSI سقف پایین‌تر"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": "StochRSI — واگرایی یافت نشد"}


# ── SRSI_04: Trend Filter ──────────────────────────

def stochrsi_trend(df, context=None):
    """StochRSI + فیلتر روند EMA50"""
    c = df["close"].values
    k, d = _calc_stoch_rsi(c)
    if k is None or len(c) < 50:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "StochRSI Trend — داده کافی نیست"}

    ema50 = _ema(c, 50)
    if ema50 is None:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "StochRSI Trend — EMA محاسبه نشد"}

    price = c[-1]
    above_ema = price > ema50[-1]
    k_now = k[-1]

    if above_ema and k_now < 0.25:
        return {"signal": "BUY", "confidence": 68,
                "reason_fa": f"StochRSI اشباع فروش + بالای EMA50 — K={k_now:.3f} | خرید تایید شده"}
    elif not above_ema and k_now > 0.75:
        return {"signal": "SELL", "confidence": 68,
                "reason_fa": f"StochRSI اشباع خرید + زیر EMA50 — K={k_now:.3f} | فروش تایید شده"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"StochRSI — K={k_now:.3f} {'بالای' if above_ema else 'زیر'} EMA50"}


# ── SRSI_05: Multi-Period ──────────────────────────

def stochrsi_multi(df, context=None):
    """StochRSI سه دوره‌ای — هم‌جهت = سیگنال قوی"""
    c = df["close"].values

    k7, _ = _calc_stoch_rsi(c, rsi_period=7, stoch_period=7)
    k14, _ = _calc_stoch_rsi(c, rsi_period=14, stoch_period=14)
    k21, _ = _calc_stoch_rsi(c, rsi_period=21, stoch_period=21)

    if k7 is None or k14 is None or k21 is None:
        return {"signal": "NEUTRAL", "confidence": 0,
                "reason_fa": "StochRSI Multi — داده کافی نیست"}

    v7, v14, v21 = k7[-1], k14[-1], k21[-1]

    all_os = v7 < 0.25 and v14 < 0.30 and v21 < 0.35
    all_ob = v7 > 0.75 and v14 > 0.70 and v21 > 0.65

    if all_os:
        return {"signal": "BUY", "confidence": 72,
                "reason_fa": f"StochRSI سه‌گانه اشباع فروش — K7={v7:.2f} K14={v14:.2f} K21={v21:.2f} | خرید قوی"}
    elif all_ob:
        return {"signal": "SELL", "confidence": 72,
                "reason_fa": f"StochRSI سه‌گانه اشباع خرید — K7={v7:.2f} K14={v14:.2f} K21={v21:.2f} | فروش قوی"}

    return {"signal": "NEUTRAL", "confidence": 0,
            "reason_fa": f"StochRSI Multi — K7={v7:.2f} K14={v14:.2f} K21={v21:.2f} هم‌جهت نیست"}


# ── Export ──────────────────────────────────────────

SRSI_STRATEGIES = [
    {"id": "SRSI_01", "name": "StochRSI OB/OS", "name_fa": "StochRSI اشباع", "func": stochrsi_obos},
    {"id": "SRSI_02", "name": "StochRSI Cross", "name_fa": "StochRSI تقاطع", "func": stochrsi_cross},
    {"id": "SRSI_03", "name": "StochRSI Divergence", "name_fa": "StochRSI واگرایی", "func": stochrsi_divergence},
    {"id": "SRSI_04", "name": "StochRSI Trend", "name_fa": "StochRSI + روند", "func": stochrsi_trend},
    {"id": "SRSI_05", "name": "StochRSI Multi", "name_fa": "StochRSI چند دوره", "func": stochrsi_multi},
]
