"""
AI Configuration — Model hyperparameters, feature sets, and pipeline settings.

Centralizes all ML configuration so that models can be tuned from a single
location without touching module code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass
class FeatureConfig:
    """Feature engineering configuration."""

    lookback_periods: List[int] = field(default_factory=lambda: [5, 10, 20, 50])
    momentum_windows: List[int] = field(default_factory=lambda: [1, 3, 5, 10, 20])
    lag_periods: List[int] = field(default_factory=lambda: [1, 2, 3, 5])
    volatility_windows: List[int] = field(default_factory=lambda: [10, 20, 50])
    volume_windows: List[int] = field(default_factory=lambda: [5, 10, 20])

    indicator_features: List[str] = field(default_factory=lambda: [
        "rsi_14", "rsi_7", "macd_line", "macd_signal", "macd_histogram",
        "bb_upper", "bb_lower", "bb_middle", "atr_14", "adx_14",
        "stoch_k", "stoch_d", "cci_14", "williams_r", "obv",
        "mfi_14", "supertrend", "ema_20", "ema_50", "sma_200",
    ])


@dataclass
class PredictiveModelConfig:
    """Signal prediction model configuration."""

    # Data
    target_horizon: int = 5  # bars ahead
    buy_threshold_pct: float = 0.3
    sell_threshold_pct: float = -0.3

    # Random Forest
    rf_n_estimators: int = 300
    rf_max_depth: int = 12
    rf_min_samples_leaf: int = 5

    # XGBoost
    xgb_n_estimators: int = 250
    xgb_max_depth: int = 8
    xgb_learning_rate: float = 0.05
    xgb_subsample: float = 0.8

    # LightGBM
    lgb_n_estimators: int = 250
    lgb_max_depth: int = 8
    lgb_learning_rate: float = 0.05
    lgb_num_leaves: int = 63

    # Training
    n_cv_splits: int = 5
    scale_features: bool = True
    random_state: int = 42


@dataclass
class RecommendationConfig:
    """Strategy recommendation engine configuration."""

    min_trades_required: int = 10
    performance_lookback_days: int = 30
    similarity_top_k: int = 5
    recency_decay: float = 0.95
    win_rate_weight: float = 0.35
    profit_factor_weight: float = 0.30
    sharpe_weight: float = 0.20
    consistency_weight: float = 0.15
    max_recommendations: int = 10


@dataclass
class NLPConfig:
    """NLP processing configuration."""

    max_text_length: int = 512
    sentiment_model: str = "lexicon"  # "lexicon" or "transformer"
    bullish_threshold: float = 0.2
    bearish_threshold: float = -0.2
    keyword_categories: Dict[str, List[str]] = field(default_factory=lambda: {
        "bullish": [
            "rally", "surge", "breakout", "bullish", "uptrend", "support",
            "accumulation", "demand", "buy", "long", "higher high",
        ],
        "bearish": [
            "crash", "selloff", "breakdown", "bearish", "downtrend", "resistance",
            "distribution", "supply", "sell", "short", "lower low",
        ],
        "volatility": [
            "volatile", "uncertainty", "fear", "panic", "squeeze",
            "whipsaw", "spike", "turbulence",
        ],
    })


@dataclass
class OptimizerConfig:
    """Decision optimizer configuration."""

    max_risk_per_trade_pct: float = 2.0
    max_portfolio_risk_pct: float = 10.0
    min_risk_reward_ratio: float = 1.5
    confidence_weight: float = 0.4
    volatility_weight: float = 0.3
    trend_weight: float = 0.3
    kelly_fraction: float = 0.25  # quarter Kelly
    max_position_size_lots: float = 1.0
    min_position_size_lots: float = 0.01
    correlation_threshold: float = 0.7


@dataclass
class AIConfig:
    """Top-level AI pipeline configuration."""

    features: FeatureConfig = field(default_factory=FeatureConfig)
    predictive: PredictiveModelConfig = field(default_factory=PredictiveModelConfig)
    recommendation: RecommendationConfig = field(default_factory=RecommendationConfig)
    nlp: NLPConfig = field(default_factory=NLPConfig)
    optimizer: OptimizerConfig = field(default_factory=OptimizerConfig)

    model_dir: Path = field(default_factory=lambda: BASE_DIR / "models")
    cache_ttl_seconds: int = 300
    log_predictions: bool = True

    def __post_init__(self) -> None:
        self.model_dir.mkdir(parents=True, exist_ok=True)
