"""Fase 4 — análisis multivariado y baseline predictivo (P6)."""

from src.analisis_proyecto.modeling.baseline import (
    CompoundLevelBaseline,
    RowLevelLeakyBaseline,
    RowLevelSplitContrast,
)
from src.analisis_proyecto.modeling.multivariate import (
    MULTIVARIATE_FEATURE_COLS,
    MultivariateAnalyzer,
    MultivariateResult,
    apply_multiple_testing_correction,
    drop_degenerate,
    kruskal_by_family,
    posthoc_dunn,
    run_kmeans_silhouette,
    run_pca,
    scale_features,
)

__all__ = [
    "CompoundLevelBaseline",
    "MULTIVARIATE_FEATURE_COLS",
    "MultivariateAnalyzer",
    "MultivariateResult",
    "RowLevelLeakyBaseline",
    "RowLevelSplitContrast",
    "apply_multiple_testing_correction",
    "drop_degenerate",
    "kruskal_by_family",
    "posthoc_dunn",
    "run_kmeans_silhouette",
    "run_pca",
    "scale_features",
]
