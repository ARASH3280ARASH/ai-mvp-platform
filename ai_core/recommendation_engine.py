"""
Recommendation Engine — Personalized strategy selection for traders.

Analyzes historical strategy performance, user trading patterns, and
market regime to recommend the most suitable strategies for each
symbol-timeframe pair. Uses collaborative filtering and performance-
weighted scoring.

Typical usage:
    >>> engine = RecommendationEngine()
    >>> engine.fit(strategy_history, user_history)
    >>> recs = engine.recommend(symbol="BTCUSD", timeframe="H1", top_n=5)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from ai_core.config import AIConfig, RecommendationConfig

logger = logging.getLogger(__name__)


@dataclass
class StrategyScore:
    """Scored strategy recommendation."""

    strategy_id: str
    strategy_name: str
    composite_score: float
    win_rate: float
    profit_factor: float
    sharpe_ratio: float
    consistency: float
    regime_fit: float
    recent_performance: float
    reason: str


@dataclass
class MarketRegime:
    """Detected market regime classification."""

    regime: str  # "trending_up", "trending_down", "ranging", "volatile"
    confidence: float
    atr_percentile: float
    trend_strength: float
    volatility_level: str  # "low", "medium", "high"


class RecommendationEngine:
    """Strategy recommendation engine with regime-aware scoring.

    Parameters
    ----------
    config : AIConfig, optional
        Uses the ``recommendation`` sub-config.
    """

    def __init__(self, config: Optional[AIConfig] = None) -> None:
        self._cfg = (config or AIConfig()).recommendation
        self._strategy_stats: Dict[str, Dict[str, Any]] = {}
        self._user_preferences: Dict[str, float] = {}
        self._is_fitted = False

    @property
    def is_fitted(self) -> bool:
        return self._is_fitted

    # ------------------------------------------------------------------
    # Fitting
    # ------------------------------------------------------------------

    def fit(
        self,
        strategy_history: pd.DataFrame,
        user_history: Optional[pd.DataFrame] = None,
    ) -> None:
        """Compute strategy performance statistics.

        Parameters
        ----------
        strategy_history : pd.DataFrame
            Trade log with columns: ``strategy_id, symbol, timeframe,
            direction, pnl, entry_time, confidence``.
        user_history : pd.DataFrame, optional
            User's personal trade history for preference learning.
        """
        logger.info("Fitting recommendation engine on %d trades", len(strategy_history))

        for sid, group in strategy_history.groupby("strategy_id"):
            if len(group) < self._cfg.min_trades_required:
                continue
            self._strategy_stats[str(sid)] = self._compute_stats(group)

        if user_history is not None and len(user_history) > 0:
            self._learn_preferences(user_history)

        self._is_fitted = True
        logger.info("Fitted: %d strategies profiled", len(self._strategy_stats))

    # ------------------------------------------------------------------
    # Recommendation
    # ------------------------------------------------------------------

    def recommend(
        self,
        symbol: str,
        timeframe: str = "H1",
        regime: Optional[MarketRegime] = None,
        top_n: Optional[int] = None,
    ) -> List[StrategyScore]:
        """Generate ranked strategy recommendations.

        Parameters
        ----------
        symbol : str
            Trading symbol (e.g. "BTCUSD").
        timeframe : str
            Timeframe (e.g. "H1").
        regime : MarketRegime, optional
            Current market regime for filtering.
        top_n : int, optional
            Max recommendations to return.

        Returns
        -------
        list[StrategyScore]
            Strategies ranked by composite score (descending).
        """
        if not self._is_fitted:
            raise RuntimeError("Engine not fitted — call fit() first")

        top_n = top_n or self._cfg.max_recommendations
        scored: List[StrategyScore] = []

        for sid, stats in self._strategy_stats.items():
            if symbol not in stats.get("symbols", []) and stats.get("symbols"):
                continue

            composite = self._score_strategy(stats, regime)
            reason = self._explain_score(stats, regime)

            scored.append(StrategyScore(
                strategy_id=sid,
                strategy_name=stats.get("name", sid),
                composite_score=round(composite, 4),
                win_rate=stats.get("win_rate", 0.0),
                profit_factor=stats.get("profit_factor", 0.0),
                sharpe_ratio=stats.get("sharpe", 0.0),
                consistency=stats.get("consistency", 0.0),
                regime_fit=stats.get("regime_fit", 0.5),
                recent_performance=stats.get("recent_score", 0.0),
                reason=reason,
            ))

        scored.sort(key=lambda s: s.composite_score, reverse=True)
        return scored[:top_n]

    # ------------------------------------------------------------------
    # Market regime detection
    # ------------------------------------------------------------------

    @staticmethod
    def detect_regime(
        df: pd.DataFrame,
        indicators: Optional[Dict[str, Any]] = None,
    ) -> MarketRegime:
        """Classify the current market regime from price data.

        Parameters
        ----------
        df : pd.DataFrame
            Recent OHLCV data (at least 50 bars).
        indicators : dict, optional
            Pre-computed indicators (expects ``atr_14``, ``adx_14``).

        Returns
        -------
        MarketRegime
        """
        close = df["close"].values
        returns = np.diff(close) / close[:-1]

        # Trend detection via linear regression slope
        x = np.arange(min(50, len(close)))
        y = close[-len(x):]
        slope = np.polyfit(x, y, 1)[0] if len(x) > 1 else 0.0
        trend_strength = abs(slope) / (np.std(y) + 1e-10)

        # Volatility via ATR percentile
        if indicators and "atr_14" in indicators:
            atr = indicators["atr_14"]
            atr_current = atr[-1] if hasattr(atr, "__len__") else atr
            atr_series = pd.Series(atr[-50:] if hasattr(atr, "__len__") else [atr])
            atr_pct = float(atr_series.rank(pct=True).iloc[-1])
        else:
            atr_pct = float(pd.Series(np.abs(returns[-50:])).rank(pct=True).iloc[-1])

        # ADX for trend strength
        adx_val = 25.0
        if indicators and "adx_14" in indicators:
            adx = indicators["adx_14"]
            adx_val = float(adx[-1]) if hasattr(adx, "__len__") else float(adx)

        # Classify
        vol_level = "high" if atr_pct > 0.75 else ("low" if atr_pct < 0.25 else "medium")

        if adx_val > 25 and slope > 0:
            regime = "trending_up"
            conf = min(1.0, adx_val / 50)
        elif adx_val > 25 and slope < 0:
            regime = "trending_down"
            conf = min(1.0, adx_val / 50)
        elif atr_pct > 0.75:
            regime = "volatile"
            conf = atr_pct
        else:
            regime = "ranging"
            conf = 1.0 - (adx_val / 50)

        return MarketRegime(
            regime=regime,
            confidence=round(conf, 3),
            atr_percentile=round(atr_pct, 3),
            trend_strength=round(trend_strength, 3),
            volatility_level=vol_level,
        )

    # ------------------------------------------------------------------
    # Internal scoring
    # ------------------------------------------------------------------

    def _compute_stats(self, trades: pd.DataFrame) -> Dict[str, Any]:
        """Compute per-strategy performance statistics."""
        pnl = trades["pnl"].values
        wins = pnl[pnl > 0]
        losses = pnl[pnl < 0]

        win_rate = len(wins) / len(pnl) if len(pnl) > 0 else 0.0
        gross_profit = np.sum(wins) if len(wins) > 0 else 0.0
        gross_loss = abs(np.sum(losses)) if len(losses) > 0 else 1e-10
        profit_factor = gross_profit / gross_loss

        # Sharpe
        if np.std(pnl) > 0:
            sharpe = float(np.mean(pnl) / np.std(pnl) * np.sqrt(252))
        else:
            sharpe = 0.0

        # Consistency: fraction of profitable months
        if "entry_time" in trades.columns:
            trades_c = trades.copy()
            trades_c["month"] = pd.to_datetime(trades_c["entry_time"]).dt.to_period("M")
            monthly_pnl = trades_c.groupby("month")["pnl"].sum()
            consistency = (monthly_pnl > 0).mean() if len(monthly_pnl) > 0 else 0.0
        else:
            consistency = win_rate

        # Recent performance (exponential decay)
        recent_pnl = pnl[-20:] if len(pnl) > 20 else pnl
        weights = np.array([self._cfg.recency_decay ** i for i in range(len(recent_pnl) - 1, -1, -1)])
        recent_score = float(np.dot(recent_pnl, weights) / np.sum(weights)) if len(recent_pnl) > 0 else 0.0

        symbols = trades["symbol"].unique().tolist() if "symbol" in trades.columns else []
        name = trades["strategy_id"].iloc[0] if "strategy_id" in trades.columns else "unknown"

        return {
            "name": name,
            "total_trades": len(pnl),
            "win_rate": round(win_rate, 4),
            "profit_factor": round(profit_factor, 4),
            "sharpe": round(sharpe, 4),
            "consistency": round(consistency, 4),
            "recent_score": round(recent_score, 4),
            "symbols": symbols,
            "regime_fit": 0.5,  # default, updated by regime analysis
        }

    def _score_strategy(
        self, stats: Dict[str, Any], regime: Optional[MarketRegime]
    ) -> float:
        """Compute weighted composite score."""
        cfg = self._cfg
        score = (
            stats["win_rate"] * cfg.win_rate_weight
            + min(stats["profit_factor"] / 3.0, 1.0) * cfg.profit_factor_weight
            + min(max(stats["sharpe"], 0) / 3.0, 1.0) * cfg.sharpe_weight
            + stats["consistency"] * cfg.consistency_weight
        )

        # Regime bonus
        if regime:
            regime_bonus = self._regime_affinity(stats, regime)
            score = score * 0.8 + regime_bonus * 0.2

        # User preference bonus
        sid = stats.get("name", "")
        if sid in self._user_preferences:
            score += self._user_preferences[sid] * 0.1

        return score

    @staticmethod
    def _regime_affinity(stats: Dict[str, Any], regime: MarketRegime) -> float:
        """Estimate how well a strategy fits the current regime."""
        name_lower = stats.get("name", "").lower()

        trend_strategies = ["trend", "ma_", "ema_", "supertrend", "adx", "ichimoku"]
        range_strategies = ["bb_", "rsi_", "stoch", "mean_rev", "channel"]
        vol_strategies = ["atr", "breakout", "volatility", "squeeze"]

        if regime.regime in ("trending_up", "trending_down"):
            if any(kw in name_lower for kw in trend_strategies):
                return 0.9
            if any(kw in name_lower for kw in range_strategies):
                return 0.3
        elif regime.regime == "ranging":
            if any(kw in name_lower for kw in range_strategies):
                return 0.9
            if any(kw in name_lower for kw in trend_strategies):
                return 0.3
        elif regime.regime == "volatile":
            if any(kw in name_lower for kw in vol_strategies):
                return 0.9

        return 0.5

    @staticmethod
    def _explain_score(stats: Dict[str, Any], regime: Optional[MarketRegime]) -> str:
        """Generate a human-readable explanation for the recommendation."""
        parts = []
        if stats["win_rate"] > 0.6:
            parts.append(f"High win rate ({stats['win_rate']*100:.0f}%)")
        if stats["profit_factor"] > 2.0:
            parts.append(f"Strong profit factor ({stats['profit_factor']:.1f})")
        if stats["sharpe"] > 1.5:
            parts.append(f"Excellent risk-adjusted returns (Sharpe {stats['sharpe']:.2f})")
        if stats["consistency"] > 0.7:
            parts.append("Consistent monthly profitability")
        if regime:
            parts.append(f"Suitable for {regime.regime.replace('_', ' ')} regime")
        return " | ".join(parts) if parts else "Meets minimum criteria"

    def _learn_preferences(self, user_history: pd.DataFrame) -> None:
        """Learn user strategy preferences from their trade history."""
        if "strategy_id" not in user_history.columns or "pnl" not in user_history.columns:
            return

        for sid, group in user_history.groupby("strategy_id"):
            usage_count = len(group)
            avg_pnl = group["pnl"].mean()
            # Preference = combination of usage frequency and profitability
            self._user_preferences[str(sid)] = min(1.0, (usage_count / 20) * 0.5 + (1 if avg_pnl > 0 else 0) * 0.5)
