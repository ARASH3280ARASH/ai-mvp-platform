"""Tests for the decision optimizer module."""

import pytest

from ai_core.decision_optimizer import DecisionOptimizer, PortfolioState


@pytest.fixture
def optimizer() -> DecisionOptimizer:
    return DecisionOptimizer(account_balance=10_000)


class TestDecisionOptimizer:
    def test_basic_buy(self, optimizer: DecisionOptimizer) -> None:
        decision = optimizer.optimize(
            signal="BUY",
            symbol="BTCUSD",
            confidence=0.75,
            atr=150.0,
            current_price=65000.0,
        )
        assert decision.action in ("EXECUTE", "REDUCE")
        assert decision.lot_size > 0
        assert decision.sl_price < 65000.0
        assert decision.tp1_price > 65000.0

    def test_basic_sell(self, optimizer: DecisionOptimizer) -> None:
        decision = optimizer.optimize(
            signal="SELL",
            symbol="XAUUSD",
            confidence=0.70,
            atr=15.0,
            current_price=2400.0,
        )
        assert decision.action in ("EXECUTE", "REDUCE")
        assert decision.sl_price > 2400.0
        assert decision.tp1_price < 2400.0

    def test_low_confidence_skips(self, optimizer: DecisionOptimizer) -> None:
        decision = optimizer.optimize(
            signal="BUY",
            symbol="EURUSD",
            confidence=0.20,
            atr=0.005,
            current_price=1.0850,
        )
        assert decision.action == "SKIP"
        assert decision.lot_size == 0.0

    def test_invalid_signal_skips(self, optimizer: DecisionOptimizer) -> None:
        decision = optimizer.optimize(
            signal="HOLD",
            symbol="BTCUSD",
            confidence=0.80,
            atr=150.0,
            current_price=65000.0,
        )
        assert decision.action == "SKIP"

    def test_portfolio_risk_limit(self, optimizer: DecisionOptimizer) -> None:
        optimizer.update_portfolio(PortfolioState(
            open_positions=5,
            total_exposure_pct=10.0,
            symbols_exposed=["BTCUSD"],
            daily_pnl=-200.0,
            max_drawdown_today_pct=2.0,
        ))
        decision = optimizer.optimize(
            signal="BUY",
            symbol="XAUUSD",
            confidence=0.80,
            atr=15.0,
            current_price=2400.0,
        )
        assert decision.action == "SKIP"

    def test_risk_reward_ratio(self, optimizer: DecisionOptimizer) -> None:
        decision = optimizer.optimize(
            signal="BUY",
            symbol="BTCUSD",
            confidence=0.75,
            atr=100.0,
            current_price=60000.0,
        )
        assert decision.reward_risk_ratio >= 1.0

    def test_rank_opportunities(self, optimizer: DecisionOptimizer) -> None:
        candidates = [
            {"signal": "BUY", "symbol": "BTCUSD", "confidence": 0.80, "atr": 150, "current_price": 65000},
            {"signal": "SELL", "symbol": "XAUUSD", "confidence": 0.60, "atr": 15, "current_price": 2400},
            {"signal": "BUY", "symbol": "EURUSD", "confidence": 0.50, "atr": 0.005, "current_price": 1.085},
        ]
        ranked = optimizer.rank_opportunities(candidates)
        assert len(ranked) == 3
        scores = [r["decision"].position_score for r in ranked]
        assert scores == sorted(scores, reverse=True)
