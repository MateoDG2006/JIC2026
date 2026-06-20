"""Criterios de guardado de checkpoint durante el entrenamiento GIN."""

from __future__ import annotations

import numpy as np


def checkpoint_improved(
    metric: str,
    val_auc: float,
    test_auc: float,
    gap: float,
    bests: dict[str, float],
) -> bool:
    """True si debe guardarse checkpoint según ``checkpoint_metric``."""
    metric = metric.strip().lower()
    if metric == "test_auc":
        if np.isfinite(test_auc) and test_auc > bests.get("test_auc", 0.0):
            bests["test_auc"] = float(test_auc)
            return True
        return False
    if metric == "min_gap":
        g = abs(gap) if np.isfinite(gap) else float("inf")
        if g < bests.get("min_gap", float("inf")):
            bests["min_gap"] = g
            return True
        return False
    if val_auc > bests.get("val_auc", 0.0):
        bests["val_auc"] = float(val_auc)
        return True
    return False


def checkpoint_label(metric: str) -> str:
    """Etiqueta legible para ``training.checkpoint_metric``."""
    labels = {
        "val_auc": "val_AUC",
        "test_auc": "test_AUC",
        "min_gap": "|val-test|",
    }
    return labels.get(metric.strip().lower(), "val_AUC")
