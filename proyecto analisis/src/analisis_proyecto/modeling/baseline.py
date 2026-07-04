"""Baseline predictivo honesto (Fase 4 / P6)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import GroupKFold, KFold, cross_val_score

from src.analisis_proyecto.preprocessing.pipeline import FEATURE_COLS


def _bootstrap_ci(
    values: list[float] | np.ndarray,
    n_bootstrap: int = 2000,
    ci: float = 0.95,
    random_state: int = 42,
) -> tuple[float, float]:
    """IC bootstrap percentil sobre los R² por fold."""
    arr = np.asarray(values, dtype=float)
    if len(arr) == 0:
        return float("nan"), float("nan")
    if len(arr) == 1:
        v = float(arr[0])
        return v, v
    rng = np.random.default_rng(random_state)
    boots = [rng.choice(arr, size=len(arr), replace=True).mean() for _ in range(n_bootstrap)]
    alpha = (1 - ci) / 2
    return float(np.quantile(boots, alpha)), float(np.quantile(boots, 1 - alpha))


def assert_no_group_leakage(groups: np.ndarray, cv, X: np.ndarray, y: np.ndarray) -> None:
    """Verifica que ningún chembl_id cae en train y test del mismo fold."""
    groups = np.asarray(groups)
    for train_idx, test_idx in cv.split(X, y, groups=groups):
        train_g = set(groups[train_idx])
        test_g = set(groups[test_idx])
        overlap = train_g & test_g
        assert not overlap, f"GroupKFold leak: chembl_id compartidos train/test: {overlap}"


@dataclass
class BaselineMetrics:
    split: str
    n: int
    r2_cv_mean: float
    r2_cv_std: float
    r2_folds: list[float]
    r2_ci95_low: float
    r2_ci95_high: float

    def to_dict(self) -> dict:
        return {
            "split": self.split,
            "n": self.n,
            "r2_cv_mean": self.r2_cv_mean,
            "r2_cv_std": self.r2_cv_std,
            "r2_folds": "|".join(f"{v:.6f}" for v in self.r2_folds),
            "r2_ci95_low": self.r2_ci95_low,
            "r2_ci95_high": self.r2_ci95_high,
        }


def _metrics_from_cv(
    split: str,
    r2_folds: np.ndarray,
    n: int,
    random_state: int = 42,
) -> BaselineMetrics:
    r2_list = [float(v) for v in r2_folds]
    ci_low, ci_high = _bootstrap_ci(r2_list, random_state=random_state)
    return BaselineMetrics(
        split=split,
        n=n,
        r2_cv_mean=float(np.mean(r2_folds)),
        r2_cv_std=float(np.std(r2_folds)),
        r2_folds=r2_list,
        r2_ci95_low=ci_low,
        r2_ci95_high=ci_high,
    )


class RowLevelSplitContrast:
    """Mismo target (pchembl_value) y mismas filas; solo cambia el split.

    Aísla el efecto de la fuga por compuestos repetidos.
    """

    def __init__(self, n_estimators: int = 300, random_state: int = 42) -> None:
        self.n_estimators = n_estimators
        self.random_state = random_state

    def evaluate(self, activities: pd.DataFrame) -> list[BaselineMetrics]:
        df = activities.dropna(subset=["pchembl_value"] + FEATURE_COLS)
        X = df[FEATURE_COLS].values
        y = df["pchembl_value"].values
        groups = df["chembl_id"].values

        def _mk() -> RandomForestRegressor:
            return RandomForestRegressor(
                n_estimators=self.n_estimators, random_state=self.random_state
            )

        kfold = KFold(5, shuffle=True, random_state=self.random_state)
        r2_leak = cross_val_score(_mk(), X, y, cv=kfold, scoring="r2")

        gkf = GroupKFold(5)
        assert_no_group_leakage(groups, gkf, X, y)
        r2_grp = cross_val_score(_mk(), X, y, groups=groups, cv=gkf, scoring="r2")

        n = len(df)
        return [
            _metrics_from_cv("filas_KFold_CON_FUGA", r2_leak, n, self.random_state),
            _metrics_from_cv("filas_GroupKFold_HONESTO", r2_grp, n, self.random_state),
        ]


class CompoundLevelBaseline:
    """Vista complementaria a nivel compuesto — predice pchembl_median."""

    def __init__(self, n_estimators: int = 300, random_state: int = 42) -> None:
        self.n_estimators = n_estimators
        self.random_state = random_state

    def evaluate(self, compounds: pd.DataFrame) -> BaselineMetrics:
        df = compounds.dropna(subset=["pchembl_median"] + FEATURE_COLS)
        X = df[FEATURE_COLS].values
        y = df["pchembl_median"].values
        groups = df["chembl_id"].values

        gkf = GroupKFold(5)
        assert_no_group_leakage(groups, gkf, X, y)
        r2_cv = cross_val_score(
            RandomForestRegressor(
                n_estimators=self.n_estimators, random_state=self.random_state
            ),
            X,
            y,
            groups=groups,
            cv=gkf,
            scoring="r2",
        )
        return _metrics_from_cv("compuesto", r2_cv, len(df), self.random_state)


# Alias retrocompatible — usar RowLevelSplitContrast en su lugar.
RowLevelLeakyBaseline = RowLevelSplitContrast
