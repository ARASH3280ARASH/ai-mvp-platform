"""
Whilber-AI MVP - Indicator Module: MACD & Derivatives
========================================================
Step 2.3 - MACD, TRIX, TSI, Awesome Oscillator
With signal cross, histogram, zero-line cross detection.
"""

import numpy as np
import pandas as pd
from typing import Dict


# ── MACD ────────────────────────────────────────────────────────

def macd(close: pd.Series, fast: int = 12, slow: int = 26,
         signal: int = 9) -> Dict[str, pd.Series]:
    """
    MACD (Moving Average Convergence Divergence).
    Returns macd_line, signal_line, histogram.
    """
    ema_fast = close.ewm(span=fast, adjust=False, min_periods=fast).mean()
    ema_slow = close.ewm(span=slow, adjust=False, min_periods=slow).mean()

    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    histogram = macd_line - signal_line

    return {
        "macd_line": macd_line,
        "macd_signal": signal_line,
        "macd_hist": histogram,
    }


def macd_signal_cross(macd_line: pd.Series, signal_line: pd.Series) -> pd.Series:
    """MACD signal line crossover: 1=bullish, -1=bearish."""
    above = macd_line > signal_line
    cross = above.astype(int).diff()
    result = pd.Series(0, index=macd_line.index)
    result[cross == 1] = 1
    result[cross == -1] = -1
    return result


def macd_zero_cross(macd_line: pd.Series) -> pd.Series:
    """MACD zero-line crossover: 1=cross above, -1=cross below."""
    above = macd_line > 0
    cross = above.astype(int).diff()
    result = pd.Series(0, index=macd_line.index)
    result[cross == 1] = 1
    result[cross == -1] = -1
    return result


def macd_histogram_trend(histogram: pd.Series) -> pd.Series:
    """
    Histogram direction: 1=growing positive, -1=growing negative,
    2=shrinking positive (weakening bull), -2=shrinking negative (weakening bear).
    """
    result = pd.Series(0, index=histogram.index)
    hist_diff = histogram.diff()

    result[(histogram > 0) & (hist_diff > 0)] = 1    # Growing positive
    result[(histogram > 0) & (hist_diff < 0)] = 2    # Shrinking positive
    result[(histogram < 0) & (hist_diff < 0)] = -1   # Growing negative
    result[(histogram < 0) & (hist_diff > 0)] = -2   # Shrinking negative

    return result


# ── TRIX ────────────────────────────────────────────────────────

def trix(close: pd.Series, period: int = 15, signal: int = 9) -> Dict[str, pd.Series]:
    """
    TRIX: Triple-smoothed EMA rate of change.
    """
    ema1 = close.ewm(span=period, adjust=False, min_periods=period).mean()
    ema2 = ema1.ewm(span=period, adjust=False, min_periods=period).mean()
    ema3 = ema2.ewm(span=period, adjust=False, min_periods=period).mean()

    trix_line = ((ema3 - ema3.shift(1)) / ema3.shift(1)) * 10000
    signal_line = trix_line.ewm(span=signal, adjust=False, min_periods=signal).mean()

    return {"trix_line": trix_line, "trix_signal": signal_line}


# ── TSI (True Strength Index) ──────────────────────────────────

def tsi(close: pd.Series, long_period: int = 25, short_period: int = 13,
        signal: int = 7) -> Dict[str, pd.Series]:
    """True Strength Index."""
    diff = close.diff()

    smooth1 = diff.ewm(span=long_period, adjust=False, min_periods=long_period).mean()
    double_smooth = smooth1.ewm(span=short_period, adjust=False, min_periods=short_period).mean()

    abs_smooth1 = diff.abs().ewm(span=long_period, adjust=False, min_periods=long_period).mean()
    abs_double = abs_smooth1.ewm(span=short_period, adjust=False, min_periods=short_period).mean()

    tsi_line = (double_smooth / abs_double.replace(0, np.nan)) * 100
    signal_line = tsi_line.ewm(span=signal, adjust=False, min_periods=signal).mean()

    return {"tsi_line": tsi_line, "tsi_signal": signal_line}


# ── Awesome Oscillator ─────────────────────────────────────────

def awesome_oscillator(high: pd.Series, low: pd.Series,
                       fast: int = 5, slow: int = 34) -> pd.Series:
    """
    Awesome Oscillator (Bill Williams).
    Midpoint SMA(5) - Midpoint SMA(34).
    """
    midpoint = (high + low) / 2
    ao = midpoint.rolling(window=fast).mean() - midpoint.rolling(window=slow).mean()
    return ao


def ao_zero_cross(ao: pd.Series) -> pd.Series:
    """AO zero-line cross: 1=bullish, -1=bearish."""
    above = ao > 0
    cross = above.astype(int).diff()
    result = pd.Series(0, index=ao.index)
    result[cross == 1] = 1
    result[cross == -1] = -1
    return result


def ao_twin_peaks(ao: pd.Series, lookback: int = 20) -> pd.Series:
    """
    Simplified twin peaks detection.
    Bullish: two negative dips, second higher (less negative).
    Bearish: two positive peaks, second lower.
    """
    result = pd.Series(0, index=ao.index)
    # Simple version: check if AO crossed zero recently then came back
    for i in range(lookback, len(ao)):
        window = ao.iloc[i - lookback:i + 1]
        if ao.iloc[i] < 0:
            neg_vals = window[window < 0]
            if len(neg_vals) > 2:
                if neg_vals.iloc[-1] > neg_vals.min():
                    result.iloc[i] = 1  # Bullish twin peak
        elif ao.iloc[i] > 0:
            pos_vals = window[window > 0]
            if len(pos_vals) > 2:
                if pos_vals.iloc[-1] < pos_vals.max():
                    result.iloc[i] = -1  # Bearish twin peak
    return result


# ── Compute All MACD-family ────────────────────────────────────

def compute_macd_indicators(df: pd.DataFrame) -> Dict[str, pd.Series]:
    """Compute all MACD-family indicators."""
    c, h, l = df["close"], df["high"], df["low"]
    results = {}

    # MACD (12, 26, 9)
    m = macd(c, 12, 26, 9)
    results.update(m)
    results["macd_cross"] = macd_signal_cross(m["macd_line"], m["macd_signal"])
    results["macd_zero_cross"] = macd_zero_cross(m["macd_line"])
    results["macd_hist_trend"] = macd_histogram_trend(m["macd_hist"])

    # TRIX
    t = trix(c, 15, 9)
    results.update(t)

    # TSI
    ts = tsi(c, 25, 13, 7)
    results.update(ts)

    # Awesome Oscillator
    results["ao"] = awesome_oscillator(h, l, 5, 34)
    results["ao_zero_cross"] = ao_zero_cross(results["ao"])

    return results
