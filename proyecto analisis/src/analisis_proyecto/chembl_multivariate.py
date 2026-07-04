"""Reducción de dimensionalidad, clustering y pruebas estadísticas (Fase 4)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from src.analisis_proyecto.chembl_preprocessing import FEATURE_COLS


def scale_features(df: pd.DataFrame, cols: list[str] = FEATURE_COLS) -> np.ndarray:
    """StandardScaler sobre los descriptores (fit+transform)."""
    return StandardScaler().fit_transform(df[cols].values)


def run_pca(X: np.ndarray, n_components: int = 2) -> dict:
    """PCA sobre X ya escalado. Retorna coords, varianza explicada y loadings."""
    pca = PCA(n_components=n_components, random_state=42)
    coords = pca.fit_transform(X)
    return {
        "coords": coords,
        "explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
        "loadings": pca.components_.tolist(),
    }


def run_kmeans_silhouette(X: np.ndarray, k_range=range(2, 9)) -> dict:
    """K-means para varios k; elige el de mayor silhouette."""
    scores: dict[int, float] = {}
    labels_by_k: dict[int, np.ndarray] = {}
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(X)
        scores[k] = float(silhouette_score(X, km.labels_))
        labels_by_k[k] = km.labels_
    best_k = max(scores, key=scores.get)
    return {
        "best_k": int(best_k),
        "silhouette_by_k": scores,
        "labels": labels_by_k[best_k].tolist(),
    }


def cluster_vs_family_ari(labels, family: pd.Series) -> float:
    """Adjusted Rand Index entre clusters y familia química."""
    return float(adjusted_rand_score(family.astype(str).values, labels))


def kruskal_by_family(
    df: pd.DataFrame,
    value_col: str,
    group_col: str = "family",
    min_n: int = 3,
) -> dict:
    """Kruskal-Wallis entre familias para value_col. Incluye tamaño de efecto epsilon²."""
    groups = [
        g[value_col].dropna().values
        for _, g in df.groupby(group_col)
        if g[value_col].notna().sum() >= min_n
    ]
    if len(groups) < 2:
        return {
            "value_col": value_col,
            "H": None,
            "p": None,
            "epsilon2": None,
            "k_groups": len(groups),
            "n": sum(len(g) for g in groups),
        }
    H, p = stats.kruskal(*groups)
    n = sum(len(g) for g in groups)
    k = len(groups)
    epsilon2 = (H - k + 1) / (n - k) if n > k else None
    return {
        "value_col": value_col,
        "H": float(H),
        "p": float(p),
        "epsilon2": (float(epsilon2) if epsilon2 is not None else None),
        "k_groups": k,
        "n": n,
    }


def posthoc_dunn(
    df: pd.DataFrame,
    value_col: str,
    group_col: str = "family",
) -> pd.DataFrame:
    """Post-hoc de Dunn con corrección Holm (requiere scikit-posthocs)."""
    import scikit_posthocs as sp

    return sp.posthoc_dunn(df, val_col=value_col, group_col=group_col, p_adjust="holm")
