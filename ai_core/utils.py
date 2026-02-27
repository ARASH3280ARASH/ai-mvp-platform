"""
AI Utilities — Data preprocessing, feature computation, and shared helpers.

Provides the data transformation layer between raw OHLCV market data and
the ML-ready feature matrices consumed by prediction models.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feature cache
# ---------------------------------------------------------------------------
_FEATURE_CACHE: Dict[str, Tuple[pd.DataFrame, List[str]]] = {}


def _cache_key(df: pd.DataFrame) -> str:
    """Compute a hash key for a DataFrame to enable caching."""
    h = hashlib.md5(pd.util.hash_pandas_object(df).values.tobytes()).hexdigest()
    return h


# ---------------------------------------------------------------------------
# Core feature builders
# ---------------------------------------------------------------------------

def compute_price_features(df: pd.DataFrame) -> pd.DataFrame:
    """Derive price-structure features from OHLCV data.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain ``open, high, low, close`` columns.

    Returns
    -------
    pd.DataFrame
        Price-derived features aligned to the input index.
    """
    c, o, h, l = df["close"], df["open"], df["high"], df["low"]
    feats: Dict[str, pd.Series] = {}

    feats["body_pct"] = (c - o) / o * 100
    feats["upper_shadow_pct"] = (h - pd.concat([c, o], axis=1).max(axis=1)) / o * 100
    feats["lower_shadow_pct"] = (pd.concat([c, o], axis=1).min(axis=1) - l) / o * 100
    feats["range_pct"] = (h - l) / o * 100

    for w in [10, 20, 50]:
        feats[f"dist_high_{w}"] = (c - h.rolling(w).max()) / c * 100
        feats[f"dist_low_{w}"] = (c - l.rolling(w).min()) / c * 100

    return pd.DataFrame(feats, index=df.index)


def compute_return_features(
    df: pd.DataFrame,
    windows: Optional[List[int]] = None,
) -> pd.DataFrame:
    """Rolling return statistics and momentum features.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain a ``close`` column.
    windows : list[int], optional
        Rolling window sizes (default [5, 10, 20, 50]).
    """
    windows = windows or [5, 10, 20, 50]
    returns = df["close"].pct_change()
    feats: Dict[str, pd.Series] = {}

    for w in windows:
        roll = returns.rolling(w)
        feats[f"ret_mean_{w}"] = roll.mean()
        feats[f"ret_std_{w}"] = roll.std()
        feats[f"ret_skew_{w}"] = roll.skew()

    for p in [1, 3, 5, 10, 20]:
        feats[f"momentum_{p}"] = df["close"].pct_change(p) * 100

    return pd.DataFrame(feats, index=df.index)


def compute_volume_features(df: pd.DataFrame) -> pd.DataFrame:
    """Volume-based features.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain ``tick_volume`` or ``volume`` column.
    """
    vol = df.get("tick_volume", df.get("volume", pd.Series(0, index=df.index)))
    feats: Dict[str, pd.Series] = {}

    if vol.sum() == 0:
        return pd.DataFrame(index=df.index)

    for w in [5, 10, 20]:
        vol_ma = vol.rolling(w).mean()
        feats[f"vol_ratio_{w}"] = vol / vol_ma.replace(0, np.nan)

    feats["vol_change"] = vol.pct_change()
    feats["vol_std_20"] = vol.rolling(20).std() / vol.rolling(20).mean().replace(0, np.nan)

    return pd.DataFrame(feats, index=df.index)


def compute_indicator_features(
    indicators: Dict[str, Any],
    df: pd.DataFrame,
    keys: Optional[List[str]] = None,
) -> pd.DataFrame:
    """Extract pre-computed indicator values as feature columns.

    Parameters
    ----------
    indicators : dict
        Indicator name → numpy array mapping.
    df : pd.DataFrame
        Reference DataFrame for index alignment.
    keys : list[str], optional
        Indicator keys to extract (extracts all if omitted).
    """
    feats: Dict[str, pd.Series] = {}
    keys = keys or list(indicators.keys())

    for key in keys:
        if key not in indicators:
            continue
        arr = indicators[key]
        if isinstance(arr, np.ndarray) and arr.shape[0] == len(df):
            feats[f"ind_{key}"] = pd.Series(arr, index=df.index)
        elif isinstance(arr, (int, float)):
            feats[f"ind_{key}"] = pd.Series(arr, index=df.index)

    return pd.DataFrame(feats, index=df.index)


def compute_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Cyclic calendar features (hour, day-of-week, month).

    Uses sine/cosine encoding to avoid discontinuities.
    """
    feats: Dict[str, pd.Series] = {}

    try:
        idx = pd.to_datetime(df.index) if not isinstance(df.index, pd.DatetimeIndex) else df.index
    except Exception:
        return pd.DataFrame(index=df.index)

    feats["hour_sin"] = np.sin(2 * np.pi * idx.hour / 24)
    feats["hour_cos"] = np.cos(2 * np.pi * idx.hour / 24)
    feats["dow_sin"] = np.sin(2 * np.pi * idx.dayofweek / 7)
    feats["dow_cos"] = np.cos(2 * np.pi * idx.dayofweek / 7)

    return pd.DataFrame(feats, index=df.index)


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

def build_feature_matrix(
    df: pd.DataFrame,
    indicators: Optional[Dict[str, Any]] = None,
    indicator_keys: Optional[List[str]] = None,
    use_cache: bool = True,
) -> Tuple[pd.DataFrame, List[str]]:
    """Build the complete ML feature matrix from OHLCV + indicators.

    Parameters
    ----------
    df : pd.DataFrame
        OHLCV data.
    indicators : dict, optional
        Pre-computed indicator values.
    indicator_keys : list[str], optional
        Which indicator keys to include.
    use_cache : bool
        Whether to use in-memory caching.

    Returns
    -------
    features : pd.DataFrame
        Clean feature matrix (NaN rows dropped, inf replaced).
    feature_names : list[str]
        Column names.
    """
    if use_cache:
        key = _cache_key(df)
        if key in _FEATURE_CACHE:
            logger.debug("Feature cache hit")
            return _FEATURE_CACHE[key]

    frames = [
        compute_price_features(df),
        compute_return_features(df),
        compute_volume_features(df),
        compute_time_features(df),
    ]

    if indicators:
        frames.append(compute_indicator_features(indicators, df, indicator_keys))

    features = pd.concat(frames, axis=1)
    features.replace([np.inf, -np.inf], np.nan, inplace=True)
    features.dropna(inplace=True)
    features.fillna(0.0, inplace=True)

    names = features.columns.tolist()

    if use_cache:
        _FEATURE_CACHE[_cache_key(df)] = (features, names)

    logger.info("Feature matrix: %d rows × %d features", len(features), len(names))
    return features, names


def build_target(
    df: pd.DataFrame,
    horizon: int = 5,
    buy_threshold: float = 0.3,
    sell_threshold: float = -0.3,
) -> pd.Series:
    """Create classification target: 1 (buy), 0 (hold), -1 (sell).

    Based on future return over *horizon* bars.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain ``close`` column.
    horizon : int
        Bars to look ahead.
    buy_threshold : float
        Minimum positive return (%) to label as BUY.
    sell_threshold : float
        Maximum negative return (%) to label as SELL.
    """
    future_ret = df["close"].pct_change(horizon).shift(-horizon) * 100
    target = pd.Series(0, index=df.index, name="target")
    target[future_ret > buy_threshold] = 1
    target[future_ret < sell_threshold] = -1
    return target


# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def normalize_confidence(raw_score: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Clamp and normalize a confidence score to [0, 1]."""
    return max(0.0, min(1.0, (raw_score - min_val) / (max_val - min_val + 1e-10)))


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Division that returns *default* when denominator is zero."""
    if abs(denominator) < 1e-10:
        return default
    return numerator / denominator
