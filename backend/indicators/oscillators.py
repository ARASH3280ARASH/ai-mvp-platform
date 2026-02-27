"""
Whilber-AI MVP - Indicator Module: Oscillators
=================================================
Step 2.2 - RSI, Stochastic, StochRSI, Williams %R, CCI, ROC, Momentum
With overbought/oversold detection and divergence helpers.
"""

import numpy as np
import pandas as pd
from typing import Dict


# ── RSI ─────────────────────────────────────────────────────────

def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def rsi_zone(rsi_series: pd.Series,
             ob: float = 70, os: float = 30) -> pd.Series:
    """
    Classify RSI zone: 1=overbought, -1=oversold, 0=neutral.
    """
    result = pd.Series(0, index=rsi_series.index)
    result[rsi_series >= ob] = 1
    result[rsi_series <= os] = -1
    return result


# ── Stochastic Oscillator ──────────────────────────────────────

def stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
               k_period: int = 14, d_period: int = 3,
               smooth_k: int = 3) -> Dict[str, pd.Series]:
    """
    Stochastic Oscillator (%K and %D).
    """
    lowest_low = low.rolling(window=k_period, min_periods=k_period).min()
    highest_high = high.rolling(window=k_period, min_periods=k_period).max()

    raw_k = ((close - lowest_low) / (highest_high - lowest_low).replace(0, np.nan)) * 100
    k = raw_k.rolling(window=smooth_k, min_periods=1).mean()
    d = k.rolling(window=d_period, min_periods=1).mean()

    return {"stoch_k": k, "stoch_d": d}


def stochastic_zone(k: pd.Series, ob: float = 80, os: float = 20) -> pd.Series:
    """Classify stochastic zone."""
    result = pd.Series(0, index=k.index)
    result[k >= ob] = 1
    result[k <= os] = -1
    return result


def stochastic_cross(k: pd.Series, d: pd.Series) -> pd.Series:
    """Stochastic K/D crossover: 1=bullish, -1=bearish, 0=none."""
    above = k > d
    cross = above.astype(int).diff()
    result = pd.Series(0, index=k.index)
    result[cross == 1] = 1
    result[cross == -1] = -1
    return result


# ── Stochastic RSI ──────────────────────────────────────────────

def stoch_rsi(close: pd.Series, rsi_period: int = 14,
              stoch_period: int = 14, k_smooth: int = 3,
              d_smooth: int = 3) -> Dict[str, pd.Series]:
    """StochRSI: Stochastic applied to RSI values."""
    rsi_val = rsi(close, rsi_period)

    lowest = rsi_val.rolling(window=stoch_period, min_periods=stoch_period).min()
    highest = rsi_val.rolling(window=stoch_period, min_periods=stoch_period).max()

    stoch_rsi_raw = ((rsi_val - lowest) / (highest - lowest).replace(0, np.nan)) * 100
    k = stoch_rsi_raw.rolling(window=k_smooth, min_periods=1).mean()
    d = k.rolling(window=d_smooth, min_periods=1).mean()

    return {"stoch_rsi_k": k, "stoch_rsi_d": d}


# ── Williams %R ─────────────────────────────────────────────────

def williams_r(high: pd.Series, low: pd.Series, close: pd.Series,
               period: int = 14) -> pd.Series:
    """
    Williams %R. Range: -100 to 0.
    -80 to -100 = oversold, 0 to -20 = overbought.
    """
    highest = high.rolling(window=period, min_periods=period).max()
    lowest = low.rolling(window=period, min_periods=period).min()
    return ((highest - close) / (highest - lowest).replace(0, np.nan)) * -100


def williams_r_zone(wr: pd.Series, ob: float = -20, os: float = -80) -> pd.Series:
    """Classify Williams %R zone."""
    result = pd.Series(0, index=wr.index)
    result[wr >= ob] = 1   # Overbought (close to 0)
    result[wr <= os] = -1  # Oversold (close to -100)
    return result


# ── CCI (Commodity Channel Index) ──────────────────────────────

def cci(high: pd.Series, low: pd.Series, close: pd.Series,
        period: int = 20) -> pd.Series:
    """
    Commodity Channel Index.
    Above +100 = overbought, Below -100 = oversold.
    """
    typical_price = (high + low + close) / 3
    sma_tp = typical_price.rolling(window=period, min_periods=period).mean()
    mad = typical_price.rolling(window=period, min_periods=period).apply(
        lambda x: np.abs(x - x.mean()).mean(), raw=True
    )
    return (typical_price - sma_tp) / (0.015 * mad).replace(0, np.nan)


def cci_zone(cci_val: pd.Series, ob: float = 100, os: float = -100) -> pd.Series:
    """Classify CCI zone."""
    result = pd.Series(0, index=cci_val.index)
    result[cci_val >= ob] = 1
    result[cci_val <= os] = -1
    return result


# ── ROC (Rate of Change) ───────────────────────────────────────

def roc(close: pd.Series, period: int = 12) -> pd.Series:
    """Rate of Change as percentage."""
    return ((close - close.shift(period)) / close.shift(period)) * 100


# ── Momentum ───────────────────────────────────────────────────

def momentum(close: pd.Series, period: int = 10) -> pd.Series:
    """Price Momentum (absolute difference)."""
    return close - close.shift(period)


# ── OB/OS Generic Detector ─────────────────────────────────────

def detect_ob_os_reversal(oscillator: pd.Series,
                          ob_level: float, os_level: float) -> pd.Series:
    """
    Detect when oscillator exits OB/OS zone (potential reversal signal).
    Returns:  1 = exiting oversold (bullish)
             -1 = exiting overbought (bearish)
              0 = no signal
    """
    was_ob = oscillator.shift(1) >= ob_level
    was_os = oscillator.shift(1) <= os_level
    now_below_ob = oscillator < ob_level
    now_above_os = oscillator > os_level

    result = pd.Series(0, index=oscillator.index)
    result[was_ob & now_below_ob] = -1  # Exiting OB = bearish
    result[was_os & now_above_os] = 1   # Exiting OS = bullish
    return result


# ── Compute All Oscillators ────────────────────────────────────

def compute_oscillators(df: pd.DataFrame) -> Dict[str, pd.Series]:
    """
    Compute all oscillators for a DataFrame.

    Args:
        df: DataFrame with open, high, low, close, volume

    Returns:
        Dict with all oscillator values and zone classifications.
    """
    h, l, c = df["high"], df["low"], df["close"]
    results = {}

    # RSI
    results["rsi_14"] = rsi(c, 14)
    results["rsi_7"] = rsi(c, 7)
    results["rsi_21"] = rsi(c, 21)
    results["rsi_zone"] = rsi_zone(results["rsi_14"])
    results["rsi_reversal"] = detect_ob_os_reversal(results["rsi_14"], 70, 30)

    # Stochastic
    stoch = stochastic(h, l, c, 14, 3, 3)
    results.update(stoch)
    results["stoch_zone"] = stochastic_zone(stoch["stoch_k"])
    results["stoch_cross"] = stochastic_cross(stoch["stoch_k"], stoch["stoch_d"])
    results["stoch_reversal"] = detect_ob_os_reversal(stoch["stoch_k"], 80, 20)

    # StochRSI
    srsi = stoch_rsi(c, 14, 14, 3, 3)
    results.update(srsi)

    # Williams %R
    results["williams_r"] = williams_r(h, l, c, 14)
    results["williams_r_zone"] = williams_r_zone(results["williams_r"])

    # CCI
    results["cci_20"] = cci(h, l, c, 20)
    results["cci_zone"] = cci_zone(results["cci_20"])
    results["cci_reversal"] = detect_ob_os_reversal(results["cci_20"], 100, -100)

    # ROC
    results["roc_12"] = roc(c, 12)
    results["roc_9"] = roc(c, 9)

    # Momentum
    results["momentum_10"] = momentum(c, 10)

    return results
