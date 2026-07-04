#!/usr/bin/env python
"""
Prepara artefactos del dashboard (Fase 5 — análisis descriptivo ChEMBL).

Entradas: Fase 2 (compounds + activities) y Fase 4 (clustering + stats).

Uso:
  python scripts/fase5/prepare_dashboard.py
  python scripts/fase5/prepare_dashboard.py --bundle
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analisis_proyecto.modeling.multivariate import run_pca, scale_features  # noqa: E402
from src.analisis_proyecto.preprocessing.pipeline import (  # noqa: E402
    get_available_feature_cols,
    load_bioactivity,
    pchembl_imputation_report,
)

ARTIFACTS_DIR = ROOT / "outputs" / "dashboard"
STATIC_DATA_DIR = ROOT / "viz" / "static" / "data"
BUNDLE_DIR = ARTIFACTS_DIR / "bundle"
CHEMBL_CSV = ROOT / "data" / "processed" / "compounds_features.csv"
COMPOUNDS_ALL_CSV = ROOT / "data" / "processed" / "compounds_all.csv"
ACTIVITIES_CSV = ROOT / "data" / "processed" / "activities_clean.csv"
RESULTS_DIR = ROOT / "outputs" / "chembl" / "results"


def _require(path: Path, hint: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"No existe: {path}\n  → {hint}")


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _build_correlation_json(df: pd.DataFrame, out_path: Path) -> None:
    cols = [c for c in get_available_feature_cols(df) if c in df.columns]
    for extra in ("pchembl_median_binding", "pchembl_std_binding", "n_activities_binding"):
        if extra in df.columns and extra not in cols:
            cols.append(extra)
    pearson = df[cols].corr(method="pearson")
    spearman = df[cols].corr(method="spearman")
    _write_json(
        out_path,
        {
            "columns": cols,
            "matrix": pearson.round(4).values.tolist(),
            "pearson": pearson.round(4).values.tolist(),
            "spearman": spearman.round(4).values.tolist(),
        },
    )


def _build_compounds_profile_json(
    compounds: pd.DataFrame, activities: pd.DataFrame, out_path: Path
) -> None:
    id_col = "chembl_id" if "chembl_id" in activities.columns else "compound_name"
    if "is_censored" in activities.columns:
        binding = activities.loc[
            ~activities["is_censored"] & activities["pchembl_value"].notna()
        ]
    else:
        binding = activities.loc[activities["pchembl_value"].notna()]
    agg = (
        binding.groupby(id_col, dropna=False)
        .agg(
            n_measurements=("pchembl_value", "count"),
            pchembl_median_meas=("pchembl_value", "median"),
            n_endpoints=("standard_type", "nunique"),
        )
        .reset_index()
    )
    merge_on = id_col if id_col in compounds.columns else "compound_name"
    profile = compounds.merge(agg, on=merge_on, how="left")
    if "pct_active" in profile.columns:
        profile["pct_active_label"] = "derivado de pchembl >= 6 (no independiente)"
    if "target_inestable" in profile.columns:
        profile["target_inestable_note"] = (
            profile["target_inestable"].map(
                {True: "σ_binding > 1 — mediana puede ocultar multimodalidad", False: ""}
            )
        )
    _write_json(out_path, profile.to_dict(orient="records"))


def _build_pca_clusters_json(
    compounds: pd.DataFrame, clustering_path: Path, out_path: Path
) -> None:
    summary = (
        json.loads(clustering_path.read_text(encoding="utf-8"))
        if clustering_path.is_file()
        else {}
    )
    X = scale_features(compounds)
    pca = run_pca(X, 2)
    ari = summary.get("ari_vs_family")
    sil = summary.get("silhouette_best") or (
        summary.get("silhouette_by_k", {}).get(str(summary.get("best_k")))
        if summary.get("best_k") is not None
        else None
    )
    cluster_note = summary.get("cluster_validity_note") or (
        f"Partición exploratoria — no corresponde a familias "
        f"(ARI={ari:.3f}, silhouette={sil:.2f})"
        if ari is not None and sil is not None
        else "Partición exploratoria — validez no reportada"
    )
    points = []
    for idx in range(len(compounds)):
        row = compounds.iloc[idx]
        points.append(
            {
                "chembl_id": row.get("chembl_id"),
                "compound_name": row.get("compound_name"),
                "family": row.get("family"),
                "cluster": int(row["cluster"])
                if "cluster" in compounds.columns and pd.notna(row.get("cluster"))
                else None,
                "cluster_label": row.get("cluster_label", cluster_note),
                "pc1": float(pca["coords"][idx, 0]),
                "pc2": float(pca["coords"][idx, 1]),
            }
        )
    _write_json(
        out_path,
        {
            "points": points,
            "explained_variance_ratio": pca["explained_variance_ratio"],
            "summary": summary,
            "cluster_validity": {
                "ari_vs_family": ari,
                "silhouette_best": sil,
                "note": cluster_note,
            },
        },
    )


def _build_family_stats_json(
    stats_csv: Path, compounds: pd.DataFrame, out_path: Path
) -> None:
    tests = (
        pd.read_csv(stats_csv).to_dict(orient="records")
        if stats_csv.is_file()
        else []
    )
    n_by_family = compounds.groupby("family").size().astype(int).to_dict()
    _write_json(out_path, {"kruskal_tests": tests, "n_by_family": n_by_family})


def _build_baseline_honest_json(src: Path, out_path: Path) -> None:
    if not src.is_file():
        _write_json(
            out_path,
            {
                "rows": [],
                "note": "Ejecuta notebooks/fase4_modelado.ipynb §4 (baseline P6).",
            },
        )
        return
    df = pd.read_csv(src)
    _write_json(
        out_path,
        {
            "rows": df.to_dict(orient="records"),
            "note": "Baseline honesto vs fuga — documentado en Fase 4 §4.",
        },
    )


def _copy_fase4_results() -> None:
    for name in (
        "clustering_summary.json",
        "stats_tests.csv",
        "baseline_honest_metrics.csv",
        "corpus_funnel.json",
        "censoring_report.json",
    ):
        src = RESULTS_DIR / name
        if src.is_file():
            shutil.copy2(src, ARTIFACTS_DIR / name)


_DEPLOYMENT_CSVS = (
    (COMPOUNDS_ALL_CSV, "compounds_all.csv"),
    (CHEMBL_CSV, "compounds_features.csv"),
    (ACTIVITIES_CSV, "activities_clean.csv"),
)


def _copy_deployment_csvs(dest: Path) -> None:
    """Copia CSVs de corpus para despliegue (Render / git)."""
    dest.mkdir(parents=True, exist_ok=True)
    for src, name in _DEPLOYMENT_CSVS:
        if src.is_file():
            shutil.copy2(src, dest / name)


def _create_bundle() -> None:
    print("\n=== Bundle de despliegue (outputs/dashboard/bundle/) ===")
    if BUNDLE_DIR.exists():
        shutil.rmtree(BUNDLE_DIR)
    BUNDLE_DIR.mkdir(parents=True)

    _copy_deployment_csvs(BUNDLE_DIR)

    for name in ARTIFACTS_DIR.glob("*.json"):
        shutil.copy2(name, BUNDLE_DIR / name.name)

    static_dst = BUNDLE_DIR / "static"
    static_dst.mkdir(parents=True, exist_ok=True)
    if STATIC_DATA_DIR.is_dir():
        for path in STATIC_DATA_DIR.glob("*.json"):
            shutil.copy2(path, static_dst / path.name)

    print(f"  Bundle listo: {BUNDLE_DIR}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepara artefactos del dashboard (Fase 5)")
    parser.add_argument("--bundle", action="store_true", help="Genera bundle para despliegue")
    args = parser.parse_args()

    print("=== Preparación dashboard (Fase 5) ===")
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    STATIC_DATA_DIR.mkdir(parents=True, exist_ok=True)

    _require(COMPOUNDS_ALL_CSV, "ejecuta scripts/fase4/verify_flow_b.py o fase2_limpieza.ipynb")
    _require(CHEMBL_CSV, "ejecuta scripts/fase4/verify_flow_b.py o fase2_limpieza.ipynb")
    _require(ACTIVITIES_CSV, "ejecuta notebooks/fase2_limpieza.ipynb")
    _require(RESULTS_DIR / "clustering_summary.json", "ejecuta notebooks/fase4_modelado.ipynb §2-§3")
    _require(RESULTS_DIR / "stats_tests.csv", "ejecuta notebooks/fase4_modelado.ipynb §3")

    compounds_all = pd.read_csv(COMPOUNDS_ALL_CSV)
    compounds_potency = pd.read_csv(CHEMBL_CSV)
    activities = load_bioactivity(ACTIVITIES_CSV)
    clustering_path = RESULTS_DIR / "clustering_summary.json"
    funnel_path = RESULTS_DIR / "corpus_funnel.json"
    censoring_path = RESULTS_DIR / "censoring_report.json"

    _build_correlation_json(compounds_all, ARTIFACTS_DIR / "correlation_pearson.json")
    _build_correlation_json(compounds_all, STATIC_DATA_DIR / "correlation.json")
    _build_compounds_profile_json(compounds_potency, activities, STATIC_DATA_DIR / "compounds_profile.json")
    _build_pca_clusters_json(compounds_all, clustering_path, STATIC_DATA_DIR / "pca_clusters.json")
    _build_family_stats_json(RESULTS_DIR / "stats_tests.csv", compounds_all, STATIC_DATA_DIR / "family_stats.json")
    _build_baseline_honest_json(RESULTS_DIR / "baseline_honest_metrics.csv", ARTIFACTS_DIR / "baseline_honest.json")
    _write_json(ARTIFACTS_DIR / "pchembl_imputation.json", pchembl_imputation_report(activities))
    _copy_fase4_results()
    _copy_deployment_csvs(ARTIFACTS_DIR)

    manifest = {
        "project": "proyecto analisis",
        "chembl_rows_structural": len(compounds_all),
        "chembl_rows_potency": len(compounds_potency),
        "activity_rows": len(activities),
        "cluster_validity": json.loads(clustering_path.read_text(encoding="utf-8"))
        if clustering_path.is_file()
        else {},
        "corpus_funnel": json.loads(funnel_path.read_text(encoding="utf-8"))
        if funnel_path.is_file()
        else {},
        "censoring_report": json.loads(censoring_path.read_text(encoding="utf-8"))
        if censoring_path.is_file()
        else {},
        "sources": {
            "compounds_all": str(COMPOUNDS_ALL_CSV.relative_to(ROOT)),
            "compounds_potency": str(CHEMBL_CSV.relative_to(ROOT)),
            "activities": str(ACTIVITIES_CSV.relative_to(ROOT)),
            "clustering": str(clustering_path.relative_to(ROOT)),
            "stats_tests": str((RESULTS_DIR / "stats_tests.csv").relative_to(ROOT)),
            "static_data": str(STATIC_DATA_DIR.relative_to(ROOT)),
        },
    }
    _write_json(ARTIFACTS_DIR / "manifest.json", manifest)

    print(f"Artefactos en: {ARTIFACTS_DIR}")
    print(f"Static data : {STATIC_DATA_DIR}")
    print(f"Compuestos (estructural): {manifest['chembl_rows_structural']}")
    print(f"Compuestos (potencia)   : {manifest['chembl_rows_potency']}")
    print(f"Mediciones              : {manifest['activity_rows']}")

    if args.bundle:
        _create_bundle()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
