"""
Whilber-AI MVP - MT5 Module
==============================
Provides MT5 connection, symbol mapping, timeframe management,
and data extraction functionality.

Usage:
    from backend.mt5 import MT5Connector, fetch_bars, fetch_current_price
"""

from backend.mt5.mt5_connector import MT5Connector
from backend.mt5.symbol_map import (
    SymbolCategory,
    SYMBOLS,
    get_symbols_by_category,
    get_symbol_info,
    get_mt5_name,
    get_farsi_name,
    get_alternates,
    get_all_categories,
    validate_symbol,
    search_symbols,
)
from backend.mt5.timeframes import (
    Timeframe,
    get_mt5_timeframe,
    get_bar_count,
    get_all_timeframes,
    validate_timeframe,
    get_tf_minutes,
)
from backend.mt5.data_fetcher import (
    fetch_bars,
    fetch_current_price,
    clear_cache,
    cleanup_expired_cache,
    get_cache_info,
)

__all__ = [
    "MT5Connector",
    "SymbolCategory",
    "Timeframe",
    "fetch_bars",
    "fetch_current_price",
    "get_symbols_by_category",
    "get_all_categories",
    "get_all_timeframes",
    "validate_symbol",
    "validate_timeframe",
    "get_farsi_name",
    "clear_cache",
]
