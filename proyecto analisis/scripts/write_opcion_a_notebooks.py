#!/usr/bin/env python
"""Reescribe notebooks fase2/fase3/fase4 + anexo según PASAMANO Opción A."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NB_DIR = ROOT / "notebooks"


def nb(cells: list) -> dict:
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "pygments_lexer": "ipython3"},
        },
        "cells": cells,
    }


def md(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(keepends=True)}


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "metadata": {},
        "source": source.splitlines(keepends=True),
        "outputs": [],
        "execution_count": None,
    }


ROOT_SETUP = '''import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from IPython.display import Image, display

from src.paths import PROJECT_ROOT as ROOT, setup_path
setup_path()

sns.set_theme(style="whitegrid", palette="muted", font_scale=1.05)
plt.rcParams.update({"figure.figsize": (10, 5), "figure.dpi": 120})

FIG_DIR = ROOT / "outputs" / "chembl" / "figures"
RESULTS_DIR = ROOT / "outputs" / "chembl" / "results"
for d in (FIG_DIR, RESULTS_DIR):
    d.mkdir(parents=True, exist_ok=True)
'''


def write_fase2() -> None:
    cells = [
        md(
            "# Fase 2 — Limpieza e ingeniería de datos\n\n"
            "| Campo | Valor |\n|---|---|\n"
            "| **Entrada** | `data/raw/chembl_panama_bioactivity.csv` |\n"
            "| **Salidas** | `activities_clean.csv` (medición) + `compounds_features.csv` (107 compuestos) |\n"
            "| **Doc** | [`docs/analisis_proyecto/fases/fase2_limpieza_datos.md`](../../docs/analisis_proyecto/fases/fase2_limpieza_datos.md) |\n\n"
            "Unidad principal de análisis: **compuesto** (107 filas). La tabla de mediciones conserva "
            "`standard_relation`, `target_chembl_id` y `standard_type` para perfiles de dianas/endpoints.\n"
        ),
        md("## 0. Configuración"),
        code(
            ROOT_SETUP
            + '''
from src.analisis_proyecto.chembl_preprocessing import (
    FEATURE_COLS,
    build_compound_features,
    drop_columns_high_nan,
    filter_potential_duplicates,
    impute_median_by_family,
    load_bioactivity,
    missingness_upset_series,
    numeric_and_categorical_cols,
    pchembl_imputation_report,
    plot_missingno_report,
)

RAW_CSV = ROOT / "data" / "raw" / "chembl_panama_bioactivity.csv"
ACTIVITIES_CSV = ROOT / "data" / "processed" / "activities_clean.csv"
COMPOUNDS_CSV = ROOT / "data" / "processed" / "compounds_features.csv"
NAN_COL_THRESHOLD = 250

assert RAW_CSV.exists(), f"No se encontró {RAW_CSV}. Ejecuta fase1_adquisicion.ipynb"

raw = load_bioactivity(RAW_CSV)
print(f"RAW: {raw.shape[0]:,} filas × {raw.shape[1]} columnas | compuestos: {raw['chembl_id'].nunique()}")
if "potential_duplicate" in raw.columns:
    n_dup = int((raw["potential_duplicate"].fillna(0).astype(int) == 1).sum())
    print(f"Filas potential_duplicate=1 (a eliminar): {n_dup}")
'''
        ),
        md(
            "## 1. Diagnóstico de faltantes\n\n"
            "Visualización sobre datos RAW (antes de dedup). Se conserva para documentar el estado inicial.\n"
        ),
        code(
            '''saved_msno = plot_missingno_report(raw, FIG_DIR)
if saved_msno:
    for path in saved_msno:
        display(Image(filename=str(path)))

upset_data, nan_cols = missingness_upset_series(raw)
if upset_data is not None:
    from upsetplot import UpSet
    upset = UpSet(upset_data, subset_size="count", show_counts=True)
    upset.plot()
    plt.suptitle("Patrones de valores faltantes (UpSet)")
    plt.savefig(FIG_DIR / "missingness_upset.png", bbox_inches="tight")
    plt.show()
'''
        ),
        md(
            "## 2. Dedup + imputación + tablas de salida\n\n"
            "1. Eliminar `potential_duplicate==1` (corrige ~801 filas duplicadas).\n"
            "2. Drop columnas con >250 NaN e imputación por mediana de `family`.\n"
            "3. Guardar `activities_clean.csv` (nivel medición).\n"
            "4. Agregar `compounds_features.csv` (107 compuestos).\n"
        ),
        code(
            '''activities, dup_report = filter_potential_duplicates(raw)
display(dup_report)

activities, nan_report = drop_columns_high_nan(activities, threshold=NAN_COL_THRESHOLD)
num_cols, cat_cols = numeric_and_categorical_cols(activities)
activities = impute_median_by_family(activities, numeric_cols=num_cols, categorical_cols=cat_cols)

ACTIVITIES_CSV.parent.mkdir(parents=True, exist_ok=True)
activities.to_csv(ACTIVITIES_CSV, index=False)

compounds = build_compound_features(activities)
assert compounds["chembl_id"].nunique() == len(compounds), "Debe haber 1 fila por compuesto"
compounds.to_csv(COMPOUNDS_CSV, index=False)

print(f"activities: {activities.shape} | compounds: {compounds.shape}")
print(pchembl_imputation_report(activities))

if "standard_relation" in activities.columns:
    rel = activities["standard_relation"].value_counts(dropna=False)
    print("\\nCensura / relación standard_relation (conservada en activities_clean):")
    display(rel.to_frame("n"))
'''
        ),
        md(
            "---\n"
            "*Anterior:* [`fase1_adquisicion.ipynb`](fase1_adquisicion.ipynb)  \n"
            "*Siguiente:* [`fase3_eda.ipynb`](fase3_eda.ipynb)\n"
        ),
    ]
    path = NB_DIR / "fase2_limpieza.ipynb"
    path.write_text(json.dumps(nb(cells), indent=1, ensure_ascii=False), encoding="utf-8")
    print("Wrote", path)


def write_fase3() -> None:
    cells = [
        md(
            "# Fase 3 — Análisis exploratorio (nivel compuesto)\n\n"
            "| Campo | Valor |\n|---|---|\n"
            "| **Entrada compuesto** | `compounds_features.csv` (107 filas) |\n"
            "| **Entrada medición** | `activities_clean.csv` (perfil dianas/endpoints) |\n"
            "| **Doc** | [`docs/analisis_proyecto/fases/fase3_eda.md`](../../docs/analisis_proyecto/fases/fase3_eda.md) |\n\n"
            "> **Unidad de análisis:** descriptores fisicoquímicos sobre **107 compuestos**, no 2.807 filas. "
            "Reportar siempre **n por familia** (Carbamates tiene muy pocos compuestos).\n"
        ),
        md("## 0. Configuración"),
        code(
            ROOT_SETUP
            + '''
from src.analisis_proyecto.chembl_preprocessing import (
    FEATURE_COLS,
    correlation_with_target,
    load_bioactivity,
    summary_statistics,
)

ACTIVITIES_CSV = ROOT / "data" / "processed" / "activities_clean.csv"
COMPOUNDS_CSV = ROOT / "data" / "processed" / "compounds_features.csv"

assert COMPOUNDS_CSV.exists(), "Ejecuta fase2_limpieza.ipynb primero"

activities = load_bioactivity(ACTIVITIES_CSV)
compounds = pd.read_csv(COMPOUNDS_CSV)
print(f"Compuestos: {compounds.shape} | Mediciones: {activities.shape}")
print("n por familia (compuesto):")
display(compounds["family"].value_counts().to_frame("n_compuestos"))
'''
        ),
        md("## 1. Tendencia central (107 compuestos)"),
        code(
            '''stats_table = summary_statistics(compounds, FEATURE_COLS + ["pchembl_median"])
display(stats_table.round(4))

for col in FEATURE_COLS:
    fig, ax = plt.subplots()
    compounds[col].dropna().hist(bins=20, ax=ax, edgecolor="white", color="#4C72B0")
    ax.set_title(f"{col} — {len(compounds)} compuestos")
    ax.set_xlabel(col)
    plt.tight_layout()
    plt.savefig(FIG_DIR / f"hist_{col}.png", bbox_inches="tight")
    plt.show()
'''
        ),
        md("## 2. Boxplots por familia (n anotado)"),
        code(
            '''family_counts = compounds["family"].value_counts()

for col in FEATURE_COLS + ["pchembl_median"]:
    fig, ax = plt.subplots(figsize=(12, 5))
    order = compounds.groupby("family")[col].median().sort_values().index
    sns.boxplot(data=compounds, x="family", y=col, order=order, ax=ax)
    labels = [f"{f}\\n(n={family_counts[f]})" for f in order]
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.set_title(f"{col} por familia química")
    plt.tight_layout()
    plt.savefig(FIG_DIR / f"box_{col}_by_family.png", bbox_inches="tight")
    plt.show()

print("Advertencia: familias con n<5 compuestos tienen comparaciones poco estables.")
'''
        ),
        md("## 3. Promiscuidad y perfil de dianas"),
        code(
            '''fig, axes = plt.subplots(1, 2, figsize=(12, 4))
compounds["n_targets"].hist(bins=20, ax=axes[0], edgecolor="white")
axes[0].set_title("Distribución n_targets por compuesto")
sns.boxplot(data=compounds, x="family", y="n_targets", ax=axes[1])
axes[1].tick_params(axis="x", rotation=30)
plt.tight_layout()
plt.savefig(FIG_DIR / "promiscuity_distribution.png", bbox_inches="tight")
plt.show()

if "target_type" in activities.columns:
    ct = pd.crosstab(activities["chembl_id"], activities["target_type"])
    top = ct.sum(axis=0).nlargest(15).index
    fig, ax = plt.subplots(figsize=(14, 10))
    sns.heatmap(ct[top], cmap="YlOrRd", ax=ax)
    ax.set_title("Heatmap compuesto × target_type")
    plt.tight_layout()
    plt.savefig(FIG_DIR / "heatmap_compound_target.png", bbox_inches="tight")
    plt.show()
'''
        ),
        md(
            "## 4. Perfil de endpoints\n\n"
            "Hay **13 `standard_type`** distintos (Ki, IC50, EC50, …). Por eso **no** se agrupa "
            "`pchembl_value` crudo como target único de regresión.\n"
        ),
        code(
            '''if "standard_type" in activities.columns:
    display(activities["standard_type"].value_counts().to_frame("n_filas"))

if "standard_relation" in activities.columns:
    print("Relaciones de censura en mediciones:")
    display(activities["standard_relation"].value_counts(dropna=False).to_frame("n"))
'''
        ),
        md("## 5. Correlación honesta (pchembl_median a nivel compuesto)"),
        code(
            '''corr_table = correlation_with_target(compounds, target="pchembl_median", columns=FEATURE_COLS)
display(corr_table.round(4))

corr_matrix = compounds[FEATURE_COLS + ["pchembl_median"]].corr(method="pearson")
mask = np.triu(np.ones_like(corr_matrix, dtype=bool))
fig, ax = plt.subplots(figsize=(10, 8))
sns.heatmap(corr_matrix, mask=mask, annot=True, fmt=".2f", cmap="coolwarm", center=0, ax=ax)
ax.set_title("Correlación Pearson — 107 compuestos")
plt.tight_layout()
plt.savefig(FIG_DIR / "correlation_heatmap.png", bbox_inches="tight")
plt.show()

pair_cols = FEATURE_COLS[:4] + ["pchembl_median"]
g = sns.pairplot(compounds[pair_cols].dropna(), diag_kind="hist", corner=True)
g.fig.suptitle("Scatter matrix — nivel compuesto", y=1.02)
g.savefig(FIG_DIR / "correlation_pairplot.png", bbox_inches="tight")
plt.show()
'''
        ),
        md(
            "---\n"
            "*Anterior:* [`fase2_limpieza.ipynb`](fase2_limpieza.ipynb)  \n"
            "*Siguiente:* [`fase4_modelado.ipynb`](fase4_modelado.ipynb)\n"
        ),
    ]
    path = NB_DIR / "fase3_eda.ipynb"
    path.write_text(json.dumps(nb(cells), indent=1, ensure_ascii=False), encoding="utf-8")
    print("Wrote", path)


def write_fase4() -> None:
    cells = [
        md(
            "# Fase 4 — Análisis multivariado y contraste de hipótesis\n\n"
            "| Campo | Valor |\n|---|---|\n"
            "| **Entrada** | `compounds_features.csv` (107 compuestos) |\n"
            "| **Salidas** | `stats_tests.csv`, `clustering_summary.json`, figuras PCA/clustering |\n"
            "| **Doc** | [`docs/analisis_proyecto/fases/fase4_modelado.md`](../../docs/analisis_proyecto/fases/fase4_modelado.md) |\n\n"
            "## Por qué no hay modelado supervisado aquí\n\n"
            "- `activity_class` es binarización de `pchembl_value >= 6` → **circular**.\n"
            "- `pchembl_value` mezcla 13 endpoints → **no comparable** como target único.\n"
            "- Split por filas = **fuga** (métricas infladas). Split por compuesto → **no generaliza**.\n"
            "- El baseline predictivo honesto está en [`anexo_baseline_predictivo.ipynb`](anexo_baseline_predictivo.ipynb).\n"
        ),
        md("## 0. Configuración"),
        code(
            ROOT_SETUP
            + '''
import json
from scipy.cluster import hierarchy

from src.analisis_proyecto.chembl_multivariate import (
    FEATURE_COLS,
    cluster_vs_family_ari,
    kruskal_by_family,
    posthoc_dunn,
    run_kmeans_silhouette,
    run_pca,
    scale_features,
)

COMPOUNDS_CSV = ROOT / "data" / "processed" / "compounds_features.csv"
assert COMPOUNDS_CSV.exists(), "Ejecuta fase2_limpieza.ipynb primero"
compounds = pd.read_csv(COMPOUNDS_CSV)
print(f"Compuestos: {len(compounds)} | familias: {compounds['family'].nunique()}")
'''
        ),
        md("## 1. PCA (descriptores escalados)"),
        code(
            '''X = scale_features(compounds)
pca = run_pca(X, 2)
ev = pca["explained_variance_ratio"]
print(f"Varianza explicada PC1+PC2: {sum(ev)*100:.1f}%")
display(pd.DataFrame({
    "componente": ["PC1", "PC2"],
    "varianza": ev,
    "loadings": pca["loadings"],
}))

fig, ax = plt.subplots(figsize=(8, 6))
for fam in compounds["family"].unique():
    m = compounds["family"] == fam
    ax.scatter(pca["coords"][m, 0], pca["coords"][m, 1], label=fam, alpha=0.85)
ax.set_xlabel(f"PC1 ({ev[0]*100:.1f}%)")
ax.set_ylabel(f"PC2 ({ev[1]*100:.1f}%)")
ax.set_title("PCA — descriptores moleculares")
ax.legend(bbox_to_anchor=(1.05, 1), fontsize=8)
plt.tight_layout()
plt.savefig(FIG_DIR / "pca_scatter.png", bbox_inches="tight")
plt.show()
'''
        ),
        md("## 2. Clustering"),
        code(
            '''km = run_kmeans_silhouette(X)
print("Silhouette por k:", km["silhouette_by_k"])
print("best_k:", km["best_k"])

fig, ax = plt.subplots()
ax.plot(list(km["silhouette_by_k"].keys()), list(km["silhouette_by_k"].values()), "o-")
ax.set_xlabel("k")
ax.set_ylabel("silhouette")
ax.set_title("Selección de k (K-means)")
plt.tight_layout()
plt.savefig(FIG_DIR / "cluster_silhouette.png", bbox_inches="tight")
plt.show()

Z = hierarchy.linkage(X, method="ward")
fig, ax = plt.subplots(figsize=(12, 5))
hierarchy.dendrogram(Z, ax=ax, truncate_mode="lastp", p=20)
ax.set_title("Clustering jerárquico (Ward)")
plt.tight_layout()
plt.savefig(FIG_DIR / "dendrogram.png", bbox_inches="tight")
plt.show()

labels = km["labels"]
ari = cluster_vs_family_ari(labels, compounds["family"])
print(f"ARI clusters vs family: {ari:.3f}")
compounds["cluster"] = labels
compounds.to_csv(COMPOUNDS_CSV, index=False)
'''
        ),
        md("## 3. Tests Kruskal-Wallis + post-hoc Dunn"),
        code(
            '''test_vars = FEATURE_COLS + ["pchembl_median"]
stats_rows = []
for col in test_vars:
    res = kruskal_by_family(compounds, col)
    stats_rows.append(res)
    if res.get("p") is not None and res["p"] < 0.05:
        print(f"\\nPost-hoc Dunn — {col} (p={res['p']:.4f}):")
        display(posthoc_dunn(compounds, col).round(4))

stats_df = pd.DataFrame(stats_rows)
display(stats_df.round(4))
stats_df.to_csv(RESULTS_DIR / "stats_tests.csv", index=False)

summary = {
    "best_k": km["best_k"],
    "silhouette_by_k": km["silhouette_by_k"],
    "ari_vs_family": ari,
}
(RESULTS_DIR / "clustering_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

fig, axes = plt.subplots(2, 3, figsize=(14, 8))
for i, col in enumerate(test_vars[:6]):
    sns.boxplot(data=compounds, x="family", y=col, ax=axes.flatten()[i])
    axes.flatten()[i].tick_params(axis="x", rotation=45)
    axes.flatten()[i].set_title(col)
plt.tight_layout()
plt.savefig(FIG_DIR / "family_boxplots_annotated.png", bbox_inches="tight")
plt.show()
'''
        ),
        md(
            "---\n"
            "*Anterior:* [`fase3_eda.ipynb`](fase3_eda.ipynb)  \n"
            "*Anexo predictivo:* [`anexo_baseline_predictivo.ipynb`](anexo_baseline_predictivo.ipynb)\n"
        ),
    ]
    path = NB_DIR / "fase4_modelado.ipynb"
    path.write_text(json.dumps(nb(cells), indent=1, ensure_ascii=False), encoding="utf-8")
    print("Wrote", path)


def write_anexo() -> None:
    cells = [
        md(
            "# Anexo — Baseline predictivo honesto (P6)\n\n"
            "> **Este notebook es ADICIONAL** al análisis descriptivo principal (Fases 2–4). "
            "Su fin es demostrar que los descriptores clásicos **no generalizan** cuando el split "
            "respeta la unidad compuesto → puente al proyecto GNN de la JIC.\n\n"
            "**NO** reportar el split por filas como resultado válido.\n"
        ),
        md("## 0. Configuración"),
        code(
            ROOT_SETUP
            + '''
from src.analisis_proyecto.chembl_baseline import (
    honest_baseline_compound_level,
    leaky_baseline_row_level,
)
from src.analisis_proyecto.chembl_preprocessing import load_bioactivity

ACTIVITIES_CSV = ROOT / "data" / "processed" / "activities_clean.csv"
COMPOUNDS_CSV = ROOT / "data" / "processed" / "compounds_features.csv"

activities = load_bioactivity(ACTIVITIES_CSV)
compounds = pd.read_csv(COMPOUNDS_CSV)
'''
        ),
        md("## 1. Comparación split compuesto vs split por filas (fuga)"),
        code(
            '''honest = honest_baseline_compound_level(compounds)
leaky = leaky_baseline_row_level(activities)

metrics = pd.DataFrame([honest, leaky])
display(metrics.round(4))
metrics.to_csv(RESULTS_DIR / "baseline_honest_metrics.csv", index=False)

fig, ax = plt.subplots(figsize=(6, 4))
ax.bar(metrics["split"], metrics["r2_test"], color=["#2ca02c", "#d62728"])
ax.set_ylabel("R² test")
ax.set_title("Baseline RF — split honesto vs fuga")
ax.axhline(0, color="gray", lw=0.8)
plt.tight_layout()
plt.savefig(FIG_DIR / "baseline_honest_vs_leaky.png", bbox_inches="tight")
plt.show()
'''
        ),
        md(
            "## 2. Conclusión\n\n"
            "- **Split por compuesto (honesto):** R² bajo o negativo con 107 compuestos y 8 descriptores.\n"
            "- **Split por filas (fuga):** R² artificialmente alto — la misma molécula aparece en train y test.\n"
            "- Con esta señal limitada, los **grafos moleculares (GNN)** son la vía prometedora "
            "(proyecto JIC hermano).\n"
        ),
    ]
    path = NB_DIR / "anexo_baseline_predictivo.ipynb"
    path.write_text(json.dumps(nb(cells), indent=1, ensure_ascii=False), encoding="utf-8")
    print("Wrote", path)


def main() -> None:
    write_fase2()
    write_fase3()
    write_fase4()
    write_anexo()


if __name__ == "__main__":
    main()
