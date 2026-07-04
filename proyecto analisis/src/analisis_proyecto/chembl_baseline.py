"""Baseline predictivo honesto (Anexo / P6). Demuestra el límite de los descriptores clásicos."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import KFold, cross_val_score, train_test_split

FEATURE_COLS = [
    "mw_freebase",
    "alogp",
    "psa",
    "hba",
    "hbd",
    "aromatic_rings",
    "rtb",
    "num_ro5_violations",
]


def honest_baseline_compound_level(compounds: pd.DataFrame) -> dict:
    """
    Split POR COMPUESTO (honesto): compounds_features tiene 1 fila/compuesto, así que
    un split normal ya es un split por compuesto. Predice pchembl_median.
    """
    X = compounds[FEATURE_COLS].values
    y = compounds["pchembl_median"].values
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
    m = RandomForestRegressor(n_estimators=300, random_state=42).fit(Xtr, ytr)
    r2_cv = cross_val_score(
        RandomForestRegressor(n_estimators=300, random_state=42),
        X,
        y,
        cv=KFold(5, shuffle=True, random_state=42),
        scoring="r2",
    )
    return {
        "split": "compuesto",
        "r2_test": float(r2_score(yte, m.predict(Xte))),
        "mae_test": float(mean_absolute_error(yte, m.predict(Xte))),
        "r2_cv_mean": float(np.mean(r2_cv)),
        "r2_cv_std": float(np.std(r2_cv)),
        "n": len(compounds),
    }


def leaky_baseline_row_level(activities: pd.DataFrame) -> dict:
    """
    Split POR FILAS (con FUGA, solo para contraste didáctico): mismas moléculas en train y test.
    Debe salir R² artificialmente alto — es exactamente lo que NO hay que reportar como válido.
    """
    df = activities.dropna(subset=["pchembl_value"] + FEATURE_COLS)
    X, y = df[FEATURE_COLS].values, df["pchembl_value"].values
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
    m = RandomForestRegressor(n_estimators=300, random_state=42).fit(Xtr, ytr)
    return {
        "split": "filas_CON_FUGA",
        "r2_test": float(r2_score(yte, m.predict(Xte))),
        "n": len(df),
    }
