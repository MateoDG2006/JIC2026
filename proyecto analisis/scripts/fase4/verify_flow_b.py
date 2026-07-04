#!/usr/bin/env python
"""Verificación end-to-end del pipeline Opción A (análisis descriptivo + multivariado).

Reproduce Fases 2–4 incluyendo baseline P6 (Fase 4 §12):

    1. load_bioactivity + filter_potential_duplicates
    2. drop_columns_high_nan + impute_median_by_family
    3. activities_clean.csv + compounds_features.csv (107 compuestos)
    4. PCA + clustering + Kruskal-Wallis
    5. baseline_honest_metrics.csv (compuesto vs filas_CON_FUGA)

Uso:
    python scripts/fase4/verify_flow_b.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.analisis_proyecto.chembl_baseline import (  # noqa: E402
    honest_baseline_compound_level,
    leaky_baseline_row_level,
)
from src.analisis_proyecto.chembl_multivariate import (  # noqa: E402
    FEATURE_COLS,
    cluster_vs_family_ari,
    kruskal_by_family,
    run_kmeans_silhouette,
    run_pca,
    scale_features,
)
from src.analisis_proyecto.chembl_preprocessing import (  # noqa: E402
    build_compound_features,
    drop_columns_high_nan,
    filter_potential_duplicates,
    impute_median_by_family,
    load_bioactivity,
    numeric_and_categorical_cols,
    pchembl_imputation_report,
)

RAW_CSV = ROOT / "data" / "raw" / "chembl_panama_bioactivity.csv"
ACTIVITIES_CSV = ROOT / "data" / "processed" / "activities_clean.csv"
COMPOUNDS_CSV = ROOT / "data" / "processed" / "compounds_features.csv"
STATS_CSV = ROOT / "outputs" / "chembl" / "results" / "stats_tests.csv"
CLUSTER_JSON = ROOT / "outputs" / "chembl" / "results" / "clustering_summary.json"
BASELINE_CSV = ROOT / "outputs" / "chembl" / "results" / "baseline_honest_metrics.csv"
NAN_THRESHOLD = 250


def run_pipeline(df: pd.DataFrame) -> None:
    df, dup_report = filter_potential_duplicates(df)
    if not dup_report.empty:
        print(f"  Duplicados eliminados: {dup_report.iloc[0]['filas_eliminadas']}")

    df, _ = drop_columns_high_nan(df, threshold=NAN_THRESHOLD)
    num_cols, cat_cols = numeric_and_categorical_cols(df)
    activities = impute_median_by_family(df, numeric_cols=num_cols, categorical_cols=cat_cols)

    ACTIVITIES_CSV.parent.mkdir(parents=True, exist_ok=True)
    activities.to_csv(ACTIVITIES_CSV, index=False)

    compounds = build_compound_features(activities)
    assert compounds["chembl_id"].nunique() == len(compounds)
    assert len(compounds) == 107, f"Esperado 107 compuestos, got {len(compounds)}"

    desc_cols = [c for c in FEATURE_COLS + ["heavy_atoms"] if c in compounds.columns]
    assert compounds[desc_cols].isna().sum().sum() == 0, "NaN en descriptores"

    X = scale_features(compounds)
    pca = run_pca(X, 2)
    km = run_kmeans_silhouette(X)
    ari = cluster_vs_family_ari(km["labels"], compounds["family"])
    compounds["cluster"] = km["labels"]
    compounds.to_csv(COMPOUNDS_CSV, index=False)

    stats_rows = [kruskal_by_family(compounds, v) for v in FEATURE_COLS + ["pchembl_median"]]
    STATS_CSV.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(stats_rows).to_csv(STATS_CSV, index=False)

    summary = {
        "best_k": km["best_k"],
        "silhouette_by_k": km["silhouette_by_k"],
        "ari_vs_family": ari,
        "pca_var_explained": sum(pca["explained_variance_ratio"]),
    }
    CLUSTER_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    baseline = pd.DataFrame([
        honest_baseline_compound_level(compounds),
        leaky_baseline_row_level(activities),
    ])
    baseline.to_csv(BASELINE_CSV, index=False)

    imp = pchembl_imputation_report(activities)
    print(f"  activities: {activities.shape} | compounds: {compounds.shape}")
    print(f"  pChEMBL imputados: {imp['pct_imputed']}%")
    print(f"  PCA var PC1+PC2: {summary['pca_var_explained']*100:.1f}%")
    print(f"  best_k={km['best_k']} | ARI={ari:.3f}")
    print(f"  baseline honest R²={baseline.iloc[0]['r2_test']:.3f}")
    print(f"  baseline leaky R²={baseline.iloc[1]['r2_test']:.3f}")


def main() -> int:
    if not RAW_CSV.exists():
        print(f"ERROR: falta {RAW_CSV}")
        return 1

    print(f"Usando dataset real: {RAW_CSV}")
    df = load_bioactivity(RAW_CSV)
    run_pipeline(df)
    print("=== verify_flow_b OK (Opción A) ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
