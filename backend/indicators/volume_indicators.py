"""
Whilber-AI MVP - Indicator Module: Volume
============================================
Step 2.5 - OBV, MFI, CMF, Chaikin Oscillator, VWAP, Volume Spike.
Note: MT5 provides tick_volume (renamed to "volume"). True volume
may not be available for forex/CFDs but works for crypto/indices.
"""

import numpy as np
import pandas as pd
from typing import Dict


# ── OBV (On Balance Volume) ────────────────────────────────────

def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On Balance Volume."""
    direction = close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    return (volume * direction).cumsum()


def obv_trend(obv_series: pd.Series, period: int = 20) -> pd.Series:
    """OBV trend: 1=rising, -1=falling, 0=flat."""
    ma = obv_series.rolling(window=period).mean()
    result = pd.Series(0, index=obv_series.index)
    result[obv_series > ma] = 1
    result[obv_series < ma] = -1
    return result


# ── MFI (Money Flow Index) ─────────────────────────────────────

def mfi(high: pd.Series, low: pd.Series, close: pd.Series,
        volume: pd.Series, period: int = 14) -> pd.Series:
    """
    Money Flow Index (volume-weighted RSI).
    Range: 0-100. Above 80 = overbought, below 20 = oversold.
    """
    typical_price = (high + low + close) / 3
    raw_money_flow = typical_price * volume

    tp_diff = typical_price.diff()
    pos_flow = raw_money_flow.where(tp_diff > 0, 0)
    neg_flow = raw_money_flow.where(tp_diff < 0, 0)

    pos_sum = pos_flow.rolling(window=period, min_periods=period).sum()
    neg_sum = neg_flow.rolling(window=period, min_periods=period).sum()

    money_ratio = pos_sum / neg_sum.replace(0, np.nan)
    return 100 - (100 / (1 + money_ratio))


def mfi_zone(mfi_val: pd.Series, ob: float = 80, os: float = 20) -> pd.Series:
    """MFI zone: 1=overbought, -1=oversold, 0=neutral."""
    result = pd.Series(0, index=mfi_val.index)
    result[mfi_val >= ob] = 1
    result[mfi_val <= os] = -1
    return result


# ── CMF (Chaikin Money Flow) ───────────────────────────────────

def cmf(high: pd.Series, low: pd.Series, close: pd.Series,
        volume: pd.Series, period: int = 20) -> pd.Series:
    """
    Chaikin Money Flow.
    Range: -1 to +1. Positive = buying pressure, negative = selling.
    """
    hl_range = (high - low).replace(0, np.nan)
    clv = ((close - low) - (high - close)) / hl_range
    mf_volume = clv * volume

    return mf_volume.rolling(window=period).sum() / volume.rolling(window=period).sum()


# ── Chaikin Oscillator ──────────────────────────────────────────

def chaikin_oscillator(high: pd.Series, low: pd.Series, close: pd.Series,
                       volume: pd.Series, fast: int = 3,
                       slow: int = 10) -> pd.Series:
    """Chaikin Oscillator: EMA(3) of ADL - EMA(10) of ADL."""
    hl_range = (high - low).replace(0, np.nan)
    clv = ((close - low) - (high - close)) / hl_range
    adl = (clv * volume).cumsum()

    ema_fast = adl.ewm(span=fast, adjust=False).mean()
    ema_slow = adl.ewm(span=slow, adjust=False).mean()
    return ema_fast - ema_slow


# ── Volume Oscillator ──────────────────────────────────────────

def volume_oscillator(volume: pd.Series, fast: int = 5,
                      slow: int = 20) -> pd.Series:
    """Volume Oscillator: percentage difference between fast/slow volume EMAs."""
    ema_fast = volume.ewm(span=fast, adjust=False).mean()
    ema_slow = volume.ewm(span=slow, adjust=False).mean()
    return ((ema_fast - ema_slow) / ema_slow) * 100


# ── VWAP (Volume Weighted Average Price) ───────────────────────

def vwap(high: pd.Series, low: pd.Series, close: pd.Series,
         volume: pd.Series) -> pd.Series:
    """
    VWAP: cumulative from start of data.
    For intraday, data should be from session start.
    """
    typical_price = (high + low + close) / 3
    cum_tp_vol = (typical_price * volume).cumsum()
    cum_vol = volume.cumsum()
    return cum_tp_vol / cum_vol.replace(0, np.nan)


def vwap_bands(vwap_series: pd.Series, close: pd.Series, volume: pd.Series,
               high: pd.Series, low: pd.Series,
               multiplier: float = 1.0) -> Dict[str, pd.Series]:
    """VWAP with standard deviation bands."""
    typical_price = (high + low + close) / 3
    cum_vol = volume.cumsum()
    cum_tp_vol = (typical_price * volume).cumsum()
    cum_tp2_vol = (typical_price ** 2 * volume).cumsum()

    vwap_val = cum_tp_vol / cum_vol.replace(0, np.nan)
    variance = (cum_tp2_vol / cum_vol.replace(0, np.nan)) - vwap_val ** 2
    std = np.sqrt(variance.clip(lower=0))

    return {
        "vwap": vwap_val,
        "vwap_upper": vwap_val + multiplier * std,
        "vwap_lower": vwap_val - multiplier * std,
    }


def vwap_position(close: pd.Series, vwap_series: pd.Series) -> pd.Series:
    """Price position vs VWAP: 1=above, -1=below."""
    result = pd.Series(0, index=close.index)
    result[close > vwap_series] = 1
    result[close < vwap_series] = -1
    return result


# ── Volume Spike Detection ─────────────────────────────────────

def volume_spike(volume: pd.Series, lookback: int = 20,
                 threshold: float = 2.0) -> pd.Series:
    """
    Detect volume spikes: volume > threshold * average.
    Returns 1 for spike, 0 for normal.
    """
    avg_vol = volume.rolling(window=lookback, min_periods=5).mean()
    result = pd.Series(0, index=volume.index)
    result[volume > threshold * avg_vol] = 1
    return result


def volume_climax(close: pd.Series, volume: pd.Series,
                  lookback: int = 20, threshold: float = 2.5) -> pd.Series:
    """
    Volume climax: extreme volume with potential reversal.
    1 = climax at top (potential bearish), -1 = climax at bottom (potential bullish).
    """
    avg_vol = volume.rolling(window=lookback, min_periods=5).mean()
    is_spike = volume > threshold * avg_vol
    price_up = close > close.shift(1)
    price_down = close < close.shift(1)

    result = pd.Series(0, index=close.index)
    result[is_spike & price_up] = 1    # Climax top
    result[is_spike & price_down] = -1  # Climax bottom
    return result


# ── Compute All Volume Indicators ──────────────────────────────

def compute_volume(df: pd.DataFrame) -> Dict[str, pd.Series]:
    """Compute all volume indicators."""
    h, l, c, v = df["high"], df["low"], df["close"], df["volume"]
    results = {}

    # OBV
    results["obv"] = obv(c, v)
    results["obv_trend"] = obv_trend(results["obv"])

    # MFI
    results["mfi_14"] = mfi(h, l, c, v, 14)
    results["mfi_zone"] = mfi_zone(results["mfi_14"])

    # CMF
    results["cmf_20"] = cmf(h, l, c, v, 20)

    # Chaikin Oscillator
    results["chaikin_osc"] = chaikin_oscillator(h, l, c, v)

    # Volume Oscillator
    results["vol_osc"] = volume_oscillator(v, 5, 20)

    # VWAP
    vw = vwap_bands(vwap(h, l, c, v), c, v, h, l)
    results.update(vw)
    results["vwap_position"] = vwap_position(c, vw["vwap"])

    # Volume Spike
    results["vol_spike"] = volume_spike(v, 20, 2.0)
    results["vol_climax"] = volume_climax(c, v, 20, 2.5)

    return results
