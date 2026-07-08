"""Modelo demostrativo para el predictor del dashboard.

Entrena un RandomForest sobre los compuestos con potencia (compounds_features)
usando los 8 descriptores. Se cachea en memoria. La predicción se acompaña
SIEMPRE de las métricas honestas (R² por compuesto negativo) para que el usuario
vea qué chance tiene de acertar — el modelo NO generaliza.
"""
from __future__ import annotations

import numpy as np

from src.analisis_proyecto.preprocessing.pipeline import FEATURE_COLS
from viz.services.dashboard.artifacts import load_compounds_potency

_MODEL = None


def _train():
    global _MODEL
    from sklearn.ensemble import RandomForestRegressor

    df = load_compounds_potency().dropna(subset=["pchembl_median_binding"] + list(FEATURE_COLS))
    X = df[FEATURE_COLS].astype(float).values
    y = df["pchembl_median_binding"].astype(float).values
    model = RandomForestRegressor(n_estimators=300, random_state=42).fit(X, y)
    ranges = {c: [float(df[c].min()), float(df[c].max()), float(df[c].median())] for c in FEATURE_COLS}
    _MODEL = {
        "model": model, "features": list(FEATURE_COLS),
        "y_mean": float(y.mean()), "y_std": float(y.std()), "n_train": int(len(df)),
        "ranges": ranges,
    }
    return _MODEL


def get_model():
    return _MODEL or _train()


def feature_info() -> dict:
    m = get_model()
    return {"features": m["features"], "ranges": m["ranges"], "n_train": m["n_train"],
            "y_mean": m["y_mean"], "y_std": m["y_std"]}


def predict(descriptors: dict) -> dict:
    m = get_model()
    x = np.array([[float(descriptors.get(c, m["ranges"][c][2]) or m["ranges"][c][2]) for c in m["features"]]])
    pred = float(m["model"].predict(x)[0])
    # margen ~ desviación de los árboles (incertidumbre del ensemble)
    per_tree = np.array([t.predict(x)[0] for t in m["model"].estimators_])
    return {
        "prediction": round(pred, 3),
        "tree_std": round(float(per_tree.std()), 3),
        "train_mean": round(m["y_mean"], 3),
        "activo": pred >= 6.0,
    }
