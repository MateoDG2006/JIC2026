"""Carga de artefactos del pipeline de análisis (Fases 2–5)."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from viz.config import (
    ACTIVITIES_CSV,
    ARTIFACTS_DIR,
    BUNDLE_DIR,
    CHEMBL_CSV,
    COMPOUNDS_ALL_CSV,
    STATIC_DATA_DIR,
    resolve_path,
)
from viz.services.dashboard.cache import load_csv_cached, load_json_cached


def _artifact_json(name: str) -> Path:
    if (ARTIFACTS_DIR / name).is_file():
        return ARTIFACTS_DIR / name
    return BUNDLE_DIR / name


def _static_json(name: str) -> Path:
    return STATIC_DATA_DIR / name


def load_chembl() -> pd.DataFrame:
    """Corpus estructural (~147 compuestos) para EDA/PCA."""
    return load_csv_cached(resolve_path(COMPOUNDS_ALL_CSV, "compounds_all.csv"))


def load_compounds_potency() -> pd.DataFrame:
    """Subconjunto con potencia cuantitativa (pchembl_median_binding)."""
    return load_csv_cached(resolve_path(CHEMBL_CSV, "compounds_features.csv"))


def load_activities() -> pd.DataFrame:
    return load_csv_cached(resolve_path(ACTIVITIES_CSV, "activities_clean.csv"))


def load_correlation() -> dict:
    return load_json_cached(_artifact_json("correlation_pearson.json"))


def load_baseline_honest() -> dict:
    path = _artifact_json("baseline_honest.json")
    if not path.is_file():
        return {"rows": [], "note": "Ejecuta: make prepare-dashboard"}
    return load_json_cached(path)


def load_pca_clusters() -> dict:
    path = _static_json("pca_clusters.json")
    if not path.is_file():
        return {"points": [], "note": "Ejecuta: make prepare-dashboard"}
    return load_json_cached(path)


def load_family_stats() -> dict:
    path = _static_json("family_stats.json")
    if not path.is_file():
        return {"kruskal_tests": [], "n_by_family": {}}
    return load_json_cached(path)


def load_compounds_profile() -> list[dict]:
    path = _static_json("compounds_profile.json")
    if not path.is_file():
        return []
    payload = load_json_cached(path)
    return list(payload) if isinstance(payload, list) else []
