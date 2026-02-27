"""Tests for the predictive model module."""

import numpy as np
import pandas as pd
import pytest

from ai_core.config import AIConfig
from ai_core.predictive_model import PredictiveModel


@pytest.fixture
def sample_features() -> pd.DataFrame:
    """Generate synthetic feature matrix."""
    np.random.seed(42)
    n = 500
    return pd.DataFrame(
        np.random.randn(n, 10),
        columns=[f"feat_{i}" for i in range(10)],
    )


@pytest.fixture
def sample_target() -> pd.Series:
    """Generate synthetic target labels."""
    np.random.seed(42)
    return pd.Series(np.random.choice([-1, 0, 1], size=500))


class TestPredictiveModel:
    def test_init(self) -> None:
        model = PredictiveModel()
        assert not model.is_trained

    def test_train(self, sample_features: pd.DataFrame, sample_target: pd.Series) -> None:
        model = PredictiveModel()
        report = model.train(sample_features, sample_target)

        assert model.is_trained
        assert len(report.models_trained) >= 2  # at least RF + Ridge
        assert report.best_f1 >= 0.0
        assert report.train_time_sec > 0

    def test_predict_before_train_raises(self, sample_features: pd.DataFrame) -> None:
        model = PredictiveModel()
        with pytest.raises(RuntimeError, match="not trained"):
            model.predict(sample_features)

    def test_predict_returns_valid_signal(
        self, sample_features: pd.DataFrame, sample_target: pd.Series
    ) -> None:
        model = PredictiveModel()
        model.train(sample_features, sample_target)
        result = model.predict(sample_features.tail(10))

        assert result.signal in ("BUY", "SELL", "HOLD")
        assert 0.0 <= result.confidence <= 1.0
        assert 0.0 <= result.agreement <= 1.0
        assert len(result.model_votes) >= 2

    def test_save_load(
        self, sample_features: pd.DataFrame, sample_target: pd.Series, tmp_path
    ) -> None:
        model = PredictiveModel()
        model.train(sample_features, sample_target)

        save_dir = str(tmp_path / "models")
        model.save(save_dir)

        model2 = PredictiveModel()
        model2.load(save_dir)
        assert model2.is_trained

        result = model2.predict(sample_features.tail(5))
        assert result.signal in ("BUY", "SELL", "HOLD")
