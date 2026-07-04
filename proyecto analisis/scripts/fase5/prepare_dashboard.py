#!/usr/bin/env python
"""
Prepara artefactos del dashboard en outputs/dashboard/.

Genera JSON derivados (correlacion, eval modelos, defaults, indice XAI).
Opcionalmente empaqueta bundle para despliegue cloud (--bundle).

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

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, roc_auc_score, roc_curve
from sklearn.preprocessing import LabelEncoder

ROOT = Path(__file__).resolve().parents[2]  # proyecto analisis root
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.analisis_proyecto.chembl_preprocessing import (  # noqa: E402
    build_supervised_matrix,
    get_available_feature_cols,
    pchembl_imputation_report,
    train_test_split_by_group,
    train_test_split_rows,
)

from src.data.mida import MIDA_ACTIVE_INGREDIENTS  # noqa: E402

TASK_NAMES = [
    "NR-AR", "NR-AR-LBD", "NR-AhR", "NR-Aromatase",
    "NR-ER", "NR-ER-LBD", "NR-PPAR-gamma",
    "SR-ARE", "SR-AtAD5", "SR-HSE", "SR-MMP", "SR-p53",
]

ARTIFACTS_DIR = ROOT / "outputs" / "dashboard"
BUNDLE_DIR = ARTIFACTS_DIR / "bundle"
CHEMBL_CSV = ROOT / "data" / "processed" / "compounds_features.csv"
CHEMBL_MODELS = ROOT / "outputs" / "chembl" / "models"
XAI_SRC = ROOT / "outputs" / "xai" / "figures"

MIDA_SLUGS = {
    name.lower().replace(" ", "_").replace(",", "").replace("-", "_"): name
    for name in MIDA_ACTIVE_INGREDIENTS
}
MIDA_SLUGS.update({
    "chlorpyrifos": "Chlorpyrifos",
    "malathion": "Malathion",
    "atrazine": "Atrazine",
    "glyphosate": "Glyphosate",
    "cypermethrin": "Cypermethrin",
    "tebuconazole": "Tebuconazole",
    "paraquat": "Paraquat",
    "carbaryl": "Carbaryl",
    "chlorothalonil": "Chlorothalonil",
    "2_4_d": "2,4-D",
})


def _require(path: Path, hint: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"No existe: {path}\n  → {hint}")


def _build_correlation_json(df: pd.DataFrame, out_path: Path) -> None:
    cols = [c for c in get_available_feature_cols(df) if c in df.columns]
    cols = cols + [c for c in ("pchembl_value", "standard_value") if c in df.columns]
    corr = df[cols].corr(method="pearson")
    payload = {
        "columns": cols,
        "matrix": corr.round(4).values.tolist(),
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _build_model_eval_json(df: pd.DataFrame, out_path: Path) -> None:
    feature_cols = json.loads((CHEMBL_MODELS / "feature_cols.json").read_text(encoding="utf-8"))
    X, y, _ = build_supervised_matrix(
        df, target_col="activity_class", numeric_cols=feature_cols, include_assay_features=False
    )
    _, X_test, _, y_test = train_test_split_rows(
        X, y, test_size=0.2, random_state=42, stratify=True
    )

    rf_clf = joblib.load(CHEMBL_MODELS / "rf_classifier.pkl")
    svm_clf = joblib.load(CHEMBL_MODELS / "svm_classifier.pkl")
    rf_reg = joblib.load(CHEMBL_MODELS / "rf_regressor.pkl")
    svr_reg = joblib.load(CHEMBL_MODELS / "svr_regressor.pkl")

    le = LabelEncoder()
    le.fit(["Active", "Inactive"])
    y_test_bin = le.transform(y_test)

    classifiers = {"RandomForest": rf_clf, "SVM_RBF": svm_clf}
    clf_eval: dict[str, dict] = {}
    for name, model in classifiers.items():
        y_pred = model.predict(X_test)
        cm = confusion_matrix(y_test, y_pred, labels=["Active", "Inactive"])
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(X_test)[:, 1]
        else:
            proba = model.decision_function(X_test)
            proba = (proba - proba.min()) / (proba.max() - proba.min() + 1e-8)
        fpr, tpr, _ = roc_curve(y_test_bin, proba)
        auc = float(roc_auc_score(y_test_bin, proba))
        clf_eval[name] = {
            "confusion_matrix": cm.tolist(),
            "labels": ["Active", "Inactive"],
            "roc": {"fpr": fpr.tolist(), "tpr": tpr.tolist(), "auc": auc},
            "accuracy_test": float((y_pred == y_test).mean()),
        }

    Xr, yr, _ = build_supervised_matrix(
        df,
        target_col="pchembl_value",
        numeric_cols=feature_cols,
        include_assay_features=True,
        assay_top_n=15,
    )
    _, Xr_test, _, yr_test = train_test_split_rows(
        Xr, yr, test_size=0.2, random_state=42, stratify=False
    )
    regressors = {"RandomForest": rf_reg, "SVR_RBF": svr_reg}
    reg_eval: dict[str, dict] = {}
    for name, model in regressors.items():
        pred = model.predict(Xr_test)
        reg_eval[name] = {
            "y_true": yr_test.tolist(),
            "y_pred": pred.tolist(),
            "r2_test": float(1 - np.sum((yr_test - pred) ** 2) / np.sum((yr_test - yr_test.mean()) ** 2)),
        }

    payload = {
        "feature_cols": feature_cols,
        "classification": clf_eval,
        "regression": reg_eval,
        "split_notes": {
            "primary_metric_split": "compuesto",
            "row_split_warning": (
                "El split por filas infla accuracy porque el mismo compuesto "
                "aparece en train y test con descriptores idénticos."
            ),
            "compound_split_interpretation": (
                "El split por compuesto evalúa generalización a moléculas nuevas; "
                "es la métrica honesta para descriptores sin contexto de ensayo."
            ),
        },
    }

    # Métricas por compuesto (split honesto — AUDIT P2)
    Xc, yc, groups = build_supervised_matrix(
        df, target_col="activity_class", numeric_cols=feature_cols, include_assay_features=False
    )
    _, X_te_g, _, y_te_g = train_test_split_by_group(Xc, yc, groups, random_state=42)
    compound_eval: dict[str, dict] = {}
    for name, model in classifiers.items():
        y_pred = model.predict(X_te_g)
        compound_eval[name] = {"accuracy_test": float((y_pred == y_te_g).mean())}
    payload["classification_compound_split"] = compound_eval

    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _build_predictor_defaults(df: pd.DataFrame, out_path: Path) -> None:
    feature_cols = json.loads((CHEMBL_MODELS / "feature_cols.json").read_text(encoding="utf-8"))
    X, _, _ = build_supervised_matrix(
        df,
        target_col="pchembl_value",
        numeric_cols=feature_cols,
        include_assay_features=True,
        assay_top_n=15,
    )
    defaults: dict[str, float] = {}
    for col in X.columns:
        if col in feature_cols:
            defaults[col] = float(df[col].median())
        else:
            defaults[col] = float(X[col].mode().iloc[0]) if X[col].dtype != float else float(X[col].median())
    out_path.write_text(json.dumps(defaults, indent=2), encoding="utf-8")


def _copy_mida_xai_svgs(xai_dst: Path) -> list[str]:
    xai_dst.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    if not XAI_SRC.exists():
        return copied

    for svg in sorted(XAI_SRC.glob("*.svg")):
        stem = svg.stem.lower()
        if any(mida in stem for mida in MIDA_SLUGS):
            shutil.copy2(svg, xai_dst / svg.name)
            copied.append(svg.name)
    return copied


def _build_xai_index(xai_dir: Path, out_path: Path) -> None:
    index: dict[str, list] = {}
    if not xai_dir.exists():
        out_path.write_text("{}", encoding="utf-8")
        return

    for svg in sorted(xai_dir.glob("*.svg")):
        parts = svg.stem.rsplit("_", 2)
        if len(parts) < 3:
            continue
        compound_slug = parts[0]
        task = parts[1]
        method = parts[2]
        index.setdefault(compound_slug, []).append({
            "task": task,
            "method": method,
            "file": svg.name,
        })

    out_path.write_text(json.dumps(index, indent=2), encoding="utf-8")


def _build_model_comparison(out_path: Path) -> None:
    """Comparativa baselines vs GIN (AUDIT P9)."""
    models: list[dict] = []
    baseline_csv = ROOT / "outputs" / "results" / "baseline_results.csv"
    gin_csv = ROOT / "outputs" / "results" / "gin_results.csv"
    gin_cv_csv = ROOT / "outputs" / "results" / "gin_cv_summary.csv"

    if baseline_csv.is_file():
        bdf = pd.read_csv(baseline_csv)
        for _, row in bdf.iterrows():
            name = str(row.get("Modelo") or row.get("model") or "baseline")
            auc = row.get("Media AUC-ROC") or row.get("mean_auc")
            if pd.notna(auc):
                models.append({"name": name, "mean_auc": float(auc), "source": "baseline"})

    if gin_csv.is_file():
        gdf = pd.read_csv(gin_csv)
        if not gdf.empty:
            row = gdf.iloc[0]
            models.append({
                "name": "GIN",
                "mean_auc": float(row["mean_auc"]),
                "source": "gin_single_fold",
            })

    cv_note = None
    if gin_cv_csv.is_file():
        cvdf = pd.read_csv(gin_cv_csv)
        if not cvdf.empty and "mean_auc" in cvdf.columns:
            cv_note = {
                "mean_auc": float(cvdf["mean_auc"].mean()),
                "std_auc": float(cvdf["mean_auc"].std()),
                "n_folds": len(cvdf),
            }

    payload = {
        "models": models,
        "cv_summary": cv_note,
        "objective_auc": 0.82,
        "note": "Ejecute make train-gin-cv para intervalos de confianza.",
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _create_bundle() -> None:
    """Empaqueta artefactos minimos para despliegue cloud (Render)."""
    print("\n=== Bundle de despliegue (outputs/dashboard/bundle/) ===")
    if BUNDLE_DIR.exists():
        shutil.rmtree(BUNDLE_DIR)
    BUNDLE_DIR.mkdir(parents=True)

    copies = [
        (CHEMBL_CSV, "chembl_clean.csv"),
        (ROOT / "data" / "processed" / "panama_distritos_merged.geojson", "panama_distritos.geojson"),
        (ROOT / "outputs" / "reports" / "panama_pesticides_profile.csv", "panama_toxicity_profile.csv"),
        (ROOT / "outputs" / "chembl" / "results" / "metrics_summary.csv", "metrics_summary.csv"),
    ]
    for src, name in copies:
        if src.is_file():
            shutil.copy2(src, BUNDLE_DIR / name)
        else:
            print(f"  [skip] {name} — no existe {src}")

    models_dst = BUNDLE_DIR / "models"
    models_dst.mkdir(parents=True, exist_ok=True)
    if CHEMBL_MODELS.is_dir():
        for pkl in CHEMBL_MODELS.glob("*.pkl"):
            shutil.copy2(pkl, models_dst / pkl.name)
        for js in CHEMBL_MODELS.glob("*.json"):
            shutil.copy2(js, models_dst / js.name)

    xai_dst = BUNDLE_DIR / "xai"
    xai_copied = _copy_mida_xai_svgs(xai_dst)

    for name in (
        "correlation_pearson.json",
        "model_eval.json",
        "predictor_defaults.json",
        "xai_index.json",
        "manifest.json",
        "model_comparison.json",
        "pchembl_imputation.json",
    ):
        src = ARTIFACTS_DIR / name
        if src.is_file():
            shutil.copy2(src, BUNDLE_DIR / name)

    print(f"  Bundle listo: {BUNDLE_DIR}")
    print(f"  SVGs XAI en bundle: {len(xai_copied)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepara artefactos del dashboard Dash")
    parser.add_argument(
        "--bundle",
        action="store_true",
        help="Genera ademas outputs/dashboard/bundle/ para despliegue cloud",
    )
    args = parser.parse_args()

    print("=== Preparacion dashboard (Fase V) ===")
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    _require(CHEMBL_CSV, "make chembl-extract")
    _require(CHEMBL_MODELS / "rf_regressor.pkl", "entrenar modelos ChEMBL (Flujo B)")
    _require(
        ROOT / "outputs" / "reports" / "panama_pesticides_profile.csv",
        "make panama-predict",
    )

    df = pd.read_csv(CHEMBL_CSV)
    _build_correlation_json(df, ARTIFACTS_DIR / "correlation_pearson.json")
    _build_model_eval_json(df, ARTIFACTS_DIR / "model_eval.json")
    _build_predictor_defaults(df, ARTIFACTS_DIR / "predictor_defaults.json")
    _build_model_comparison(ARTIFACTS_DIR / "model_comparison.json")
    (ARTIFACTS_DIR / "pchembl_imputation.json").write_text(
        json.dumps(pchembl_imputation_report(df), indent=2), encoding="utf-8"
    )

    xai_artifacts = ARTIFACTS_DIR / "xai"
    xai_copied = _copy_mida_xai_svgs(xai_artifacts)
    _build_xai_index(xai_artifacts if xai_artifacts.exists() else XAI_SRC, ARTIFACTS_DIR / "xai_index.json")

    manifest = {
        "chembl_rows": len(df),
        "xai_svgs": len(xai_copied),
        "models_dir": str(CHEMBL_MODELS.relative_to(ROOT)),
        "tasks_tox21": TASK_NAMES,
        "sources": {
            "chembl": str(CHEMBL_CSV.relative_to(ROOT)),
            "toxicity": "outputs/reports/panama_pesticides_profile.csv",
            "xai": "outputs/xai/figures/",
            "geojson": "data/processed/panama_distritos_merged.geojson",
        },
    }
    (ARTIFACTS_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"Artefactos en: {ARTIFACTS_DIR}")
    print(f"Filas ChEMBL: {manifest['chembl_rows']}")
    print(f"SVGs XAI (copia MIDA): {manifest['xai_svgs']}")

    if args.bundle:
        _create_bundle()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
