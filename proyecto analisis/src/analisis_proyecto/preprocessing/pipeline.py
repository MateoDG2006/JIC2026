"""
Preprocesamiento y utilidades EDA para el dataset ChEMBL panameño (Flujo B).

Pipeline típico:
    df = load_bioactivity(csv)                       # parseo + dtypes
    df, dup = filter_potential_duplicates(df)        # quita duplicados marcados
    df_clean, rep = drop_columns_high_nan(df)        # umbral 250 NaN
    df_clean = impute_median_by_family(df_clean)     # mediana por familia
    X, y, groups = build_supervised_matrix(df_clean, target_col="activity_class")
    X_tr, X_te, y_tr, y_te = train_test_split_by_group(X, y, groups)  # split honesto

Constantes importantes:
    FEATURE_COLS              — 8 descriptores RDKit usados para modelar
    NUMERIC_DESCRIPTOR_COLS   — FEATURE_COLS + pchembl_value + standard_value (EDA)
    CATEGORICAL_COLS          — variables categóricas (family, target_type, etc.)
    ASSAY_FEATURE_COLS        — columnas de contexto de ensayo (one-hot opcional)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from src.analisis_proyecto.core.constants import (
    assay_feature_columns,
    binding_types,
    categorical_columns,
    feature_columns,
    id_and_text_columns,
    min_potency_activities,
    numeric_coerce_columns,
    numeric_descriptor_columns,
    organism_types,
    reliability_tier,
)
from src.analisis_proyecto.acquisition.common import mark_is_censored

# Ver ``config/chembl/columns.json`` para editar estas listas.
FEATURE_COLS: list[str] = feature_columns()
NUMERIC_DESCRIPTOR_COLS: list[str] = numeric_descriptor_columns()
ID_AND_TEXT_COLS = id_and_text_columns()
CATEGORICAL_COLS = categorical_columns()
ASSAY_FEATURE_COLS = assay_feature_columns()

PROTECTED_ACTIVITY_COLS = frozenset({
    "chembl_id",
    "compound_name",
    "family",
    "smiles",
    "standard_relation",
    "standard_type",
    "pchembl_value",
    "is_censored",
    "activity_class",
    "standard_value",
    "standard_units",
    "target_chembl_id",
    "assay_type",
    "pchembl_imputed",
})


def load_bioactivity(path: str | Path) -> pd.DataFrame:
    """Carga CSV de bioactividad y normaliza dtypes numéricos."""
    df = pd.read_csv(path)
    for col in NUMERIC_DESCRIPTOR_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in numeric_coerce_columns():
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "pubchem_cid" in df.columns:
        df["pubchem_cid"] = pd.to_numeric(df["pubchem_cid"], errors="coerce")
    return df


def numeric_and_categorical_cols(
    df: pd.DataFrame,
) -> tuple[list[str], list[str]]:
    """Devuelve listas de columnas numéricas y categóricas presentes en df."""
    numeric = [
        c
        for c in df.columns
        if c not in ID_AND_TEXT_COLS
        and pd.api.types.is_numeric_dtype(df[c])
    ]
    categorical = [c for c in CATEGORICAL_COLS if c in df.columns]
    return numeric, categorical


def summary_statistics(df: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    """
    Media, mediana, moda y desviación estándar por columna numérica.

    La moda usa el valor más frecuente (redondeo a 4 decimales en continuas).
    """
    cols = columns or [c for c in NUMERIC_DESCRIPTOR_COLS if c in df.columns]
    rows: list[dict[str, Any]] = []
    for col in cols:
        series = pd.to_numeric(df[col], errors="coerce").dropna()
        if series.empty:
            continue
        rounded = series.round(4)
        mode_vals = rounded.mode()
        mode_val = mode_vals.iloc[0] if not mode_vals.empty else np.nan
        rows.append(
            {
                "columna": col,
                "media": series.mean(),
                "mediana": series.median(),
                "moda": mode_val,
                "desv_std": series.std(),
                "n": int(series.count()),
            }
        )
    return pd.DataFrame(rows)


def columns_with_missing(df: pd.DataFrame) -> list[str]:
    """Columnas con al menos un NaN."""
    return df.columns[df.isna().any()].tolist()


def missingness_upset_series(
    df: pd.DataFrame,
    columns: list[str] | None = None,
) -> tuple[pd.Series | None, list[str]]:
    """
    Serie para UpSetPlot: un registro por fila con el mismo patrón de NaN.

    Usar con ``UpSet(..., subset_size=\"count\")`` — el índice no es único.
    """
    from upsetplot import from_indicators

    cols = columns if columns is not None else columns_with_missing(df)
    if not cols:
        return None, []
    return from_indicators(df[cols].isna()), cols


def plot_missingno_report(
    df: pd.DataFrame,
    fig_dir: str | Path,
    *,
    columns: list[str] | None = None,
    dpi: int = 120,
) -> list[Path]:
    """
    Genera matrix, bar y heatmap de missingno; guarda PNG y cierra cada figura.

    Si hay columnas con NaN, solo se grafican esas (más legible en tablas anchas).
    """
    import matplotlib.pyplot as plt
    import missingno as msno

    out_dir = Path(fig_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    nan_cols = columns if columns is not None else columns_with_missing(df)
    if not nan_cols:
        return []

    work = df[nan_cols]
    saved: list[Path] = []

    specs: list[tuple[str, Any, dict[str, Any]]] = [
        ("missingno_matrix.png", msno.matrix, {"figsize": (12, 6), "sparkline": False}),
        ("missingno_bar.png", msno.bar, {"figsize": (10, 5)}),
    ]
    if len(nan_cols) >= 2:
        specs.append(("missingno_heatmap.png", msno.heatmap, {"figsize": (10, 8)}))

    for filename, plot_fn, kwargs in specs:
        plot_fn(work, **kwargs)
        path = out_dir / filename
        plt.tight_layout()
        plt.savefig(path, bbox_inches="tight", dpi=dpi)
        plt.close()
        saved.append(path)

    return saved


def drop_columns_high_nan(
    df: pd.DataFrame,
    threshold: int = 250,
    *,
    never_drop: frozenset[str] | set[str] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Elimina columnas con más de `threshold` valores NaN.

    Returns:
        (df_reduced, report_df)
    """
    n = len(df)
    nan_counts = df.isna().sum()
    report_rows: list[dict[str, Any]] = []
    drop_cols: list[str] = []
    protected = never_drop or frozenset()

    for col in df.columns:
        n_nan = int(nan_counts[col])
        pct = round(100 * n_nan / n, 2) if n else 0.0
        if col in protected:
            decision = "conservar (protegida)"
        else:
            decision = "eliminar" if n_nan > threshold else "conservar"
        if decision == "eliminar":
            drop_cols.append(col)
        report_rows.append(
            {
                "columna": col,
                "n_nan": n_nan,
                "pct_nan": pct,
                "decision": decision,
            }
        )

    report = pd.DataFrame(report_rows).sort_values("n_nan", ascending=False)
    reduced = df.drop(columns=drop_cols, errors="ignore").copy()
    return reduced, report


def impute_median_by_family(
    df: pd.DataFrame,
    numeric_cols: list[str] | None = None,
    group_col: str = "family",
    categorical_cols: list[str] | None = None,
) -> pd.DataFrame:
    """
    Imputa numéricas con mediana por familia; fallback mediana global.

    Categóricas: moda global o 'Unknown' si no hay moda.
    """
    out = df.copy()
    num_cols = numeric_cols or [
        c for c in out.columns if pd.api.types.is_numeric_dtype(out[c])
    ]
    cat_cols = categorical_cols or [
        c for c in CATEGORICAL_COLS if c in out.columns and c != group_col
    ]

    for col in num_cols:
        if col not in out.columns:
            continue
        global_median = out[col].median()

        def _fill_group(s: pd.Series, fallback: float = global_median) -> pd.Series:
            med = s.median()
            return s.fillna(med if not np.isnan(med) else fallback)

        out[col] = out.groupby(group_col)[col].transform(_fill_group)
        out[col] = out[col].fillna(global_median)

    for col in cat_cols:
        if col not in out.columns:
            continue
        mode_vals = out[col].dropna().mode()
        fill_val = mode_vals.iloc[0] if not mode_vals.empty else "Unknown"
        out[col] = out[col].fillna(fill_val)

    return out


def get_available_feature_cols(df: pd.DataFrame) -> list[str]:
    """Features de modelado presentes en el dataframe."""
    return [c for c in FEATURE_COLS if c in df.columns]


def train_test_split_rows(
    X: pd.DataFrame,
    y: pd.Series,
    *,
    test_size: float = 0.2,
    random_state: int = 42,
    stratify: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Split aleatorio por filas; stratify si hay suficientes muestras por clase."""
    stratify_arg = None
    if stratify and y.dtype == object:
        counts = y.value_counts()
        if len(counts) >= 2 and counts.min() >= 2:
            stratify_arg = y

    return train_test_split(
        X,
        y,
        test_size=test_size,
        random_state=random_state,
        stratify=stratify_arg,
    )


def encode_assay_features(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    *,
    top_n: int = 15,
) -> pd.DataFrame:
    """One-hot de columnas de ensayo; categorías fuera del top-N → ``Other``."""
    cols = columns or [c for c in ASSAY_FEATURE_COLS if c in df.columns]
    if not cols:
        return pd.DataFrame(index=df.index)

    parts: list[pd.DataFrame] = []
    for col in cols:
        series = df[col].fillna("Unknown").astype(str).str.strip()
        series = series.replace("", "Unknown")
        top = set(series.value_counts().head(top_n).index)
        series = series.where(series.isin(top), "Other")
        parts.append(pd.get_dummies(series, prefix=col, dtype=float))
    return pd.concat(parts, axis=1)


def build_supervised_matrix(
    df: pd.DataFrame,
    *,
    target_col: str,
    numeric_cols: list[str] | None = None,
    include_assay_features: bool = False,
    assay_top_n: int = 15,
    group_col: str = "compound_name",
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    Matriz X, objetivo y y grupos (compuesto) listos para modelado.

    ``include_assay_features=True`` añade one-hot de tipo de ensayo/diana/organismo.
    """
    num_cols = numeric_cols or get_available_feature_cols(df)
    missing = [c for c in num_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas numéricas: {missing}")

    X = df[num_cols].copy()
    if include_assay_features:
        X = pd.concat([X, encode_assay_features(df, top_n=assay_top_n)], axis=1)

    if target_col not in df.columns:
        raise ValueError(f"Columna objetivo ausente: {target_col}")

    y = df[target_col].copy()
    groups = df[group_col].copy()

    valid = y.notna() & X.notna().all(axis=1)
    if target_col == "activity_class":
        valid &= y.isin(["Active", "Inactive"])

    return X.loc[valid], y.loc[valid], groups.loc[valid]


def train_test_split_by_group(
    X: pd.DataFrame,
    y: pd.Series,
    groups: pd.Series,
    *,
    test_size: float = 0.2,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Split por grupo (p. ej. compuesto) — evalúa generalización a moléculas nuevas."""
    from sklearn.model_selection import GroupShuffleSplit

    gss = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
    train_idx, test_idx = next(gss.split(X, y, groups))
    return (
        X.iloc[train_idx],
        X.iloc[test_idx],
        y.iloc[train_idx],
        y.iloc[test_idx],
    )


def correlation_with_target(
    df: pd.DataFrame,
    target: str = "pchembl_value",
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """Pearson y Spearman de columnas vs variable objetivo."""
    cols = columns or [c for c in NUMERIC_DESCRIPTOR_COLS if c in df.columns and c != target]
    rows = []
    target_series = pd.to_numeric(df[target], errors="coerce")
    for col in cols:
        s = pd.to_numeric(df[col], errors="coerce")
        valid = target_series.notna() & s.notna()
        if valid.sum() < 3:
            continue
        rows.append(
            {
                "variable": col,
                "pearson": target_series[valid].corr(s[valid], method="pearson"),
                "spearman": target_series[valid].corr(s[valid], method="spearman"),
                "n": int(valid.sum()),
            }
        )
    result = pd.DataFrame(rows)
    if not result.empty:
        result = result.sort_values("spearman", key=abs, ascending=False)
    return result


def _descriptor_cols(df: pd.DataFrame) -> list[str]:
    cols = list(feature_columns()) + ["heavy_atoms"]
    return [c for c in cols if c in df.columns]


def _ensure_censored_flag(df: pd.DataFrame) -> pd.DataFrame:
    if "is_censored" in df.columns:
        return df.copy()
    return mark_is_censored(df)


def quantitative_binding_activities(activities_df: pd.DataFrame) -> pd.DataFrame:
    """Filas no censuradas con pChEMBL y endpoint de afinidad de unión (BINDING_TYPES)."""
    df = _ensure_censored_flag(activities_df)
    binding = binding_types()
    st = df["standard_type"].astype(str)
    mask = ~df["is_censored"] & df["pchembl_value"].notna() & st.isin(binding)
    return df.loc[mask].copy()


def censoring_report(activities_df: pd.DataFrame) -> dict[str, Any]:
    """Recuento de censura y filas excluidas del agregado de potencia."""
    df = _ensure_censored_flag(activities_df)
    n_total = len(df)
    n_censored = int(df["is_censored"].sum())
    rel_counts = (
        df["standard_relation"].fillna("NaN").astype(str).value_counts().astype(int).to_dict()
    )
    n_potency = int((~df["is_censored"] & df["pchembl_value"].notna()).sum())
    return {
        "n_total": n_total,
        "n_censored": n_censored,
        "pct_censored": round(100 * n_censored / n_total, 2) if n_total else 0.0,
        "by_standard_relation": rel_counts,
        "n_used_for_potency_aggregation": n_potency,
        "pct_excluded_from_potency": round(100 * n_censored / n_total, 2) if n_total else 0.0,
        "note": (
            "Censurados se conservan en activities_clean; "
            "se excluyen solo de pchembl_median_binding y pct_active."
        ),
    }


def build_compounds_all(activities_df: pd.DataFrame) -> pd.DataFrame:
    """Corpus estructural: todos los compuestos con descriptores (~147), con o sin potencia."""
    df = _ensure_censored_flag(activities_df)
    desc_cols = _descriptor_cols(df)
    g = df.groupby("chembl_id", dropna=False)
    out = g.agg(
        compound_name=("compound_name", "first"),
        family=("family", "first"),
        smiles=("smiles", "first"),
        n_activities_total=("chembl_id", "size"),
        n_censored=("is_censored", "sum"),
    ).join(g[desc_cols].first()).reset_index()
    out["n_censored"] = out["n_censored"].astype(int)
    return out


def _endpoint_flags_by_compound(activities_df: pd.DataFrame) -> pd.DataFrame:
    """Marca compuestos que mezclan endpoints de unión y organismo."""
    df = _ensure_censored_flag(activities_df)
    quant = df.loc[~df["is_censored"] & df["pchembl_value"].notna()]
    binding = binding_types()
    organism = organism_types()
    rows: list[dict[str, Any]] = []
    for chembl_id, group in quant.groupby("chembl_id", dropna=False):
        types = set(group["standard_type"].astype(str))
        has_binding = bool(types & binding)
        has_organism = bool(types & organism)
        rows.append({
            "chembl_id": chembl_id,
            "mixed_endpoint_class": has_binding and has_organism,
            "endpoint_types_seen": "|".join(sorted(types)),
        })
    return pd.DataFrame(rows)


def build_compound_features(
    activities_df: pd.DataFrame,
    *,
    min_binding_n: int | None = None,
) -> pd.DataFrame:
    """
    Agrega potencia a nivel compuesto (subconjunto con soporte mínimo).

    Target: pchembl_median_binding — solo BINDING_TYPES, filas no censuradas.
    """
    min_n = min_binding_n if min_binding_n is not None else min_potency_activities()
    df = _ensure_censored_flag(activities_df)
    qbind = quantitative_binding_activities(df)
    endpoint_flags = _endpoint_flags_by_compound(df)

    if qbind.empty:
        base = build_compounds_all(df)
        return base.iloc[0:0].copy()

    def _iqr(series: pd.Series) -> float:
        return float(series.quantile(0.75) - series.quantile(0.25))

    potency = qbind.groupby("chembl_id", dropna=False).agg(
        pchembl_median_binding=("pchembl_value", "median"),
        pchembl_std_binding=("pchembl_value", "std"),
        pchembl_iqr_binding=("pchembl_value", _iqr),
        n_activities_binding=("pchembl_value", "count"),
    ).reset_index()
    potency["pchembl_std_binding"] = potency["pchembl_std_binding"].fillna(0.0)
    potency["target_inestable"] = potency["pchembl_std_binding"] > 1.0
    potency["reliability_tier"] = potency["n_activities_binding"].apply(reliability_tier)

    low_support = potency["n_activities_binding"] < min_n
    potency.loc[low_support, "pchembl_median_binding"] = np.nan
    potency.loc[low_support, "reliability_tier"] = "bajo"

    if "activity_class" in qbind.columns:
        pct = qbind.groupby("chembl_id")["activity_class"].apply(
            lambda s: float((s == "Active").mean())
        )
        potency = potency.merge(
            pct.rename("pct_active").reset_index(), on="chembl_id", how="left"
        )
        potency["pct_active_note"] = "derivado de pchembl >= 6 (no independiente)"

    potency = potency.merge(endpoint_flags, on="chembl_id", how="left")
    potency["mixed_endpoint_class"] = potency["mixed_endpoint_class"].fillna(False)

    base = build_compounds_all(df)
    out = base.merge(potency, on="chembl_id", how="inner")
    out["has_quantitative_potency"] = out["pchembl_median_binding"].notna()
    return out.loc[out["has_quantitative_potency"]].reset_index(drop=True)


def build_corpus_funnel(
    activities_df: pd.DataFrame,
    compounds_all: pd.DataFrame,
    compounds_potency: pd.DataFrame,
) -> dict[str, Any]:
    """Embudo 147→107: sesgo de selección hacia compuestos con potencia cuantitativa."""
    df = _ensure_censored_flag(activities_df)
    raw_n = int(df["chembl_id"].nunique())
    with_eq = int(
        df.loc[~df["is_censored"] & df["pchembl_value"].notna(), "chembl_id"].nunique()
    )
    potency_n = len(compounds_potency)
    potency_ids = set(compounds_potency["chembl_id"])
    dropped_ids = set(compounds_all["chembl_id"]) - potency_ids
    dropped_by_family = (
        compounds_all.loc[compounds_all["chembl_id"].isin(dropped_ids)]
        .groupby("family")
        .size()
        .astype(int)
        .to_dict()
    )
    mixed_n = int(compounds_potency.get("mixed_endpoint_class", pd.Series(dtype=bool)).sum())
    return {
        "raw_compounds": raw_n,
        "with_eq_pchembl": with_eq,
        "with_potency_binding_min_support": potency_n,
        "dropped_no_quantitative": raw_n - potency_n,
        "dropped_by_family": dropped_by_family,
        "n_mixed_endpoint_class": mixed_n,
        "selection_bias_note": (
            "El subconjunto con potencia excluye compuestos solo-censurados/inactivos "
            "→ potencia sesgada al alza."
        ),
    }


def filter_potential_duplicates(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Elimina registros marcados como duplicados potenciales en ChEMBL (P10).

    Conserva la columna ``potential_duplicate`` en el reporte pero la excluye
    del dataframe limpio si todos los duplicados fueron removidos.
    """
    if "potential_duplicate" not in df.columns:
        return df.copy(), pd.DataFrame(columns=["accion", "filas_eliminadas"])

    dup_mask = df["potential_duplicate"].fillna(0).astype(int) == 1
    n_dup = int(dup_mask.sum())
    cleaned = df.loc[~dup_mask].copy()
    report = pd.DataFrame([{
        "accion": "eliminar_potential_duplicate",
        "filas_eliminadas": n_dup,
        "filas_restantes": len(cleaned),
    }])
    return cleaned, report


def pchembl_imputation_report(df: pd.DataFrame) -> dict[str, float | int]:
    """Estadísticas de valores pChEMBL imputados vs. originales (m4)."""
    if "pchembl_imputed" not in df.columns:
        return {"n_total": len(df), "n_imputed": 0, "pct_imputed": 0.0}

    imputed = df["pchembl_imputed"].fillna(False).astype(bool)
    n_imputed = int(imputed.sum())
    n_total = len(df)
    return {
        "n_total": n_total,
        "n_imputed": n_imputed,
        "n_original": n_total - n_imputed,
        "pct_imputed": round(100 * n_imputed / n_total, 2) if n_total else 0.0,
    }


class ChemblPreprocessor:
    """Pipeline de limpieza Fase 2 — encapsula dedup, NaN e imputación."""

    def __init__(self, nan_threshold: int = 250) -> None:
        self.nan_threshold = nan_threshold

    def clean_activities(self, df: pd.DataFrame) -> pd.DataFrame:
        df, dup_report = filter_potential_duplicates(df)
        if not dup_report.empty:
            print(f"  Duplicados eliminados: {dup_report.iloc[0]['filas_eliminadas']}")
        df = mark_is_censored(df)
        df, _ = drop_columns_high_nan(
            df, threshold=self.nan_threshold, never_drop=PROTECTED_ACTIVITY_COLS
        )
        num_cols, cat_cols = numeric_and_categorical_cols(df)
        if "is_censored" in num_cols:
            num_cols.remove("is_censored")
        return impute_median_by_family(df, numeric_cols=num_cols, categorical_cols=cat_cols)

    def build_compounds_all(self, activities: pd.DataFrame) -> pd.DataFrame:
        return build_compounds_all(activities)

    def build_compound_features(self, activities: pd.DataFrame) -> pd.DataFrame:
        return build_compound_features(activities)

    def censoring_report(self, activities: pd.DataFrame) -> dict[str, Any]:
        return censoring_report(activities)

    def corpus_funnel(
        self,
        activities: pd.DataFrame,
        compounds_all: pd.DataFrame,
        compounds_potency: pd.DataFrame,
    ) -> dict[str, Any]:
        return build_corpus_funnel(activities, compounds_all, compounds_potency)

    def imputation_report(self, df: pd.DataFrame) -> dict[str, float | int]:
        return pchembl_imputation_report(df)
