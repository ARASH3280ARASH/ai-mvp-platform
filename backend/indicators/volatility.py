"""
Whilber-AI MVP - Indicator Module: Volatility & Bands
========================================================
Step 2.4 - Bollinger Bands, Keltner Channel, ATR, Donchian,
Squeeze Momentum, SuperTrend, Parabolic SAR.
"""

import numpy as np
import pandas as pd
from typing import Dict


# ── ATR (Average True Range) ───────────────────────────────────

def atr(high: pd.Series, low: pd.Series, close: pd.Series,
        period: int = 14) -> pd.Series:
    """Average True Range."""
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return true_range.ewm(alpha=1/period, min_periods=period, adjust=False).mean()


def atr_percent(high: pd.Series, low: pd.Series, close: pd.Series,
                period: int = 14) -> pd.Series:
    """ATR as percentage of price (normalized volatility)."""
    atr_val = atr(high, low, close, period)
    return (atr_val / close) * 100


# ── Bollinger Bands ─────────────────────────────────────────────

def bollinger_bands(close: pd.Series, period: int = 20,
                    std_dev: float = 2.0) -> Dict[str, pd.Series]:
    """Bollinger Bands: upper, middle, lower, bandwidth, %B."""
    middle = close.rolling(window=period, min_periods=period).mean()
    std = close.rolling(window=period, min_periods=period).std()

    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)

    bandwidth = ((upper - lower) / middle) * 100
    percent_b = ((close - lower) / (upper - lower).replace(0, np.nan)) * 100

    return {
        "bb_upper": upper,
        "bb_middle": middle,
        "bb_lower": lower,
        "bb_bandwidth": bandwidth,
        "bb_percent_b": percent_b,
    }


def bb_position(close: pd.Series, upper: pd.Series, lower: pd.Series,
                middle: pd.Series) -> pd.Series:
    """
    Price position relative to Bollinger Bands.
    2 = above upper, 1 = above middle, -1 = below middle, -2 = below lower.
    """
    result = pd.Series(0, index=close.index)
    result[close > upper] = 2
    result[(close > middle) & (close <= upper)] = 1
    result[(close < middle) & (close >= lower)] = -1
    result[close < lower] = -2
    return result


def bb_squeeze(bandwidth: pd.Series, lookback: int = 120,
               threshold_percentile: float = 20) -> pd.Series:
    """
    Detect Bollinger Band squeeze (low volatility).
    Returns 1 when bandwidth is in lowest percentile.
    """
    rolling_min = bandwidth.rolling(window=lookback, min_periods=20).quantile(threshold_percentile / 100)
    result = pd.Series(0, index=bandwidth.index)
    result[bandwidth <= rolling_min] = 1
    return result


# ── Keltner Channel ─────────────────────────────────────────────

def keltner_channel(high: pd.Series, low: pd.Series, close: pd.Series,
                    ema_period: int = 20, atr_period: int = 14,
                    multiplier: float = 2.0) -> Dict[str, pd.Series]:
    """Keltner Channel."""
    middle = close.ewm(span=ema_period, adjust=False, min_periods=ema_period).mean()
    atr_val = atr(high, low, close, atr_period)

    upper = middle + (atr_val * multiplier)
    lower = middle - (atr_val * multiplier)

    return {
        "kc_upper": upper,
        "kc_middle": middle,
        "kc_lower": lower,
    }


# ── Donchian Channel ───────────────────────────────────────────

def donchian_channel(high: pd.Series, low: pd.Series,
                     period: int = 20) -> Dict[str, pd.Series]:
    """Donchian Channel: highest high and lowest low over N bars."""
    upper = high.rolling(window=period, min_periods=period).max()
    lower = low.rolling(window=period, min_periods=period).min()
    middle = (upper + lower) / 2

    return {
        "dc_upper": upper,
        "dc_middle": middle,
        "dc_lower": lower,
    }


def donchian_breakout(close: pd.Series, upper: pd.Series,
                      lower: pd.Series) -> pd.Series:
    """Donchian breakout: 1=new high, -1=new low."""
    result = pd.Series(0, index=close.index)
    result[close >= upper] = 1
    result[close <= lower] = -1
    return result


# ── Squeeze Momentum ───────────────────────────────────────────

def squeeze_momentum(high: pd.Series, low: pd.Series, close: pd.Series,
                     bb_period: int = 20, bb_mult: float = 2.0,
                     kc_period: int = 20, kc_mult: float = 1.5) -> Dict[str, pd.Series]:
    """
    Squeeze Momentum Indicator (LazyBear style).
    Squeeze ON = BB inside KC (low volatility).
    Squeeze OFF = BB outside KC (expansion).
    """
    bb = bollinger_bands(close, bb_period, bb_mult)
    kc = keltner_channel(high, low, close, kc_period, 14, kc_mult)

    # Squeeze: BB inside KC
    squeeze_on = (bb["bb_lower"] > kc["kc_lower"]) & (bb["bb_upper"] < kc["kc_upper"])

    # Momentum (linear regression value)
    highest = high.rolling(window=kc_period).max()
    lowest = low.rolling(window=kc_period).min()
    midline = (highest + lowest) / 2
    sma_close = close.rolling(window=kc_period).mean()
    val = close - ((midline + sma_close) / 2)

    return {
        "squeeze_on": squeeze_on.astype(int),
        "squeeze_val": val,
    }


# ── SuperTrend ──────────────────────────────────────────────────

def supertrend(high: pd.Series, low: pd.Series, close: pd.Series,
               period: int = 10, multiplier: float = 3.0) -> Dict[str, pd.Series]:
    """
    SuperTrend indicator.
    Returns supertrend line and direction (1=bullish, -1=bearish).
    """
    atr_val = atr(high, low, close, period)
    hl2 = (high + low) / 2

    upper_band = hl2 + (multiplier * atr_val)
    lower_band = hl2 - (multiplier * atr_val)

    st = pd.Series(np.nan, index=close.index)
    direction = pd.Series(1, index=close.index)

    for i in range(period, len(close)):
        if i == period:
            st.iloc[i] = upper_band.iloc[i] if close.iloc[i] <= upper_band.iloc[i] else lower_band.iloc[i]
            direction.iloc[i] = -1 if close.iloc[i] <= upper_band.iloc[i] else 1
            continue

        prev_st = st.iloc[i-1]
        prev_dir = direction.iloc[i-1]

        if prev_dir == 1:  # Was bullish
            curr_lower = max(lower_band.iloc[i], prev_st) if not np.isnan(prev_st) else lower_band.iloc[i]
            if close.iloc[i] < curr_lower:
                st.iloc[i] = upper_band.iloc[i]
                direction.iloc[i] = -1
            else:
                st.iloc[i] = curr_lower
                direction.iloc[i] = 1
        else:  # Was bearish
            curr_upper = min(upper_band.iloc[i], prev_st) if not np.isnan(prev_st) else upper_band.iloc[i]
            if close.iloc[i] > curr_upper:
                st.iloc[i] = lower_band.iloc[i]
                direction.iloc[i] = 1
            else:
                st.iloc[i] = curr_upper
                direction.iloc[i] = -1

    return {"supertrend": st, "supertrend_dir": direction}


def supertrend_flip(direction: pd.Series) -> pd.Series:
    """Detect SuperTrend direction changes: 1=bullish flip, -1=bearish flip."""
    diff = direction.diff()
    result = pd.Series(0, index=direction.index)
    result[diff == 2] = 1    # -1 to 1 = bullish
    result[diff == -2] = -1  # 1 to -1 = bearish
    return result


# ── Parabolic SAR ───────────────────────────────────────────────

def parabolic_sar(high: pd.Series, low: pd.Series,
                  af_start: float = 0.02, af_step: float = 0.02,
                  af_max: float = 0.20) -> Dict[str, pd.Series]:
    """
    Parabolic SAR.
    Returns SAR values and direction (1=bullish/below price, -1=bearish/above).
    """
    length = len(high)
    sar = pd.Series(np.nan, index=high.index)
    direction = pd.Series(0, index=high.index)

    # Initialize
    is_long = True
    af = af_start
    ep = high.iloc[0]
    sar.iloc[0] = low.iloc[0]
    direction.iloc[0] = 1

    for i in range(1, length):
        prev_sar = sar.iloc[i-1]
        if np.isnan(prev_sar):
            sar.iloc[i] = low.iloc[i]
            direction.iloc[i] = 1
            continue

        if is_long:
            sar_val = prev_sar + af * (ep - prev_sar)
            sar_val = min(sar_val, low.iloc[i-1])
            if i >= 2:
                sar_val = min(sar_val, low.iloc[i-2])

            if low.iloc[i] < sar_val:
                is_long = False
                sar_val = ep
                ep = low.iloc[i]
                af = af_start
            else:
                if high.iloc[i] > ep:
                    ep = high.iloc[i]
                    af = min(af + af_step, af_max)
        else:
            sar_val = prev_sar + af * (ep - prev_sar)
            sar_val = max(sar_val, high.iloc[i-1])
            if i >= 2:
                sar_val = max(sar_val, high.iloc[i-2])

            if high.iloc[i] > sar_val:
                is_long = True
                sar_val = ep
                ep = high.iloc[i]
                af = af_start
            else:
                if low.iloc[i] < ep:
                    ep = low.iloc[i]
                    af = min(af + af_step, af_max)

        sar.iloc[i] = sar_val
        direction.iloc[i] = 1 if is_long else -1

    return {"psar": sar, "psar_dir": direction}


def psar_flip(psar_dir: pd.Series) -> pd.Series:
    """PSAR direction flip: 1=bullish, -1=bearish."""
    diff = psar_dir.diff()
    result = pd.Series(0, index=psar_dir.index)
    result[diff == 2] = 1
    result[diff == -2] = -1
    return result


# ── Compute All Volatility Indicators ──────────────────────────

def compute_volatility(df: pd.DataFrame) -> Dict[str, pd.Series]:
    """Compute all volatility and band indicators."""
    h, l, c = df["high"], df["low"], df["close"]
    results = {}

    # ATR
    results["atr_14"] = atr(h, l, c, 14)
    results["atr_7"] = atr(h, l, c, 7)
    results["atr_percent"] = atr_percent(h, l, c, 14)

    # Bollinger Bands
    bb = bollinger_bands(c, 20, 2.0)
    results.update(bb)
    results["bb_position"] = bb_position(c, bb["bb_upper"], bb["bb_lower"], bb["bb_middle"])
    results["bb_squeeze"] = bb_squeeze(bb["bb_bandwidth"])

    # Keltner Channel
    kc = keltner_channel(h, l, c, 20, 14, 2.0)
    results.update(kc)

    # Donchian Channel
    dc = donchian_channel(h, l, 20)
    results.update(dc)
    results["dc_breakout"] = donchian_breakout(c, dc["dc_upper"], dc["dc_lower"])

    # Squeeze Momentum
    sq = squeeze_momentum(h, l, c)
    results.update(sq)

    # SuperTrend
    st = supertrend(h, l, c, 10, 3.0)
    results.update(st)
    results["supertrend_flip"] = supertrend_flip(st["supertrend_dir"])

    # Parabolic SAR
    ps = parabolic_sar(h, l)
    results.update(ps)
    results["psar_flip"] = psar_flip(ps["psar_dir"])

    return results
