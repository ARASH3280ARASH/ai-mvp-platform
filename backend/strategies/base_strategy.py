"""
Whilber-AI MVP - Base Strategy Framework
===========================================
Abstract base class for all trading strategies.
Every strategy:
  1. Receives fresh OHLCV data from MT5
  2. Computes needed indicators
  3. Analyzes current market state
  4. Returns signal with confidence and Farsi explanation

All analysis is REAL-TIME on the last closed candle.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd


# ── Signal Types ────────────────────────────────────────────────

class Signal(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL"


SIGNAL_FA = {
    Signal.BUY: "خرید",
    Signal.SELL: "فروش",
    Signal.NEUTRAL: "خنثی",
}

SIGNAL_COLOR = {
    Signal.BUY: "#22c55e",     # Green
    Signal.SELL: "#ef4444",    # Red
    Signal.NEUTRAL: "#f59e0b", # Yellow
}


# ── Strategy Result ─────────────────────────────────────────────

@dataclass
class StrategyResult:
    """Standard output from every strategy analysis."""

    # Core
    strategy_id: str            # Unique ID like "trend_following"
    strategy_name_fa: str       # Farsi name "روند‌یاب"
    strategy_name_en: str       # English name "Trend Following"
    category: str               # Category like "trend_structure"

    # Signal
    signal: Signal              # BUY / SELL / NEUTRAL
    confidence: float           # 0-100 percentage

    # Explanation
    reason_fa: str              # Farsi explanation for user
    reason_en: str              # English explanation (for logs)

    # Technical Details
    details: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    symbol: str = ""
    timeframe: str = ""
    timestamp: str = ""

    def to_dict(self) -> Dict:
        return {
            "strategy_id": self.strategy_id,
            "strategy_name_fa": self.strategy_name_fa,
            "strategy_name_en": self.strategy_name_en,
            "category": self.category,
            "signal": self.signal.value,
            "signal_fa": SIGNAL_FA[self.signal],
            "signal_color": SIGNAL_COLOR[self.signal],
            "confidence": round(self.confidence, 1),
            "reason_fa": self.reason_fa,
            "reason_en": self.reason_en,
            "details": self.details,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "timestamp": self.timestamp,
        }


# ── Base Strategy Class ────────────────────────────────────────

class BaseStrategy(ABC):
    """
    Abstract base class for all strategies.

    Every strategy must implement:
      - analyze(df, indicators) -> StrategyResult

    The orchestrator will:
      1. Fetch fresh data from MT5
      2. Compute indicators
      3. Call strategy.analyze()
      4. Return result to user
    """

    # Subclass must set these
    STRATEGY_ID: str = ""
    STRATEGY_NAME_FA: str = ""
    STRATEGY_NAME_EN: str = ""
    CATEGORY: str = ""

    # Which indicator categories this strategy needs
    # Options: "ma", "osc", "macd", "vol", "volume", "trend", "structure", "candle"
    REQUIRED_INDICATORS: List[str] = []

    @abstractmethod
    def analyze(self, df: pd.DataFrame, indicators: Dict) -> StrategyResult:
        """
        Analyze current market state and return signal.

        Args:
            df: Fresh OHLCV DataFrame from MT5 (last closed bars)
            indicators: Pre-computed indicators dict (grouped by category)

        Returns:
            StrategyResult with signal, confidence, and explanation
        """
        pass

    def _make_result(self, signal: Signal, confidence: float,
                     reason_fa: str, reason_en: str,
                     details: Dict = None) -> StrategyResult:
        """Helper to create a StrategyResult."""
        return StrategyResult(
            strategy_id=self.STRATEGY_ID,
            strategy_name_fa=self.STRATEGY_NAME_FA,
            strategy_name_en=self.STRATEGY_NAME_EN,
            category=self.CATEGORY,
            signal=signal,
            confidence=min(max(confidence, 0), 100),
            reason_fa=reason_fa,
            reason_en=reason_en,
            details=details or {},
        )

    def _neutral(self, reason_fa: str = "شرایط ورود محقق نشده",
                 reason_en: str = "Entry conditions not met",
                 details: Dict = None) -> StrategyResult:
        """Quick neutral result."""
        return self._make_result(Signal.NEUTRAL, 0, reason_fa, reason_en, details)

    # ── Helpers for last bar analysis ───────────────────────

    @staticmethod
    def last(series: pd.Series):
        """Get last valid value of a series."""
        if series is None or len(series) == 0:
            return None
        val = series.iloc[-1]
        if pd.isna(val):
            # Try second-to-last
            valid = series.dropna()
            if len(valid) == 0:
                return None
            return valid.iloc[-1]
        return val

    @staticmethod
    def prev(series: pd.Series, n: int = 1):
        """Get N bars ago value."""
        if series is None or len(series) <= n:
            return None
        val = series.iloc[-(n+1)]
        return None if pd.isna(val) else val

    @staticmethod
    def last_n(series: pd.Series, n: int = 5) -> pd.Series:
        """Get last N values."""
        if series is None or len(series) < n:
            return series
        return series.iloc[-n:]
