"""Inferencia sklearn ChEMBL."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd

from viz.config import BUNDLE_DIR, CHEMBL_MODELS_DIR, use_bundle
from viz.services.dashboard.artifacts import load_predictor_defaults


def _models_dir() -> Path:
    if use_bundle() and (BUNDLE_DIR / "models").is_dir():
        return BUNDLE_DIR / "models"
    return CHEMBL_MODELS_DIR


@lru_cache(maxsize=1)
def load_rf_regressor():
    return joblib.load(_models_dir() / "rf_regressor.pkl")


def predict_pchembl(user_inputs: dict[str, float]) -> float:
    defaults = load_predictor_defaults()
    row = dict(defaults)
    for col, val in user_inputs.items():
        row[col] = float(val)

    model = load_rf_regressor()
    X = pd.DataFrame([row])
    if hasattr(model, "feature_names_in_"):
        X = X.reindex(columns=list(model.feature_names_in_), fill_value=0.0)
    return float(model.predict(X)[0])
