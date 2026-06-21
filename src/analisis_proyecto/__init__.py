"""Pipeline de análisis ChEMBL para la parte de "analítica de datos" del curso (Flujo B).

Este módulo es paralelo al pipeline GIN: usa el corpus PubChem panameño
extendido con datos de bioactividad ChEMBL (pChEMBL, descriptores RDKit)
para entrenar modelos clásicos (RF, SVM, SVR) en lugar de la GNN.

Submódulos:
    chembl_preprocessing — EDA, missingno, imputación, splits, evaluación
    chembl_extract       — orquestador de extracción ChEMBL (SQLite o API)
    chembl_local         — backend SQLite con descarga del dump oficial
    chembl_api           — backend REST (fallback si no hay dump local)
    geodata_panama       — geoBoundaries + estimaciones MAPI por distrito
"""

from src.analisis_proyecto.chembl_preprocessing import (
    FEATURE_COLS,
    NUMERIC_DESCRIPTOR_COLS,
    columns_with_missing,
    drop_columns_high_nan,
    filter_potential_duplicates,
    get_available_feature_cols,
    get_feature_matrix,
    impute_median_by_family,
    load_bioactivity,
    missingness_upset_series,
    pchembl_imputation_report,
    plot_missingno_report,
    numeric_and_categorical_cols,
    summary_statistics,
    train_test_split_by_group,
    train_test_split_rows,
)

__all__ = [
    "FEATURE_COLS",
    "NUMERIC_DESCRIPTOR_COLS",
    "columns_with_missing",
    "drop_columns_high_nan",
    "filter_potential_duplicates",
    "get_available_feature_cols",
    "get_feature_matrix",
    "impute_median_by_family",
    "load_bioactivity",
    "missingness_upset_series",
    "pchembl_imputation_report",
    "plot_missingno_report",
    "numeric_and_categorical_cols",
    "summary_statistics",
    "train_test_split_by_group",
    "train_test_split_rows",
]
