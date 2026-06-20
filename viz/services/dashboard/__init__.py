"""Servicios de analytics integrados en el visor FastAPI."""

from viz.services.dashboard.artifacts import (
    geojson_to_dataframe,
    load_chembl,
    load_correlation,
    load_feature_cols,
    load_geojson,
    load_metrics_summary,
    load_model_eval,
    load_predictor_defaults,
    load_toxicity_profile,
    load_xai_index,
)
from viz.services.dashboard.chembl import predict_pchembl
from viz.services.dashboard.xai import resolve_xai_filename, slugify, xai_figures_dir
from viz.services.dashboard.artifacts import load_model_comparison

__all__ = [
    "geojson_to_dataframe",
    "load_chembl",
    "load_correlation",
    "load_feature_cols",
    "load_geojson",
    "load_metrics_summary",
    "load_model_eval",
    "load_predictor_defaults",
    "load_toxicity_profile",
    "load_xai_index",
    "load_model_comparison",
    "predict_pchembl",
    "resolve_xai_filename",
    "slugify",
    "xai_figures_dir",
]
