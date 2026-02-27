"""
AI Core — Intelligent trading analysis and prediction pipeline.

This package extends the Whilber-AI trading platform with machine learning
capabilities for signal prediction, strategy recommendation, market sentiment
analysis, and trade decision optimization.

Modules:
    pipeline: Orchestrates the full AI analysis workflow
    predictive_model: ML-based price movement prediction
    recommendation_engine: Personalized strategy recommendations
    nlp_processor: Market sentiment and news analysis
    decision_optimizer: ML-optimized position sizing and timing
    config: Model hyperparameters and feature configuration
    utils: Shared preprocessing and data utilities
"""

from ai_core.pipeline import AIPipeline
from ai_core.config import AIConfig

__version__ = "1.0.0"
__all__ = ["AIPipeline", "AIConfig"]
