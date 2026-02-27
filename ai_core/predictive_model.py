"""
Predictive Model — ML-based market signal prediction.

Trains an ensemble of classifiers (Random Forest, XGBoost, LightGBM)
using time-series cross-validation on engineered features to predict
BUY / SELL / HOLD signals for any supported trading symbol.

Designed to complement (not replace) the 400+ rule-based strategies
by providing a data-driven confidence overlay.

Typical usage:
    >>> model = PredictiveModel()
    >>> model.train(X_train, y_train)
    >>> signal = model.predict(X_latest)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import RidgeClassifier
from sklearn.metrics import classification_report, f1_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import StandardScaler

from ai_core.config import AIConfig, PredictiveModelConfig

logger = logging.getLogger(__name__)

try:
    import xgboost as xgb
    _HAS_XGB = True
except ImportError:
    _HAS_XGB = False

try:
    import lightgbm as lgb
    _HAS_LGB = True
except ImportError:
    _HAS_LGB = False


@dataclass
class PredictionResult:
    """Output of a single prediction."""

    signal: str  # "BUY", "SELL", "HOLD"
    confidence: float  # 0.0 – 1.0
    model_votes: Dict[str, str]
    probabilities: Dict[str, List[float]]
    agreement: float


@dataclass
class TrainingReport:
    """Summary of a training run."""

    models_trained: List[str]
    best_model: str
    best_f1: float
    cv_scores: Dict[str, List[float]]
    feature_importances: Dict[str, float]
    train_time_sec: float


class PredictiveModel:
    """Ensemble signal predictor with time-series aware training.

    Parameters
    ----------
    config : AIConfig, optional
        Full AI configuration (uses ``predictive`` sub-config).
    """

    LABEL_MAP = {-1: "SELL", 0: "HOLD", 1: "BUY"}
    REVERSE_MAP = {"SELL": -1, "HOLD": 0, "BUY": 1}

    def __init__(self, config: Optional[AIConfig] = None) -> None:
        self._config = (config or AIConfig()).predictive
        self._models: Dict[str, Any] = {}
        self._scaler: Optional[StandardScaler] = None
        self._feature_names: List[str] = []
        self._is_trained = False

    @property
    def is_trained(self) -> bool:
        return self._is_trained

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(
        self,
        X: pd.DataFrame,
        y: pd.Series,
    ) -> TrainingReport:
        """Train all model families using TimeSeriesSplit.

        Parameters
        ----------
        X : pd.DataFrame
            Feature matrix.
        y : pd.Series
            Target labels (-1, 0, 1).

        Returns
        -------
        TrainingReport
        """
        t0 = time.perf_counter()
        self._feature_names = X.columns.tolist()
        cfg = self._config

        # Scale
        self._scaler = StandardScaler()
        X_arr = self._scaler.fit_transform(X.values.astype(np.float64))
        y_arr = y.values.astype(np.int64)

        tscv = TimeSeriesSplit(n_splits=cfg.n_cv_splits)
        builders = self._get_builders()
        cv_scores: Dict[str, List[float]] = {}
        best_f1 = -1.0
        best_name = ""

        for name, build_fn in builders.items():
            logger.info("Training %s ...", name)
            model = build_fn()
            scores: List[float] = []

            for train_idx, val_idx in tscv.split(X_arr):
                model.fit(X_arr[train_idx], y_arr[train_idx])
                preds = model.predict(X_arr[val_idx])
                scores.append(f1_score(y_arr[val_idx], preds, average="weighted", zero_division=0))

            # Final fit on all data
            model.fit(X_arr, y_arr)
            self._models[name] = model
            cv_scores[name] = scores
            mean_f1 = float(np.mean(scores))

            if mean_f1 > best_f1:
                best_f1 = mean_f1
                best_name = name

            logger.info("%s — mean CV F1=%.4f", name, mean_f1)

        self._is_trained = True
        elapsed = time.perf_counter() - t0

        importances = self._extract_importances(self._models.get(best_name))

        return TrainingReport(
            models_trained=list(builders.keys()),
            best_model=best_name,
            best_f1=best_f1,
            cv_scores=cv_scores,
            feature_importances=importances,
            train_time_sec=elapsed,
        )

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------

    def predict(self, X: pd.DataFrame) -> PredictionResult:
        """Generate an ensemble prediction.

        Uses the latest row when multiple rows are provided.

        Parameters
        ----------
        X : pd.DataFrame
            Feature matrix (one or more rows).

        Returns
        -------
        PredictionResult
        """
        if not self._is_trained:
            raise RuntimeError("Model not trained — call train() first")

        row = X.iloc[[-1]] if len(X) > 1 else X
        x = self._prepare_input(row)

        votes: Dict[str, str] = {}
        probas: Dict[str, List[float]] = {}

        for name, model in self._models.items():
            pred_int = int(model.predict(x)[0])
            votes[name] = self.LABEL_MAP.get(pred_int, "HOLD")

            if hasattr(model, "predict_proba"):
                probas[name] = model.predict_proba(x)[0].tolist()
            else:
                p = [0.1, 0.1, 0.1]
                idx_map = {-1: 0, 0: 1, 1: 2}
                p[idx_map.get(pred_int, 1)] = 0.8
                probas[name] = p

        # Aggregate via probability averaging
        avg_proba = np.mean(list(probas.values()), axis=0)
        winner_idx = int(np.argmax(avg_proba))
        confidence = float(avg_proba[winner_idx])
        class_map = {0: "SELL", 1: "HOLD", 2: "BUY"}
        signal = class_map.get(winner_idx, "HOLD")

        # Agreement
        vote_list = list(votes.values())
        agreement = vote_list.count(signal) / len(vote_list) if vote_list else 0.0

        if confidence < 0.45:
            signal = "HOLD"

        return PredictionResult(
            signal=signal,
            confidence=round(confidence, 4),
            model_votes=votes,
            probabilities=probas,
            agreement=round(agreement, 4),
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, directory: str) -> None:
        """Save all models and scaler to disk."""
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)

        for name, model in self._models.items():
            joblib.dump(model, path / f"{name}.joblib")

        if self._scaler:
            joblib.dump(self._scaler, path / "scaler.joblib")
        joblib.dump(self._feature_names, path / "feature_names.joblib")
        logger.info("Models saved to %s", path)

    def load(self, directory: str) -> None:
        """Load models from disk."""
        path = Path(directory)

        scaler_p = path / "scaler.joblib"
        if scaler_p.exists():
            self._scaler = joblib.load(scaler_p)

        names_p = path / "feature_names.joblib"
        if names_p.exists():
            self._feature_names = joblib.load(names_p)

        for fp in sorted(path.glob("*.joblib")):
            if fp.name in ("scaler.joblib", "feature_names.joblib"):
                continue
            self._models[fp.stem] = joblib.load(fp)

        self._is_trained = bool(self._models)
        logger.info("Loaded %d models from %s", len(self._models), path)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _prepare_input(self, row: pd.DataFrame) -> np.ndarray:
        """Align features and scale a single input row."""
        if self._feature_names:
            for col in set(self._feature_names) - set(row.columns):
                row[col] = 0.0
            row = row[self._feature_names]

        x = row.values.astype(np.float64)
        if self._scaler:
            x = self._scaler.transform(x)
        return x

    def _get_builders(self) -> Dict[str, Any]:
        """Return factory callables for each model family."""
        cfg = self._config
        builders: Dict[str, Any] = {
            "random_forest": lambda: RandomForestClassifier(
                n_estimators=cfg.rf_n_estimators,
                max_depth=cfg.rf_max_depth,
                min_samples_leaf=cfg.rf_min_samples_leaf,
                n_jobs=-1,
                random_state=cfg.random_state,
                class_weight="balanced",
            ),
            "ridge": lambda: RidgeClassifier(alpha=1.0, class_weight="balanced"),
        }
        if _HAS_XGB:
            builders["xgboost"] = lambda: xgb.XGBClassifier(
                n_estimators=cfg.xgb_n_estimators,
                max_depth=cfg.xgb_max_depth,
                learning_rate=cfg.xgb_learning_rate,
                subsample=cfg.xgb_subsample,
                use_label_encoder=False,
                eval_metric="mlogloss",
                verbosity=0,
                random_state=cfg.random_state,
            )
        if _HAS_LGB:
            builders["lightgbm"] = lambda: lgb.LGBMClassifier(
                n_estimators=cfg.lgb_n_estimators,
                max_depth=cfg.lgb_max_depth,
                learning_rate=cfg.lgb_learning_rate,
                num_leaves=cfg.lgb_num_leaves,
                verbose=-1,
                random_state=cfg.random_state,
                class_weight="balanced",
            )
        return builders

    def _extract_importances(self, model: Any) -> Dict[str, float]:
        if model is None:
            return {}
        arr: Optional[np.ndarray] = None
        if hasattr(model, "feature_importances_"):
            arr = model.feature_importances_
        elif hasattr(model, "coef_"):
            coef = model.coef_
            arr = np.abs(coef).mean(axis=0) if coef.ndim > 1 else np.abs(coef)

        if arr is None or len(arr) != len(self._feature_names):
            return {}

        imp = {n: float(v) for n, v in zip(self._feature_names, arr)}
        return dict(sorted(imp.items(), key=lambda kv: kv[1], reverse=True)[:20])
