"""
Whilber-AI MVP - Indicator Module: Market Structure
======================================================
Step 2.7 - Swing points, market structure (HH/HL/LH/LL),
Break of Structure (BOS), Change of Character (CHoCH),
Automatic Support/Resistance levels.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple


# ── Swing High / Low Detection ─────────────────────────────────

def swing_highs(high: pd.Series, left: int = 5, right: int = 5) -> pd.Series:
    """
    Detect swing highs (pivot highs).
    A bar is a swing high if it's the highest within left+right bars.
    Returns NaN where no swing, high value where swing detected.
    """
    result = pd.Series(np.nan, index=high.index)
    for i in range(left, len(high) - right):
        window = high.iloc[i - left:i + right + 1]
        if high.iloc[i] == window.max() and high.iloc[i] > high.iloc[i-1]:
            result.iloc[i] = high.iloc[i]
    return result


def swing_lows(low: pd.Series, left: int = 5, right: int = 5) -> pd.Series:
    """
    Detect swing lows (pivot lows).
    Returns NaN where no swing, low value where swing detected.
    """
    result = pd.Series(np.nan, index=low.index)
    for i in range(left, len(low) - right):
        window = low.iloc[i - left:i + right + 1]
        if low.iloc[i] == window.min() and low.iloc[i] < low.iloc[i-1]:
            result.iloc[i] = low.iloc[i]
    return result


def swing_points(high: pd.Series, low: pd.Series,
                 left: int = 5, right: int = 5) -> Dict[str, pd.Series]:
    """Detect both swing highs and lows."""
    return {
        "swing_high": swing_highs(high, left, right),
        "swing_low": swing_lows(low, left, right),
    }


# ── Market Structure (HH/HL/LH/LL) ────────────────────────────

def market_structure(high: pd.Series, low: pd.Series,
                     left: int = 5, right: int = 5) -> Dict[str, pd.Series]:
    """
    Classify market structure using swing points.
    HH = Higher High, HL = Higher Low (uptrend)
    LH = Lower High, LL = Lower Low (downtrend)

    Returns structure labels and trend direction.
    """
    sh = swing_highs(high, left, right)
    sl = swing_lows(low, left, right)

    # Extract valid swing points
    high_points = sh.dropna()
    low_points = sl.dropna()

    # Label highs
    high_labels = pd.Series("", index=high.index)
    prev_high = None
    for idx, val in high_points.items():
        if prev_high is not None:
            if val > prev_high:
                high_labels[idx] = "HH"
            else:
                high_labels[idx] = "LH"
        prev_high = val

    # Label lows
    low_labels = pd.Series("", index=low.index)
    prev_low = None
    for idx, val in low_points.items():
        if prev_low is not None:
            if val > prev_low:
                low_labels[idx] = "HL"
            else:
                low_labels[idx] = "LL"
        prev_low = val

    # Determine trend direction
    # Uptrend: HH + HL, Downtrend: LH + LL
    trend = pd.Series(0, index=high.index)
    last_high_label = ""
    last_low_label = ""

    for i in range(len(high)):
        if high_labels.iloc[i] != "":
            last_high_label = high_labels.iloc[i]
        if low_labels.iloc[i] != "":
            last_low_label = low_labels.iloc[i]

        if last_high_label == "HH" and last_low_label == "HL":
            trend.iloc[i] = 1   # Uptrend
        elif last_high_label == "LH" and last_low_label == "LL":
            trend.iloc[i] = -1  # Downtrend
        # Mixed = 0

    return {
        "swing_high": sh,
        "swing_low": sl,
        "high_label": high_labels,
        "low_label": low_labels,
        "structure_trend": trend,
    }


# ── BOS (Break of Structure) ───────────────────────────────────

def break_of_structure(close: pd.Series, high: pd.Series, low: pd.Series,
                       left: int = 5, right: int = 5) -> pd.Series:
    """
    Detect Break of Structure.
    Bullish BOS: price breaks above a previous swing high
    Bearish BOS: price breaks below a previous swing low

    Returns: 1 = bullish BOS, -1 = bearish BOS, 0 = none
    """
    sh = swing_highs(high, left, right)
    sl = swing_lows(low, left, right)

    result = pd.Series(0, index=close.index)

    last_swing_high = np.nan
    last_swing_low = np.nan

    for i in range(len(close)):
        # Update last known swing points
        if not np.isnan(sh.iloc[i]):
            last_swing_high = sh.iloc[i]
        if not np.isnan(sl.iloc[i]):
            last_swing_low = sl.iloc[i]

        # Check for BOS
        if not np.isnan(last_swing_high) and close.iloc[i] > last_swing_high:
            result.iloc[i] = 1   # Bullish BOS
            last_swing_high = np.nan  # Reset to avoid repeated signals

        if not np.isnan(last_swing_low) and close.iloc[i] < last_swing_low:
            result.iloc[i] = -1  # Bearish BOS
            last_swing_low = np.nan

    return result


# ── CHoCH (Change of Character) ────────────────────────────────

def change_of_character(close: pd.Series, high: pd.Series, low: pd.Series,
                        left: int = 5, right: int = 5) -> pd.Series:
    """
    Detect Change of Character.
    In uptrend (HH/HL): first break below a swing low = bearish CHoCH
    In downtrend (LH/LL): first break above a swing high = bullish CHoCH

    Returns: 1 = bullish CHoCH, -1 = bearish CHoCH, 0 = none
    """
    ms = market_structure(high, low, left, right)
    trend = ms["structure_trend"]
    sh = ms["swing_high"]
    sl = ms["swing_low"]

    result = pd.Series(0, index=close.index)

    last_swing_high = np.nan
    last_swing_low = np.nan
    prev_trend = 0

    for i in range(len(close)):
        if not np.isnan(sh.iloc[i]):
            last_swing_high = sh.iloc[i]
        if not np.isnan(sl.iloc[i]):
            last_swing_low = sl.iloc[i]

        curr_trend = trend.iloc[i]

        # Bearish CHoCH: was uptrend, price breaks below swing low
        if prev_trend == 1 and not np.isnan(last_swing_low):
            if close.iloc[i] < last_swing_low:
                result.iloc[i] = -1
                last_swing_low = np.nan

        # Bullish CHoCH: was downtrend, price breaks above swing high
        if prev_trend == -1 and not np.isnan(last_swing_high):
            if close.iloc[i] > last_swing_high:
                result.iloc[i] = 1
                last_swing_high = np.nan

        if curr_trend != 0:
            prev_trend = curr_trend

    return result


# ── Auto Support / Resistance ───────────────────────────────────

def auto_support_resistance(high: pd.Series, low: pd.Series, close: pd.Series,
                            left: int = 10, right: int = 10,
                            merge_threshold: float = 0.002) -> Dict[str, list]:
    """
    Automatically detect support and resistance levels.
    Uses swing points and clusters nearby levels.

    Args:
        merge_threshold: levels within this % are merged (default 0.2%)

    Returns:
        Dict with "support" and "resistance" level lists.
    """
    sh = swing_highs(high, left, right).dropna()
    sl = swing_lows(low, left, right).dropna()

    # Cluster nearby levels
    def cluster_levels(levels: list, threshold: float) -> list:
        if not levels:
            return []
        sorted_levels = sorted(levels)
        clusters = [[sorted_levels[0]]]
        for lvl in sorted_levels[1:]:
            if (lvl - clusters[-1][-1]) / clusters[-1][-1] < threshold:
                clusters[-1].append(lvl)
            else:
                clusters.append([lvl])
        return [np.mean(c) for c in clusters]

    resistance = cluster_levels(sh.tolist(), merge_threshold)
    support = cluster_levels(sl.tolist(), merge_threshold)

    return {
        "resistance_levels": resistance,
        "support_levels": support,
    }


def price_near_level(close: pd.Series, levels: list,
                     proximity: float = 0.001) -> pd.Series:
    """
    Check if price is near any S/R level.
    Returns the closest level value, or NaN if none nearby.
    """
    result = pd.Series(np.nan, index=close.index)
    for i in range(len(close)):
        price = close.iloc[i]
        for level in levels:
            if abs(price - level) / level < proximity:
                result.iloc[i] = level
                break
    return result


def sr_interaction(close: pd.Series, high: pd.Series, low: pd.Series,
                   levels: list, proximity: float = 0.002) -> pd.Series:
    """
    Detect S/R interaction: bounce, break, or test.
    1 = bounce up from support
    -1 = bounce down from resistance
    2 = break above resistance
    -2 = break below support
    0 = no interaction
    """
    result = pd.Series(0, index=close.index)

    for i in range(1, len(close)):
        for level in levels:
            dist_pct = abs(close.iloc[i] - level) / level

            if dist_pct < proximity:
                # Near level - check if bounce or break
                if close.iloc[i] > level and close.iloc[i-1] < level:
                    result.iloc[i] = 2   # Break above
                elif close.iloc[i] < level and close.iloc[i-1] > level:
                    result.iloc[i] = -2  # Break below
                elif close.iloc[i] > level and low.iloc[i] <= level * (1 + proximity):
                    result.iloc[i] = 1   # Bounce from support
                elif close.iloc[i] < level and high.iloc[i] >= level * (1 - proximity):
                    result.iloc[i] = -1  # Bounce from resistance

    return result


# ── Compute All Structure ──────────────────────────────────────

def compute_structure(df: pd.DataFrame) -> Dict:
    """Compute all structure indicators."""
    h, l, c = df["high"], df["low"], df["close"]
    results = {}

    # Market Structure
    ms = market_structure(h, l, 5, 5)
    results.update(ms)

    # BOS and CHoCH
    results["bos"] = break_of_structure(c, h, l, 5, 5)
    results["choch"] = change_of_character(c, h, l, 5, 5)

    # Auto S/R
    sr = auto_support_resistance(h, l, c, 10, 10)
    results["sr_levels"] = sr

    # S/R interaction
    all_levels = sr["support_levels"] + sr["resistance_levels"]
    if all_levels:
        results["sr_interaction"] = sr_interaction(c, h, l, all_levels)
    else:
        results["sr_interaction"] = pd.Series(0, index=c.index)

    return results
