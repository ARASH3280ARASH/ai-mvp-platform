"""
Whilber-AI MVP - Indicator Module: Candlestick Patterns
==========================================================
Step 2.8 - Pattern recognition for single and dual candle patterns.
All patterns return: 1=bullish, -1=bearish, 0=none.
"""

import numpy as np
import pandas as pd
from typing import Dict


# ── Candle Properties ───────────────────────────────────────────

def candle_body(open: pd.Series, close: pd.Series) -> pd.Series:
    """Candle body size (absolute)."""
    return (close - open).abs()


def candle_body_pct(open: pd.Series, close: pd.Series,
                    high: pd.Series, low: pd.Series) -> pd.Series:
    """Body as percentage of total range."""
    total_range = (high - low).replace(0, np.nan)
    return (candle_body(open, close) / total_range) * 100


def upper_shadow(open: pd.Series, close: pd.Series,
                 high: pd.Series) -> pd.Series:
    """Upper shadow (wick) size."""
    return high - pd.concat([open, close], axis=1).max(axis=1)


def lower_shadow(open: pd.Series, close: pd.Series,
                 low: pd.Series) -> pd.Series:
    """Lower shadow (wick) size."""
    return pd.concat([open, close], axis=1).min(axis=1) - low


def is_bullish(open: pd.Series, close: pd.Series) -> pd.Series:
    """True if close > open."""
    return (close > open).astype(int)


def is_bearish(open: pd.Series, close: pd.Series) -> pd.Series:
    """True if close < open."""
    return (close < open).astype(int)


# ── Single Candle Patterns ─────────────────────────────────────

def doji(open: pd.Series, close: pd.Series, high: pd.Series,
         low: pd.Series, body_threshold: float = 10) -> pd.Series:
    """
    Doji: very small body relative to total range.
    body_threshold: max body percentage of total range.
    """
    body_pct = candle_body_pct(open, close, high, low)
    return (body_pct < body_threshold).astype(int)


def hammer(open: pd.Series, close: pd.Series, high: pd.Series,
           low: pd.Series) -> pd.Series:
    """
    Hammer (bullish): small body at top, long lower shadow (2x+ body).
    """
    body = candle_body(open, close)
    lower = lower_shadow(open, close, low)
    upper = upper_shadow(open, close, high)
    total = (high - low).replace(0, np.nan)

    result = pd.Series(0, index=open.index)
    is_hammer = (
        (lower >= 2 * body) &
        (upper < body * 0.5) &
        (body / total > 0.1) &
        (body > 0)
    )
    result[is_hammer] = 1
    return result


def shooting_star(open: pd.Series, close: pd.Series, high: pd.Series,
                  low: pd.Series) -> pd.Series:
    """
    Shooting Star (bearish): small body at bottom, long upper shadow.
    """
    body = candle_body(open, close)
    lower = lower_shadow(open, close, low)
    upper = upper_shadow(open, close, high)
    total = (high - low).replace(0, np.nan)

    result = pd.Series(0, index=open.index)
    is_star = (
        (upper >= 2 * body) &
        (lower < body * 0.5) &
        (body / total > 0.1) &
        (body > 0)
    )
    result[is_star] = -1
    return result


def pin_bar(open: pd.Series, close: pd.Series, high: pd.Series,
            low: pd.Series) -> pd.Series:
    """
    Pin Bar: combines hammer (bullish) and shooting star (bearish).
    1 = bullish pin, -1 = bearish pin.
    """
    h = hammer(open, close, high, low)
    s = shooting_star(open, close, high, low)
    return h + s


def marubozu(open: pd.Series, close: pd.Series, high: pd.Series,
             low: pd.Series, shadow_threshold: float = 5) -> pd.Series:
    """
    Marubozu: very small shadows (strong conviction candle).
    1 = bullish marubozu, -1 = bearish.
    """
    total = (high - low).replace(0, np.nan)
    upper = upper_shadow(open, close, high)
    lower = lower_shadow(open, close, low)

    upper_pct = (upper / total) * 100
    lower_pct = (lower / total) * 100

    result = pd.Series(0, index=open.index)
    small_shadows = (upper_pct < shadow_threshold) & (lower_pct < shadow_threshold)
    result[small_shadows & (close > open)] = 1
    result[small_shadows & (close < open)] = -1
    return result


# ── Dual Candle Patterns ───────────────────────────────────────

def engulfing(open: pd.Series, close: pd.Series, high: pd.Series,
              low: pd.Series) -> pd.Series:
    """
    Engulfing pattern:
    1 = bullish engulfing (bearish candle followed by larger bullish)
    -1 = bearish engulfing
    """
    result = pd.Series(0, index=open.index)

    prev_bearish = close.shift(1) < open.shift(1)
    prev_bullish = close.shift(1) > open.shift(1)
    curr_bullish = close > open
    curr_bearish = close < open

    prev_body_high = pd.concat([open.shift(1), close.shift(1)], axis=1).max(axis=1)
    prev_body_low = pd.concat([open.shift(1), close.shift(1)], axis=1).min(axis=1)
    curr_body_high = pd.concat([open, close], axis=1).max(axis=1)
    curr_body_low = pd.concat([open, close], axis=1).min(axis=1)

    # Bullish engulfing
    bull_engulf = (
        prev_bearish & curr_bullish &
        (curr_body_high > prev_body_high) &
        (curr_body_low < prev_body_low)
    )

    # Bearish engulfing
    bear_engulf = (
        prev_bullish & curr_bearish &
        (curr_body_high > prev_body_high) &
        (curr_body_low < prev_body_low)
    )

    result[bull_engulf] = 1
    result[bear_engulf] = -1
    return result


def inside_bar(high: pd.Series, low: pd.Series) -> pd.Series:
    """
    Inside bar: current bar range is within previous bar range.
    Returns 1 for inside bar detected.
    """
    result = pd.Series(0, index=high.index)
    inside = (high <= high.shift(1)) & (low >= low.shift(1))
    result[inside] = 1
    return result


def outside_bar(high: pd.Series, low: pd.Series) -> pd.Series:
    """
    Outside bar: current bar range engulfs previous bar range.
    1 = bullish (close > open), -1 = bearish.
    """
    result = pd.Series(0, index=high.index)
    outside = (high > high.shift(1)) & (low < low.shift(1))
    result[outside] = 1  # Just detection, direction determined by close
    return result


def morning_star(open: pd.Series, close: pd.Series, high: pd.Series,
                 low: pd.Series) -> pd.Series:
    """
    Morning Star (3-candle bullish reversal):
    1st: large bearish, 2nd: small body (any), 3rd: large bullish above midpoint of 1st.
    """
    result = pd.Series(0, index=open.index)
    body = candle_body(open, close)
    total = (high - low).replace(0, np.nan)
    body_pct = (body / total) * 100

    for i in range(2, len(open)):
        # 1st candle: large bearish
        if close.iloc[i-2] >= open.iloc[i-2]:
            continue
        if body_pct.iloc[i-2] < 50:
            continue

        # 2nd candle: small body
        if body_pct.iloc[i-1] > 30:
            continue

        # 3rd candle: large bullish, closes above midpoint of 1st
        if close.iloc[i] <= open.iloc[i]:
            continue
        midpoint = (open.iloc[i-2] + close.iloc[i-2]) / 2
        if close.iloc[i] > midpoint and body_pct.iloc[i] > 40:
            result.iloc[i] = 1

    return result


def evening_star(open: pd.Series, close: pd.Series, high: pd.Series,
                 low: pd.Series) -> pd.Series:
    """
    Evening Star (3-candle bearish reversal):
    1st: large bullish, 2nd: small body, 3rd: large bearish below midpoint of 1st.
    """
    result = pd.Series(0, index=open.index)
    body = candle_body(open, close)
    total = (high - low).replace(0, np.nan)
    body_pct = (body / total) * 100

    for i in range(2, len(open)):
        if close.iloc[i-2] <= open.iloc[i-2]:
            continue
        if body_pct.iloc[i-2] < 50:
            continue
        if body_pct.iloc[i-1] > 30:
            continue
        if close.iloc[i] >= open.iloc[i]:
            continue
        midpoint = (open.iloc[i-2] + close.iloc[i-2]) / 2
        if close.iloc[i] < midpoint and body_pct.iloc[i] > 40:
            result.iloc[i] = -1

    return result


# ── Compute All Candlestick Patterns ──────────────────────────

def compute_candlesticks(df: pd.DataFrame) -> Dict[str, pd.Series]:
    """Compute all candlestick patterns."""
    o, h, l, c = df["open"], df["high"], df["low"], df["close"]
    results = {}

    # Candle properties
    results["candle_body_pct"] = candle_body_pct(o, c, h, l)
    results["is_bullish"] = is_bullish(o, c)
    results["is_bearish"] = is_bearish(o, c)

    # Single candle
    results["doji"] = doji(o, c, h, l)
    results["hammer"] = hammer(o, c, h, l)
    results["shooting_star"] = shooting_star(o, c, h, l)
    results["pin_bar"] = pin_bar(o, c, h, l)
    results["marubozu"] = marubozu(o, c, h, l)

    # Dual candle
    results["engulfing"] = engulfing(o, c, h, l)
    results["inside_bar"] = inside_bar(h, l)
    results["outside_bar"] = outside_bar(h, l)

    # Three candle
    results["morning_star"] = morning_star(o, c, h, l)
    results["evening_star"] = evening_star(o, c, h, l)

    # Combined signal (any strong pattern)
    results["candle_signal"] = (
        results["pin_bar"] +
        results["engulfing"] +
        results["morning_star"] +
        results["evening_star"]
    ).clip(-1, 1)

    return results
