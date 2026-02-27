"""
Whilber-AI MVP - Indicators Module
=====================================
Unified interface for all technical indicators.

Usage:
    from backend.indicators import compute_all_indicators
    results = compute_all_indicators(df)
"""

from backend.indicators.moving_averages import compute_moving_averages
from backend.indicators.oscillators import compute_oscillators
from backend.indicators.macd_indicators import compute_macd_indicators
from backend.indicators.volatility import compute_volatility
from backend.indicators.volume_indicators import compute_volume
from backend.indicators.trend_strength import compute_trend_strength
from backend.indicators.structure import compute_structure
from backend.indicators.candlesticks import compute_candlesticks
from typing import Dict
import pandas as pd


def compute_all_indicators(df: pd.DataFrame,
                           ma_periods: list = None,
                           ma_type: str = "ema") -> Dict:
    """
    Compute ALL indicators for a given DataFrame.

    Args:
        df: DataFrame with columns: time, open, high, low, close, volume
        ma_periods: MA periods to calculate (default: [9, 21, 50, 100, 200])
        ma_type: Type of MA (default: "ema")

    Returns:
        Dict with all indicator values grouped by category.
    """
    results = {}

    # 1. Moving Averages
    results["ma"] = compute_moving_averages(df, ma_periods, ma_type)

    # 2. Oscillators
    results["osc"] = compute_oscillators(df)

    # 3. MACD family
    results["macd"] = compute_macd_indicators(df)

    # 4. Volatility & Bands
    results["vol"] = compute_volatility(df)

    # 5. Volume
    results["volume"] = compute_volume(df)

    # 6. Trend Strength
    results["trend"] = compute_trend_strength(df)

    # 7. Structure
    results["structure"] = compute_structure(df)

    # 8. Candlesticks
    results["candle"] = compute_candlesticks(df)

    return results


def compute_selective(df: pd.DataFrame, categories: list) -> Dict:
    """
    Compute only selected indicator categories.
    categories: list of "ma", "osc", "macd", "vol", "volume",
                "trend", "structure", "candle"
    """
    func_map = {
        "ma": lambda: compute_moving_averages(df),
        "osc": lambda: compute_oscillators(df),
        "macd": lambda: compute_macd_indicators(df),
        "vol": lambda: compute_volatility(df),
        "volume": lambda: compute_volume(df),
        "trend": lambda: compute_trend_strength(df),
        "structure": lambda: compute_structure(df),
        "candle": lambda: compute_candlesticks(df),
    }

    results = {}
    for cat in categories:
        if cat in func_map:
            results[cat] = func_map[cat]()

    return results
