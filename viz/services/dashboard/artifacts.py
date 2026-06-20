"""Carga de artefactos desde rutas canonicas del pipeline GIN/ChEMBL."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

from viz.config import (
    ARTIFACTS_DIR,
    BUNDLE_DIR,
    CHEMBL_CSV,
    CHEMBL_METRICS,
    CHEMBL_MODELS_DIR,
    GEOJSON_PATH,
    TOXICITY_PROFILE_CSV,
    resolve_path,
    use_bundle,
)
from viz.services.dashboard.cache import invalidate_all, load_csv_cached, load_json_cached


def _artifact_json(name: str) -> Path:
    if (ARTIFACTS_DIR / name).is_file():
        return ARTIFACTS_DIR / name
    return BUNDLE_DIR / name


def load_chembl() -> pd.DataFrame:
    return load_csv_cached(resolve_path(CHEMBL_CSV, "chembl_clean.csv"))


def load_toxicity_profile() -> pd.DataFrame:
    return load_csv_cached(resolve_path(TOXICITY_PROFILE_CSV, "panama_toxicity_profile.csv"))


def load_correlation() -> dict:
    return load_json_cached(_artifact_json("correlation_pearson.json"))


def load_model_eval() -> dict:
    return load_json_cached(_artifact_json("model_eval.json"))


def load_metrics_summary() -> pd.DataFrame:
    return load_csv_cached(resolve_path(CHEMBL_METRICS, "metrics_summary.csv"))


def load_predictor_defaults() -> dict:
    return load_json_cached(_artifact_json("predictor_defaults.json"))


def load_model_comparison() -> dict:
    path = _artifact_json("model_comparison.json")
    if not path.is_file():
        return {"models": [], "note": "Ejecute: make prepare-dashboard"}
    return load_json_cached(path)


@lru_cache(maxsize=1)
def load_feature_cols() -> list[str]:
    if use_bundle() and (BUNDLE_DIR / "models" / "feature_cols.json").is_file():
        path = BUNDLE_DIR / "models" / "feature_cols.json"
    else:
        path = CHEMBL_MODELS_DIR / "feature_cols.json"
    payload = load_json_cached(path)
    return list(payload) if isinstance(payload, list) else list(payload.get("feature_cols", []))


def load_geojson() -> dict:
    path = resolve_path(GEOJSON_PATH, "panama_distritos.geojson")
    return load_json_cached(path)


def load_xai_index() -> dict:
    path = _artifact_json("xai_index.json")
    if not path.is_file():
        return {}
    return load_json_cached(path)


def geojson_to_dataframe() -> pd.DataFrame:
    geo = load_geojson()
    rows = [feat["properties"] for feat in geo.get("features", [])]
    return pd.DataFrame(rows)
