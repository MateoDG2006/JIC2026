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
    categorical_columns,
    feature_columns,
    id_and_text_columns,
    numeric_coerce_columns,
    numeric_descriptor_columns,
)

# Ver ``config/chembl/columns.json`` para editar estas listas.
FEATURE_COLS: list[str] = feature_columns()
NUMERIC_DESCRIPTOR_COLS: list[str] = numeric_descriptor_columns()
ID_AND_TEXT_COLS = id_and_text_columns()
CATEGORICAL_COLS = categorical_columns()
ASSAY_FEATURE_COLS = assay_feature_columns()


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

    for col in df.columns:
        n_nan = int(nan_counts[col])
        pct = round(100 * n_nan / n, 2) if n else 0.0
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


def build_compound_features(activities_df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega el dataset a nivel COMPUESTO (una fila por chembl_id).

    Los descriptores son constantes dentro de cada compuesto, así que se toma el primer valor.
    Los agregados de bioactividad resumen todas las mediciones del compuesto.
    """
    df = activities_df.copy()

    descriptor_cols = list(feature_columns()) + ["heavy_atoms"]
    descriptor_cols = [c for c in descriptor_cols if c in df.columns]

    g = df.groupby("chembl_id", dropna=False)

    rows = g.agg(
        compound_name=("compound_name", "first"),
        family=("family", "first"),
        smiles=("smiles", "first"),
        pchembl_median=("pchembl_value", "median"),
        pchembl_std=("pchembl_value", "std"),
        n_activities=("pchembl_value", "size"),
        n_targets=("target_chembl_id", "nunique"),
        n_assay_types=("assay_type", "nunique"),
        n_standard_types=("standard_type", "nunique"),
    )

    desc = g[descriptor_cols].first()

    if "activity_class" in df.columns:
        pct = g["activity_class"].apply(lambda s: (s == "Active").mean())
        rows["pct_active"] = pct

    out = rows.join(desc).reset_index()
    out["pchembl_std"] = out["pchembl_std"].fillna(0.0)
    return out


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
        df, _ = drop_columns_high_nan(df, threshold=self.nan_threshold)
        num_cols, cat_cols = numeric_and_categorical_cols(df)
        return impute_median_by_family(df, numeric_cols=num_cols, categorical_cols=cat_cols)

    def build_compound_features(self, activities: pd.DataFrame) -> pd.DataFrame:
        return build_compound_features(activities)

    def imputation_report(self, df: pd.DataFrame) -> dict[str, float | int]:
        return pchembl_imputation_report(df)
