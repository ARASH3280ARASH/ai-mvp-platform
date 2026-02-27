"""
Whilber-AI MVP - Data Fetcher
================================
Core module for extracting price data (bars/candles) from MT5.

Features:
  - Fetches OHLCV bars for any symbol/timeframe
  - Ensures last closed bar is included
  - Short-term memory cache (30s) to avoid duplicate MT5 calls
  - Auto-cleanup after use
  - Tries alternate symbol names if primary fails
"""

import time
import threading
from datetime import datetime, timezone
from typing import Optional, Dict, Tuple

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from loguru import logger

# ═══ SYMBOL MAPPING ═══
_MT5_SYMBOL_MAP = {
    "XAUUSD": "XAUUSD+",
    "EURUSD": "EURUSD+",
    "GBPUSD": "GBPUSD+",
    "USDJPY": "USDJPY+",
    "AUDUSD": "AUDUSD+",
    "USDCAD": "USDCAD+",
    "NZDUSD": "NZDUSD+",
    "USDCHF": "USDCHF+",
    "US30": "DJ30",
}

def _resolve_symbol(symbol):
    """Map our symbol name to MT5 symbol name."""
    if symbol in _MT5_SYMBOL_MAP:
        return _MT5_SYMBOL_MAP[symbol]
    # Try adding + suffix
    import MetaTrader5 as mt5
    for candidate in [symbol, symbol + "+", symbol + ".crp"]:
        info = mt5.symbol_info(candidate)
        if info:
            return candidate
    return symbol


# Import our modules (will be at backend.mt5.xxx when deployed)
# For now, direct import for testing
try:
    from backend.mt5.mt5_connector import MT5Connector
    from backend.mt5.symbol_map import get_mt5_name, get_alternates, validate_symbol
    from backend.mt5.timeframes import get_mt5_timeframe, get_bar_count, Timeframe
except ImportError:
    from mt5_connector import MT5Connector
    from symbol_map import get_mt5_name, get_alternates, validate_symbol
    from timeframes import get_mt5_timeframe, get_bar_count, Timeframe


# ── In-Memory Cache ─────────────────────────────────────────────

class DataCache:
    """
    Short-lived in-memory cache for fetched data.
    Prevents duplicate MT5 calls within CACHE_TTL seconds.
    """

    def __init__(self, ttl: int = 30):
        self._cache: Dict[str, Tuple[pd.DataFrame, float]] = {}
        self._ttl = ttl
        self._lock = threading.Lock()

    def _make_key(self, symbol: str, timeframe: str) -> str:
        return f"{symbol}_{timeframe}"

    def get(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        key = self._make_key(symbol, timeframe)
        with self._lock:
            if key in self._cache:
                df, timestamp = self._cache[key]
                if time.time() - timestamp < self._ttl:
                    logger.debug(f"Cache HIT: {key}")
                    return df.copy()
                else:
                    del self._cache[key]
                    logger.debug(f"Cache EXPIRED: {key}")
        return None

    def set(self, symbol: str, timeframe: str, df: pd.DataFrame):
        key = self._make_key(symbol, timeframe)
        with self._lock:
            self._cache[key] = (df.copy(), time.time())
            logger.debug(f"Cache SET: {key} ({len(df)} bars)")

    def clear(self):
        with self._lock:
            self._cache.clear()
            logger.debug("Cache cleared")

    def cleanup_expired(self):
        now = time.time()
        with self._lock:
            expired = [k for k, (_, t) in self._cache.items()
                       if now - t >= self._ttl]
            for k in expired:
                del self._cache[k]
            if expired:
                logger.debug(f"Cache cleanup: removed {len(expired)} entries")


# ── Global Cache Instance ───────────────────────────────────────

_cache = DataCache(ttl=30)


# ── Core Fetch Function ─────────────────────────────────────────

def fetch_bars(
    symbol: str,
    timeframe: str,
    count: int = None,
    use_cache: bool = True,
) -> Optional[pd.DataFrame]:
    """
    Fetch OHLCV bars from MT5 for a given symbol and timeframe.

    Args:
        symbol: Symbol name (e.g., "EURUSD", "BTCUSD")
        timeframe: Timeframe string (e.g., "M1", "H1", "D1")
        count: Number of bars to fetch. If None, uses default for timeframe.
        use_cache: Whether to use short-term cache.

    Returns:
        DataFrame with columns: time, open, high, low, close, volume, spread
        Returns None if fetch fails.
    """
    symbol = symbol.upper()
    timeframe = timeframe.upper()

    # Validate
    if not validate_symbol(symbol):
        logger.error(f"Unknown symbol: {symbol}")
        return None

    # Check cache
    if use_cache:
        cached = _cache.get(symbol, timeframe)
        if cached is not None:
            return cached

    # Determine bar count
    if count is None:
        count = get_bar_count(timeframe)

    # Ensure MT5 connected
    connector = MT5Connector.get_instance()
    if not connector.ensure_connected():
        logger.error("Cannot connect to MT5")
        return None

    # Get MT5 timeframe constant
    mt5_tf = get_mt5_timeframe(timeframe)

    # Try to fetch with primary name, then alternates
    mt5_symbol = get_mt5_name(symbol)
    alternates = get_alternates(symbol)
    all_names = [mt5_symbol] + [a for a in alternates if a != mt5_symbol]

    rates = None
    used_name = None

    for name in all_names:
        # Ensure symbol is visible in Market Watch
        if not mt5.symbol_select(name, True):
            continue

        # Fetch bars: position 0 = current (incomplete) bar
        # We fetch count+1 and skip the first (incomplete) one
        rates = mt5.copy_rates_from_pos(_resolve_symbol(name), mt5_tf, 0, count + 1)

        if rates is not None and len(rates) > 0:
            used_name = name
            break

    if rates is None or len(rates) == 0:
        error = mt5.last_error()
        logger.error(f"Failed to fetch {symbol} {timeframe}: {error}")
        logger.error(f"Tried names: {all_names}")
        return None

    # Convert to DataFrame
    df = pd.DataFrame(rates)

    # Convert time from unix timestamp to datetime
    df["time"] = pd.to_datetime(df["time"], unit="s")

    # Column names: time, open, high, low, close, tick_volume, spread, real_volume
    # Rename tick_volume to volume for consistency
    if "tick_volume" in df.columns:
        df = df.rename(columns={"tick_volume": "volume"})

    # Drop real_volume if exists (not always useful)
    if "real_volume" in df.columns:
        df = df.drop(columns=["real_volume"])

    # Remove the FIRST row (current incomplete bar)
    # The last row in MT5 copy_rates_from_pos(pos=0) is the CURRENT bar
    # So we drop the LAST row to only keep CLOSED bars
    df = df.iloc[:-1].reset_index(drop=True)

    # Verify we have data
    if len(df) == 0:
        logger.error(f"No closed bars for {symbol} {timeframe}")
        return None

    # Ensure proper dtypes
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(np.float64)
    df["volume"] = df["volume"].astype(np.int64)
    df["spread"] = df["spread"].astype(np.int32)

    logger.info(
        f"Fetched {len(df)} bars | {symbol} ({used_name}) {timeframe} | "
        f"Range: {df['time'].iloc[0]} → {df['time'].iloc[-1]}"
    )

    # Cache it
    if use_cache:
        _cache.set(symbol, timeframe, df)

    return df


# ── Utility Functions ───────────────────────────────────────────

def fetch_current_price(symbol: str) -> Optional[Dict]:
    """
    Get current bid/ask price for a symbol.

    Returns:
        Dict with bid, ask, spread, time. None if fails.
    """
    symbol = symbol.upper()
    connector = MT5Connector.get_instance()
    if not connector.ensure_connected():
        return None

    mt5_symbol = get_mt5_name(symbol)
    alternates = get_alternates(symbol)
    all_names = [mt5_symbol] + [a for a in alternates if a != mt5_symbol]

    for name in all_names:
        mt5.symbol_select(name, True)
        tick = mt5.symbol_info_tick(name)
        if tick:
            return {
                "symbol": symbol,
                "bid": tick.bid,
                "ask": tick.ask,
                "spread": round(tick.ask - tick.bid, 6),
                "time": datetime.fromtimestamp(tick.time, tz=timezone.utc).isoformat(),
            }

    return None


def clear_cache():
    """Clear the data cache."""
    _cache.clear()


def cleanup_expired_cache():
    """Remove expired entries from cache."""
    _cache.cleanup_expired()


def get_cache_info() -> Dict:
    """Get cache statistics."""
    return {
        "entries": len(_cache._cache),
        "ttl": _cache._ttl,
    }
