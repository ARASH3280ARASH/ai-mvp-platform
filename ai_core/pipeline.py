"""
AI Pipeline — Orchestrates the full ML-enhanced analysis workflow.

Coordinates feature engineering, signal prediction, strategy recommendation,
sentiment analysis, and trade optimization into a unified pipeline that
integrates with the existing Whilber-AI analysis endpoints.

Typical usage:
    >>> pipeline = AIPipeline()
    >>> result = pipeline.analyze(
    ...     symbol="BTCUSD", timeframe="H1",
    ...     df=ohlcv_data, indicators=indicator_dict,
    ... )
    >>> print(result.ml_signal, result.recommendations)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from ai_core.config import AIConfig
from ai_core.utils import build_feature_matrix, build_target
from ai_core.predictive_model import PredictiveModel, PredictionResult
from ai_core.recommendation_engine import (
    RecommendationEngine,
    MarketRegime,
    StrategyScore,
)
from ai_core.nlp_processor import NLPProcessor, SentimentResult
from ai_core.decision_optimizer import DecisionOptimizer, TradeDecision

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Unified output of the AI analysis pipeline."""

    symbol: str
    timeframe: str
    timestamp: float

    # ML Prediction
    ml_signal: str  # "BUY", "SELL", "HOLD"
    ml_confidence: float
    ml_details: Optional[PredictionResult] = None

    # Market Regime
    regime: Optional[MarketRegime] = None

    # Strategy Recommendations
    recommendations: List[StrategyScore] = field(default_factory=list)

    # Sentiment (if news text provided)
    sentiment: Optional[SentimentResult] = None

    # Trade Decision
    trade_decision: Optional[TradeDecision] = None

    # Metadata
    processing_time_ms: float = 0.0
    errors: List[str] = field(default_factory=list)


class AIPipeline:
    """Orchestrate ML analysis for trading signals.

    The pipeline runs five stages:
        1. Feature engineering from OHLCV + indicators
        2. ML signal prediction (ensemble)
        3. Market regime detection
        4. Strategy recommendation (regime-aware)
        5. Trade decision optimization

    Sentiment analysis runs optionally when news text is provided.

    Parameters
    ----------
    config : AIConfig, optional
        Full pipeline configuration.
    account_balance : float
        Account balance for position sizing.
    """

    def __init__(
        self,
        config: Optional[AIConfig] = None,
        account_balance: float = 10_000.0,
    ) -> None:
        self._config = config or AIConfig()

        self.predictor = PredictiveModel(self._config)
        self.recommender = RecommendationEngine(self._config)
        self.nlp = NLPProcessor(self._config)
        self.optimizer = DecisionOptimizer(account_balance, self._config)

        self._is_ready = False

    @property
    def is_ready(self) -> bool:
        """Whether the prediction model has been trained."""
        return self.predictor.is_trained

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(
        self,
        df: pd.DataFrame,
        indicators: Optional[Dict[str, Any]] = None,
        strategy_history: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Any]:
        """Train all pipeline components.

        Parameters
        ----------
        df : pd.DataFrame
            Historical OHLCV data for ML model training.
        indicators : dict, optional
            Pre-computed technical indicators.
        strategy_history : pd.DataFrame, optional
            Trade log for recommendation engine.

        Returns
        -------
        dict
            Training summary with metrics per component.
        """
        summary: Dict[str, Any] = {}
        t0 = time.perf_counter()

        # 1. Build features
        logger.info("Building feature matrix ...")
        features, names = build_feature_matrix(df, indicators)
        target = build_target(
            df,
            horizon=self._config.predictive.target_horizon,
            buy_threshold=self._config.predictive.buy_threshold_pct,
            sell_threshold=self._config.predictive.sell_threshold_pct,
        )
        target_aligned = target.loc[features.index]

        # 2. Train prediction model
        logger.info("Training predictive model ...")
        report = self.predictor.train(features, target_aligned)
        summary["predictive_model"] = {
            "best_model": report.best_model,
            "best_f1": report.best_f1,
            "models_trained": report.models_trained,
            "n_features": len(names),
            "n_samples": len(features),
        }

        # 3. Fit recommendation engine
        if strategy_history is not None and len(strategy_history) > 0:
            logger.info("Fitting recommendation engine ...")
            self.recommender.fit(strategy_history)
            summary["recommendation_engine"] = {
                "strategies_profiled": len(self.recommender._strategy_stats),
            }

        self._is_ready = True
        summary["total_training_time_sec"] = round(time.perf_counter() - t0, 2)
        logger.info("Pipeline training complete in %.1fs", summary["total_training_time_sec"])
        return summary

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def analyze(
        self,
        symbol: str,
        timeframe: str,
        df: pd.DataFrame,
        indicators: Optional[Dict[str, Any]] = None,
        news_texts: Optional[List[str]] = None,
        strategy_win_rate: float = 0.5,
        strategy_avg_rr: float = 1.5,
        current_price: Optional[float] = None,
        pip_value: float = 1.0,
    ) -> PipelineResult:
        """Run the full AI analysis pipeline.

        Parameters
        ----------
        symbol : str
            Trading symbol.
        timeframe : str
            Timeframe string.
        df : pd.DataFrame
            Recent OHLCV data.
        indicators : dict, optional
            Pre-computed indicators.
        news_texts : list[str], optional
            Market news / commentary for sentiment.
        strategy_win_rate : float
            Historical win rate for sizing.
        strategy_avg_rr : float
            Historical R:R for sizing.
        current_price : float, optional
            Current market price (defaults to last close).
        pip_value : float
            Dollar per pip for this symbol.

        Returns
        -------
        PipelineResult
        """
        t0 = time.perf_counter()
        result = PipelineResult(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=time.time(),
            ml_signal="HOLD",
            ml_confidence=0.0,
        )

        price = current_price or float(df["close"].iloc[-1])

        # Stage 1: Feature engineering + ML prediction
        try:
            features, _ = build_feature_matrix(df, indicators)
            if self.predictor.is_trained and len(features) > 0:
                pred = self.predictor.predict(features)
                result.ml_signal = pred.signal
                result.ml_confidence = pred.confidence
                result.ml_details = pred
        except Exception as e:
            logger.exception("ML prediction failed")
            result.errors.append(f"Prediction: {e}")

        # Stage 2: Market regime
        try:
            regime = self.recommender.detect_regime(df, indicators)
            result.regime = regime
        except Exception as e:
            logger.exception("Regime detection failed")
            result.errors.append(f"Regime: {e}")

        # Stage 3: Strategy recommendations
        try:
            if self.recommender.is_fitted:
                recs = self.recommender.recommend(
                    symbol=symbol,
                    timeframe=timeframe,
                    regime=result.regime,
                    top_n=5,
                )
                result.recommendations = recs
        except Exception as e:
            logger.exception("Recommendation failed")
            result.errors.append(f"Recommendation: {e}")

        # Stage 4: Sentiment (optional)
        if news_texts:
            try:
                agg = self.nlp.analyze_batch(news_texts)
                result.sentiment = SentimentResult(
                    sentiment=agg.overall_sentiment,
                    score=agg.overall_score,
                    confidence=agg.bullish_pct / 100,
                    keywords_found={},
                    word_count=agg.n_sources,
                )
            except Exception as e:
                logger.exception("Sentiment analysis failed")
                result.errors.append(f"Sentiment: {e}")

        # Stage 5: Trade optimization
        try:
            atr_val = 0.0
            if indicators and "atr_14" in indicators:
                atr = indicators["atr_14"]
                atr_val = float(atr[-1]) if hasattr(atr, "__len__") else float(atr)

            if result.ml_signal != "HOLD":
                decision = self.optimizer.optimize(
                    signal=result.ml_signal,
                    symbol=symbol,
                    confidence=result.ml_confidence,
                    atr=atr_val,
                    current_price=price,
                    trend_strength=result.regime.trend_strength if result.regime else 0.5,
                    volatility_percentile=result.regime.atr_percentile if result.regime else 0.5,
                    strategy_win_rate=strategy_win_rate,
                    strategy_avg_rr=strategy_avg_rr,
                    pip_value=pip_value,
                )
                result.trade_decision = decision
        except Exception as e:
            logger.exception("Trade optimization failed")
            result.errors.append(f"Optimizer: {e}")

        result.processing_time_ms = round((time.perf_counter() - t0) * 1000, 1)
        logger.info(
            "Pipeline: %s %s → %s (%.0f%% conf) in %.1fms",
            symbol, timeframe, result.ml_signal,
            result.ml_confidence * 100, result.processing_time_ms,
        )
        return result

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, directory: str) -> None:
        """Save all trained models."""
        self.predictor.save(f"{directory}/predictive")
        logger.info("Pipeline models saved to %s", directory)

    def load(self, directory: str) -> None:
        """Load previously trained models."""
        self.predictor.load(f"{directory}/predictive")
        self._is_ready = self.predictor.is_trained
        logger.info("Pipeline models loaded from %s", directory)
