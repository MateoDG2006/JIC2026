#!/usr/bin/env python
"""Genera figuras y resultados de Fases 3-4 + anexo baseline (Opción A)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.cluster import hierarchy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analisis_proyecto.chembl_baseline import (  # noqa: E402
    honest_baseline_compound_level,
    leaky_baseline_row_level,
)
from src.analisis_proyecto.chembl_multivariate import (  # noqa: E402
    cluster_vs_family_ari,
    kruskal_by_family,
    run_kmeans_silhouette,
    run_pca,
    scale_features,
)
from src.analisis_proyecto.chembl_preprocessing import (  # noqa: E402
    FEATURE_COLS,
    correlation_with_target,
    load_bioactivity,
)

FIG = ROOT / "outputs" / "chembl" / "figures"
RES = ROOT / "outputs" / "chembl" / "results"


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    RES.mkdir(parents=True, exist_ok=True)

    activities = load_bioactivity(ROOT / "data/processed/activities_clean.csv")
    compounds = pd.read_csv(ROOT / "data/processed/compounds_features.csv")

    for col in FEATURE_COLS + ["pchembl_median"]:
        if col not in compounds.columns:
            continue
        fig, ax = plt.subplots(figsize=(12, 5))
        order = compounds.groupby("family")[col].median().sort_values().index
        sns.boxplot(data=compounds, x="family", y=col, order=order, ax=ax)
        counts = compounds["family"].value_counts()
        labels = [f"{f}\n(n={counts[f]})" for f in order if f in counts.index]
        ax.set_xticklabels(labels, rotation=30, ha="right")
        ax.set_title(f"{col} por familia (n compuestos)")
        plt.tight_layout()
        plt.savefig(FIG / f"box_{col}_by_family.png", bbox_inches="tight")
        plt.close()

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    compounds["n_targets"].hist(bins=20, ax=axes[0], edgecolor="white")
    axes[0].set_title("Promiscuidad: n_targets por compuesto")
    sns.boxplot(data=compounds, x="family", y="n_targets", ax=axes[1])
    axes[1].tick_params(axis="x", rotation=30)
    plt.tight_layout()
    plt.savefig(FIG / "promiscuity_distribution.png", bbox_inches="tight")
    plt.close()

    if "target_type" in activities.columns:
        ct = pd.crosstab(activities["chembl_id"], activities["target_type"])
        top_targets = ct.sum(axis=0).nlargest(15).index
        ct_top = ct[top_targets]
        fig, ax = plt.subplots(figsize=(14, 10))
        sns.heatmap(ct_top, cmap="YlOrRd", ax=ax, cbar_kws={"label": "n mediciones"})
        ax.set_title("Heatmap compuesto x target_type (top 15)")
        plt.tight_layout()
        plt.savefig(FIG / "heatmap_compound_target.png", bbox_inches="tight")
        plt.close()

    corr_matrix = compounds[FEATURE_COLS + ["pchembl_median"]].corr(method="pearson")
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(corr_matrix, mask=mask, annot=True, fmt=".2f", cmap="coolwarm", center=0, ax=ax)
    ax.set_title("Correlación descriptores (107 compuestos)")
    plt.tight_layout()
    plt.savefig(FIG / "correlation_heatmap.png", bbox_inches="tight")
    plt.close()

    pair_cols = FEATURE_COLS[:4] + ["pchembl_median"]
    g = sns.pairplot(compounds[pair_cols].dropna(), diag_kind="hist", corner=True)
    g.fig.suptitle("Scatter matrix — nivel compuesto", y=1.02)
    g.savefig(FIG / "correlation_pairplot.png", bbox_inches="tight")
    plt.close("all")

    correlation_with_target(compounds, target="pchembl_median", columns=FEATURE_COLS)

    X = scale_features(compounds)
    pca = run_pca(X, 2)
    ev1 = pca["explained_variance_ratio"][0] * 100
    ev2 = pca["explained_variance_ratio"][1] * 100
    fig, ax = plt.subplots(figsize=(8, 6))
    for fam in compounds["family"].unique():
        m = compounds["family"] == fam
        ax.scatter(pca["coords"][m, 0], pca["coords"][m, 1], label=fam, alpha=0.8)
    ax.set_xlabel(f"PC1 ({ev1:.1f}%)")
    ax.set_ylabel(f"PC2 ({ev2:.1f}%)")
    ax.set_title("PCA descriptores moleculares")
    ax.legend(bbox_to_anchor=(1.05, 1), fontsize=8)
    plt.tight_layout()
    plt.savefig(FIG / "pca_scatter.png", bbox_inches="tight")
    plt.close()

    km = run_kmeans_silhouette(X)
    fig, ax = plt.subplots()
    ax.plot(list(km["silhouette_by_k"].keys()), list(km["silhouette_by_k"].values()), "o-")
    ax.set_xlabel("k")
    ax.set_ylabel("silhouette")
    ax.set_title("K-means silhouette")
    plt.tight_layout()
    plt.savefig(FIG / "cluster_silhouette.png", bbox_inches="tight")
    plt.close()

    Z = hierarchy.linkage(X, method="ward")
    fig, ax = plt.subplots(figsize=(12, 5))
    hierarchy.dendrogram(Z, ax=ax, truncate_mode="lastp", p=20)
    ax.set_title("Dendrograma Ward")
    plt.tight_layout()
    plt.savefig(FIG / "dendrogram.png", bbox_inches="tight")
    plt.close()

    labels = km["labels"]
    ari = cluster_vs_family_ari(labels, compounds["family"])
    compounds["cluster"] = labels
    compounds.to_csv(ROOT / "data/processed/compounds_features.csv", index=False)

    test_vars = FEATURE_COLS + ["pchembl_median"]
    stats_df = pd.DataFrame([kruskal_by_family(compounds, v) for v in test_vars])
    stats_df.to_csv(RES / "stats_tests.csv", index=False)

    summary = {
        "best_k": km["best_k"],
        "silhouette_by_k": km["silhouette_by_k"],
        "ari_vs_family": ari,
    }
    (RES / "clustering_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    fig, axes = plt.subplots(2, 3, figsize=(14, 8))
    for i, col in enumerate(test_vars[:6]):
        sns.boxplot(data=compounds, x="family", y=col, ax=axes.flatten()[i])
        axes.flatten()[i].tick_params(axis="x", rotation=45)
        axes.flatten()[i].set_title(col)
    plt.tight_layout()
    plt.savefig(FIG / "family_boxplots_annotated.png", bbox_inches="tight")
    plt.close()

    baseline_rows = [
        honest_baseline_compound_level(compounds),
        leaky_baseline_row_level(activities),
    ]
    pd.DataFrame(baseline_rows).to_csv(RES / "baseline_honest_metrics.csv", index=False)

    print("=== run_opcion_a_outputs OK ===")
    print(stats_df[["value_col", "p", "epsilon2"]].to_string())
    print("baseline:", baseline_rows)
    print("cluster column added to compounds_features.csv")


if __name__ == "__main__":
    main()
