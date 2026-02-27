"""
Whilber-AI MVP - Indicator Module: Moving Averages
=====================================================
Step 2.1 - All MA types with slope and distance analysis.

Supported: SMA, EMA, WMA, HMA, DEMA, TEMA
Analysis: slope, distance from price, cross detection, stack alignment
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple


# ── Core MA Functions ───────────────────────────────────────────

def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period, min_periods=period).mean()


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def wma(series: pd.Series, period: int) -> pd.Series:
    """Weighted Moving Average."""
    weights = np.arange(1, period + 1, dtype=float)
    return series.rolling(window=period, min_periods=period).apply(
        lambda x: np.dot(x, weights) / weights.sum(), raw=True
    )


def hma(series: pd.Series, period: int) -> pd.Series:
    """Hull Moving Average (faster, less lag)."""
    half_period = max(int(period / 2), 1)
    sqrt_period = max(int(np.sqrt(period)), 1)
    wma_half = wma(series, half_period)
    wma_full = wma(series, period)
    diff = 2 * wma_half - wma_full
    return wma(diff, sqrt_period)


def dema(series: pd.Series, period: int) -> pd.Series:
    """Double Exponential Moving Average."""
    ema1 = ema(series, period)
    ema2 = ema(ema1, period)
    return 2 * ema1 - ema2


def tema(series: pd.Series, period: int) -> pd.Series:
    """Triple Exponential Moving Average."""
    ema1 = ema(series, period)
    ema2 = ema(ema1, period)
    ema3 = ema(ema2, period)
    return 3 * ema1 - 3 * ema2 + ema3


# ── MA Selector ─────────────────────────────────────────────────

MA_FUNCTIONS = {
    "sma": sma,
    "ema": ema,
    "wma": wma,
    "hma": hma,
    "dema": dema,
    "tema": tema,
}


def calc_ma(series: pd.Series, period: int, ma_type: str = "ema") -> pd.Series:
    """Calculate any MA type by name."""
    func = MA_FUNCTIONS.get(ma_type.lower())
    if func is None:
        raise ValueError(f"Unknown MA type: {ma_type}. Use: {list(MA_FUNCTIONS.keys())}")
    return func(series, period)


# ── MA Analysis ─────────────────────────────────────────────────

def ma_slope(ma_series: pd.Series, lookback: int = 5) -> pd.Series:
    """
    Calculate MA slope (rate of change over lookback bars).
    Positive = uptrend, Negative = downtrend.
    """
    return (ma_series - ma_series.shift(lookback)) / lookback


def ma_slope_angle(ma_series: pd.Series, lookback: int = 5) -> pd.Series:
    """
    Normalized slope as percentage change.
    Easier to compare across different price levels.
    """
    shifted = ma_series.shift(lookback)
    return ((ma_series - shifted) / shifted) * 100


def ma_slope_direction(ma_series: pd.Series, lookback: int = 5,
                       threshold: float = 0.0) -> pd.Series:
    """
    Classify slope: 1 = up, -1 = down, 0 = flat.
    threshold: minimum slope to count as trending.
    """
    slope = ma_slope_angle(ma_series, lookback)
    result = pd.Series(0, index=ma_series.index)
    result[slope > threshold] = 1
    result[slope < -threshold] = -1
    return result


def price_distance_from_ma(close: pd.Series, ma_series: pd.Series) -> pd.Series:
    """
    Distance of price from MA as percentage.
    Positive = price above MA, Negative = below.
    """
    return ((close - ma_series) / ma_series) * 100


def price_vs_ma(close: pd.Series, ma_series: pd.Series) -> pd.Series:
    """
    Simple position: 1 = price above MA, -1 = below, 0 = touching.
    """
    result = pd.Series(0, index=close.index)
    result[close > ma_series] = 1
    result[close < ma_series] = -1
    return result


# ── MA Crossover Detection ─────────────────────────────────────

def ma_cross(fast_ma: pd.Series, slow_ma: pd.Series) -> pd.Series:
    """
    Detect MA crossovers.
    Returns: 1 = bullish cross (fast crosses above slow)
            -1 = bearish cross (fast crosses below slow)
             0 = no cross
    """
    above = fast_ma > slow_ma
    cross = above.astype(int).diff()
    result = pd.Series(0, index=fast_ma.index)
    result[cross == 1] = 1    # Bullish cross
    result[cross == -1] = -1  # Bearish cross
    return result


def ma_cross_bars_ago(fast_ma: pd.Series, slow_ma: pd.Series) -> pd.Series:
    """
    How many bars ago the last cross happened.
    Positive value = bullish cross N bars ago.
    Negative value = bearish cross N bars ago.
    """
    cross = ma_cross(fast_ma, slow_ma)
    result = pd.Series(np.nan, index=fast_ma.index)

    last_cross_bar = None
    last_cross_type = 0

    for i in range(len(cross)):
        if cross.iloc[i] != 0:
            last_cross_bar = i
            last_cross_type = cross.iloc[i]
        if last_cross_bar is not None:
            result.iloc[i] = (i - last_cross_bar) * last_cross_type

    return result


# ── MA Stack / Alignment ───────────────────────────────────────

def ma_stack_alignment(ma_fast: pd.Series, ma_mid: pd.Series,
                       ma_slow: pd.Series) -> pd.Series:
    """
    Check if MAs are properly stacked (aligned).
    Returns:  1 = bullish stack (fast > mid > slow)
             -1 = bearish stack (fast < mid < slow)
              0 = mixed/no alignment
    """
    result = pd.Series(0, index=ma_fast.index)
    bullish = (ma_fast > ma_mid) & (ma_mid > ma_slow)
    bearish = (ma_fast < ma_mid) & (ma_mid < ma_slow)
    result[bullish] = 1
    result[bearish] = -1
    return result


# ── Compute All MAs for DataFrame ──────────────────────────────

def compute_moving_averages(df: pd.DataFrame,
                            periods: list = None,
                            ma_type: str = "ema",
                            source: str = "close") -> Dict[str, pd.Series]:
    """
    Compute multiple MAs and their analysis for a DataFrame.

    Args:
        df: DataFrame with OHLCV data
        periods: List of periods (default: [9, 21, 50, 100, 200])
        ma_type: Type of MA to use
        source: Column to use (default: "close")

    Returns:
        Dict with keys like "ema_9", "ema_9_slope", etc.
    """
    if periods is None:
        periods = [9, 21, 50, 100, 200]

    src = df[source]
    results = {}

    for p in periods:
        key = f"{ma_type}_{p}"
        ma_val = calc_ma(src, p, ma_type)
        results[key] = ma_val
        results[f"{key}_slope"] = ma_slope_angle(ma_val, lookback=5)
        results[f"{key}_direction"] = ma_slope_direction(ma_val, lookback=5)
        results[f"{key}_distance"] = price_distance_from_ma(src, ma_val)
        results[f"{key}_position"] = price_vs_ma(src, ma_val)

    # Crossover pairs
    if len(periods) >= 2:
        sorted_p = sorted(periods)
        for i in range(len(sorted_p) - 1):
            fast_key = f"{ma_type}_{sorted_p[i]}"
            slow_key = f"{ma_type}_{sorted_p[i+1]}"
            cross_key = f"cross_{sorted_p[i]}_{sorted_p[i+1]}"
            results[cross_key] = ma_cross(results[fast_key], results[slow_key])

    # Stack alignment (if 3+ periods)
    if len(periods) >= 3:
        sorted_p = sorted(periods)
        fast = results[f"{ma_type}_{sorted_p[0]}"]
        mid = results[f"{ma_type}_{sorted_p[len(sorted_p)//2]}"]
        slow = results[f"{ma_type}_{sorted_p[-1]}"]
        results["ma_stack"] = ma_stack_alignment(fast, mid, slow)

    return results
