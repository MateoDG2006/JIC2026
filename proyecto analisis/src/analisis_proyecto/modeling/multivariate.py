"""Reducción de dimensionalidad, clustering y pruebas estadísticas (Fase 4)."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.multitest import multipletests

from src.analisis_proyecto.core.constants import multivariate_feature_columns
from src.analisis_proyecto.preprocessing.pipeline import FEATURE_COLS

MULTIVARIATE_FEATURE_COLS: list[str] = multivariate_feature_columns()


def _elbow_k(k_values: list[int], inertias: list[float]) -> int:
    """Método del codo: k con mayor cambio de curvatura (2ª diferencia de inercia)."""
    if len(k_values) < 3:
        return k_values[0]
    second_diff = np.diff(np.array(inertias, dtype=float), 2)
    idx = int(np.argmin(second_diff)) + 1
    return k_values[idx]


def _knee_k(k_values: list[int], inertias: list[float]) -> int:
    """Método de la rodilla (Kneedle): máxima distancia a la recta en la curva de inercia."""
    if len(k_values) < 2:
        return k_values[0]
    x = np.array(k_values, dtype=float)
    y = np.array(inertias, dtype=float)
    x_norm = (x - x.min()) / (x.max() - x.min() + 1e-12)
    y_norm = (y - y.max()) / (y.min() - y.max() + 1e-12)
    line = y_norm[0] + (y_norm[-1] - y_norm[0]) * (x_norm - x_norm[0]) / (
        x_norm[-1] - x_norm[0] + 1e-12
    )
    knee_idx = int(np.argmax(y_norm - line))
    return k_values[knee_idx]


def drop_degenerate(
    df: pd.DataFrame, cols: list[str], min_unique: int = 3
) -> tuple[list[str], list[str]]:
    """Descarta features con varianza casi nula (p. ej. num_ro5_violations)."""
    keep = [c for c in cols if df[c].nunique(dropna=True) >= min_unique]
    dropped = sorted(set(cols) - set(keep))
    return keep, dropped


def scale_features(
    df: pd.DataFrame, cols: list[str] | None = None
) -> np.ndarray:
    """StandardScaler sobre los descriptores multivariados (fit+transform)."""
    use_cols = cols or MULTIVARIATE_FEATURE_COLS
    return StandardScaler().fit_transform(df[use_cols].values)


def run_pca(X: np.ndarray, n_components: int = 2) -> dict:
    """PCA sobre X ya escalado. Retorna coords, varianza explicada y loadings."""
    pca = PCA(n_components=n_components, random_state=42)
    coords = pca.fit_transform(X)
    return {
        "coords": coords,
        "explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
        "loadings": pca.components_.tolist(),
    }


def run_kmeans_silhouette(
    X: np.ndarray, k_range: int | Iterable[int] = range(2, 9)
) -> dict:
    """K-means para varios k; selecciona k por codo, rodilla y silhouette."""
    k_values = [k_range] if isinstance(k_range, int) else list(k_range)
    scores: dict[int, float] = {}
    inertias: dict[int, float] = {}
    labels_by_k: dict[int, np.ndarray] = {}
    for k in k_values:
        km = KMeans(n_clusters=k, random_state=42, n_init=10).fit(X)
        scores[k] = float(silhouette_score(X, km.labels_))
        inertias[k] = float(km.inertia_)
        labels_by_k[k] = km.labels_

    inertia_list = [inertias[k] for k in k_values]
    k_silhouette = max(scores, key=scores.get)
    k_elbow = _elbow_k(k_values, inertia_list) if len(k_values) > 1 else k_values[0]
    k_knee = _knee_k(k_values, inertia_list) if len(k_values) > 1 else k_values[0]
    best_k = k_knee

    return {
        "best_k": int(best_k),
        "k_silhouette": int(k_silhouette),
        "k_elbow": int(k_elbow),
        "k_knee": int(k_knee),
        "silhouette_by_k": scores,
        "inertia_by_k": inertias,
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
    exclude_groups: tuple[str, ...] = ("mixed",),
) -> dict:
    """Kruskal-Wallis entre familias. Incluye epsilon² y n excluido por grupo."""
    work = df.copy()
    if exclude_groups:
        work = work[~work[group_col].isin(exclude_groups)]
    groups = [
        g[value_col].dropna().values
        for _, g in work.groupby(group_col)
        if g[value_col].notna().sum() >= min_n
    ]
    n_excluded = int(df[group_col].isin(exclude_groups).sum()) if exclude_groups else 0
    if len(groups) < 2:
        return {
            "value_col": value_col,
            "H": None,
            "p": None,
            "p_adjusted": None,
            "epsilon2": None,
            "k_groups": len(groups),
            "n": sum(len(g) for g in groups),
            "n_excluded_groups": n_excluded,
        }
    H, p = stats.kruskal(*groups)
    n = sum(len(g) for g in groups)
    k = len(groups)
    epsilon2 = (H - k + 1) / (n - k) if n > k else None
    return {
        "value_col": value_col,
        "H": float(H),
        "p": float(p),
        "p_adjusted": None,
        "epsilon2": (float(epsilon2) if epsilon2 is not None else None),
        "k_groups": k,
        "n": n,
        "n_excluded_groups": n_excluded,
    }


def apply_multiple_testing_correction(rows: list[dict], method: str = "fdr_bh") -> list[dict]:
    """Añade p_adjusted (Benjamini-Hochberg) sobre la batería confirmatoria."""
    idx_with_p = [(i, r["p"]) for i, r in enumerate(rows) if r.get("p") is not None]
    if not idx_with_p:
        return rows
    indices, pvals = zip(*idx_with_p)
    _, adj, _, _ = multipletests(pvals, method=method)
    out = [dict(r) for r in rows]
    for i, p_adj in zip(indices, adj):
        out[i]["p_adjusted"] = float(p_adj)
    return out


def posthoc_dunn(
    df: pd.DataFrame,
    value_col: str,
    group_col: str = "family",
    exclude_groups: tuple[str, ...] = ("mixed",),
) -> pd.DataFrame:
    """Post-hoc de Dunn con corrección Holm (requiere scikit-posthocs)."""
    import scikit_posthocs as sp

    work = df.copy()
    if exclude_groups:
        work = work[~work[group_col].isin(exclude_groups)]
    return sp.posthoc_dunn(work, val_col=value_col, group_col=group_col, p_adjust="holm")


@dataclass
class MultivariateResult:
    kmeans_labels: list[int]
    stats_rows: list[dict]
    exploratory_stats_rows: list[dict]
    summary: dict


class MultivariateAnalyzer:
    """PCA, clustering y pruebas Kruskal-Wallis sobre compuestos agregados."""

    def analyze(
        self,
        compounds: pd.DataFrame,
        *,
        potency_compounds: pd.DataFrame | None = None,
    ) -> MultivariateResult:
        feat_cols = [c for c in MULTIVARIATE_FEATURE_COLS if c in compounds.columns]
        dropped = sorted(set(FEATURE_COLS) - set(MULTIVARIATE_FEATURE_COLS))
        feat_cols, dropped_degen = drop_degenerate(compounds, feat_cols)
        dropped = sorted(set(dropped) | set(dropped_degen))
        assert set(feat_cols) == set(MULTIVARIATE_FEATURE_COLS) - set(dropped_degen), (
            f"Features multivariado inesperadas: {feat_cols}"
        )
        X = scale_features(compounds, feat_cols)
        pca = run_pca(X, 2)
        km = run_kmeans_silhouette(X)
        ari = cluster_vs_family_ari(km["labels"], compounds["family"])

        stats_rows = [
            kruskal_by_family(compounds, v, exclude_groups=("mixed",))
            for v in feat_cols
        ]
        stats_rows = apply_multiple_testing_correction(stats_rows)

        pot_df = potency_compounds if potency_compounds is not None else compounds
        if "pchembl_median_binding" in pot_df.columns:
            exploratory = kruskal_by_family(
                pot_df,
                "pchembl_median_binding",
                exclude_groups=("mixed",),
            )
        else:
            exploratory = {
                "value_col": "pchembl_median_binding",
                "H": None,
                "p": None,
                "p_adjusted": None,
                "epsilon2": None,
                "k_groups": 0,
                "n": 0,
                "n_excluded_groups": 0,
            }
        exploratory["note"] = (
            "EXPLORATORIO — pchembl_median_binding solo BINDING_TYPES (IC50/Ki/…); "
            "no usar como feature independiente junto a pct_active."
        )

        summary = {
            "best_k": km["best_k"],
            "k_silhouette": km["k_silhouette"],
            "k_elbow": km["k_elbow"],
            "k_knee": km["k_knee"],
            "silhouette_by_k": km["silhouette_by_k"],
            "inertia_by_k": km["inertia_by_k"],
            "silhouette_best": km["silhouette_by_k"][km["best_k"]],
            "ari_vs_family": ari,
            "pca_var_explained": sum(pca["explained_variance_ratio"]),
            "features_used": feat_cols,
            "features_dropped": dropped,
            "features_dropped_reason": (
                "near-zero variance (nunique < 3)" if dropped else None
            ),
            "cluster_validity_note": (
                f"Partición exploratoria — no corresponde a familias "
                f"(ARI={ari:.3f}, silhouette={km['silhouette_by_k'][km['best_k']]:.2f})"
            ),
        }
        return MultivariateResult(
            kmeans_labels=km["labels"],
            stats_rows=stats_rows,
            exploratory_stats_rows=[exploratory],
            summary=summary,
        )
