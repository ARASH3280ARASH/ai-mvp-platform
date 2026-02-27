"""
Decision Optimizer — ML-driven trade sizing, timing, and risk allocation.

Combines strategy confidence, market regime, portfolio exposure, and
volatility conditions to compute optimal position sizes and entry timing.
Uses a modified Kelly criterion with configurable safety fractions.

Typical usage:
    >>> optimizer = DecisionOptimizer(account_balance=10000)
    >>> decision = optimizer.optimize(
    ...     signal="BUY", symbol="BTCUSD", confidence=0.72,
    ...     atr=150, current_price=65000,
    ... )
    >>> print(decision.lot_size, decision.sl_price, decision.tp_price)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from ai_core.config import AIConfig, OptimizerConfig

logger = logging.getLogger(__name__)


@dataclass
class TradeDecision:
    """Optimized trade parameters."""

    action: str  # "EXECUTE", "SKIP", "REDUCE"
    lot_size: float
    sl_price: float
    tp1_price: float
    tp2_price: float
    risk_dollars: float
    risk_pct: float
    reward_risk_ratio: float
    position_score: float  # 0–1 overall quality
    reasons: List[str]


@dataclass
class PortfolioState:
    """Current portfolio risk exposure."""

    open_positions: int
    total_exposure_pct: float
    symbols_exposed: List[str]
    daily_pnl: float
    max_drawdown_today_pct: float


class DecisionOptimizer:
    """ML-enhanced trade decision optimizer.

    Combines signal confidence, volatility, trend alignment, and portfolio
    risk constraints to determine optimal position sizing and entry levels.

    Parameters
    ----------
    account_balance : float
        Current account balance in USD.
    config : AIConfig, optional
        Uses the ``optimizer`` sub-config.
    """

    def __init__(
        self,
        account_balance: float = 10_000.0,
        config: Optional[AIConfig] = None,
    ) -> None:
        self._cfg = (config or AIConfig()).optimizer
        self._balance = account_balance
        self._portfolio = PortfolioState(
            open_positions=0,
            total_exposure_pct=0.0,
            symbols_exposed=[],
            daily_pnl=0.0,
            max_drawdown_today_pct=0.0,
        )

    @property
    def portfolio(self) -> PortfolioState:
        return self._portfolio

    def update_portfolio(self, state: PortfolioState) -> None:
        """Update current portfolio state."""
        self._portfolio = state

    def update_balance(self, balance: float) -> None:
        """Update account balance."""
        self._balance = balance

    # ------------------------------------------------------------------
    # Main optimization
    # ------------------------------------------------------------------

    def optimize(
        self,
        signal: str,
        symbol: str,
        confidence: float,
        atr: float,
        current_price: float,
        trend_strength: float = 0.5,
        volatility_percentile: float = 0.5,
        strategy_win_rate: float = 0.5,
        strategy_avg_rr: float = 1.5,
        pip_value: float = 1.0,
    ) -> TradeDecision:
        """Compute optimal trade parameters.

        Parameters
        ----------
        signal : str
            Direction — "BUY" or "SELL".
        symbol : str
            Trading symbol.
        confidence : float
            Signal confidence (0–1).
        atr : float
            Current ATR value (in price units).
        current_price : float
            Current market price.
        trend_strength : float
            Trend alignment score (0–1).
        volatility_percentile : float
            Current volatility percentile (0–1).
        strategy_win_rate : float
            Historical win rate of the strategy.
        strategy_avg_rr : float
            Historical average risk-reward ratio.
        pip_value : float
            Dollar value per pip for this symbol.

        Returns
        -------
        TradeDecision
        """
        reasons: List[str] = []
        cfg = self._cfg

        # -- Pre-flight checks --
        if signal not in ("BUY", "SELL"):
            return self._skip_decision("Invalid signal direction", signal)

        if confidence < 0.40:
            return self._skip_decision("Confidence too low", signal)

        if self._portfolio.total_exposure_pct >= cfg.max_portfolio_risk_pct:
            return self._skip_decision("Portfolio risk limit reached", signal)

        if symbol in self._portfolio.symbols_exposed:
            corr_penalty = cfg.correlation_threshold
            reasons.append(f"Symbol already exposed (correlation penalty {corr_penalty:.0%})")
        else:
            corr_penalty = 0.0

        # -- Position quality score --
        position_score = (
            confidence * cfg.confidence_weight
            + (1 - volatility_percentile) * cfg.volatility_weight
            + trend_strength * cfg.trend_weight
        )
        position_score *= (1.0 - corr_penalty * 0.3)
        position_score = round(np.clip(position_score, 0, 1), 4)

        if position_score < 0.35:
            return self._skip_decision(f"Position score too low ({position_score:.2f})", signal)

        # -- Kelly-based position sizing --
        kelly_pct = self._kelly_criterion(strategy_win_rate, strategy_avg_rr)
        risk_pct = kelly_pct * position_score

        # Hard cap
        risk_pct = min(risk_pct, cfg.max_risk_per_trade_pct)
        risk_dollars = self._balance * (risk_pct / 100.0)

        # -- SL/TP calculation --
        sl_distance = atr * 1.5
        tp1_distance = sl_distance * 1.5
        tp2_distance = sl_distance * 3.0

        if signal == "BUY":
            sl_price = current_price - sl_distance
            tp1_price = current_price + tp1_distance
            tp2_price = current_price + tp2_distance
        else:
            sl_price = current_price + sl_distance
            tp1_price = current_price - tp1_distance
            tp2_price = current_price - tp2_distance

        # -- Lot size from risk --
        sl_pips = sl_distance / pip_value if pip_value > 0 else sl_distance
        if sl_pips > 0:
            lot_size = risk_dollars / (sl_pips * pip_value * 100)
        else:
            lot_size = cfg.min_position_size_lots

        lot_size = round(np.clip(lot_size, cfg.min_position_size_lots, cfg.max_position_size_lots), 2)

        # -- Volatility adjustment --
        if volatility_percentile > 0.80:
            lot_size = round(lot_size * 0.7, 2)
            reasons.append("Lot reduced 30% — high volatility environment")
        elif volatility_percentile < 0.20:
            lot_size = round(lot_size * 1.15, 2)
            reasons.append("Lot increased 15% — low volatility environment")

        lot_size = round(np.clip(lot_size, cfg.min_position_size_lots, cfg.max_position_size_lots), 2)

        rr_ratio = tp1_distance / sl_distance if sl_distance > 0 else 0.0
        actual_risk = lot_size * sl_pips * pip_value * 100
        actual_risk_pct = actual_risk / self._balance * 100 if self._balance > 0 else 0.0

        reasons.append(f"Confidence: {confidence:.0%}")
        reasons.append(f"Position score: {position_score:.2f}")
        reasons.append(f"Kelly fraction: {kelly_pct:.2f}%")
        reasons.append(f"R:R = 1:{rr_ratio:.1f}")

        action = "EXECUTE" if position_score >= 0.5 else "REDUCE"

        return TradeDecision(
            action=action,
            lot_size=lot_size,
            sl_price=round(sl_price, 5),
            tp1_price=round(tp1_price, 5),
            tp2_price=round(tp2_price, 5),
            risk_dollars=round(actual_risk, 2),
            risk_pct=round(actual_risk_pct, 2),
            reward_risk_ratio=round(rr_ratio, 2),
            position_score=position_score,
            reasons=reasons,
        )

    # ------------------------------------------------------------------
    # Kelly criterion
    # ------------------------------------------------------------------

    def _kelly_criterion(self, win_rate: float, avg_rr: float) -> float:
        """Compute fractional Kelly bet size.

        Kelly % = W - (1 - W) / R

        Parameters
        ----------
        win_rate : float
            Historical win probability (0–1).
        avg_rr : float
            Average reward / risk ratio.

        Returns
        -------
        float
            Risk percentage (clamped to [0, max_risk]).
        """
        if avg_rr <= 0 or win_rate <= 0:
            return 0.0

        kelly = win_rate - (1 - win_rate) / avg_rr
        kelly *= self._cfg.kelly_fraction  # fractional Kelly (safety)
        return float(np.clip(kelly * 100, 0, self._cfg.max_risk_per_trade_pct))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _skip_decision(self, reason: str, signal: str) -> TradeDecision:
        """Return a SKIP decision."""
        return TradeDecision(
            action="SKIP",
            lot_size=0.0,
            sl_price=0.0,
            tp1_price=0.0,
            tp2_price=0.0,
            risk_dollars=0.0,
            risk_pct=0.0,
            reward_risk_ratio=0.0,
            position_score=0.0,
            reasons=[reason],
        )

    # ------------------------------------------------------------------
    # Batch optimization
    # ------------------------------------------------------------------

    def rank_opportunities(
        self,
        candidates: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Score and rank multiple trade candidates.

        Parameters
        ----------
        candidates : list[dict]
            Each dict should have: signal, symbol, confidence, atr,
            current_price, and optionally trend_strength, win_rate, avg_rr.

        Returns
        -------
        list[dict]
            Sorted by position_score (descending), each with a ``decision`` key.
        """
        results = []
        for c in candidates:
            decision = self.optimize(
                signal=c["signal"],
                symbol=c["symbol"],
                confidence=c.get("confidence", 0.5),
                atr=c.get("atr", 0),
                current_price=c.get("current_price", 0),
                trend_strength=c.get("trend_strength", 0.5),
                volatility_percentile=c.get("volatility_percentile", 0.5),
                strategy_win_rate=c.get("win_rate", 0.5),
                strategy_avg_rr=c.get("avg_rr", 1.5),
                pip_value=c.get("pip_value", 1.0),
            )
            results.append({**c, "decision": decision})

        results.sort(key=lambda x: x["decision"].position_score, reverse=True)
        return results
