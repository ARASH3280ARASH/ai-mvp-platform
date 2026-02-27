"""
Whilber-AI MVP - Indicator Module: Trend Strength
====================================================
Step 2.6 - ADX, +DI/-DI, Aroon, trend regime detection.
Classifies market as trending or ranging.
"""

import numpy as np
import pandas as pd
from typing import Dict


# ── ADX / DMI (Directional Movement) ───────────────────────────

def adx_dmi(high: pd.Series, low: pd.Series, close: pd.Series,
            period: int = 14) -> Dict[str, pd.Series]:
    """
    ADX with +DI and -DI.
    ADX > 25 = trending, ADX < 20 = ranging.
    """
    # True Range
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Directional Movement
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low

    plus_dm = pd.Series(0.0, index=high.index)
    minus_dm = pd.Series(0.0, index=high.index)

    plus_dm[(up_move > down_move) & (up_move > 0)] = up_move
    minus_dm[(down_move > up_move) & (down_move > 0)] = down_move

    # Smooth with Wilder's method
    atr_smooth = tr.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    plus_dm_smooth = plus_dm.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    minus_dm_smooth = minus_dm.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

    # +DI and -DI
    plus_di = (plus_dm_smooth / atr_smooth.replace(0, np.nan)) * 100
    minus_di = (minus_dm_smooth / atr_smooth.replace(0, np.nan)) * 100

    # DX and ADX
    di_sum = plus_di + minus_di
    dx = ((plus_di - minus_di).abs() / di_sum.replace(0, np.nan)) * 100
    adx_val = dx.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

    return {
        "adx": adx_val,
        "plus_di": plus_di,
        "minus_di": minus_di,
    }


def adx_trend_strength(adx: pd.Series) -> pd.Series:
    """
    Classify trend strength by ADX value.
    0 = no trend (<20), 1 = weak (20-25), 2 = strong (25-50), 3 = very strong (>50).
    """
    result = pd.Series(0, index=adx.index)
    result[(adx >= 20) & (adx < 25)] = 1
    result[(adx >= 25) & (adx < 50)] = 2
    result[adx >= 50] = 3
    return result


def di_cross(plus_di: pd.Series, minus_di: pd.Series) -> pd.Series:
    """DI crossover: 1=+DI crosses above -DI (bullish), -1=bearish."""
    above = plus_di > minus_di
    cross = above.astype(int).diff()
    result = pd.Series(0, index=plus_di.index)
    result[cross == 1] = 1
    result[cross == -1] = -1
    return result


def adx_direction(adx: pd.Series, plus_di: pd.Series, minus_di: pd.Series,
                  min_adx: float = 20) -> pd.Series:
    """
    Combined ADX direction signal.
    1 = bullish trend (+DI > -DI and ADX > threshold)
    -1 = bearish trend (-DI > +DI and ADX > threshold)
    0 = no clear trend
    """
    result = pd.Series(0, index=adx.index)
    trending = adx >= min_adx
    result[trending & (plus_di > minus_di)] = 1
    result[trending & (minus_di > plus_di)] = -1
    return result


# ── Aroon ───────────────────────────────────────────────────────

def aroon(high: pd.Series, low: pd.Series,
          period: int = 25) -> Dict[str, pd.Series]:
    """
    Aroon indicator: Aroon Up, Aroon Down, Aroon Oscillator.
    """
    aroon_up = pd.Series(np.nan, index=high.index)
    aroon_down = pd.Series(np.nan, index=high.index)

    for i in range(period, len(high)):
        window_high = high.iloc[i - period:i + 1]
        window_low = low.iloc[i - period:i + 1]

        bars_since_high = period - window_high.values.argmax()
        bars_since_low = period - window_low.values.argmin()

        aroon_up.iloc[i] = ((period - bars_since_high) / period) * 100
        aroon_down.iloc[i] = ((period - bars_since_low) / period) * 100

    aroon_osc = aroon_up - aroon_down

    return {
        "aroon_up": aroon_up,
        "aroon_down": aroon_down,
        "aroon_osc": aroon_osc,
    }


def aroon_trend(aroon_up: pd.Series, aroon_down: pd.Series) -> pd.Series:
    """
    Aroon trend: 1=uptrend (up>70, down<30), -1=downtrend, 0=consolidation.
    """
    result = pd.Series(0, index=aroon_up.index)
    result[(aroon_up > 70) & (aroon_down < 30)] = 1
    result[(aroon_down > 70) & (aroon_up < 30)] = -1
    return result


# ── Market Regime Detection ─────────────────────────────────────

def detect_regime(close: pd.Series, high: pd.Series, low: pd.Series,
                  adx_period: int = 14, lookback: int = 20) -> Dict[str, pd.Series]:
    """
    Detect market regime: trending vs ranging.

    Uses multiple methods:
    1. ADX level
    2. Price range compression
    3. MA slope

    Returns regime: "trending_up", "trending_down", "ranging"
    And a numeric: 1=uptrend, -1=downtrend, 0=range
    """
    # ADX
    dmi = adx_dmi(high, low, close, adx_period)
    adx_val = dmi["adx"]

    # Price range / ATR compression
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)

    atr_val = tr.ewm(alpha=1/adx_period, min_periods=adx_period, adjust=False).mean()
    atr_pct = (atr_val / close) * 100

    # MA slope
    ma_20 = close.rolling(window=20, min_periods=20).mean()
    ma_slope = ((ma_20 - ma_20.shift(5)) / ma_20.shift(5)) * 100

    # Classify
    regime = pd.Series(0, index=close.index)

    # Strong trend
    strong = adx_val > 25
    regime[strong & (dmi["plus_di"] > dmi["minus_di"])] = 1
    regime[strong & (dmi["minus_di"] > dmi["plus_di"])] = -1

    # Weak/range
    regime[adx_val < 20] = 0

    # Regime label
    regime_label = pd.Series("ranging", index=close.index)
    regime_label[regime == 1] = "trending_up"
    regime_label[regime == -1] = "trending_down"

    return {
        "regime": regime,
        "regime_label": regime_label,
        "regime_adx": adx_val,
        "regime_atr_pct": atr_pct,
        "regime_ma_slope": ma_slope,
    }


# ── Compute All Trend Strength ─────────────────────────────────

def compute_trend_strength(df: pd.DataFrame) -> Dict[str, pd.Series]:
    """Compute all trend strength indicators."""
    h, l, c = df["high"], df["low"], df["close"]
    results = {}

    # ADX / DMI
    dmi = adx_dmi(h, l, c, 14)
    results.update(dmi)
    results["adx_strength"] = adx_trend_strength(dmi["adx"])
    results["di_cross"] = di_cross(dmi["plus_di"], dmi["minus_di"])
    results["adx_direction"] = adx_direction(dmi["adx"], dmi["plus_di"], dmi["minus_di"])

    # Aroon
    ar = aroon(h, l, 25)
    results.update(ar)
    results["aroon_trend"] = aroon_trend(ar["aroon_up"], ar["aroon_down"])

    # Market Regime
    regime = detect_regime(c, h, l)
    results.update(regime)

    return results
