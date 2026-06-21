#!/usr/bin/env python
"""Verificación end-to-end del pipeline Flujo B (ChEMBL clásico).

Pertenece a la **Fase 4 — Modelado predictivo** del proyecto de analítica de
datos (tarea de ML Engineer "Verificar reproducibilidad" en
``docs/analisis_proyecto/fases/fase4_modelado.md``).

Reproduce el pipeline de "analítica de datos" del curso de principio a fin
(integra Fases 2, 3 y 4 sobre el dataset ChEMBL):

    1. ``load_bioactivity`` del CSV raw de ChEMBL.
    2. Filtrado de potential_duplicates (AUDIT P10).
    3. ``drop_columns_high_nan`` (umbral 250 NaN) + reporte missingness.
    4. ``impute_median_by_family`` para descriptores numéricos.
    5. ``build_supervised_matrix`` para clasificación y regresión.
    6. ``train_test_split_by_group`` (compuesto) — split honesto sin leakage.
    7. Entrena RF (clasificación), SVM (clasificación), RF-Reg y SVR.
    8. Evalúa con ``evaluate_classification`` / ``evaluate_regression``.
    9. Guarda modelos en ``outputs/chembl/models/`` y métricas en CSV.

Sirve como test de integración + script de generación de artefactos para
el visor (``viz/services/dashboard/chembl.py`` carga ``rf_regressor.pkl``).

Uso:
    python scripts/analisis_proyecto/fase4/verify_flow_b.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC, SVR

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.analisis_proyecto.chembl_preprocessing import (  # noqa: E402
    build_supervised_matrix,
    drop_columns_high_nan,
    evaluate_classification,
    evaluate_regression,
    filter_potential_duplicates,
    get_available_feature_cols,
    impute_median_by_family,
    load_bioactivity,
    numeric_and_categorical_cols,
    pchembl_imputation_report,
    train_test_split_by_group,
    train_test_split_rows,
)
RAW_CSV = ROOT / "data" / "raw" / "chembl_panama_bioactivity.csv"
CLEAN_CSV = ROOT / "data" / "processed" / "chembl_clean.csv"
MODEL_DIR = ROOT / "outputs" / "chembl" / "models"
METRICS_CSV = ROOT / "outputs" / "chembl" / "results" / "metrics_summary.csv"
IMPUTATION_JSON = ROOT / "outputs" / "chembl" / "results" / "pchembl_imputation.json"
RANDOM_STATE = 42

BIOACTIVITY_COLUMNS = [
    "compound_name", "pubchem_cid", "chembl_id", "smiles", "family", "match_method",
    "activity_id", "assay_chembl_id", "target_chembl_id", "target_name", "target_type",
    "organism", "standard_type", "standard_value", "standard_units", "standard_relation",
    "pchembl_value", "pchembl_imputed", "activity_class", "activity_comment",
    "data_validity_comment", "potential_duplicate", "assay_type", "bao_label",
    "mw_freebase", "alogp", "psa", "hba", "hbd", "num_ro5_violations",
    "aromatic_rings", "heavy_atoms", "rtb", "molecular_species", "cx_logp", "cx_logd",
]


def _synthetic_bioactivity(n: int = 400) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    families = ["Organophosphates", "Triazines", "Herbicides", "Pyrethroids"]
    compounds = [f"Compound_{i % 8}" for i in range(n)]
    rows = []
    for i in range(n):
        fam = families[i % len(families)]
        mw = rng.uniform(200, 500)
        alogp = rng.uniform(-1, 5)
        pchembl = rng.uniform(4, 10)
        rows.append({
            "compound_name": compounds[i],
            "pubchem_cid": 1000 + i % 8,
            "chembl_id": f"CHEMBL{i % 8}",
            "smiles": "CCO",
            "family": fam,
            "match_method": "smiles",
            "activity_id": i,
            "assay_chembl_id": f"CHEMBL_ASSAY_{i % 20}",
            "target_chembl_id": f"CHEMBL_TARGET_{i % 30}",
            "target_name": "Target",
            "target_type": "SINGLE PROTEIN",
            "organism": "Homo sapiens",
            "standard_type": rng.choice(["IC50", "EC50", "Ki"]),
            "standard_value": 10 ** (6 - pchembl),
            "standard_units": "nM",
            "standard_relation": "=",
            "pchembl_value": pchembl,
            "pchembl_imputed": int(i % 17 == 0),
            "activity_class": "Active" if pchembl >= 6 else "Inactive",
            "activity_comment": np.nan,
            "data_validity_comment": np.nan,
            "potential_duplicate": int(i % 25 == 0),
            "assay_type": "B",
            "bao_label": "cell-based",
            "mw_freebase": mw,
            "alogp": alogp,
            "psa": rng.uniform(20, 120),
            "hba": int(rng.integers(1, 8)),
            "hbd": int(rng.integers(0, 4)),
            "num_ro5_violations": int(rng.integers(0, 2)),
            "aromatic_rings": int(rng.integers(0, 4)),
            "heavy_atoms": int(rng.uniform(15, 40)),
            "rtb": int(rng.integers(0, 10)),
            "molecular_species": "NEUTRAL",
            "cx_logp": np.nan,
            "cx_logd": np.nan,
        })
    return pd.DataFrame(rows).reindex(columns=BIOACTIVITY_COLUMNS)


def run_pipeline(df: pd.DataFrame) -> None:
    df, dup_report = filter_potential_duplicates(df)
    if not dup_report.empty:
        print(f"  Duplicados potenciales eliminados: {dup_report.iloc[0]['filas_eliminadas']}")

    df_dropped, _ = drop_columns_high_nan(df, threshold=250)
    num_cols, cat_cols = numeric_and_categorical_cols(df_dropped)
    df_clean = impute_median_by_family(df_dropped, numeric_cols=num_cols, categorical_cols=cat_cols)

    CLEAN_CSV.parent.mkdir(parents=True, exist_ok=True)
    df_clean.to_csv(CLEAN_CSV, index=False)

    imputation_stats = pchembl_imputation_report(df_clean)
    IMPUTATION_JSON.parent.mkdir(parents=True, exist_ok=True)
    IMPUTATION_JSON.write_text(json.dumps(imputation_stats, indent=2), encoding="utf-8")
    print(f"  pChEMBL imputados: {imputation_stats['pct_imputed']}% ({imputation_stats['n_imputed']}/{imputation_stats['n_total']})")

    feature_cols = get_available_feature_cols(df_clean)
    metrics_rows: list[dict] = []

    # Clasificación
    X_cls, y_cls, groups_cls = build_supervised_matrix(
        df_clean, target_col="activity_class", numeric_cols=feature_cols, include_assay_features=False
    )
    for split_name, split_fn in [("filas", train_test_split_rows), ("compuesto", train_test_split_by_group)]:
        if split_name == "compuesto":
            X_tr, X_te, y_tr, y_te = split_fn(X_cls, y_cls, groups_cls, random_state=RANDOM_STATE)
        else:
            X_tr, X_te, y_tr, y_te = split_fn(X_cls, y_cls, random_state=RANDOM_STATE)

        rf_cls = RandomForestClassifier(n_estimators=100, random_state=RANDOM_STATE, class_weight="balanced")
        rf_cls.fit(X_tr, y_tr)
        scores = evaluate_classification(rf_cls, X_tr, X_te, y_tr, y_te)
        metrics_rows.append({
            "modelo": "RandomForest",
            "tarea": "clasificacion",
            "split": split_name,
            "feature_set": "descriptores",
            "accuracy_test": scores["accuracy_test"],
            "auc_test": scores.get("auc_test", np.nan),
            "r2_test": np.nan,
        })
        print(f"  Clasificación RF ({split_name}) accuracy: {scores['accuracy_test']:.4f}")

    X_tr, X_te, y_tr, y_te = train_test_split_rows(X_cls, y_cls, random_state=RANDOM_STATE)
    rf_cls = RandomForestClassifier(n_estimators=100, random_state=RANDOM_STATE, class_weight="balanced")
    rf_cls.fit(X_tr, y_tr)
    svm_cls = Pipeline([("scaler", StandardScaler()), ("svm", SVC(probability=True, random_state=RANDOM_STATE))])
    svm_cls.fit(X_tr, y_tr)

    # Regresión
    reg_configs = [
        (False, "filas"),
        (False, "compuesto"),
        (True, "filas"),
        (True, "compuesto"),
    ]
    rf_reg_final = None
    svr_final = None
    for include_assay, split_by in reg_configs:
        X, y, groups = build_supervised_matrix(
            df_clean,
            target_col="pchembl_value",
            numeric_cols=feature_cols,
            include_assay_features=include_assay,
        )
        if split_by == "compuesto":
            Xtr, Xte, ytr, yte = train_test_split_by_group(X, y, groups, random_state=RANDOM_STATE)
        else:
            Xtr, Xte, ytr, yte = train_test_split_rows(X, y, stratify=False, random_state=RANDOM_STATE)

        rf_reg = RandomForestRegressor(n_estimators=100, random_state=RANDOM_STATE)
        rf_reg.fit(Xtr, ytr)
        rf_scores = evaluate_regression(rf_reg, Xtr, Xte, ytr, yte)
        metrics_rows.append({
            "modelo": "RandomForest",
            "tarea": "regresion",
            "split": split_by,
            "feature_set": "descriptores+ensayo" if include_assay else "descriptores",
            "accuracy_test": np.nan,
            "auc_test": np.nan,
            "r2_test": rf_scores["r2_test"],
        })

        svr = Pipeline([("scaler", StandardScaler()), ("svr", SVR())])
        svr.fit(Xtr, ytr)
        svr_scores = evaluate_regression(svr, Xtr, Xte, ytr, yte)
        metrics_rows.append({
            "modelo": "SVR_RBF",
            "tarea": "regresion",
            "split": split_by,
            "feature_set": "descriptores+ensayo" if include_assay else "descriptores",
            "accuracy_test": np.nan,
            "auc_test": np.nan,
            "r2_test": svr_scores["r2_test"],
        })
        feat = "desc+ensayo" if include_assay else "descriptores"
        print(f"  Regresión RF ({feat}, {split_by}) R² test: {rf_scores['r2_test']:.4f}")

        if include_assay and split_by == "filas":
            rf_reg_final = rf_reg
            svr_final = svr

    METRICS_CSV.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(metrics_rows).to_csv(METRICS_CSV, index=False)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(rf_cls, MODEL_DIR / "rf_classifier.pkl")
    joblib.dump(svm_cls, MODEL_DIR / "svm_classifier.pkl")
    if rf_reg_final is not None:
        joblib.dump(rf_reg_final, MODEL_DIR / "rf_regressor.pkl")
    if svr_final is not None:
        joblib.dump(svr_final, MODEL_DIR / "svr_regressor.pkl")

    with open(MODEL_DIR / "feature_cols.json", "w", encoding="utf-8") as f:
        json.dump(feature_cols, f)

    X_full, _, _ = build_supervised_matrix(
        df_clean,
        target_col="pchembl_value",
        numeric_cols=feature_cols,
        include_assay_features=True,
    )
    with open(MODEL_DIR / "regression_feature_cols.json", "w", encoding="utf-8") as f:
        json.dump(list(X_full.columns), f, indent=2)

    print(f"  Guardado: {CLEAN_CSV} ({len(df_clean)} filas)")
    print(f"  Métricas: {METRICS_CSV}")


def main() -> int:
    if RAW_CSV.exists():
        print(f"Usando dataset real: {RAW_CSV}")
        df = load_bioactivity(RAW_CSV)
    else:
        print(f"[WARN] {RAW_CSV} no existe — verificación con datos sintéticos.")
        df = _synthetic_bioactivity()
        RAW_CSV.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(RAW_CSV, index=False)

    run_pipeline(df)
    print("=== verify_flow_b OK ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
